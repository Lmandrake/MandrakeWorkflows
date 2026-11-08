import Foundation
import Darwin
import CoreGraphics

/// Small pure decisions of the host, factored out so sprites/tests/swift/ can test them without AppKit, a window or
/// the owner's wallpaper (reviews/SPRITES_REVIEW_R1.md). No side effects unless a name says so.

// MARK: JSON numbers (review #3)

/// A JSON number as a Double; nil for a Boolean or anything else.
func jsonNumber(_ v: Any?) -> Double? {
    // `is Bool` is wrong here: JSONSerialization's 0 and 1 bridge to Bool. Only the CFBoolean singletons are Booleans.
    guard let n = v as? NSNumber, CFGetTypeID(n) != CFBooleanGetTypeID() else { return nil }
    return n.doubleValue
}

/// "Dim desktop icons" from behaviors.json text: key "dimIcons", integer percent 0-80; missing = 45; 0 = off.
func dimIconsPercent(behaviorsJSON: String) -> Double {
    guard let d = behaviorsJSON.data(using: .utf8),
          let o = try? JSONSerialization.jsonObject(with: d) as? [String: Any],
          let n = jsonNumber(o["dimIcons"]) else { return 45 }
    return min(80, max(0, n))
}

/// behaviors.json "backdropSpeed": {"b07": 1.5, ...} or one number for every backdrop; nil = the catalog's speed.
func backdropSpeedOverride(_ o: [String: Any], id: String) -> Double? {
    if let m = o["backdropSpeed"] as? [String: Any] { return jsonNumber(m[id]) }
    return jsonNumber(o["backdropSpeed"])
}

// MARK: wallpaper Store (review #4, #9)

/// The wallpaper bookkeeping, on injected paths so tests run on temp files and fake Store directories only. It never
/// talks to WallpaperAgent or NSWorkspace; Backdrop.swift's Wallpaper does that around it.
///
/// The Store (`com.apple.wallpaper/Store/Index.plist`) holds one "leaf" per Space x display (plus Displays/*,
/// AllSpacesAndDisplays, SystemDefault): a dict whose "Desktop" holds the choice. The snapshot is a map leaf path ->
/// that Desktop dict. Rules (review R1 #4):
///  - taken fresh when a backdrop is first chosen from "none";
///  - before every write Sprites makes, every leaf that does not show a Sprites PNG is copied into it, so a choice the
///    owner made meanwhile replaces the old one;
///  - restore replaces ONLY leaves that currently show a Sprites PNG. A leaf showing anything else is the owner's (or
///    untouched) and is kept, so a newer user choice is never overwritten;
///  - deleted whenever the per-Space records become empty, by any path, and on "none" once nothing of ours shows.
/// Tombstones (review R1_MACOS #4): the snapshot also lists every leaf path that existed (key "#known"). A leaf that
/// shows ours and is NOT in that list was created after the snapshot (a new display or Space while a still was on), so
/// restore deletes it and that Space x display inherits again. A leaf showing ours on a display that is not connected
/// and that nothing can restore is "later": it does not hold the snapshot or the records open.
final class WallpaperBook {
    let store: String, snap: String, file: String, cacheDir: String
    /// UUIDs of the connected displays; nil = treat every display as connected.
    let connected: () -> Set<String>?
    private(set) var originals: [String: [String: Any]] = [:]
    static let knownKey = "#known"
    init(store: String, snap: String, originalsFile: String, cacheDir: String, connected: @escaping () -> Set<String>? = { nil }) {
        self.store = store; self.snap = snap; file = originalsFile; self.cacheDir = cacheDir; self.connected = connected
        if let d = FileManager.default.contents(atPath: file), let o = try? JSONSerialization.jsonObject(with: d) as? [String: [String: Any]] { originals = o }
    }
    var snapExists: Bool { FileManager.default.fileExists(atPath: snap) }
    func isOurs(_ path: String?) -> Bool { path?.hasPrefix(cacheDir) ?? false }

    // MARK: Store reading

    private static func plist(_ path: String) -> [String: Any]? {
        guard let d = FileManager.default.contents(atPath: path) else { return nil }
        return (try? PropertyListSerialization.propertyList(from: d, format: nil)) as? [String: Any]
    }
    /// Every leaf of a Store dict: key path -> its "Desktop" dict.
    static func leaves(_ o: [String: Any], _ path: String = "") -> [String: [String: Any]] {
        var out: [String: [String: Any]] = [:]
        if let d = o["Desktop"] as? [String: Any], d["Content"] != nil { out[path] = d }
        for (k, v) in o where k != "Desktop" && k != "Idle" { if let c = v as? [String: Any] { out.merge(leaves(c, path + "/" + k)) { a, _ in a } } }
        return out
    }
    /// The same Store dict with some leaves' Desktop replaced.
    static func replacing(_ o: [String: Any], _ repl: [String: [String: Any]], _ path: String = "") -> [String: Any] {
        var r = o
        if let d = repl[path], o["Desktop"] != nil { r["Desktop"] = d }
        for (k, v) in o where k != "Desktop" && k != "Idle" { if let c = v as? [String: Any] { r[k] = replacing(c, repl, path + "/" + k) } }
        return r
    }
    /// The same Store dict with the leaves at `paths` removed (and any dict that only held them).
    static func removing(_ o: [String: Any], _ paths: Set<String>, _ path: String = "") -> [String: Any] {
        var r = o
        for (k, v) in o where k != "Desktop" && k != "Idle" {
            guard let c = v as? [String: Any] else { continue }
            let p = path + "/" + k
            if paths.contains(p) { r[k] = nil; continue }
            let n = removing(c, paths, p)
            if n.isEmpty && !c.isEmpty { r[k] = nil } else { r[k] = n }
        }
        return r
    }
    /// The display UUID a leaf path belongs to ("/Spaces/S/Displays/D" or "/Displays/D"); nil = every display.
    static func display(ofLeaf path: String) -> String? {
        let c = path.split(separator: "/")
        guard let i = c.firstIndex(of: "Displays"), i + 1 < c.count else { return nil }
        return String(c[i + 1])
    }
    private func isConnected(_ leafPath: String) -> Bool {
        guard let d = Self.display(ofLeaf: leafPath), let set = connected() else { return true }
        return set.contains { $0.caseInsensitiveCompare(d) == .orderedSame }
    }
    /// The image file paths a leaf's Desktop shows (decoded from Choices[].Configuration, a nested plist).
    static func images(_ desktop: [String: Any]) -> [String] {
        let choices = (desktop["Content"] as? [String: Any])?["Choices"] as? [[String: Any]] ?? []
        return choices.compactMap { c in
            guard let cd = c["Configuration"] as? Data,
                  let conf = (try? PropertyListSerialization.propertyList(from: cd, format: nil)) as? [String: Any],
                  let rel = (conf["url"] as? [String: Any])?["relative"] as? String else { return nil }
            return URL(string: rel)?.path ?? rel
        }
    }
    private func showsOurs(_ desktop: [String: Any]) -> Bool { Self.images(desktop).contains { isOurs($0) } }
    private func liveLeaves() -> [String: [String: Any]]? { Self.plist(store).map { Self.leaves($0) } }
    private func snapLeaves() -> [String: [String: Any]] {
        guard let o = Self.plist(snap) else { return [:] }
        if o["Spaces"] != nil || o["SystemDefault"] != nil { return Self.leaves(o) }   // a pre-R1 whole-Store copy
        return o.compactMapValues { $0 as? [String: Any] }
    }
    /// Leaf paths that existed when the snapshot was taken or were absorbed later; nil = unknown (an older snapshot).
    private func snapKnown() -> Set<String>? { (Self.plist(snap)?[Self.knownKey] as? [String]).map(Set.init) }
    private func writeSnap(_ l: [String: [String: Any]], known: Set<String>?) -> Bool {
        var o: [String: Any] = l
        if let known { o[Self.knownKey] = known.sorted() }
        do { try FileManager.default.createDirectory(atPath: (snap as NSString).deletingLastPathComponent, withIntermediateDirectories: true)
             try PropertyListSerialization.data(fromPropertyList: o, format: .binary, options: 0).write(to: URL(fileURLWithPath: snap), options: .atomic)
             return true } catch { return false }
    }
    /// Any leaf showing a Sprites PNG. connectedOnly: only leaves of connected displays (a disconnected display's
    /// unrestorable leaf must not hold the snapshot open for ever, review R1_MACOS #4b).
    func liveHasOurs(connectedOnly: Bool = false) -> Bool {
        liveLeaves()?.contains { showsOurs($0.value) && (!connectedOnly || isConnected($0.key)) } ?? false
    }
    /// Every image path the Store shows on any Space or display (review R1 #9: a cached PNG still in use elsewhere).
    func storeImagePaths() -> Set<String> { Set((liveLeaves() ?? [:]).values.flatMap { Self.images($0) }) }

    // MARK: transitions

    /// The backdrop changed. none -> a backdrop: a fresh snapshot (if Sprites PNGs still show from an earlier run,
    /// the old snapshot is kept and refreshed instead, since a fresh one would record ours as the owner's).
    @discardableResult
    func backdropChosen(from prev: String, to next: String) -> Bool {
        guard prev == "none", next != "none", FileManager.default.fileExists(atPath: store) else { return true }
        if snapExists, liveHasOurs(connectedOnly: true) { return absorb() }
        try? FileManager.default.removeItem(atPath: snap)
        return absorb()
    }
    /// Copy every live leaf that does not show ours into the snapshot. False = could not write it.
    @discardableResult
    func absorb() -> Bool {
        guard let live = liveLeaves() else { return !FileManager.default.fileExists(atPath: store) }
        let fresh = !snapExists
        var s = snapLeaves()
        // A fresh snapshot knows every leaf that exists now (one showing ours already is a crash leftover: it existed).
        var known: Set<String>? = fresh ? Set(live.keys) : snapKnown()
        for (k, d) in live where !showsOurs(d) { s[k] = d; known?.insert(k) }
        return writeSnap(s, known: known)
    }
    /// Before Sprites writes the wallpaper. False = do not change it.
    func prepareWrite() -> Bool { absorb() }
    func record(_ key: String, _ rec: [String: Any]) { originals[key] = rec; save() }
    func forget(_ key: String) { originals[key] = nil; save(); if originals.isEmpty { try? FileManager.default.removeItem(atPath: snap) } }
    /// On "none": with no records left and nothing of ours showing, the snapshot has no work left.
    func dropSnapshotIfIdle() { if originals.isEmpty && !liveHasOurs(connectedOnly: true) { try? FileManager.default.removeItem(atPath: snap) } }

    struct Restore: Equatable { var restored: [String] = [], removed: [String] = [], kept: [String] = [], unresolved: [String] = [], later: [String] = [] }
    /// Put the snapshot back on every leaf that shows ours, delete every leaf of ours the snapshot has a tombstone for
    /// (it did not exist), keep every other leaf as it is now. nil = no snapshot or no readable Store. With finalize,
    /// when nothing is left unresolved the records and the snapshot are deleted; without, call finalize(_:) once the
    /// write is known to have stuck (review R1_MACOS #11: WallpaperAgent can overwrite it).
    func restoreStore(finalize: Bool = true) -> Restore? {
        guard snapExists, let liveDict = Self.plist(store) else { return nil }
        let live = Self.leaves(liveDict), s = snapLeaves(), known = snapKnown()
        var r = Restore(), repl: [String: [String: Any]] = [:]
        for (k, d) in live.sorted(by: { $0.key < $1.key }) {
            if !showsOurs(d) { r.kept.append(k); continue }
            if let o = s[k], !showsOurs(o) { repl[k] = o; r.restored.append(k) }
            else if let known, !known.contains(k), s[k] == nil { r.removed.append(k) }
            else if !isConnected(k) { r.later.append(k) }
            else { r.unresolved.append(k) }
        }
        if !repl.isEmpty || !r.removed.isEmpty {
            let out = Self.removing(Self.replacing(liveDict, repl), Set(r.removed))
            guard let d = try? PropertyListSerialization.data(fromPropertyList: out, format: .binary, options: 0),
                  (try? d.write(to: URL(fileURLWithPath: store), options: .atomic)) != nil else { return nil }
        }
        if finalize && r.unresolved.isEmpty { clearAll() }
        return r
    }
    /// After WallpaperAgent reread the Store: true when every leaf the restore replaced or removed no longer shows ours.
    /// Only then (and with nothing unresolved) are the records and the snapshot deleted.
    @discardableResult
    func finalize(_ r: Restore) -> Bool {
        guard let live = liveLeaves() else { return false }
        let stuck = (r.restored + r.removed).allSatisfy { k in live[k].map { !showsOurs($0) } ?? true }
        if stuck && r.unresolved.isEmpty { clearAll() }
        return stuck
    }
    private func clearAll() { originals = [:]; save(); try? FileManager.default.removeItem(atPath: snap) }
    private func save() {
        if let d = try? JSONSerialization.data(withJSONObject: originals, options: [.prettyPrinted, .sortedKeys]) {
            try? FileManager.default.createDirectory(atPath: (file as NSString).deletingLastPathComponent, withIntermediateDirectories: true)
            try? d.write(to: URL(fileURLWithPath: file), options: .atomic)
        }
    }
}

/// The NSWorkspace fallback's image for a record; nil = do not set it. Never the macOS placeholder: NSWorkspace reports
/// DefaultDesktop.heic for a colour, aerial or dynamic wallpaper, so setting it would replace his choice with the stock
/// picture (review R1_MACOS #4).
let wallpaperPlaceholder = "/System/Library/CoreServices/DefaultDesktop.heic"
func fallbackRestorePath(_ rec: [String: Any]) -> String? {
    guard let p = rec["url"] as? String, p.hasPrefix("/"), p != wallpaperPlaceholder,
          !p.hasPrefix("/System/Library/CoreServices/DefaultDesktop") else { return nil }
    return p
}

/// Pids of processes with this exact name (proc_name), read from the kernel: no pgrep subprocess.
func pidsNamed(_ name: String) -> [pid_t] {
    let n = proc_listallpids(nil, 0)
    guard n > 0 else { return [] }
    var pids = [pid_t](repeating: 0, count: Int(n) + 64)
    let got = proc_listallpids(&pids, Int32(pids.count * MemoryLayout<pid_t>.size))
    guard got > 0 else { return [] }
    var buf = [CChar](repeating: 0, count: 256)
    return pids.prefix(Int(got)).filter { p in
        p > 0 && proc_name(p, &buf, UInt32(buf.count)) > 0 && String(cString: buf) == name
    }
}
/// A relaunched agent: a pid with the name that is not the one killed. nil = not back yet.
func relaunchedPid(old: [pid_t], now: [pid_t]) -> pid_t? { now.first { !old.contains($0) } }

/// The current Space of one display from CGSCopyManagedDisplaySpaces' array (review R1_MACOS #15). Entries carry
/// "Display Identifier" (a display UUID, or "Main" when one Space spans every display) and "Current Space" {id64}.
/// nil = not found (the caller falls back to the main display's active Space).
func currentSpace(displayUUID: String, managed: [[String: Any]]) -> String? {
    func sp(_ e: [String: Any]) -> String? {
        guard let c = e["Current Space"] as? [String: Any], let n = jsonNumber(c["id64"]) ?? jsonNumber(c["ManagedSpaceID"]) else { return nil }
        return String(Int64(n))
    }
    if let e = managed.first(where: { ($0["Display Identifier"] as? String)?.caseInsensitiveCompare(displayUUID) == .orderedSame }) { return sp(e) }
    if managed.count == 1, let e = managed.first, (e["Display Identifier"] as? String) == "Main" { return sp(e) }
    return nil
}

/// The live backdrop's window level (review R1_MACOS #10): one above the desktop window level, so a relaunched
/// WallpaperAgent cannot order its wallpaper over it, and still far below the desktop icons and the dim layer.
func backdropWindowLevel() -> Int { Int(CGWindowLevelForKey(.desktopWindow)) + 1 }

/// Which cached PNGs to delete: all but the newest `keep`, never one in use.
func prunePaths(_ files: [(path: String, date: Date)], keep: Int, inUse: Set<String>) -> [String] {
    files.sorted { $0.date > $1.date }.dropFirst(keep).map(\.path).filter { !inUse.contains($0) }
}

// MARK: click to session (review #8)

/// A process's start time (epoch seconds, kinfo_proc p_starttime); nil if it is gone.
func processStart(_ pid: pid_t) -> Int? {
    var info = kinfo_proc(), size = MemoryLayout<kinfo_proc>.stride
    var mib: [Int32] = [CTL_KERN, KERN_PROC, KERN_PROC_PID, pid]
    guard pid > 0, sysctl(&mib, 4, &info, &size, nil, 0) == 0, size > 0, info.kp_proc.p_pid == pid else { return nil }
    return Int(info.kp_proc.p_un.__p_starttime.tv_sec)
}

/// The controlling terminal of a process ("/dev/ttys003"), from kinfo_proc e_tdev: no `ps` subprocess.
func processTTY(_ pid: pid_t) -> String? {
    var info = kinfo_proc(), size = MemoryLayout<kinfo_proc>.stride
    var mib: [Int32] = [CTL_KERN, KERN_PROC, KERN_PROC_PID, pid]
    guard pid > 0, sysctl(&mib, 4, &info, &size, nil, 0) == 0, size > 0, info.kp_proc.p_pid == pid else { return nil }
    let dev = info.kp_eproc.e_tdev
    guard dev != -1, dev != 0, let name = devname(dev, S_IFCHR) else { return nil }
    let s = String(cString: name)
    return s.isEmpty || s.hasPrefix("?") ? nil : "/dev/" + s
}

/// Augur's snapshot valid_until (epoch s); nil if absent or unreadable.
func snapshotValidUntil(_ json: String?) -> Double? {
    guard let d = json?.data(using: .utf8), let o = try? JSONSerialization.jsonObject(with: d) as? [String: Any] else { return nil }
    return jsonNumber(o["valid_until"])
}

enum ClickAction: Equatable { case ghost(String), focus(pid_t), ignore(String) }

/// What a click on a sprite does (review R1 #8). A live session is focused only when the snapshot is fresh (now <=
/// valid_until) and its pid still belongs to the process the session id names: Augur's id is "<pid>@<start epoch s>",
/// checked against the kernel's start time, so a reused pid never activates an unrelated app.
/// A ghost is what the stage says it is (`ghost: true` in the click, review R1 #17), never an id prefix: Augur's ids are
/// "<pid>@<start>", but a real session must never launch a new one because of how its id is spelled. `.ghost` carries
/// the project_key (app/projects.js), which ghostPlan resolves.
/// Demo mode ignores every click: its sessions and ghosts are invented, and a demo ghost's key can name a real project
/// (review R2_MACOS #2). The stale gate applies to ghosts too: a ghost drawn from an expired snapshot opens nothing.
func clickAction(id: String, pid: pid_t, project: String, ghost: Bool = false, key: String = "", validUntil: Double?, now: Double,
                 demo: Bool = false, startOf: (pid_t) -> Int?) -> ClickAction {
    if demo { return .ignore("demo") }
    guard let vu = validUntil, now <= vu else { return .ignore("snapshot stale") }
    if ghost { return key.isEmpty ? .ignore("ghost without a project_key") : .ghost(key) }
    let parts = id.split(separator: "@")
    guard parts.count == 2, let idPid = pid_t(parts[0]), idPid > 0, let start = Int(parts[1]) else { return .ignore("id has no pid@start") }
    if pid != 0 && pid != idPid { return .ignore("pid \(pid) disagrees with id") }
    guard let real = startOf(idPid) else { return .ignore("pid \(idPid) has exited") }
    guard abs(real - start) <= 1 else { return .ignore("pid \(idPid) was reused (started \(real), session \(start))") }
    return .focus(idPid)
}

// MARK: the gesture (owner, 2026-11-05: "I really do want to be able to double-click on a Sprite and have it open the
// relevant Claude session or switch Spaces/Focus to it")

/// What a mouse-down with this clickCount should do.
enum ClickGesture: Equatable {
    case act              // the second click of a double-click: open or focus now
    case waitForSecond    // one click so far: act only if no second click arrives within singleClickDelay
    case alreadyActed     // a third or later click in the same gesture: the action already ran, do nothing
}
/// The owner's gesture is the DOUBLE-click, so two clicks act immediately. A single click must still never be eaten
/// (R3-SPEC #1, #2: "no behaviour may block a click" — a sprite that swallows a click and does nothing is a defect),
/// so one click acts too, once the double-click window has passed with no second click. Clicks past the second do
/// nothing: one gesture, one action, so holding the button down does not open a window per click.
func clickGesture(count: Int) -> ClickGesture {
    if count >= 3 { return .alreadyActed }
    return count == 2 ? .act : .waitForSecond
}
/// How long a single click waits for its partner: the user's OWN double-click interval
/// (NSEvent.doubleClickInterval / "com.apple.mouse.doubleClickThreshold"), never a hardcoded guess. Absent (0) means
/// 0.25 s; clamped to 0.15...1.0 so an absurd preference cannot make a sprite feel dead or fire twice.
func singleClickDelay(doubleClickInterval: Double) -> Double {
    guard doubleClickInterval > 0 else { return 0.25 }
    return min(1.0, max(0.15, doubleClickInterval))
}

/// The terminal's AppleScript found no tab with the session's tty: never raise every window (log only).
func activateAllAfterScript(_ result: String?) -> Bool { false }

// MARK: visibility (review #10)

/// What the app's hidden state (hide, meeting mode, locked) means for each layer.
struct VisibilityPlan: Equatable { let stagesShown: Bool; let backdropHidden: Bool }
func visibilityPlan(userHidden: Bool, meeting: Bool, locked: Bool) -> VisibilityPlan {
    let hidden = userHidden || meeting || locked
    return VisibilityPlan(stagesShown: !hidden, backdropHidden: hidden)
}

/// Backdrop: draw a tick only when nothing pauses it.
func backdropPaused(locked: Bool, asleep: Bool, hidden: Bool, reduceMotion: Bool) -> Bool { locked || asleep || hidden || reduceMotion }

// MARK: robustness (review #18)

/// Host -> stage calls waiting for the page (or replayed after a WebContent crash). Every host call is a setter
/// (`SpritesStage.setX(...)`, `update(...)`), so only the latest of each kind matters: a new call replaces the queued
/// one of the same kind in place (first-seen order kept), and at most `cap` kinds are held, oldest dropped.
struct JSQueue {
    static let cap = 64
    private(set) var items: [String] = []
    static func kind(_ s: String) -> Substring { s.prefix { $0 != "(" } }
    mutating func add(_ s: String) {
        let k = Self.kind(s)
        if let i = items.firstIndex(where: { Self.kind($0) == k }) { items[i] = s; return }
        items.append(s)
        if items.count > Self.cap { items.removeFirst(items.count - Self.cap) }
    }
    mutating func take() -> [String] { defer { items = [] }; return items }
}

/// Notification observers owned by one object, removed together (BackdropWindow's occlusion observer).
final class ObserverBag {
    private var tokens: [(NotificationCenter, NSObjectProtocol)] = []
    func observe(_ nc: NotificationCenter, _ name: Notification.Name, object: AnyObject?, _ block: @escaping (Notification) -> Void) {
        tokens.append((nc, nc.addObserver(forName: name, object: object, queue: nil, using: block)))
    }
    func removeAll() { tokens.forEach { $0.0.removeObserver($0.1) }; tokens = [] }
    deinit { removeAll() }
}

/// What identifies the screen layout the stages and backdrops are built for.
struct ScreenSig: Equatable { let id: UInt32; let frame: CGRect; let scale: CGFloat }
/// didChangeScreenParameters also fires for Dock and menu-bar changes; rebuild only when ids, frames or scales differ.
func screensChanged(_ old: [ScreenSig], _ new: [ScreenSig]) -> Bool { old != new }

// MARK: ghost launch (review R1 #2, #17)

enum GhostPlan: Equatable { case launch(String), claude(String), refuse(String) }
/// A ghost click opens a session for its project, looked up by project_key in the project table (app/projects.js build:
/// [{key, name, dir, alias, ...}]): `launch <alias>` when Waypoint has an alias for it (a shell identifier only, since it
/// is typed into a terminal), else `claude` in the registry's own directory for it (an absolute path in the table, never
/// one built from a name). A key the table does not hold opens nothing.
func ghostPlan(key: String, table: [[String: Any]]) -> GhostPlan {
    guard !key.isEmpty, let e = table.first(where: { ($0["key"] as? String) == key }) else { return .refuse("no project \(key) in the table") }
    if let a = e["alias"] as? String, a.range(of: "^[A-Za-z_][A-Za-z0-9_]*$", options: .regularExpression) != nil { return .launch(a) }
    guard let d = e["dir"] as? String, d.hasPrefix("/"), !d.split(separator: "/").contains(where: { $0 == ".." || $0 == "." }) else {
        return .refuse("project \(key) has no launch alias and no usable directory")
    }
    return .claude(d)
}
/// One window per project per 3 s (double-click debounce). Stamped only after a launch was sent, so a refused or
/// failed click does not suppress the next one.
func ghostDebounced(last: Date?, now: Date) -> Bool { last.map { now.timeIntervalSince($0) < 3 } ?? false }

// MARK: Space switch for a deliberate click (owner, 2026-11-04)
/// With `com.apple.dock workspaces-auto-swoosh` 0 (Machinist, 2026-10-21, kept on purpose), activating iTerm2 makes it
/// frontmost but never flies to the clicked window's Space; the Dock's Dock-icon path goes to the app's LAST Space,
/// not the window's. Sprites therefore posts Mission Control's own "Switch to Desktop N" shortcut for that one click.
enum SpaceSwitch: Equatable { case stay(String), desktop(Int, keyCode: Int, flags: UInt64), unreachable(String) }
/// `displays` is SLSCopyManagedDisplaySpaces' answer, `windowSpaces` the window's space ids (SLSCopySpacesForWindows),
/// `hotkeys` com.apple.symbolichotkeys' AppleSymbolicHotKeys (ids 118... = Desktop 1...). Desktop N is the window's
/// 1-based position among its display's user desktops (type 0; fullscreen spaces are not numbered).
func spaceSwitchPlan(displays: [[String: Any]], windowSpaces: [Int], hotkeys: [String: Any]) -> SpaceSwitch {
    guard windowSpaces.count == 1, let sid = windowSpaces.first else {
        return .stay(windowSpaces.isEmpty ? "window has no space (minimised or gone)" : "window is on every space")
    }
    func id(_ s: [String: Any]) -> Int { (s["ManagedSpaceID"] as? Int) ?? (s["id64"] as? Int) ?? -1 }
    for d in displays {
        let cur = (d["Current Space"] as? [String: Any]).map(id) ?? -1
        if cur == sid { return .stay("already on the window's space") }
        var n = 0
        for s in (d["Spaces"] as? [[String: Any]]) ?? [] {
            let user = (s["type"] as? Int ?? 0) == 0
            if user { n += 1 }
            guard id(s) == sid else { continue }
            if !user { return .unreachable("window is on a fullscreen space") }
            guard (1...16).contains(n), let hk = hotkeys[String(117 + n)] as? [String: Any], (hk["enabled"] as? Bool ?? false)
                    || (hk["enabled"] as? Int ?? 0) == 1,
                  let p = (hk["value"] as? [String: Any])?["parameters"] as? [Int], p.count == 3, p[1] != 65535 else {
                return .unreachable("\"Switch to Desktop \(n)\" shortcut is off (System Settings > Keyboard > Shortcuts > Mission Control)")
            }
            return .desktop(n, keyCode: p[1], flags: UInt64(p[2]))
        }
    }
    return .unreachable("space \(sid) is on no display")
}
/// iTerm2/Terminal focus scripts answer "ok <window id>"; the id is the window's CGWindowNumber. nil when not "ok".
func focusedWindow(_ reply: String?) -> Int? {
    guard let r = reply, r == "ok" || r.hasPrefix("ok ") else { return nil }
    return Int(r.dropFirst(2).trimmingCharacters(in: .whitespaces)) ?? 0
}

// MARK: one wandering area across every screen (SPRITES_UNIFY_MONITORS_AS_ONE)

/// One screen's place in the shared world. Pure geometry: `Span.of` is the only thing that reads NSScreen (in
/// Stage.swift), everything below is testable without AppKit.
///
/// WHY A WORLD RECT AND NOT ONE BIG WINDOW (measured 2026-11-05, this Desktop, macOS 26.7.1): a single NSPanel whose
/// frame spans the union of both screens KEEPS that frame (AppKit does not clamp it) but renders on the MAIN DISPLAY
/// ONLY — difference imaging of two `screencapture -D` frames showed 60 fully-covered rows on display 1 and 0 on
/// display 2, with "Displays have separate Spaces" on. So the cast cannot live in one window. Instead every screen
/// keeps its own panel and its own JS world sized to the UNION, and each is told, via setVisible, only the sub-rect
/// IT shows. One simulation per panel still runs, but they share one coordinate system, so a creature's position means
/// the same place on both — and `setVisible` keeps each panel's creatures inside the part of the world it can display.
struct SpanLayout: Equatable {
    /// The union of every screen frame, in Cocoa global coordinates (bottom-left origin).
    let world: CGRect
    /// Per screen, in the same order as the screens given: its rect in WORLD STAGE px (top-left origin of the world).
    let rects: [CGRect]
    /// Per screen, its visible frame (menu bar and Dock excluded) in world stage px.
    let visible: [CGRect]
    /// World size in stage px.
    var size: CGSize { world.size }
}

/// Cocoa global rect (bottom-left origin) -> world stage px (top-left origin of `world`).
/// The single conversion every span path uses, so a negative-origin secondary screen is handled in ONE place.
/// Mirrors `visibleStageRect`'s flip, but against the world instead of one screen.
func worldRect(_ r: CGRect, world: CGRect) -> CGRect {
    CGRect(x: r.minX - world.minX, y: world.maxY - r.maxY, width: r.width, height: r.height)
}

/// Cocoa global point -> world stage px.
func worldPoint(_ p: CGPoint, world: CGRect) -> CGPoint {
    CGPoint(x: p.x - world.minX, y: world.maxY - p.y)
}

/// Build the shared world from each screen's (frame, visibleFrame), in Cocoa global coordinates.
/// A single screen yields world == that frame and rect == (0, 0, w, h), i.e. EXACTLY today's numbers — the Laptop
/// regression guard.
func spanLayout(frames: [CGRect], visibleFrames: [CGRect]) -> SpanLayout {
    var u = CGRect.null
    for f in frames { u = u.union(f) }
    let world = u.isNull ? .zero : u
    return SpanLayout(world: world,
                      rects: frames.map { worldRect($0, world: world) },
                      visible: zip(frames, visibleFrames).map { f, v in
                          // An empty or bogus visibleFrame falls back to the whole frame rather than to nothing.
                          worldRect(v.isEmpty ? f : v, world: world) })
}

/// DEAD SPACE (the ticket's hazard 1). The union of two non-aligned screens contains regions no screen displays — on
/// this Desktop, measured 2026-11-05, the screens are offset 103 px vertically, so 8.7 % of the union is dead. A
/// creature that wandered there would be invisible AND unclickable.
///
/// The decision: the world is the union, but each panel's WALKABLE MASK is its own visible rect, pushed through
/// `setVisible`. stage.html already bounds every layer's terrain to the visible rect it was given
/// (visitors_runtime.js `buildGrid` walls off every cell outside `visRect`), so a creature on a panel simply never
/// routes into a band its own screen cannot show. Dead space is therefore unreachable BY CONSTRUCTION, with no clamp
/// and no new geometry in the pieces — it is the mechanism that already keeps them out of the Dock and menu bar.
/// This function exists to MEASURE that claim, not to enforce it: it returns the part of the world no screen covers.
func deadSpaceFraction(_ l: SpanLayout) -> Double {
    let total = Double(l.world.width * l.world.height)
    guard total > 0 else { return 0 }
    // Screens never overlap in a non-mirrored arrangement, so covered area is the plain sum (asserted by the caller's
    // tests with an overlap case, where this deliberately reads high rather than silently de-duplicating).
    let covered = l.rects.reduce(0.0) { $0 + Double($1.width * $1.height) }
    return max(0, (total - covered) / total)
}

/// Which screen index owns this world point (-1 = dead space or off-world). Clicks and the cursor resolve through
/// this, so a world coordinate that crosses a panel boundary still lands on exactly one panel.
func screenOf(worldPoint p: CGPoint, _ l: SpanLayout) -> Int {
    for (i, r) in l.rects.enumerated() where r.contains(p) { return i }
    return -1
}

/// PER-SCREEN SCALE (the ticket's hazard 3). Two monitors can differ; the world is one coordinate system in POINTS,
/// so each panel renders the same world at its OWN backing scale and nothing in the world depends on either. This is
/// the per-panel device scale, still clamped at 2 as before (a 4K TV reports 2.0 here, measured).
func panelScale(_ backing: CGFloat) -> CGFloat { min(2, backing) }

/// THE WALKABLE AREA (the ticket's hazard 1, the decision). One world spanning both monitors contains dead space no
/// screen displays. stage.html bounds every layer's terrain to the ONE rect it is given through `setVisible`
/// (visitors_runtime.js `buildGrid` walls off every cell outside it), and that single-rect shape is load-bearing all
/// the way down into the pieces — so the walkable area must be expressible as one rectangle.
///
/// The choice: the largest axis-aligned rectangle inscribed in the union of the per-screen VISIBLE rects, PREFERRING
/// a rectangle that touches more screens over a merely bigger one. Every point of it is on a real screen, below the
/// menu bar and clear of the Dock, so no creature can reach dead space, go invisible, or become unclickable — no clamp
/// needed anywhere.
///
/// 🔴 WHY SPANNING BEATS AREA, and it is a real trade (measured 2026-11-05): maximising area alone DEFEATS THE TICKET.
/// With a 2560x1440 beside a 1440x900, the single big screen (3 686 400 px²) is larger than the band crossing both
/// (4000x900 = 3 600 000 px²), so a pure-area rule would put the whole cast back on one monitor — exactly the
/// complaint. So the rule is lexicographic: most screens touched first, then area. The cost is paid in usable area
/// (here ~2 %); the benefit is that the cast actually spans, which is what was asked for.
///
/// On this Desktop's measured 103 px vertical offset the answer is the common horizontal band both screens show: the
/// cast spans both monitors and simply does not use the 103 px lip at the top of one and the bottom of the other. On
/// ONE screen it returns exactly that screen's visible rect, so the Laptop is bit-for-bit unchanged.
///
/// Exact for any axis-aligned arrangement: the screen edges cut the plane into a grid, each cell is wholly covered or
/// wholly not, and the answer is a maximal all-covered block. A plain band sweep is NOT enough — it cannot union two
/// stacked screens, and reported one screen for a vertical stack whose union is fully covered.
func largestInscribedRect(_ rects: [CGRect]) -> CGRect {
    let rs = rects.filter { $0.width > 0 && $0.height > 0 }
    if rs.isEmpty { return .zero }
    if rs.count == 1 { return rs[0] }
    let xs = Array(Set(rs.flatMap { [$0.minX, $0.maxX] })).sorted()
    let ys = Array(Set(rs.flatMap { [$0.minY, $0.maxY] })).sorted()
    guard xs.count > 1, ys.count > 1 else { return .zero }
    // cell (i, j) covered: its centre lies in some screen. Cells never straddle an edge, so a centre decides the cell.
    let nx = xs.count - 1, ny = ys.count - 1
    var cov = [Bool](repeating: false, count: nx * ny)
    for j in 0..<ny {
        for i in 0..<nx {
            let c = CGPoint(x: (xs[i] + xs[i + 1]) / 2, y: (ys[j] + ys[j + 1]) / 2)
            cov[j * nx + i] = rs.contains { $0.contains(c) }
        }
    }
    // every all-covered block of cells; score = (screens it touches, area), lexicographic.
    var best = CGRect.zero, bestScreens = -1, bestArea: CGFloat = 0
    for j0 in 0..<ny {
        for j1 in j0..<ny {
            for i0 in 0..<nx {
                var i1 = i0 - 1
                // extend right while the whole column block stays covered
                while i1 + 1 < nx, (j0...j1).allSatisfy({ cov[$0 * nx + i1 + 1] }) { i1 += 1 }
                if i1 < i0 { continue }
                let r = CGRect(x: xs[i0], y: ys[j0], width: xs[i1 + 1] - xs[i0], height: ys[j1 + 1] - ys[j0])
                let touched = rs.reduce(0) { n, s in
                    let o = s.intersection(r); return n + (o.isNull || o.width <= 0 || o.height <= 0 ? 0 : 1)
                }
                let area = r.width * r.height
                if touched > bestScreens || (touched == bestScreens && area > bestArea) {
                    bestScreens = touched; bestArea = area; best = r
                }
            }
        }
    }
    return best
}

/// The one rect `SpritesStage.setVisible` gets for the whole world: the walkable area above.
func spanVisibleRect(_ l: SpanLayout) -> CGRect { largestInscribedRect(l.visible) }

/// CG global rect (top-left origin of the PRIMARY display, what CGWindowList reports) -> world stage px.
/// `primaryMaxY` is NSScreen.screens.first!.frame.maxY. Windows and the focused rect come in this way.
func worldRectFromCG(_ cg: CGRect, world: CGRect, primaryMaxY: CGFloat) -> CGRect {
    // CG y is measured down from the primary's top; the world's top is primaryMaxY - world.maxY below it.
    CGRect(x: cg.minX - world.minX, y: cg.minY - (primaryMaxY - world.maxY), width: cg.width, height: cg.height)
}

/// ONE SIMULATION, N VIEWPORTS (the heart of the fix). Giving each panel its own world-sized JS world would NOT fix
/// the duplication: two independent simulations of the same world drift apart within seconds (own RNG, own timers), so
/// the same creature would sit at different world positions in each and show up on both monitors anyway. There is
/// therefore exactly ONE NativeHost for the whole world, and each panel is a VIEWPORT onto it — the same recorded
/// frame encoded once per panel with that panel's world origin, so a creature exists once and is drawn by whichever
/// panel happens to cover it.
///
/// Where a panel's viewport sits in the world, in world stage px (top-left origin): simply its rect's origin.
func viewportOrigin(_ worldRect: CGRect) -> CGPoint { CGPoint(x: worldRect.minX, y: worldRect.minY) }

/// Does this panel show any of the world at all? A screen whose rect is empty (disconnected mid-refit) is skipped
/// rather than encoded with a degenerate viewport.
func viewportDraws(_ worldRect: CGRect) -> Bool { worldRect.width >= 1 && worldRect.height >= 1 }

/// 🔴 Must the CAMetalLayer's drawableSize be reset before encoding into it? (The "squish" regression, 2026-11-05.)
/// It tested the WIDTH ALONE. With two 1920x1080 screens the widths are equal, so a layer carrying the other
/// viewport's (or the union's) drawableSize was left alone, the drawable kept a stale size, and CAMetalLayer scaled the
/// content into the layer's bounds — the owner's "squished horizontally, as though it kept something from one screen to
/// another", and the resampling that made it blurry. BOTH dimensions decide.
func drawableStale(_ current: CGSize, w: Int, h: Int) -> Bool {
    current.width != CGFloat(w) || current.height != CGFloat(h)
}

/// 🔴 The size and scale a viewport's OUTPUT must have: its panel's own, never the world's. f48a980 built the primary
/// `MetalStage` at WORLD size (`NativeHost(size: s.size, scale:)` with no output of its own), so on this Desktop the
/// primary panel's drawable was 7680x2366 device px inside a 3840x2160 layer — a measured 2.000x horizontal and 1.095x
/// vertical compression. A one-screen world returns exactly that screen, so the Laptop is unchanged.
func viewportOutput(panelSize: CGSize, backing: CGFloat) -> (size: CGSize, scale: CGFloat) {
    (panelSize, panelScale(backing))
}
