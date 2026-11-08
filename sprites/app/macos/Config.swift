import Foundation

/// Where everything lives. The sprites/ folder: $SPRITES_HOME, else the bundle's SpritesHome key
/// (stamped by `make app`), else ~/dev/MandrakeWorkflows/sprites. Missing = fail loudly by name.
enum Paths {
    static let home = NSHomeDirectory()

    static let sprites: URL = {
        let env = ProcessInfo.processInfo.environment["SPRITES_HOME"] ?? ""
        let plist = (Bundle.main.object(forInfoDictionaryKey: "SpritesHome") as? String) ?? ""
        let (path, source): (String, String) =
            !env.isEmpty ? (env, "SPRITES_HOME") :
            !plist.isEmpty ? (plist, "Info.plist SpritesHome") :
            (home + "/dev/MandrakeWorkflows/sprites", "default ~/dev/MandrakeWorkflows/sprites")
        var dir: ObjCBool = false
        guard FileManager.default.fileExists(atPath: path, isDirectory: &dir), dir.boolValue else {
            fail("sprites folder not found: \(path) (from \(source)); set SPRITES_HOME")
        }
        return URL(fileURLWithPath: path, isDirectory: true)
    }()

    static var stage: URL { sprites.appendingPathComponent("app/stage.html") }
    static var settings: URL { sprites.appendingPathComponent("app/settings.html") }

    /// The one input: $SPRITES_STATE (demo feed), else $AUGUR_SNAPSHOT, else UserDefaults
    /// "augurSnapshot", else the Augur default.
    static let state: String = {
        let env = ProcessInfo.processInfo.environment
        for k in ["SPRITES_STATE", "AUGUR_SNAPSHOT"] { if let v = env[k], !v.isEmpty { return v } }
        let ud = UserDefaults.standard.string(forKey: "augurSnapshot") ?? ""
        return ud.isEmpty ? home + "/agent-storage/augur/live/snapshot.json" : ud
    }()
    /// $SPRITES_CAST (tests: a cast that leaves the owner's untouched), else the saved cast.
    static let cast: String = { let v = ProcessInfo.processInfo.environment["SPRITES_CAST"] ?? ""; return v.isEmpty ? home + "/agent-storage/sprites/config/cast.json" : v }()
    static let behaviors = home + "/agent-storage/sprites/config/behaviors.json"
    /// Waypoint's tables: $WAYPOINT_DATA if set (as the waypoint CLI reads it), else ~/.config/waypoint.
    static var launches: String { waypointData + "/launches.md" }
    static var waypoints: String { waypointData + "/waypoints.md" }
    /// The waypoint CLI beside its data (`waypoint install` symlinks it there), else the checkout's.
    static var waypointCLI: [String] { [waypointData + "/waypoint", home + "/dev/MandrakeWorkflows/tools/waypoint/waypoint"] }
    /// Per-project colour and focus WITHOUT Waypoint (owner, 2026-11-05). Beside cast.json and
    /// behaviors.json, the app's other preferences — not a third location. With Waypoint these two
    /// settings live in launches.md instead and this file is never written.
    /// $SPRITES_PROJECTS overrides it, as $SPRITES_CAST does for the cast (tests).
    static let projects: String = { let v = ProcessInfo.processInfo.environment["SPRITES_PROJECTS"] ?? ""
        return v.isEmpty ? home + "/agent-storage/sprites/config/projects.json" : v }()
    static var waypointData: String { ProcessInfo.processInfo.environment["WAYPOINT_DATA"].flatMap { $0.isEmpty ? nil : $0 }
        ?? (home + "/.config/waypoint") }
}

func fail(_ msg: String) -> Never {
    FileHandle.standardError.write("sprites: FATAL: \(msg)\n".data(using: .utf8)!)
    exit(2)
}

func log(_ msg: String) {
    let t = debugClicks ? String(format: "[%.3f] ", CFAbsoluteTimeGetCurrent()) : ""
    FileHandle.standardError.write("sprites: \(t)\(msg)\n".data(using: .utf8)!)
}

/// `SPRITES_DEBUG_CLICKS=1`: log where every sprite is, when the panel arms and disarms its mouse capture, and what a
/// click decided — with a timestamp on every line. The reason this exists: the click path failed SILENTLY for weeks
/// (CLICK-1, CLICK-2, 2026-11-05) because nothing was logged until a click had already been accepted, so a click lost
/// before that point looked identical to no click at all. Diagnosing a dead click starts here.
let debugClicks = ProcessInfo.processInfo.environment["SPRITES_DEBUG_CLICKS"] == "1"

/// Polls a file's mtime; calls back with its bytes when it changes, nil once when it disappears.
final class FileWatch {
    private let path: String
    private var last: Date? = nil
    private var present = false
    private var timer: Timer?
    let onChange: (Data?) -> Void

    init(_ path: String, every: TimeInterval = 1.0, onChange: @escaping (Data?) -> Void) {
        self.path = path; self.onChange = onChange
        timer = Timer.scheduledTimer(withTimeInterval: every, repeats: true) { [weak self] _ in self?.tick() }
        tick()
    }

    func tick() {
        let attrs = try? FileManager.default.attributesOfItem(atPath: path)
        guard let m = attrs?[.modificationDate] as? Date else {
            if present { present = false; last = nil; onChange(nil) }
            return
        }
        if m == last { return }
        guard let d = FileManager.default.contents(atPath: path),
              (try? JSONSerialization.jsonObject(with: d)) != nil else { return }   // mid-write; retry next tick
        last = m; present = true
        onChange(d)
    }
}

/// Atomic JSON write (temp + rename).
func writeAtomically(_ data: Data, to path: String) throws {
    let url = URL(fileURLWithPath: path)
    try FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
    try data.write(to: url, options: .atomic)
}

/// Waypoint focus projects: rows of launches.md with Focus = yes; hex from `]10;#RRGGBB`.
/// Returns nil when the file is absent (no Waypoint).
func waypointProjects() -> [[String: String]]? {
    guard let text = try? String(contentsOfFile: Paths.launches, encoding: .utf8) else { return nil }
    var cols: [String] = []
    var out: [[String: String]] = []
    var seen = Set<String>()
    let colour = try! NSRegularExpression(pattern: "\\]10;#([0-9A-Fa-f]{6})")
    for raw in text.split(separator: "\n") {
        let line = raw.trimmingCharacters(in: .whitespaces)
        guard line.hasPrefix("|") else { continue }
        let cells = line.dropFirst().split(separator: "|", omittingEmptySubsequences: false)
            .map { $0.trimmingCharacters(in: .whitespaces) }
        if cols.isEmpty { if cells.contains("Name") && cells.contains("Focus") { cols = cells }; continue }
        if cells.first?.hasPrefix("---") == true || cells.first?.hasPrefix(":--") == true { continue }
        func cell(_ n: String) -> String { cols.firstIndex(of: n).flatMap { $0 < cells.count ? cells[$0] : nil } ?? "" }
        guard cell("Focus").lowercased() == "yes" else { continue }
        let name = cell("Name")
        if name.isEmpty || seen.contains(name) { continue }
        seen.insert(name)
        var row = ["name": name, "hex": "#8899AA"]   // settings.js drops rows without a hex
        let cmd = cell("Command")
        if let m = colour.firstMatch(in: cmd, range: NSRange(cmd.startIndex..., in: cmd)),
           let r = Range(m.range(at: 1), in: cmd) { row["hex"] = "#" + cmd[r].uppercased() }
        out.append(row)
    }
    return out
}

// MARK: Waypoint presence, and writing a project's colour / focus back (owner, 2026-11-05)

/// Waypoint is PRESENT when both halves resolve: an executable CLI, and a launches.md that parses
/// into at least one launch row. A path string that merely exists is not enough — the no-Waypoint
/// view is what the owner sees when either half is missing, the same switch `nowp=1` drives.
/// Returns the CLI path when present.
func waypointCLIPath() -> String? {
    let fm = FileManager.default
    // At least one launch ROW, not one focus row: Waypoint with nothing focused yet is still installed,
    // and that is exactly the state the focus toggle exists to change.
    guard launchRowCount() > 0 else { return nil }
    for p in Paths.waypointCLI where fm.isExecutableFile(atPath: p) { return p }
    return nil
}

/// How many launch rows launches.md actually parses into (0 when it is missing or has no table).
func launchRowCount() -> Int {
    guard let text = try? String(contentsOfFile: Paths.launches, encoding: .utf8) else { return 0 }
    var seenHeader = false, n = 0
    for raw in text.split(separator: "\n", omittingEmptySubsequences: false) {
        let line = raw.trimmingCharacters(in: .whitespaces)
        guard line.hasPrefix("|") else { continue }
        let cells = line.dropFirst().split(separator: "|", omittingEmptySubsequences: false)
            .map { $0.trimmingCharacters(in: .whitespaces) }
        if !seenHeader { if cells.contains("Name") && cells.contains("Command") { seenHeader = true }; continue }
        if cells.first?.hasPrefix("---") == true || cells.first?.hasPrefix(":--") == true { continue }
        if let first = cells.first, !first.isEmpty { n += 1 }
    }
    return n
}

/// Run `waypoint <args>`, inheriting $WAYPOINT_DATA. Returns nil on success, else a message for the UI.
/// Synchronous and short (the CLI rewrites one markdown table); called off the main thread.
func runWaypoint(_ args: [String]) -> String? {
    guard let cli = waypointCLIPath() else { return "Waypoint is not installed" }
    let p = Process()
    p.executableURL = URL(fileURLWithPath: cli)
    p.arguments = args
    let out = Pipe(), errp = Pipe()
    p.standardOutput = out; p.standardError = errp
    do { try p.run() } catch { return error.localizedDescription }
    let o = out.fileHandleForReading.readDataToEndOfFile(), e = errp.fileHandleForReading.readDataToEndOfFile()
    p.waitUntilExit()
    if p.terminationStatus == 0 { return nil }
    let msg = (String(data: e, encoding: .utf8) ?? "") + (String(data: o, encoding: .utf8) ?? "")
    let line = msg.split(separator: "\n").last.map(String.init) ?? "waypoint exited \(p.terminationStatus)"
    log("waypoint \(args.joined(separator: " ")): \(line)")
    return line
}

/// The local store used ONLY when Waypoint is absent: {"projects": {"<key>": {"hex", "focus"}}}.
/// Beside cast.json and behaviors.json (Paths.projects), because these are the owner's settings for
/// the same projects those files describe, not agent scratch.
func loadLocalProjects() -> [String: [String: Any]] {
    guard let d = FileManager.default.contents(atPath: Paths.projects),
          let o = try? JSONSerialization.jsonObject(with: d) as? [String: Any],
          let p = o["projects"] as? [String: [String: Any]] else { return [:] }
    return p
}

/// Merge one project's `hex` / `focus` into the local store. Returns nil on success, else a message.
func saveLocalProject(key: String, hex: String?, focus: Bool?) -> String? {
    guard !key.isEmpty else { return "no project key" }
    var all = loadLocalProjects()
    var entry = all[key] ?? [:]
    if let h = hex { entry["hex"] = h }
    if let f = focus { entry["focus"] = f }
    all[key] = entry
    guard let d = try? JSONSerialization.data(withJSONObject: ["projects": all],
                                              options: [.prettyPrinted, .sortedKeys]) else { return "not JSON" }
    do { try writeAtomically(d, to: Paths.projects) } catch { return error.localizedDescription }
    return nil
}

/// Set a project's ONE colour (owner's ruling: the sprite, the iTerm2 text and the SidePulse LED share it).
/// Waypoint present: `waypoint launch colour <alias> <hex>` rewrites only the `]10;` hex in that alias's
/// Command cell (every machine row for the alias, as `focus add` does). Absent: the local file, by key.
func setProjectColour(key: String, alias: String, hex: String) -> String? {
    guard hex.range(of: "^#[0-9A-Fa-f]{6}$", options: .regularExpression) != nil else { return "not a #RRGGBB colour" }
    if waypointCLIPath() != nil {
        guard !alias.isEmpty else { return "this project has no launch alias to colour" }
        return runWaypoint(["launch", "colour", alias, hex])
    }
    return saveLocalProject(key: key, hex: hex, focus: nil)
}

/// Mark or unmark a project as a focus item. Waypoint present: the `Focus` column, through
/// `waypoint focus add|remove <alias>`; a project with no launch alias CANNOT be focused and says so.
func setProjectFocus(key: String, alias: String, on: Bool) -> String? {
    if waypointCLIPath() != nil {
        guard !alias.isEmpty else { return "this project has no launch alias, so it cannot be a focus project" }
        return runWaypoint(["focus", on ? "add" : "remove", alias])
    }
    return saveLocalProject(key: key, hex: nil, focus: on)
}

// MARK: single instance (review R1_MACOS #3)

/// Exclusive, non-blocking flock on a lock file, held for the life of the object (the process). Two Sprites from two
/// build trees cannot both hold it. nil = another holder (or the file cannot be opened).
final class InstanceLock {
    static var defaultPath: String { Paths.home + "/agent-storage/sprites/run/sprites.lock" }
    private let fd: Int32
    init?(path: String = InstanceLock.defaultPath) {
        try? FileManager.default.createDirectory(atPath: (path as NSString).deletingLastPathComponent, withIntermediateDirectories: true)
        let f = open(path, O_RDWR | O_CREAT | O_CLOEXEC, 0o600)
        guard f >= 0 else { return nil }
        guard flock(f, LOCK_EX | LOCK_NB) == 0 else { close(f); return nil }
        let s = "\(getpid())\n"; ftruncate(f, 0); _ = s.withCString { write(f, $0, strlen($0)) }
        fd = f
    }
    deinit { flock(fd, LOCK_UN); close(fd) }
}

/// What launch does about other instances. `qaSecond` (`--qa-second-instance`) runs beside the owner's app with no
/// hotkey, backdrop or dim (QA only); otherwise any other pid with our bundle id, or a held lock, means exit.
enum InstancePlan: Equatable { case run, runAsQASecond, exitDuplicate(String) }
func instancePlan(me: pid_t, sameBundle: [pid_t], lockAcquired: Bool, qaSecond: Bool) -> InstancePlan {
    if qaSecond { return .runAsQASecond }
    let others = sameBundle.filter { $0 != me && $0 > 0 }
    if !others.isEmpty { return .exitDuplicate("another Sprites is running (pid \(others.map(String.init).joined(separator: ",")))") }
    if !lockAcquired { return .exitDuplicate("another Sprites holds \(InstanceLock.defaultPath)") }
    return .run
}

// MARK: demo clicks (review R2_MACOS #2, host half)

/// Whether a stage click may act at all. Demo sprites are invented: a click on one never focuses or launches anything.
func hostDemoForClick(appDemo: Bool?) -> Bool { appDemo ?? true }

// MARK: visibility (review R2_MACOS #8, host half)

/// The stage is paused (no frames) when hidden, faded for full screen, while the displays sleep, while the user session
/// is switched away (fast user switching), or when the panel is fully occluded.
func stagePaused(hidden: Bool, fsFaded: Bool, asleep: Bool, away: Bool, occluded: Bool) -> Bool {
    hidden || fsFaded || asleep || away || occluded
}

// MARK: Settings close (review R1_MACOS #7)

/// After the Settings window closes, give activation back: the app that was frontmost before Settings opened, if it is
/// still running and is not us; else hide Sprites so keystrokes do not go to an app with no window.
enum SettingsCloseAction: Equatable { case reactivate(pid_t), hide }
func settingsCloseAction(previous: pid_t?, me: pid_t, isRunning: (pid_t) -> Bool) -> SettingsCloseAction {
    if let p = previous, p != me, p > 0, isRunning(p) { return .reactivate(p) }
    return .hide
}
