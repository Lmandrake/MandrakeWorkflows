import AppKit
import JavaScriptCore
import Darwin

/// The parent pid; nil when the process is gone. A parent of 1 (launchd) is returned as 1: an orphaned iTermServer
/// (ppid 1) still owns its shells (review R1_MACOS #2), so the walk must see it rather than stop below it.
func parentPID(_ pid: pid_t) -> pid_t? {
    var info = kinfo_proc()
    var size = MemoryLayout<kinfo_proc>.stride
    var mib: [Int32] = [CTL_KERN, KERN_PROC, KERN_PROC_PID, pid]
    guard pid > 1, sysctl(&mib, 4, &info, &size, nil, 0) == 0, size > 0, info.kp_proc.p_pid == pid else { return nil }
    return info.kp_eproc.e_ppid
}

/// A process's short name (proc_name), "" if gone.
func procName(_ pid: pid_t) -> String {
    var buf = [CChar](repeating: 0, count: 256)
    return proc_name(pid, &buf, UInt32(buf.count)) > 0 ? String(cString: buf) : ""
}

/// The pid chain from a process up to (not including) launchd: [pid, parent, grandparent, ...], at most 40.
func ancestry(_ pid: pid_t) -> [pid_t] {
    var out: [pid_t] = [], p: pid_t? = pid
    while let cur = p, cur > 1, out.count < 40, !out.contains(cur) { out.append(cur); p = parentPID(cur) }
    return out
}

/// Which terminal a session's ancestry names, by process name, when no GUI app is an ancestor (review R1_MACOS #2):
/// an iTermServer-* process is iTerm2's session server, which outlives (and is orphaned from) the iTerm2 that started it.
func terminalByAncestry(_ names: [String]) -> String? {
    if names.contains(where: { $0.hasPrefix("iTermServer") }) { return "com.googlecode.iterm2" }
    return nil
}

/// A tmux pane's shell: its tty is tmux's pane pty, which no iTerm2 or Terminal session owns (review R1_MACOS #17).
func underTmux(_ names: [String]) -> Bool { names.contains { $0 == "tmux" || $0.hasPrefix("tmux:") } }

private var loggedNoOwner = Set<pid_t>()
/// The GUI app that owns a process: walk parents until one is an NSRunningApplication with a UI; failing that, an
/// iTermServer ancestor means iTerm2. Logged once per pid when nothing owns it.
func owningApp(_ pid: pid_t) -> NSRunningApplication? {
    let chain = ancestry(pid)
    for cur in chain {
        if let a = NSRunningApplication(processIdentifier: cur), a.activationPolicy == .regular { return a }
    }
    if let b = terminalByAncestry(chain.map(procName)),
       let a = NSRunningApplication.runningApplications(withBundleIdentifier: b).first { return a }
    if !loggedNoOwner.contains(pid) { loggedNoOwner.insert(pid); log("no owning app for pid \(pid) (chain \(chain))") }
    return nil
}

/// The session's tty, from the kernel (Decide.swift processTTY): no `ps` subprocess.
func ttyOf(_ pid: pid_t) -> String? { processTTY(pid) }

func appleQuoted(_ s: String) -> String {
    "\"" + s.replacingOccurrences(of: "\\", with: "\\\\").replacingOccurrences(of: "\"", with: "\\\"") + "\""
}

/// AppleScript through /usr/bin/osascript, so it can run off the main thread (NSAppleScript is main-thread only). The
/// first-run Automation prompt then blocks only the click queue, not the stage or the cursor poll (review R1 #8c).
func runOsascript(_ src: String) -> String? {
    let p = Process(); p.executableURL = URL(fileURLWithPath: "/usr/bin/osascript"); p.arguments = ["-e", src]
    let out = Pipe(), err = Pipe(); p.standardOutput = out; p.standardError = err
    do { try p.run() } catch { log("osascript: \(error.localizedDescription)"); return nil }
    let o = out.fileHandleForReading.readDataToEndOfFile(), e = err.fileHandleForReading.readDataToEndOfFile()
    p.waitUntilExit()
    if let es = String(data: e, encoding: .utf8), !es.isEmpty { log("AppleScript: \(es.trimmingCharacters(in: .whitespacesAndNewlines))") }
    return String(data: o, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines)
}
private let clickQueue = DispatchQueue(label: "sprites.click", qos: .userInitiated)

/// Bring a Claude session's terminal tab forward (switching Space). iTerm2 and Terminal by tty, off the main thread;
/// no tty match does nothing but log (review R1 #8a: never raise every window). Any other owner app is activated.
/// `startedAt` is the session id's start time: re-checked just before acting, so a reused pid is never focused.
/// The AppleScript that brings the iTerm2 session on this tty forward. A minimised window is un-minimised first
/// (`select w` alone leaves it in the Dock; review R1_MACOS #17). The window id is read BEFORE `select`: `w` is an index
/// reference, and selecting reorders the windows, so `id of w` afterwards names another window (measured 2026-11-04).
///
/// 🔴 EVERY REFERENCE IS AN INDEX REFERENCE, NOT JUST `w` (measured 2026-11-05, from the owner's live log):
/// `sprites: AppleScript: 317:323: execution error: iTerm got an error: Can't get item 2 of every tab of item 3 of
/// every window. Invalid index. (-1719)` — offsets 317:323 are exactly `tell t to select` on line 9, the statement
/// AFTER `select w`. `t` and `s` are `item N of every tab of item M of every window`: once `select w` has reordered
/// the windows, item M is a DIFFERENT window and item N may not exist, so the whole script aborts and the click
/// focuses nothing. Same tab in the same window succeeded moments later in that log, so it was never a mis-indexed
/// tab list — it was a reference invalidated mid-script by our own side effect.
///
/// The fix resolves EVERYTHING FIRST, by id, and only then mutates: tab index and window id are read while the
/// references are still valid, the window is selected BY ID, and the tab BY INDEX within it. A session whose tty has
/// no tab still returns "none" and the caller logs and does nothing (`activateAllAfterScript` is false by design —
/// never raise every window).
func itermFocusScript(tty: String) -> String {
    """
    tell application id "com.googlecode.iterm2"
      set wid to missing value
      set ti to 0
      set si to 0
      repeat with w in windows
        set ti to 0
        repeat with t in tabs of w
          set ti to ti + 1
          set si to 0
          repeat with s in sessions of t
            set si to si + 1
            if tty of s is \(appleQuoted(tty)) then
              set wid to id of w
              exit repeat
            end if
          end repeat
          if wid is not missing value then exit repeat
        end repeat
        if wid is not missing value then exit repeat
      end repeat
      if wid is missing value then return "none"
      set tw to first window whose id is wid
      if miniaturized of tw then set miniaturized of tw to false
      select tw
      set tt to item ti of tabs of (first window whose id is wid)
      tell tt to select
      tell (item si of sessions of tt) to select
      activate
      return "ok " & wid
    end tell
    """
}

/// Activate a GUI app from a never-active accessory app. macOS 14+ cooperative activation can refuse a plain
/// `activate()`; `activate(from: .current)` yields our activation to it. Refused: `open -b <bundle>` (review R1_MACOS #6).
func activationFallback(activated: Bool, bundle: String) -> [String]? {
    activated || bundle.isEmpty ? nil : ["/usr/bin/open", "-b", bundle]
}
func activateApp(_ app: NSRunningApplication) {
    let ok: Bool
    if #available(macOS 14.0, *) { ok = app.activate(from: NSRunningApplication.current, options: []) }
    else { ok = app.activate(options: []) }
    if let cmd = activationFallback(activated: ok, bundle: app.bundleIdentifier ?? "") {
        log("click: activate refused for \(app.bundleIdentifier ?? "?"); \(cmd.joined(separator: " "))")
        let p = Process(); p.executableURL = URL(fileURLWithPath: cmd[0]); p.arguments = Array(cmd.dropFirst())
        try? p.run()
    }
}

func activateSession(pid: pid_t, startedAt: Int) {
    guard let app = owningApp(pid) else { log("click: no owning app for pid \(pid)"); return }
    let bundle = app.bundleIdentifier ?? ""
    clickQueue.async {
        guard let st = processStart(pid), abs(st - startedAt) <= 1 else { log("click: pid \(pid) is no longer the session"); return }
        let tty = ttyOf(pid)
        let r: String?
        switch (bundle, tty) {
        case ("com.googlecode.iterm2", let t?):
            r = runOsascript(itermFocusScript(tty: t))
        case ("com.apple.Terminal", let t?):
            r = runOsascript("""
        tell application id "com.apple.Terminal"
          repeat with w in windows
            repeat with t in tabs of w
              if tty of t is \(appleQuoted(t)) then
                set wid to id of w
                set selected of t to true
                set index of w to 1
                activate
                return "ok " & wid
              end if
            end repeat
          end repeat
          return "none"
        end tell
        """)
        case (_, nil) where bundle == "com.googlecode.iterm2" || bundle == "com.apple.Terminal":
            log("click: pid \(pid) has no tty; not focusing anything"); return
        default:
            DispatchQueue.main.async { activateApp(app) }; return
        }
        if let wid = focusedWindow(r) {
            let how = switchToWindowSpace(wid)
            if how.hasPrefix("switched") { usleep(450_000); DispatchQueue.main.async { activateApp(app) } }
            log("click: focused pid \(pid) on tty \(tty ?? "?") (window \(wid); \(how))")
            return
        }
        do {
            if underTmux(ancestry(pid).map(procName)) { log("click: pid \(pid) is a tmux session: not focusable (its tty \(tty ?? "?") is a tmux pane)"); return }
            if activateAllAfterScript(r) { DispatchQueue.main.async { app.activate(options: [.activateAllWindows]) } }
            log("click: no \(bundle) tab on \(tty ?? "?") for pid \(pid) (\(r ?? "error")); not focusing anything")
        }
    }
}

// MARK: Space switch (owner, 2026-11-04; Decide.swift spaceSwitchPlan)
// Measured 2026-11-04, macOS 26.7.1, swoosh 0: `activate`, `open -b`, AXMain+AXRaise and a Dock-icon AXPress all leave
// the Space alone or go to the app's last Space. Posting Mission Control's "Switch to Desktop N" key goes to the window.
// The space lookup is the READ-ONLY SkyLight pair Machinist's tools/windowspaces.swift uses; nothing is written to it.
private typealias SLSMainConn = @convention(c) () -> Int32
private typealias SLSSpacesForWindows = @convention(c) (Int32, Int32, CFArray) -> Unmanaged<CFArray>?
private typealias SLSManagedSpaces = @convention(c) (Int32) -> Unmanaged<CFArray>?
private let skyLight = dlopen("/System/Library/PrivateFrameworks/SkyLight.framework/SkyLight", RTLD_LAZY)
private func skySym<T>(_ n: String, _ t: T.Type) -> T? { dlsym(skyLight, n).map { unsafeBitCast($0, to: t) } }

/// Move to window `wid`'s Space if it is not the current one. Returns what it did, for the click log line.
func switchToWindowSpace(_ wid: Int) -> String {
    guard wid > 0 else { return "no window id" }
    guard let conn = skySym("SLSMainConnectionID", SLSMainConn.self),
          let forWin = skySym("SLSCopySpacesForWindows", SLSSpacesForWindows.self),
          let managed = skySym("SLSCopyManagedDisplaySpaces", SLSManagedSpaces.self) else { return "no SkyLight space symbols" }
    let cid = conn()
    let displays = (managed(cid)?.takeRetainedValue() as? [[String: Any]]) ?? []
    let spaces = (forWin(cid, 7, [wid] as CFArray)?.takeRetainedValue() as? [Int]) ?? []
    let hk = (UserDefaults(suiteName: "com.apple.symbolichotkeys")?.dictionary(forKey: "AppleSymbolicHotKeys")) ?? [:]
    switch spaceSwitchPlan(displays: displays, windowSpaces: spaces, hotkeys: hk) {
    case .stay(let why): return why
    case .unreachable(let why): log("click: cannot switch to window \(wid)'s space: \(why)"); return why
    case .desktop(let n, let key, let flags):
        guard CGPreflightPostEventAccess() else {
            _ = CGRequestPostEventAccess()
            log("click: Sprites needs Accessibility to switch to Desktop \(n) (System Settings > Privacy & Security > Accessibility)")
            return "no Accessibility: stayed"
        }
        let src = CGEventSource(stateID: .hidSystemState)
        for down in [true, false] {
            guard let e = CGEvent(keyboardEventSource: src, virtualKey: CGKeyCode(key), keyDown: down) else { continue }
            e.flags = CGEventFlags(rawValue: flags & 0xFFFF_0000)
            e.post(tap: .cghidEventTap)
        }
        return "switched to Desktop \(n)"
    }
}

/// The project table (review R1 #2): app/projects.js `SpritesProjects.build` run in JavaScriptCore over Lodestar's
/// registry and machines.md and Waypoint's waypoints.md and launches.md, so the host, the stage and Settings share ONE
/// mapping keyed by Augur's project_key. Rebuilt when any of the five files changes (a stat per call).
final class ProjectTable {
    static let shared = ProjectTable()
    private var sig = "", table: [[String: Any]] = [], json = "[]"
    private let env = ProcessInfo.processInfo.environment
    private var lodestar: String { let v = env["AUGUR_LODESTAR"] ?? ""; return v.isEmpty ? Paths.home + "/dev/Lodestar" : v }
    private var files: [String] {
        [lodestar + "/sync/registry.md", lodestar + "/machines.md", Paths.home + "/.config/waypoint/waypoints.md", Paths.launches,
         Paths.sprites.appendingPathComponent("app/projects.js").path, Paths.projects]
    }
    /// (table, its JSON) for this machine; [] when the files or the module are missing.
    func current() -> ([[String: Any]], String) {
        let s = files.map { f -> String in
            let a = try? FileManager.default.attributesOfItem(atPath: f)
            return "\((a?[.modificationDate] as? Date)?.timeIntervalSince1970 ?? 0):\(a?[.size] ?? 0)"
        }.joined(separator: "|")
        if s == sig { return (table, json) }
        sig = s
        let rd = { (f: String) in (try? String(contentsOfFile: f, encoding: .utf8)) ?? "" }
        // POSIX gethostname, as Augur and waypoint read it (socket.gethostname). Not ProcessInfo.hostName: on some networks that
        // is a reverse-DNS name, which matches no Machine column.
        var hb = [CChar](repeating: 0, count: 256); gethostname(&hb, 255)
        let host = String(cString: hb).lowercased()
        let wm = (env["WAYPOINT_MACHINE"] ?? "").isEmpty ? (host.hasSuffix(".local") ? String(host.dropLast(6)) : host) : env["WAYPOINT_MACHINE"]!.lowercased()
        let lm = (env["LODESTAR_MACHINE"] ?? "").isEmpty ? String(host.split(separator: ".").first ?? "") : env["LODESTAR_MACHINE"]!.lowercased()
        let args: [String: Any] = ["registry": rd(files[0]), "machines": rd(files[1]), "waypoints": rd(files[2]), "launches": rd(files[3]),
                                   "home": Paths.home, "machine": wm, "lodestarMachine": lm,
                                   // the local projects file: focus and colour for what Waypoint cannot hold (owner, 2026-11-08)
                                   "local": loadLocalProjects(), "hasWaypoint": waypointCLIPath() != nil]
        guard let ctx = JSContext() else { return (table, json) }
        ctx.exceptionHandler = { _, e in log("projects.js: \(e?.toString() ?? "?")") }
        ctx.evaluateScript(rd(files[4]))
        let out = ctx.evaluateScript("JSON.stringify(SpritesProjects.build(\(jsonString(args))))")?.toString() ?? "[]"
        if let d = out.data(using: .utf8), let t = try? JSONSerialization.jsonObject(with: d) as? [[String: Any]] {
            table = t; json = out
            log("project table: \(t.count) entries (\(t.filter { $0["key"] is String }.count) keyed) for \(wm)")
        } else { log("project table: projects.js returned \(out.prefix(80))") }
        return (table, json)
    }
}

/// Ghost click (owner, 2026-11-01 05:47: "If they're a ghost, it should open one."): open a new iTerm2 window for the
/// project_key the stage sent, as Decide.swift ghostPlan says: `launch <alias>` (Waypoint) or `claude` in the registry's
/// directory for that key. Nothing else is ever run (R1 #17). One window per project per 3 s, stamped after the launch.
/// One window per project per 3 s (review R1_MACOS #13): stamped BEFORE the launch is dispatched, so clicks queued while
/// an Automation prompt is up are debounced; cleared when the launch failed, so the next click can retry.
final class GhostGate {
    private var last: [String: Date] = [:]
    func begin(_ key: String, now: Date) -> Bool {
        if ghostDebounced(last: last[key], now: now) { return false }
        last[key] = now; return true
    }
    func failed(_ key: String) { last[key] = nil }
}
private let ghostGate = GhostGate()
/// Runs the launch through osascript on the click queue (never NSAppleScript on main: the Automation prompt and iTerm2's
/// window creation froze the stage and the cursor poll). Call on main.
func openGhost(key: String) {
    let cmd: String
    switch ghostPlan(key: key, table: ProjectTable.shared.current().0) {
    case .launch(let alias): cmd = "launch " + alias
    case .claude(let dir):
        guard FileManager.default.fileExists(atPath: dir) else { log("ghost click \(key): no \(dir)"); return }
        cmd = "cd " + "'" + dir.replacingOccurrences(of: "'", with: "'\\''") + "'" + " && claude"
    case .refuse(let why): log("ghost click \(key): \(why)"); return
    }
    guard ghostGate.begin(key, now: Date()) else { log("ghost click \(key): debounced"); return }
    log("ghost click \(key): \(cmd)")
    let src = ghostScript(cmd)
    clickQueue.async {
        if runOsascript(src) != "ok" { DispatchQueue.main.async { ghostGate.failed(key) } }
    }
}
func ghostScript(_ cmd: String) -> String {
    """
    tell application id "com.googlecode.iterm2"
      activate
      set w to (create window with default profile)
      tell current session of w to write text \(appleQuoted(cmd))
      return "ok"
    end tell
    """
}

// MARK: followOwnWindow (review R1_SPEC S7)

/// Is Sprites already allowed to send Apple events to this app? Never prompts (askUserIfNeeded false), so a background
/// poll never raises an Automation prompt; nil = the app is not running or the answer is unknown.
func automationGranted(bundle: String) -> Bool? {
    var addr = AEAddressDesc()
    let id = Array(bundle.utf8)
    guard AECreateDesc(typeApplicationBundleID, id, id.count, &addr) == noErr else { return nil }
    defer { AEDisposeDesc(&addr) }
    let st = AEDeterminePermissionToAutomateTarget(&addr, typeWildCard, typeWildCard, false)
    if st == noErr { return true }
    if st == OSStatus(errAEEventNotPermitted) { return false }
    return nil
}

/// iTerm2's "tty<TAB>window id" lines (one per session) -> tty -> window id. iTerm2's AppleScript window id is the
/// window's CGWindowNumber (measured 2026-11-01: AppleScript ids 9360, 3854, ... match kCGWindowNumber).
func parseTTYWindows(_ text: String) -> [String: Int] {
    var out: [String: Int] = [:]
    for line in text.split(whereSeparator: { $0 == "\n" || $0 == "\r" }) {
        let f = line.split(separator: "\t")
        if f.count == 2, f[0].hasPrefix("/dev/"), let n = Int(f[1].trimmingCharacters(in: .whitespaces)) { out[String(f[0])] = n }
    }
    return out
}
/// Session pid -> its window number, from each session's tty. Several sessions in one window (tabs): the lowest pid,
/// so the choice is stable.
func sessionWindows(ttyOf: [pid_t: String], ttyWindow: [String: Int]) -> [Int: pid_t] {
    var out: [Int: pid_t] = [:]
    for (p, t) in ttyOf { if let w = ttyWindow[t] { out[w] = min(out[w] ?? p, p) } }
    return out
}
let itermTTYScript = """
tell application id "com.googlecode.iterm2"
  set out to ""
  repeat with w in windows
    set wid to id of w
    repeat with t in tabs of w
      repeat with s in sessions of t
        set out to out & (tty of s) & tab & wid & linefeed
      end repeat
    end repeat
  end repeat
  return out
end tell
"""
/// Cached tty -> iTerm2 window, refreshed off main at most every `every` seconds and only when Automation is granted.
final class TTYWindowCache {
    private(set) var map: [String: Int] = [:]
    private var lastT = -1e9, busy = false
    func refresh(now: Double, every: Double = 10, force: Bool = false) {
        guard !busy, force || now - lastT >= every else { return }
        guard !NSRunningApplication.runningApplications(withBundleIdentifier: "com.googlecode.iterm2").isEmpty,
              automationGranted(bundle: "com.googlecode.iterm2") == true else { return }
        busy = true; lastT = now
        clickQueue.async { [weak self] in
            let m = parseTTYWindows(runOsascript(itermTTYScript) ?? "")
            DispatchQueue.main.async { self?.map = m; self?.busy = false }
        }
    }
}
