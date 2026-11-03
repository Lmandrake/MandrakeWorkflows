import Foundation

// Tests for app/macos/Decide.swift (reviews/SPRITES_REVIEW_R1.md findings 3, 4, 8, 9, 10, 18; R1_MACOS 4, 10, 11, 15; R2_MACOS 2). Run: tests/swift/run.sh
var failed = 0, passed = 0
func check(_ ok: Bool, _ name: String) { if ok { passed += 1 } else { failed += 1; print("FAIL: \(name)") } }
func obj(_ s: String) -> [String: Any] { (try! JSONSerialization.jsonObject(with: s.data(using: .utf8)!)) as! [String: Any] }

// #3: Foundation's JSON parser bridges 0 and 1 to NSNumbers that `is Bool` accepts; only true/false are CFBoolean.
check(dimIconsPercent(behaviorsJSON: #"{"dimIcons":0}"#) == 0, "#3 dimIcons 0 is off (0 %), not 45")
check(dimIconsPercent(behaviorsJSON: #"{"dimIcons":1}"#) == 1, "#3 dimIcons 1 is 1 %")
check(dimIconsPercent(behaviorsJSON: #"{"dimIcons":30}"#) == 30, "#3 dimIcons 30")
check(dimIconsPercent(behaviorsJSON: #"{"dimIcons":95}"#) == 80, "#3 dimIcons clamps to 80")
check(dimIconsPercent(behaviorsJSON: #"{"dimIcons":true}"#) == 45, "#3 a Boolean is not a percent: default 45")
check(dimIconsPercent(behaviorsJSON: #"{"dimIcons":false}"#) == 45, "#3 false is not 0: default 45")
check(dimIconsPercent(behaviorsJSON: "{}") == 45, "#3 missing: 45")
check(dimIconsPercent(behaviorsJSON: "not json") == 45, "#3 unreadable: 45")
check(backdropSpeedOverride(obj(#"{"backdropSpeed":0}"#), id: "b07") == 0, "#3 scalar backdropSpeed 0")
check(backdropSpeedOverride(obj(#"{"backdropSpeed":1}"#), id: "b07") == 1, "#3 scalar backdropSpeed 1")
check(backdropSpeedOverride(obj(#"{"backdropSpeed":true}"#), id: "b07") == nil, "#3 scalar backdropSpeed true is no speed")
check(backdropSpeedOverride(obj(#"{"backdropSpeed":{"b07":0}}"#), id: "b07") == 0, "#3 per-id backdropSpeed 0")
check(backdropSpeedOverride(obj(#"{"backdropSpeed":{"b07":1.5}}"#), id: "b11") == nil, "#3 per-id, other id: nil")

// #4, #9: the wallpaper Store. Fake Store directories under the temp dir given as argv[1]; never the real one.
let tmpRoot = CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : NSTemporaryDirectory()
let realStore = NSHomeDirectory() + "/Library/Application Support/com.apple.wallpaper"
func bp(_ o: Any) -> Data { try! PropertyListSerialization.data(fromPropertyList: o, format: .binary, options: 0) }
/// One Store leaf the way macOS 26 writes it: Desktop.Content.Choices[0].Configuration is a nested bplist.
func leaf(_ choice: String) -> [String: Any] {
    let conf: [String: Any] = choice.hasPrefix("/") ? ["type": "imageFile", "url": ["relative": "file://" + choice]]
                                                    : ["type": "systemColor", "systemColor": [choice: [String: Any]()]]
    return ["Desktop": ["Content": ["Choices": [["Configuration": bp(conf), "Files": [Any](), "Provider": "com.apple.wallpaper.choice.image"]],
                                    "EncodedOptionValues": bp(["values": ["placement": "Crop"]]), "Shuffle": "$null"],
                        "LastSet": Date(timeIntervalSince1970: 1), "LastUse": Date()],
            "Type": "individual"]
}
func storeDict(_ spaces: [String: String]) -> [String: Any] {
    var sp: [String: Any] = [:]
    for (k, v) in spaces { sp[k] = ["Default": leaf(v), "Displays": ["D1": leaf(v)]] }
    return ["Spaces": sp, "SystemDefault": leaf("black")]
}
func writeStore(_ path: String, _ spaces: [String: String]) { try! bp(storeDict(spaces)).write(to: URL(fileURLWithPath: path)) }
/// What each Space's Default desktop shows in the store file: an image path or a colour name.
func shown(_ path: String) -> [String: String] {
    guard let d = FileManager.default.contents(atPath: path),
          let o = try? PropertyListSerialization.propertyList(from: d, format: nil) as? [String: Any],
          let sp = o["Spaces"] as? [String: Any] else { return [:] }
    var out: [String: String] = [:]
    for (k, v) in sp {
        guard let c = (((((v as? [String: Any])?["Default"] as? [String: Any])?["Desktop"] as? [String: Any])?["Content"] as? [String: Any])?["Choices"] as? [[String: Any]])?.first,
              let cd = c["Configuration"] as? Data,
              let conf = try? PropertyListSerialization.propertyList(from: cd, format: nil) as? [String: Any] else { continue }
        if let u = (conf["url"] as? [String: Any])?["relative"] as? String { out[k] = String(u.dropFirst("file://".count)) }
        else if let c = (conf["systemColor"] as? [String: Any])?.keys.first { out[k] = c }
    }
    return out
}
var caseN = 0
func freshBook() -> (WallpaperBook, String, String) {
    caseN += 1
    let dir = tmpRoot + "/wall\(caseN)"
    try? FileManager.default.removeItem(atPath: dir)
    try! FileManager.default.createDirectory(atPath: dir + "/Store", withIntermediateDirectories: true)
    let cache = dir + "/backdrops"
    let b = WallpaperBook(store: dir + "/Store/Index.plist", snap: dir + "/config/store_snap.plist",
                          originalsFile: dir + "/config/originals.json", cacheDir: cache)
    precondition(!b.store.hasPrefix(realStore) && !b.snap.hasPrefix(realStore))
    return (b, b.store, cache)
}
let ph = "/System/Library/CoreServices/DefaultDesktop.heic"

do {   // (b) in-session: a still on Space A; the owner sets a new image on Space B himself; None keeps B's new choice.
    let (b, store, cache) = freshBook()
    writeStore(store, ["A": "black", "B": "/pics/old.jpg"])
    b.backdropChosen(from: "none", to: "b10")
    check(b.prepareWrite(), "#4b prepare")
    b.record("d|1", ["url": ph])
    writeStore(store, ["A": cache + "/b10.png", "B": "/pics/new.jpg"])   // Sprites on A; owner on B
    _ = b.restoreStore()
    let s = shown(store)
    check(s["A"] == "black", "#4b Sprites' Space A goes back to black (got \(s["A"] ?? "nil"))")
    check(s["B"] == "/pics/new.jpg", "#4b the owner's newer choice on B survives (got \(s["B"] ?? "nil"))")
    check(!b.snapExists && b.originals.isEmpty, "#4b snapshot and records gone after a full restore")
}
do {   // (a) weeks later: the snapshot from an earlier session must not come back.
    let (b, store, cache) = freshBook()
    writeStore(store, ["A": "/pics/2025.jpg"])
    b.backdropChosen(from: "none", to: "b10"); _ = b.prepareWrite()
    b.record("d|1", ["url": "/pics/2025.jpg"])
    writeStore(store, ["A": cache + "/b10.png"])
    // None through the per-Space path (the NSWorkspace fallback): it puts A back and forgets the record.
    writeStore(store, ["A": "/pics/2025.jpg"]); b.forget("d|1")
    check(!b.snapExists, "#4a the snapshot is deleted when the records become empty by the per-Space path")
    writeStore(store, ["A": "/pics/2026.jpg"])   // weeks later the owner changes his wallpaper
    b.backdropChosen(from: "none", to: "b10"); _ = b.prepareWrite()
    b.record("d|1", ["url": ph])
    writeStore(store, ["A": cache + "/b10.png"])
    _ = b.restoreStore()
    check(shown(store)["A"] == "/pics/2026.jpg", "#4a None restores the 2026 choice, not the 2025 one (got \(shown(store)["A"] ?? "nil"))")
}
do {   // the owner changes Space B, then Sprites covers B too: None gives B his newer choice, not the snapshot's.
    let (b, store, cache) = freshBook()
    writeStore(store, ["A": "black", "B": "/pics/old.jpg"])
    b.backdropChosen(from: "none", to: "b10"); _ = b.prepareWrite(); b.record("d|1", ["url": ph])
    writeStore(store, ["A": cache + "/b10.png", "B": "/pics/new.jpg"])
    _ = b.prepareWrite()                                                   // Sprites is about to cover B
    writeStore(store, ["A": cache + "/b10.png", "B": cache + "/b10.png"])
    _ = b.restoreStore()
    check(shown(store)["B"] == "/pics/new.jpg", "#4 a change outside Sprites refreshes the snapshot (got \(shown(store)["B"] ?? "nil"))")
}
do {   // the snapshot is taken when a backdrop is first chosen from None, and only then
    let (b, store, _) = freshBook()
    writeStore(store, ["A": "black"])
    b.backdropChosen(from: "none", to: "b11")
    check(b.snapExists, "#4 snapshot exists right after none -> backdrop")
    b.dropSnapshotIfIdle()   // moving backdrop (no records) -> None, nothing of ours showing
    check(!b.snapExists, "#4 None with no records and nothing of ours showing deletes the snapshot")
}
do {   // a Store that already shows ours (records lost in a crash) is never snapshotted as the owner's choice
    let (b, store, cache) = freshBook()
    writeStore(store, ["A": cache + "/b10.png", "B": "/pics/mine.jpg"])
    b.backdropChosen(from: "none", to: "b10"); _ = b.prepareWrite()
    let r = b.restoreStore()
    check(shown(store)["A"] == cache + "/b10.png" && shown(store)["B"] == "/pics/mine.jpg", "#4 nothing invented for a Space with no known original")
    check(r != nil && r!.unresolved.count > 0 && r!.restored.isEmpty, "#4 an unknown original is reported unresolved")
    check(b.snapExists || !b.originals.isEmpty || r!.unresolved.count > 0, "#4 unresolved keeps the work open")
}
do {   // #9: every Store Space's PNG is in use, not only the current Space's
    let (b, store, cache) = freshBook()
    writeStore(store, ["A": "black", "B": cache + "/b10_old.png"])
    let used = b.storeImagePaths()
    check(used.contains(cache + "/b10_old.png"), "#9 a PNG shown on another Space is in use")
    let t0 = Date()
    let files = (0..<30).map { (path: cache + "/f\($0).png", date: t0.addingTimeInterval(Double($0))) } + [(path: cache + "/b10_old.png", date: Date.distantPast)]
    let gone = prunePaths(files, keep: 24, inUse: used)
    check(!gone.contains(cache + "/b10_old.png") && gone.count == 6, "#9 pruning spares it and drops the 6 oldest others")
}

// R1_MACOS #4: Store leaves Sprites creates; the placeholder; disconnected displays. Hand truth for each case is what the
// fake Store held before Sprites wrote anything.
/// The fake Store with extra per-display leaves: [(space, display, choice)].
func writeStoreWith(_ path: String, _ spaces: [String: String], extra: [(String, String, String)]) {
    var o = storeDict(spaces), sp = o["Spaces"] as! [String: Any]
    for (s, d, c) in extra { var a = sp[s] as! [String: Any], ds = a["Displays"] as! [String: Any]; ds[d] = leaf(c); a["Displays"] = ds; sp[s] = a }
    o["Spaces"] = sp
    try! bp(o).write(to: URL(fileURLWithPath: path))
}
func displaysOf(_ path: String, _ space: String) -> [String] {
    let o = try! PropertyListSerialization.propertyList(from: FileManager.default.contents(atPath: path)!, format: nil) as! [String: Any]
    return (((o["Spaces"] as! [String: Any])[space] as! [String: Any])["Displays"] as? [String: Any]).map { Array($0.keys).sorted() } ?? []
}
do {   // (a) a projector D2 plugged in while a still is on: its new leaf is deleted on None, so it inherits A's black again.
    let (b, store, cache) = freshBook()
    writeStore(store, ["A": "black"])
    b.backdropChosen(from: "none", to: "b10"); _ = b.prepareWrite(); b.record("d|1", ["url": ph])
    writeStoreWith(store, ["A": cache + "/b10.png"], extra: [("A", "D2", cache + "/b10.png")])
    let r = b.restoreStore()
    check(r?.removed == ["/Spaces/A/Displays/D2"] && r?.unresolved == [], "R1M-4a the leaf Sprites created is a tombstone, removed (got \(String(describing: r)))")
    check(displaysOf(store, "A") == ["D1"], "R1M-4a D2's leaf is gone, so it inherits Default (got \(displaysOf(store, "A")))")
    check(shown(store)["A"] == "black" && !b.snapExists && b.originals.isEmpty, "R1M-4a Default back to black, work closed")
}
do {   // (a) a new Space C added while a still is on: removed, not restored to anything invented.
    let (b, store, cache) = freshBook()
    writeStore(store, ["A": "black"])
    b.backdropChosen(from: "none", to: "b10"); _ = b.prepareWrite()
    writeStore(store, ["A": cache + "/b10.png", "C": cache + "/b10.png"])
    let r = b.restoreStore()
    check(Set(r?.removed ?? []) == ["/Spaces/C/Default", "/Spaces/C/Displays/D1"] && shown(store)["C"] == nil && shown(store)["A"] == "black",
          "R1M-4a a new Space's leaves are removed (got \(String(describing: r)), \(shown(store)))")
}
do {   // a leaf the owner set himself after the snapshot (absorbed) is restored, not removed.
    let (b, store, cache) = freshBook()
    writeStore(store, ["A": "black"])
    b.backdropChosen(from: "none", to: "b10"); _ = b.prepareWrite()
    writeStoreWith(store, ["A": cache + "/b10.png"], extra: [("A", "D2", "/pics/projector.jpg")])
    _ = b.prepareWrite()
    writeStoreWith(store, ["A": cache + "/b10.png"], extra: [("A", "D2", cache + "/b10.png")])
    let r = b.restoreStore()
    check(r?.restored.contains("/Spaces/A/Displays/D2") == true && r?.removed == [], "R1M-4 an absorbed new leaf is restored (got \(String(describing: r)))")
    check(displaysOf(store, "A") == ["D1", "D2"], "R1M-4 its leaf stays")
}
do {   // the fallback never sets the placeholder.
    check(fallbackRestorePath(["url": ph]) == nil, "R1M-4 the DefaultDesktop.heic placeholder is never restored through NSWorkspace")
    check(fallbackRestorePath(["url": "/pics/mine.jpg"]) == "/pics/mine.jpg", "R1M-4 a real image is restored")
    check(fallbackRestorePath([:]) == nil && fallbackRestorePath(["url": "pics/rel.jpg"]) == nil, "R1M-4 no or relative url: nothing")
}
do {   // (b) display D2 unplugged before None: its leaf shows ours with no restore; it is resolved-later, not blocking.
    caseN += 1
    let dir = tmpRoot + "/wall\(caseN)"
    try? FileManager.default.removeItem(atPath: dir); try! FileManager.default.createDirectory(atPath: dir + "/Store", withIntermediateDirectories: true)
    var conn: Set<String> = ["D1", "D2"]
    let b = WallpaperBook(store: dir + "/Store/Index.plist", snap: dir + "/config/s.plist", originalsFile: dir + "/config/o.json",
                          cacheDir: dir + "/backdrops", connected: { conn })
    let store = b.store, cache = dir + "/backdrops"
    writeStoreWith(store, ["A": "black"], extra: [("A", "D2", cache + "/b10.png")])   // a crash leftover on D2: no original
    b.backdropChosen(from: "none", to: "b10"); _ = b.prepareWrite()
    writeStoreWith(store, ["A": cache + "/b10.png"], extra: [("A", "D2", cache + "/b10.png")])
    conn = ["D1"]                                                                         // unplugged
    let r = b.restoreStore()
    check(r?.later == ["/Spaces/A/Displays/D2"] && r?.unresolved == [], "R1M-4b a disconnected display's leaf is later, not unresolved (got \(String(describing: r)))")
    check(!b.snapExists, "R1M-4b it does not hold the snapshot open")
    check(!b.liveHasOurs(connectedOnly: true) && b.liveHasOurs(), "R1M-4b liveHasOurs(connectedOnly:) ignores the unplugged display")
    b.backdropChosen(from: "none", to: "b11")
    check(b.snapExists, "R1M-4b the next none -> backdrop takes a fresh snapshot")
    b.dropSnapshotIfIdle()
    check(!b.snapExists, "R1M-4b dropSnapshotIfIdle is not blocked by the unplugged display")
}
// R1_MACOS #11: finalize only after the restore stuck.
do {
    let (b, store, cache) = freshBook()
    writeStore(store, ["A": "black"])
    b.backdropChosen(from: "none", to: "b10"); _ = b.prepareWrite(); b.record("d|1", ["url": ph])
    writeStore(store, ["A": cache + "/b10.png"])
    let r = b.restoreStore(finalize: false)!
    check(b.snapExists && !b.originals.isEmpty, "R1M-11 without finalize the snapshot and records stay")
    writeStore(store, ["A": cache + "/b10.png"])   // WallpaperAgent persisted its old in-memory state over ours
    check(!b.finalize(r) && b.snapExists, "R1M-11 a lost restore is detected and keeps the snapshot")
    let r2 = b.restoreStore(finalize: false)!      // retry once
    check(r2.restored.count == 2 && shown(store)["A"] == "black", "R1M-11 the retry restores again")
    check(b.finalize(r2) && !b.snapExists && b.originals.isEmpty, "R1M-11 once it stuck, the work closes")
}
do {   // pidsNamed against a child we spawn (independent truth: its own pid); relaunchedPid.
    let p = Process(); p.executableURL = URL(fileURLWithPath: "/bin/sleep"); p.arguments = ["3"]
    try! p.run()
    check(pidsNamed("sleep").contains(p.processIdentifier), "R1M-11 pidsNamed finds a spawned child by name")
    check(!pidsNamed("no-such-process-xyz").contains(p.processIdentifier) && pidsNamed("no-such-process-xyz").isEmpty, "R1M-11 an absent name finds nothing")
    p.terminate(); p.waitUntilExit()
    check(relaunchedPid(old: [10], now: [10]) == nil && relaunchedPid(old: [10], now: []) == nil && relaunchedPid(old: [10], now: [10, 77]) == 77,
          "R1M-11 relaunched = a pid not killed")
}
// R1_MACOS #10: the backdrop sits above WallpaperAgent's level (measured on macOS 26.7: Dock's Wallpaper-<space> windows
// at -2147483624, the desktopWindow key -2147483623) and below the icons (-2147483603).
check(backdropWindowLevel() == -2147483622, "R1M-10 backdrop level is desktopWindow + 1 (got \(backdropWindowLevel()))")
check(backdropWindowLevel() < -2147483603 - 1, "R1M-10 still below the desktop icons and the dim layer")
// R1_MACOS #15: each display's own current Space.
do {
    let sep: [[String: Any]] = [["Display Identifier": "AAAA-1", "Current Space": ["id64": 3]], ["Display Identifier": "bbbb-2", "Current Space": ["id64": 9]]]
    check(currentSpace(displayUUID: "AAAA-1", managed: sep) == "3" && currentSpace(displayUUID: "BBBB-2", managed: sep) == "9",
          "R1M-15 separate Spaces: the secondary display gets its own Space (9), not the main one's (3)")
    let spans: [[String: Any]] = [["Display Identifier": "Main", "Current Space": ["id64": 3, "ManagedSpaceID": 3]]]
    check(currentSpace(displayUUID: "AAAA-1", managed: spans) == "3", "R1M-15 spans-displays: one Main entry serves every display")
    check(currentSpace(displayUUID: "CCCC", managed: sep) == nil && currentSpace(displayUUID: "x", managed: []) == nil, "R1M-15 unknown display: nil")
}

// #8: click to session.
do {
    let now = 1_800_000_000.0, fresh = now + 5, start = 1_799_990_000
    let alive: (pid_t) -> Int? = { $0 == 4242 ? start : nil }
    let reused: (pid_t) -> Int? = { $0 == 4242 ? start + 3600 : nil }
    check(clickAction(id: "4242@\(start)", pid: 4242, project: "P", validUntil: fresh, now: now, startOf: alive) == .focus(4242), "#8 fresh, same start: focus")
    check(clickAction(id: "4242@\(start)", pid: 4242, project: "P", validUntil: fresh, now: now, startOf: reused) != .focus(4242), "#8 reused pid (other start time): not focused")
    check(clickAction(id: "4242@\(start)", pid: 4242, project: "P", validUntil: fresh, now: now, startOf: { _ in nil }) != .focus(4242), "#8 exited pid: not focused")
    check(clickAction(id: "4242@\(start)", pid: 4242, project: "P", validUntil: now - 1, now: now, startOf: alive) != .focus(4242), "#8 stale snapshot: not clickable")
    check(clickAction(id: "4242@\(start)", pid: 4242, project: "P", validUntil: nil, now: now, startOf: alive) != .focus(4242), "#8 no valid_until: not clickable")
    check(clickAction(id: "4242", pid: 4242, project: "P", validUntil: fresh, now: now, startOf: alive) != .focus(4242), "#8 an id with no @start cannot be verified")
    check(clickAction(id: "4242@\(start)", pid: 999, project: "P", validUntil: fresh, now: now, startOf: { _ in start }) != .focus(999), "#8 pid disagreeing with the id: not focused")
    check(clickAction(id: "ghost:orchard-mandrake", pid: 0, project: "Orchard_Mandrake", ghost: true, key: "orchard-mandrake", validUntil: fresh, now: now, startOf: alive) == .ghost("orchard-mandrake"), "#8 ghosts from a fresh snapshot stay clickable (#17: by the ghost flag, carrying the key)")
    check(clickAction(id: "ghost:4242@\(start)", pid: 4242, project: "P", ghost: false, key: "p", validUntil: fresh, now: now, startOf: alive) != .ghost("p"), "#17 a real session whose id starts with ghost: is not launched")
    check(clickAction(id: "ghost:x", pid: 0, project: "X", ghost: true, key: "", validUntil: fresh, now: now, startOf: alive) == .ignore("ghost without a project_key"), "#17 a ghost without a key opens nothing")
    // R2_MACOS #2: demo ignores every click; the stale gate covers ghosts (validUntil nil = no snapshot = stale).
    check(clickAction(id: "ghost:hestia", pid: 0, project: "Hestia", ghost: true, key: "hestia", validUntil: fresh, now: now, demo: true, startOf: alive) == .ignore("demo"), "R2M-2 a demo ghost (key of a real project) launches nothing")
    check(clickAction(id: "4242@\(start)", pid: 4242, project: "P", validUntil: fresh, now: now, demo: true, startOf: alive) == .ignore("demo"), "R2M-2 a demo sprite focuses nothing, even a live pid")
    check(clickAction(id: "ghost:hestia", pid: 0, project: "Hestia", ghost: true, key: "hestia", validUntil: nil, now: now, startOf: alive) == .ignore("snapshot stale"), "R2M-2 a ghost with no snapshot is not clickable")
    check(!activateAllAfterScript("none") && !activateAllAfterScript(nil) && !activateAllAfterScript("ok"), "#8 no tty match never raises every window")
    check(snapshotValidUntil(#"{"valid_until": 1793564693.057}"#) == 1793564693.057 && snapshotValidUntil("null") == nil, "#8 valid_until parse")
}
do {   // #8 independent truth for the kernel reads: a child we spawn, and ps.
    let t0 = Int(Date().timeIntervalSince1970)
    let p = Process(); p.executableURL = URL(fileURLWithPath: "/bin/sleep"); p.arguments = ["3"]
    try! p.run()
    let t1 = Int(Date().timeIntervalSince1970)
    let st = processStart(p.processIdentifier)
    check(st != nil && st! >= t0 - 1 && st! <= t1 + 1, "#8 processStart of a fresh child is its spawn time (got \(st.map(String.init) ?? "nil"), \(t0)-\(t1))")
    p.terminate(); p.waitUntilExit()
    check(processStart(p.processIdentifier) == nil, "#8 processStart of an exited pid is nil")
    let ps = Process(); ps.executableURL = URL(fileURLWithPath: "/bin/ps"); ps.arguments = ["-o", "tty=", "-p", String(getpid())]
    let pipe = Pipe(); ps.standardOutput = pipe; try! ps.run(); ps.waitUntilExit()
    let t = String(data: pipe.fileHandleForReading.readDataToEndOfFile(), encoding: .utf8)!.trimmingCharacters(in: .whitespacesAndNewlines)
    let want: String? = t.isEmpty || t.hasPrefix("?") ? nil : "/dev/" + t
    check(processTTY(getpid()) == want, "#8 processTTY agrees with ps (\(processTTY(getpid()) ?? "nil") vs \(want ?? "nil"))")
}

// #10: the moving backdrop stops drawing whenever Sprites is hidden (MACHINE_BACKGROUNDS §9).
for (u, m, l) in [(true, false, false), (false, true, false), (false, false, true)] {
    let v = visibilityPlan(userHidden: u, meeting: m, locked: l)
    check(v.backdropHidden && !v.stagesShown, "#10 hidden (user \(u), meeting \(m), locked \(l)) hides the backdrop too")
    check(backdropPaused(locked: false, asleep: false, hidden: v.backdropHidden, reduceMotion: false), "#10 and pauses its drawing")
}
check(visibilityPlan(userHidden: false, meeting: false, locked: false) == VisibilityPlan(stagesShown: true, backdropHidden: false), "#10 shown: backdrop draws")

// #18: the pending JS queue is bounded and keeps the latest call of each kind, in first-seen order.
do {
    var q = JSQueue()
    q.add("SpritesStage.setCast({\"a\":1})"); q.add("SpritesStage.update({\"seq\":1})")
    for i in 0..<10_000 { q.add("SpritesStage.setCursor({\"x\":\(i),\"y\":0})") }
    q.add("SpritesStage.setCast({\"a\":2})")
    let it = q.items
    check(it.count == 3, "#18 10k cursor moves while unloaded leave 3 queued calls (got \(it.count))")
    check(it.first == "SpritesStage.setCast({\"a\":2})" && it.contains("SpritesStage.setCursor({\"x\":9999,\"y\":0})"), "#18 latest of each kind, first-seen order")
    check(it.firstIndex(of: "SpritesStage.update({\"seq\":1})") == 1, "#18 setCast stays ahead of update")
    var q2 = JSQueue()
    for i in 0..<500 { q2.add("f\(i)()") }
    check(q2.items.count <= JSQueue.cap && q2.items.last == "f499()", "#18 distinct calls are capped, newest kept")
    check(q2.take().count > 0 && q2.items.isEmpty, "#18 take drains")
}
// #18: an observer bag really unregisters (a closed BackdropWindow stops hearing occlusion changes).
do {
    let nc = NotificationCenter(), name = Notification.Name("sprites.test.occlusion")
    var heard = 0
    let bag = ObserverBag(); bag.observe(nc, name, object: nil) { _ in heard += 1 }
    nc.post(name: name, object: nil); bag.removeAll(); nc.post(name: name, object: nil)
    check(heard == 1, "#18 no callback after removeAll (heard \(heard))")
}
// #18: Dock or menu-bar changes (same frames, ids and scale) do not rebuild the stages.
do {
    let a = [ScreenSig(id: 1, frame: CGRect(x: 0, y: 0, width: 1728, height: 1117), scale: 2)]
    let b = [ScreenSig(id: 1, frame: CGRect(x: 0, y: 0, width: 1728, height: 1117), scale: 2)]
    check(!screensChanged(a, b), "#18 same layout: no rebuild")
    check(screensChanged(a, a + [ScreenSig(id: 2, frame: CGRect(x: 1728, y: 0, width: 2560, height: 1440), scale: 1)]), "#18 a display added: rebuild")
    check(screensChanged(a, [ScreenSig(id: 1, frame: CGRect(x: 0, y: 0, width: 1512, height: 982), scale: 2)]), "#18 resolution change: rebuild")
    check(screensChanged(a, [ScreenSig(id: 1, frame: a[0].frame, scale: 1)]), "#18 scale change: rebuild")
}

// #2, #17: ghost launch by project_key. Hand truth: the Fixer response's join (Orchard -> orchard-mandrake, KesMine ->
// kestrel, KestrelWorks -> kestrel-team, MSGRAPH -> microsoftgraphaccess); a key the table lacks opens nothing.
do {
    let T: [[String: Any]] = [
        ["key": "orchard-mandrake", "name": "Orchard_Mandrake", "dir": "/Users/x/dev/Orchard_Mandrake", "alias": "Orchard"],
        ["key": "kestrel", "name": "KestrelWorks_Mandrake", "dir": "/Users/x/dev/KestrelWorks_Mandrake", "alias": "KesMine"],
        ["key": "kestrel-team", "name": "KestrelWorks", "dir": "/Users/x/dev/KestrelWorks", "alias": "KestrelWorks"],
        ["key": "microsoftgraphaccess", "name": "MicrosoftGraphAccess", "dir": "/Users/x/dev/MicrosoftGraphAccess", "alias": "MSGRAPH"],
        ["key": "custos", "name": "Custos", "dir": "/Users/x/dev/Custos", "alias": NSNull()],
        ["key": "evil", "name": "Evil", "dir": "/Users/x/dev/../x", "alias": "a; rm -rf ~"],
        ["key": NSNull(), "name": "MandrakeVisualize", "dir": "/Users/x/dev/MandrakeWorkflows/visualize", "alias": "MandrakeVisualize"],
    ]
    check(ghostPlan(key: "orchard-mandrake", table: T) == .launch("Orchard"), "#2 ghost Orchard_Mandrake runs launch Orchard")
    check(ghostPlan(key: "kestrel", table: T) == .launch("KesMine"), "#2 ghost KestrelWorks_Mandrake runs launch KesMine (not the team alias)")
    check(ghostPlan(key: "kestrel-team", table: T) == .launch("KestrelWorks"), "#2 ghost of the team repo runs launch KestrelWorks")
    check(ghostPlan(key: "microsoftgraphaccess", table: T) == .launch("MSGRAPH"), "#2 ghost MicrosoftGraphAccess runs launch MSGRAPH")
    check(ghostPlan(key: "custos", table: T) == .claude("/Users/x/dev/Custos"), "#17 no alias: claude in the registry directory")
    if case .refuse = ghostPlan(key: "evil", table: T) {} else { check(false, "#17 a non-identifier alias and a dir with .. open nothing") }
    if case .refuse = ghostPlan(key: "..", table: T) {} else { check(false, "#17 key .. opens nothing (was claude in ~)") }
    if case .refuse = ghostPlan(key: "../x", table: T) {} else { check(false, "#17 key ../x opens nothing (was claude in ~/x)") }
    if case .refuse = ghostPlan(key: "mandrakevisualize", table: T) {} else { check(false, "#2 a keyless launch row matches no ghost") }
    if case .refuse = ghostPlan(key: "orchard-mandrake", table: []) {} else { check(false, "#17 no table: nothing opens") }
    let t0 = Date(timeIntervalSince1970: 1000)
    check(!ghostDebounced(last: nil, now: t0), "#17 first click goes through")
    check(ghostDebounced(last: t0, now: t0.addingTimeInterval(2.9)), "#17 a second click within 3 s of a launch is debounced")
    check(!ghostDebounced(last: t0, now: t0.addingTimeInterval(3.1)), "#17 after 3 s it goes through")
}

print("\(passed) passed, \(failed) failed")
exit(failed == 0 ? 0 : 1)
