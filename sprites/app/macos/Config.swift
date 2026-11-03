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
        return ud.isEmpty ? home + "/ClaudeWork/augur/live/snapshot.json" : ud
    }()
    /// $SPRITES_CAST (tests: a cast that leaves the owner's untouched), else the saved cast.
    static let cast: String = { let v = ProcessInfo.processInfo.environment["SPRITES_CAST"] ?? ""; return v.isEmpty ? home + "/ClaudeWork/sprites/config/cast.json" : v }()
    static let behaviors = home + "/ClaudeWork/sprites/config/behaviors.json"
    static let launches = home + "/.config/waypoint/launches.md"
}

func fail(_ msg: String) -> Never {
    FileHandle.standardError.write("sprites: FATAL: \(msg)\n".data(using: .utf8)!)
    exit(2)
}

func log(_ msg: String) {
    FileHandle.standardError.write("sprites: \(msg)\n".data(using: .utf8)!)
}

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

// MARK: single instance (review R1_MACOS #3)

/// Exclusive, non-blocking flock on a lock file, held for the life of the object (the process). Two Sprites from two
/// build trees cannot both hold it. nil = another holder (or the file cannot be opened).
final class InstanceLock {
    static var defaultPath: String { Paths.home + "/ClaudeWork/sprites/run/sprites.lock" }
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
