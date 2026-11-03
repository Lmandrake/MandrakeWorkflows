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
