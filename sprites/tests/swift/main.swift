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

// CLICK-3 (owner, 2026-11-05: "I really do want to be able to DOUBLE-CLICK on a Sprite and have it open the
// relevant Claude session or switch Spaces/Focus to it"). The gesture is the double-click; the single click must
// still never be eaten (R3-SPEC #1, #2: "no behaviour may block a click"), so one click acts too, after the
// double-click window has passed with no second click. clickGesture is the pure rule the host follows.
do {
    check(clickGesture(count: 2) == .act, "CLICK-3 the second click of a double-click acts at once")
    check(clickGesture(count: 1) == .waitForSecond, "CLICK-3 a single click waits out the double-click window")
    check(clickGesture(count: 3) == .alreadyActed, "CLICK-3 a third click does not act again (one action per gesture)")
    check(clickGesture(count: 4) == .alreadyActed, "CLICK-3 a fourth click does not act again")
    check(clickGesture(count: 0) == .waitForSecond, "CLICK-3 a clickCount the window server did not set is treated as one click")
    // The fallback delay must be the user's own double-click interval, never a hardcoded guess, and must stay sane
    // when the preference is absent or absurd.
    check(singleClickDelay(doubleClickInterval: 0.5) == 0.5, "CLICK-3 the delay is the user's double-click interval")
    check(singleClickDelay(doubleClickInterval: 0) == 0.25, "CLICK-3 no preference: a 0.25 s default, not zero")
    check(singleClickDelay(doubleClickInterval: 9) == 1.0, "CLICK-3 an absurd interval is capped at 1 s")
    check(singleClickDelay(doubleClickInterval: 0.05) == 0.15, "CLICK-3 a tiny interval is floored at 0.15 s")
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

// Space switch for a deliberate click (2026-11-04): swoosh is off, so Sprites posts "Switch to Desktop N" itself.
do {
    let disp: [[String: Any]] = [["Display Identifier": "Main", "Current Space": ["ManagedSpaceID": 5],
        "Spaces": [["ManagedSpaceID": 1, "type": 0], ["ManagedSpaceID": 3, "type": 0], ["ManagedSpaceID": 9, "type": 4],
                   ["ManagedSpaceID": 4, "type": 0], ["ManagedSpaceID": 5, "type": 0]]]]
    func hk(_ on: Bool, _ key: Int = 20) -> [String: Any] { ["enabled": on, "value": ["parameters": [65535, key, 262144], "type": "standard"]] }
    let keys: [String: Any] = ["118": hk(true, 18), "119": hk(true, 19), "120": hk(true, 20), "121": hk(false, 21)]
    check(spaceSwitchPlan(displays: disp, windowSpaces: [3], hotkeys: keys) == .desktop(2, keyCode: 19, flags: 262144), "space: 2nd user desktop -> Ctrl-2")
    check(spaceSwitchPlan(displays: disp, windowSpaces: [4], hotkeys: keys) == .desktop(3, keyCode: 20, flags: 262144), "space: fullscreen space is not numbered")
    if case .stay = spaceSwitchPlan(displays: disp, windowSpaces: [5], hotkeys: keys) { check(true, "") } else { check(false, "space: current space stays") }
    if case .stay = spaceSwitchPlan(displays: disp, windowSpaces: [1, 3], hotkeys: keys) { check(true, "") } else { check(false, "space: sticky window stays") }
    if case .stay = spaceSwitchPlan(displays: disp, windowSpaces: [], hotkeys: keys) { check(true, "") } else { check(false, "space: no space stays") }
    if case .unreachable = spaceSwitchPlan(displays: disp, windowSpaces: [9], hotkeys: keys) { check(true, "") } else { check(false, "space: fullscreen unreachable") }
    let d4: [[String: Any]] = [["Current Space": ["ManagedSpaceID": 1], "Spaces": [["ManagedSpaceID": 1, "type": 0], ["ManagedSpaceID": 3, "type": 0],
                                ["ManagedSpaceID": 4, "type": 0], ["ManagedSpaceID": 5, "type": 0]]]]
    if case .unreachable = spaceSwitchPlan(displays: d4, windowSpaces: [5], hotkeys: keys) { check(true, "") } else { check(false, "space: disabled shortcut unreachable") }
    if case .unreachable = spaceSwitchPlan(displays: disp, windowSpaces: [77], hotkeys: keys) { check(true, "") } else { check(false, "space: unknown space unreachable") }
    check(spaceSwitchPlan(displays: d4, windowSpaces: [3], hotkeys: ["119": ["enabled": 1, "value": ["parameters": [65535, 19, 262144]]]]) == .desktop(2, keyCode: 19, flags: 262144), "space: enabled as 1")
    check(focusedWindow("ok 26848") == 26848 && focusedWindow("ok") == 0 && focusedWindow("none") == nil && focusedWindow(nil) == nil, "focusedWindow parses the script reply")
}

// MARK: SPRITES_UNIFY_MONITORS_AS_ONE — one wandering area across every screen.
// Truth is hand-derived from the arrangement geometry, not from the code under test. The Desktop's real arrangement was
// MEASURED 2026-11-05 (probe over NSScreen): LG TV (main) frame (0,0,1920,1080) scale 2, TH-55CQE1 (-1920,-103,1920,1080)
// scale 2 — NOT the equal-height, aligned case, so the offset cases below are live, not hypothetical.
do {
    // --- the Laptop regression guard: ONE screen must come out exactly as before the change ---
    let lf = CGRect(x: 0, y: 0, width: 1728, height: 1117), lv = CGRect(x: 0, y: 0, width: 1728 - 70, height: 1117 - 33)
    let one = spanLayout(frames: [lf], visibleFrames: [lv])
    check(one.world == lf, "span: one screen, world is that screen's frame")
    check(one.size == CGSize(width: 1728, height: 1117), "span: one screen, world size unchanged")
    check(one.rects == [CGRect(x: 0, y: 0, width: 1728, height: 1117)], "span: one screen sits at the world origin")
    // The literal is what visibleStageRect produces today for this frame/visible pair; the host suite asserts the two
    // helpers agree (it builds Stage.swift too), so setVisible stays byte-identical on the Laptop.
    check(one.visible == [CGRect(x: 0, y: 33, width: 1658, height: 1084)], "span: one screen visible (menu bar 33, Dock 70)")
    check(spanVisibleRect(one) == CGRect(x: 0, y: 33, width: 1658, height: 1084), "span: one screen's walkable area IS its visible rect")
    check(deadSpaceFraction(one) == 0, "span: one screen has no dead space")

    // --- this Desktop, as measured: secondary LEFT of main at NEGATIVE x, offset 103 px DOWN ---
    let m = CGRect(x: 0, y: 0, width: 1920, height: 1080), s2 = CGRect(x: -1920, y: -103, width: 1920, height: 1080)
    let mv = CGRect(x: 0, y: 0, width: 1862, height: 1050), s2v = CGRect(x: -1920, y: -103, width: 1920, height: 1050)
    let two = spanLayout(frames: [m, s2], visibleFrames: [mv, s2v])
    check(two.world == CGRect(x: -1920, y: -103, width: 3840, height: 1183), "span: Desktop world is the union, 3840x1183")
    // main's top IS the world's top (world.maxY == m.maxY == 1080): y 0. The secondary hangs 103 px lower.
    check(two.rects[0] == CGRect(x: 1920, y: 0, width: 1920, height: 1080), "span: main screen sits right, at world y 0")
    check(two.rects[1] == CGRect(x: 0, y: 103, width: 1920, height: 1080), "span: a NEGATIVE-origin secondary maps to world x 0, y 103")
    check(abs(deadSpaceFraction(two) - (1183.0 * 3840 - 2 * 1920.0 * 1080) / (1183.0 * 3840)) < 1e-12, "span: Desktop dead-space fraction is the union minus both screens")
    check(deadSpaceFraction(two) > 0.08 && deadSpaceFraction(two) < 0.09, "span: the measured Desktop really has ~8.7 % dead space")
    // walkable = the common band both screens show: full 3840 wide, from the lower top edge to the higher bottom edge
    let w2 = spanVisibleRect(two)
    check(w2.width == 3782, "span: the walkable area spans BOTH monitors (1920 + 1862 px), which is the whole point")
    check(w2 == CGRect(x: 0, y: 133, width: 3782, height: 947), "span: walkable band is the 947 px both screens share, 58 px of main lost to its Dock")
    // every corner of the walkable area is on a real screen: nothing can wander into dead space
    for (nm, p) in [("top-left", CGPoint(x: w2.minX + 1, y: w2.minY + 1)), ("top-right", CGPoint(x: w2.maxX - 1, y: w2.minY + 1)),
                    ("bottom-left", CGPoint(x: w2.minX + 1, y: w2.maxY - 1)), ("bottom-right", CGPoint(x: w2.maxX - 1, y: w2.maxY - 1))] {
        check(screenOf(worldPoint: p, two) >= 0, "span: walkable \(nm) corner is on a real screen")
    }
    // the dead bands themselves are correctly reported as belonging to no screen
    check(screenOf(worldPoint: CGPoint(x: 100, y: 50), two) == -1, "span: the secondary's missing top band is dead space")
    check(screenOf(worldPoint: CGPoint(x: 3000, y: 1150), two) == -1, "span: the main's missing bottom band is dead space")
    check(screenOf(worldPoint: CGPoint(x: 3000, y: 50), two) == 0, "span: a point high on the right is the main screen")
    check(screenOf(worldPoint: CGPoint(x: 100, y: 1150), two) == 1, "span: a point low on the left is the secondary")
    // crossing the seam: one step in world x moves from one panel to the other, with no gap between them
    check(screenOf(worldPoint: CGPoint(x: 1919, y: 500), two) == 1 && screenOf(worldPoint: CGPoint(x: 1920, y: 500), two) == 0,
          "span: the seam is continuous — x 1919 is the secondary, x 1920 the main, no gap")

    // --- equal heights, top aligned (the brief's 'easy case'): the whole combined visible area is walkable ---
    let a = CGRect(x: 0, y: 0, width: 1920, height: 1080), b = CGRect(x: 1920, y: 0, width: 1920, height: 1080)
    let flat = spanLayout(frames: [a, b], visibleFrames: [CGRect(x: 0, y: 0, width: 1920, height: 1055), CGRect(x: 1920, y: 0, width: 1920, height: 1055)])
    check(flat.world == CGRect(x: 0, y: 0, width: 3840, height: 1080), "span: aligned pair unions to 3840x1080")
    check(deadSpaceFraction(flat) == 0, "span: aligned equal heights have NO dead space")
    check(spanVisibleRect(flat) == CGRect(x: 0, y: 25, width: 3840, height: 1055), "span: aligned pair is walkable across its whole visible area")

    // --- unequal heights (a laptop beside a monitor) ---
    let big = CGRect(x: 0, y: 0, width: 2560, height: 1440), small = CGRect(x: 2560, y: 0, width: 1440, height: 900)
    let un = spanLayout(frames: [big, small], visibleFrames: [big, small])
    check(un.world == CGRect(x: 0, y: 0, width: 4000, height: 1440), "span: unequal heights union")
    check(un.rects[0] == CGRect(x: 0, y: 0, width: 2560, height: 1440), "span: the taller screen fills the world height")
    check(un.rects[1] == CGRect(x: 2560, y: 540, width: 1440, height: 900), "span: a SHORTER bottom-aligned screen is pushed down in world y")
    let wu = spanVisibleRect(un)
    check(wu == CGRect(x: 0, y: 540, width: 4000, height: 900), "span: unequal heights walk the shared 900 px band across both")
    check(wu.width == 4000, "span: unequal heights still span both screens")
    // 4000x1440 union = 5 760 000; covered 2560*1440 + 1440*900 = 4 982 400; dead 777 600 = 13.5 %
    check(abs(deadSpaceFraction(un) - 777_600.0 / 5_760_000.0) < 1e-12, "span: unequal heights leave 13.5 % dead space, and it is excluded")

    // --- a vertical stack (one above the other): the shared band is the narrower width, not zero ---
    let top = CGRect(x: 0, y: 1080, width: 1920, height: 1080), bot = CGRect(x: 0, y: 0, width: 1920, height: 1080)
    let st = spanLayout(frames: [top, bot], visibleFrames: [top, bot])
    check(st.world == CGRect(x: 0, y: 0, width: 1920, height: 2160), "span: a stacked pair unions vertically")
    check(st.rects[0] == CGRect(x: 0, y: 0, width: 1920, height: 1080), "span: the upper screen is world y 0")
    check(st.rects[1] == CGRect(x: 0, y: 1080, width: 1920, height: 1080), "span: the lower screen is world y 1080")
    check(spanVisibleRect(st) == CGRect(x: 0, y: 0, width: 1920, height: 2160), "span: a stack is walkable over its whole height")
    check(deadSpaceFraction(st) == 0, "span: an exact stack has no dead space")

    // --- an L shape: three screens where the inscribed rect must NOT include the notch ---
    let l1 = CGRect(x: 0, y: 0, width: 1920, height: 1080), l2 = CGRect(x: 1920, y: 0, width: 1920, height: 1080), l3 = CGRect(x: 0, y: 1080, width: 1920, height: 1080)
    let L = spanLayout(frames: [l1, l2, l3], visibleFrames: [l1, l2, l3])
    check(L.world == CGRect(x: 0, y: 0, width: 3840, height: 2160), "span: L world is the bounding box")
    check(deadSpaceFraction(L) > 0.24 && deadSpaceFraction(L) < 0.26, "span: the L's empty quadrant is a quarter of the union")
    let wl = spanVisibleRect(L)
    check(wl.width * wl.height == 3840 * 1080, "span: the L's walkable rect is the full-width band, never the empty quadrant")
    check(screenOf(worldPoint: CGPoint(x: wl.midX, y: wl.midY), L) >= 0, "span: the L's walkable centre is on a real screen")
    // the empty quadrant is the top-right in world coords (l3 is the upper-left); confirm it is excluded
    check(!wl.contains(CGPoint(x: 3000, y: 100)), "span: the L's empty quadrant is NOT walkable")

    // --- the conversions, which the ticket flags as the error-prone part ---
    // a window on the secondary, reported by CGWindowList in primary-top-left coordinates
    check(worldRectFromCG(CGRect(x: -1920, y: 103, width: 400, height: 300), world: two.world, primaryMaxY: 1080)
            == CGRect(x: 0, y: 103, width: 400, height: 300), "span: a CG rect on the negative-origin secondary maps into the world")
    check(worldRectFromCG(CGRect(x: 0, y: 0, width: 400, height: 300), world: two.world, primaryMaxY: 1080)
            == CGRect(x: 1920, y: 0, width: 400, height: 300), "span: a CG rect at the primary's top-left is world (1920, 0)")
    // the Cocoa point conversion, against the per-screen one it replaces
    check(worldPoint(CGPoint(x: 10, y: 1070), world: two.world) == CGPoint(x: 1930, y: 10), "span: a Cocoa point near the main's top-left")
    check(worldPoint(CGPoint(x: -1910, y: 967), world: two.world) == CGPoint(x: 10, y: 113), "span: a Cocoa point on the secondary")
    // a one-screen world must agree with the per-screen helper exactly (the Laptop guard, at the point level)
    for p in [CGPoint(x: 0, y: 0), CGPoint(x: 864, y: 558), CGPoint(x: 1728, y: 1117), CGPoint(x: 5, y: 1112)] {
        let w = worldPoint(p, world: one.world)
        check(w.x == p.x && w.y == lf.maxY - p.y, "span: one screen, world point == stage point at (\(Int(p.x)),\(Int(p.y)))")
    }
    check(panelScale(2) == 2 && panelScale(3) == 2 && panelScale(1) == 1, "span: each panel keeps its own backing scale, clamped at 2")

    // degenerate inputs must not crash or produce a bogus world
    check(spanLayout(frames: [], visibleFrames: []).world == .zero, "span: no screens, zero world")
    check(largestInscribedRect([]) == .zero, "span: no rects, zero inscribed rect")
    check(largestInscribedRect([CGRect(x: 5, y: 7, width: 100, height: 50)]) == CGRect(x: 5, y: 7, width: 100, height: 50), "span: one rect inscribes itself")
    // two screens that touch at a corner only share no band: the inscribed rect is one of them, never the union
    let diag1 = CGRect(x: 0, y: 0, width: 800, height: 600), diag2 = CGRect(x: 800, y: 600, width: 800, height: 600)
    let dg = largestInscribedRect([diag1, diag2])
    check(dg == diag1 || dg == diag2, "span: corner-touching screens fall back to ONE screen, never a rect over dead space")
}

// MARK: SQUISH/BLUR — the drawable and the viewport output (regressions of f48a980, owner, 2026-11-05)
// Truth is hand-derived from the measured arrangement and from what CAMetalLayer does with a drawable that does not
// match its layer: it RESCALES it into the layer's bounds. Both numbers below come from that geometry, not the code.
do {
    // --- the stale-drawable guard tested WIDTH ONLY, and this Desktop's two screens share a width ---
    let d = CGSize(width: 3840, height: 2160)          // one 1920x1080 @2 panel, correct
    check(!drawableStale(d, w: 3840, h: 2160), "squish: a drawable that already matches is left alone")
    check(drawableStale(d, w: 2560, h: 2160), "squish: a different WIDTH is stale (the old guard caught this one)")
    // 🔴 the regression itself: equal width, different height. The old `width != w` test said "fine" and the drawable
    // kept the other viewport's size, so the content was scaled — the owner's "kept something from one screen to another".
    check(drawableStale(d, w: 3840, h: 2366), "squish: EQUAL WIDTH but a different height is stale too (the bug)")
    check(drawableStale(.zero, w: 3840, h: 2160), "squish: a fresh layer (0x0) is stale")
    check(drawableStale(CGSize(width: 7680, height: 2366), w: 3840, h: 2160), "squish: a union-sized drawable on a one-screen panel is stale")

    // --- a viewport's output is its PANEL, never the world ---
    // Measured Desktop: both panels 1920x1080 @2; the world is the union 3840x1183.
    let o0 = viewportOutput(panelSize: CGSize(width: 1920, height: 1080), backing: 2)
    check(o0.size == CGSize(width: 1920, height: 1080), "squish: the primary viewport renders its PANEL's size, not the union's")
    check(o0.scale == 2, "squish: the primary viewport renders at its own backing scale")
    // The device-pixel numbers that made the measured 2.000x horizontal / 1.095x vertical squish:
    let panelPx = CGSize(width: o0.size.width * o0.scale, height: o0.size.height * o0.scale)
    let worldPx = CGSize(width: 3840 * 2, height: 1183 * 2)
    check(panelPx == CGSize(width: 3840, height: 2160), "squish: the correct primary drawable is 3840x2160 device px")
    check(worldPx == CGSize(width: 7680, height: 2366), "squish: the world is 7680x2366 device px — what f48a980 wrongly used")
    check(worldPx.width / panelPx.width == 2.0, "squish: the regression compressed the primary panel exactly 2x horizontally")
    check(abs(worldPx.height / panelPx.height - 1.0953703703703703) < 1e-12, "squish: and ~1.095x vertically — hence blurry, not just narrow")
    // A mixed-DPI pair: each panel keeps its own scale even though the recording is made at the finest (clamped at 2).
    check(viewportOutput(panelSize: CGSize(width: 1440, height: 900), backing: 1).scale == 1, "squish: a 1x panel renders at 1x")
    check(viewportOutput(panelSize: CGSize(width: 1920, height: 1080), backing: 3).scale == 2, "squish: a >2x panel is still clamped at 2")
    // 🔴 the Laptop guard: one screen means output == world, so nothing about the single-screen path moves.
    let lone = CGRect(x: 0, y: 0, width: 1728, height: 1117)
    let lo = viewportOutput(panelSize: lone.size, backing: 2)
    check(lo.size == lone.size && lo.scale == 2, "squish: with ONE screen the panel IS the world — Laptop unchanged")
    check(!drawableStale(CGSize(width: 1728 * 2, height: 1117 * 2), w: Int(lone.width * 2), h: Int(lone.height * 2)),
          "squish: the Laptop's own drawable is never considered stale")
}

print("\(passed) passed, \(failed) failed")
exit(failed == 0 ? 0 : 1)
