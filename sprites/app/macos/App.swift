import AppKit
import Carbon.HIToolbox
import WebKit

@main
final class AppDelegate: NSObject, NSApplicationDelegate {
    static func main() {
        let app = NSApplication.shared
        let d = AppDelegate()
        app.delegate = d
        app.setActivationPolicy(.accessory)
        app.run()
    }

    /// ONE stage for the whole world (SPRITES_UNIFY_MONITORS_AS_ONE): one simulation, one panel per screen. It was one
    /// independent Stage per NSScreen, which is why every sprite existed once per monitor.
    var stage: Stage?
    var status: NSStatusItem!
    var settings: SettingsWindow?
    var stateWatch: FileWatch?
    var castWatch: FileWatch?
    var lastState: String? = nil
    var lastCast: String? = nil
    var userHidden = false, meeting = false, locked = false
    var hotKey: EventHotKeyRef?
    var hotKeyOK = true
    var showItem: NSMenuItem!, meetingItem: NSMenuItem!, demoItem: NSMenuItem!
    /// Demo mode: a random cast floats around; the state file is ignored. Remembered; a fresh
    /// install with no state file starts in it so something shows.
    var demo = false
    var lastCursor = ""
    var behaviorsWatch: FileWatch?
    var lastBehaviors = "{}"
    var lastActivity = "", lastWindows = ""
    var appOfSession: [pid_t: pid_t] = [:]   // session pid -> owning terminal app pid
    let dim = DimLayer()
    let backdrop = Backdrop()   // Backdrop.swift: behaviors.json backdrop/backdropSpeed
    /// "Dim desktop icons": behaviors.json key "dimIcons", integer percent 0-80; missing = 45; 0 = off.
    func dimPercent() -> Double {
        if let v = UserDefaults.standard.volatileDomain(forName: UserDefaults.argumentDomain)["dimIcons"],
           let a = Double("\(v)") {
            return min(80, max(0, a))   // `-dimIcons N` on the command line (tests); never persisted
        }
        return dimIconsPercent(behaviorsJSON: lastBehaviors)   // Decide.swift (0 and 1 are numbers, review R1 #3)
    }
    func applyDim() { dim.set(CGFloat(dimPercent() / 100)) }
    /// Default ON: a missing key or file means on.
    func behaviorOn(_ k: String) -> Bool {
        guard let d = lastBehaviors.data(using: .utf8),
              let o = try? JSONSerialization.jsonObject(with: d) as? [String: Any] else { return true }
        return (o[k] as? Bool) ?? true
    }

    var hidden: Bool { userHidden || meeting || locked }
    /// Displays asleep, user session switched away (review R2_MACOS #8): the stages pause, as WebKit pauses a hidden page.
    var asleep = false, away = false
    /// `--qa-second-instance`: a QA copy beside the owner's app; no hotkey, backdrop or dim (review R1_MACOS #3).
    var qaSecond = false
    var instanceLock: InstanceLock?
    let ttyWindows = TTYWindowCache()
    /// SPAN: one simulation feeds every panel, so it may pause only when NO panel still needs frames — otherwise a
    /// full-screen video on one monitor would freeze the sprites on the other.
    func pauseState() -> Bool {
        guard let st = stage, !st.screens.isEmpty else { return true }
        return st.screens.allSatisfy { stagePaused(hidden: hidden, fsFaded: $0.fsFaded, asleep: asleep, away: away, occluded: $0.occluded) }
    }
    func pushPaused() { stage?.js("SpritesStage.setPaused(\(pauseState()))") }

    func applicationDidFinishLaunching(_ n: Notification) {
        _ = Paths.sprites   // fail loudly now, by name, if the folder is missing
        if let d = UserDefaults.standard.object(forKey: "demo") as? Bool { demo = d }
        else {
            demo = !FileManager.default.fileExists(atPath: Paths.state)
        }
        let args = CommandLine.arguments
        if args.contains("--demo") { demo = true } else if args.contains("--no-demo") { demo = false }
        log("state path: \(Paths.state)")
        if let i = args.firstIndex(of: "--native-frames"), args.count > i + 1 { exit(NativeHost.renderFrames(spec: args[i + 1])) }   // QA: offscreen, no window
        if let i = args.firstIndex(of: "--native-qos-bench"), args.count > i + 1 { exit(NativeHost.qosBench(seconds: Double(args[i + 1]) ?? 10)) }   // QA: offscreen
        if let a = Optional(CommandLine.arguments), let i = a.firstIndex(of: "--backdrop-export"), a.count > i + 5 {   // QA: one offscreen frame, then exit
            exit(backdrop.exportPNG(a[i + 1], w: Int(a[i + 2]) ?? 1728, h: Int(a[i + 3]) ?? 1117, t: Double(a[i + 4]) ?? 0, to: a[i + 5]) ? 0 : 1)
        }
        if let i = args.firstIndex(of: "--focus-pid"), args.count > i + 1, let fp = pid_t(args[i + 1]), let st = processStart(fp) {   // QA: a click's focus path, then exit
            activateSession(pid: fp, startedAt: st)
            DispatchQueue.main.asyncAfter(deadline: .now() + 6) { exit(0) }
            return
        }
        // Review R1_MACOS #3: one Sprites per login. Another pid with our bundle id (any build tree) or the lock held = exit.
        qaSecond = args.contains("--qa-second-instance")
        let me = getpid()
        let same = NSRunningApplication.runningApplications(withBundleIdentifier: Bundle.main.bundleIdentifier ?? "com.mandrake.sprites").map { $0.processIdentifier }
        if !qaSecond { instanceLock = InstanceLock() }
        switch instancePlan(me: me, sameBundle: same, lockAcquired: instanceLock != nil, qaSecond: qaSecond) {
        case .exitDuplicate(let why): log("\(why); exiting"); exit(0)
        case .runAsQASecond: log("QA second instance: no hotkey, backdrop or dim")
        case .run: break
        }
        if !qaSecond { dim.layout(); applyDim() }   // FileWatch never fires for an absent behaviors.json
        buildStages()
        buildMenu()
        if !qaSecond { registerHotKey() } else { hotKeyOK = false }

        stateWatch = FileWatch(Paths.state) { [weak self] d in
            self?.pushState(d.flatMap { String(data: $0, encoding: .utf8) })
        }
        castWatch = FileWatch(Paths.cast, every: 2.0) { [weak self] d in
            guard let self, let d, let s = String(data: d, encoding: .utf8) else { return }
            self.lastCast = s
            self.broadcast("SpritesStage.setCast(\(s))")
        }

        let ws = NSWorkspace.shared.notificationCenter
        backdrop.aetherSprites = { [weak self] in   // the stage's hit circles, world stage px -> CG global points
            guard let st = self?.stage else { return [] }
            let w = st.span.world, top = NSScreen.screens.first?.frame.maxY ?? 0
            return st.hits.map { AetherHit(pos: CGPoint(x: $0.x + w.minX, y: $0.y - w.maxY + top), r: $0.r, id: $0.id, species: $0.concept, key: $0.key) }
        }
        backdrop.aetherDrift = { [weak self] d in self?.settings?.mirrorAetherDrift(d) }
        backdrop.aetherCurrents = { [weak self] k, cur in   // wake reader: each sprite's leftover current, to the stage
            var m: [String: [Double]] = [:]
            for (id, v) in cur { m[id] = [(v.0 * 100).rounded() / 100, (v.1 * 100).rounded() / 100] }
            self?.broadcast("SpritesStage.setCurrents(\(k),\(jsonString(m)))")
        }
        behaviorsWatch = FileWatch(Paths.behaviors, every: 2.0) { [weak self] d in
            guard let self else { return }
            self.lastBehaviors = d.flatMap { String(data: $0, encoding: .utf8) } ?? "{}"
            self.broadcast("SpritesStage.setBehaviors(\(self.lastBehaviors))")
            if !self.qaSecond { self.applyDim(); self.backdrop.apply(self.lastBehaviors) }
            self.pushWindows()
        }
        // Host polling, one shared 10 Hz tick (CPU, docs/NATIVE_PORT.md): activity every 0.5 s; windows and focus every 0.5 s,
        // but the expensive CGWindowList read happens only once per tick and is shared; app switches and Space changes
        // push at once (notifications below), so the poll is only a safety net for moves and resizes.
        Timer.scheduledTimer(withTimeInterval: 0.1, repeats: true) { [weak self] t in
            guard let self else { return }
            self.hostTick += 1
            if self.mouseNear || self.hostTick % 2 == 0 { self.trackMouse() }   // 10 Hz near a sprite, else 5 Hz
            if self.hostTick % 5 == 0 { self.pushActivity(); self.hostWindowTick(self.hostTick / 5) }
            if self.hostTick % 50 == 0 { self.pushProjects() }   // Waypoint or registry edited: a stat of five files
        }.tolerance = 0.02
        // R1_SPEC S12: a Space change moves the focus and the windows together, at once and once more after 0.4 s
        // (the window list settles late after the switch animation).
        ws.addObserver(forName: NSWorkspace.activeSpaceDidChangeNotification, object: nil, queue: .main) { [weak self] _ in
            self?.pushFocus(); self?.pushWindows()
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.4) { self?.lastFocus = ""; self?.pushFocus(); self?.pushWindows() }
        }
        // R2_MACOS #8 (host half): display sleep and fast user switching pause the stages.
        for (n, f) in [(NSWorkspace.screensDidSleepNotification, { (d: AppDelegate) in d.asleep = true }),
                       (NSWorkspace.screensDidWakeNotification, { (d: AppDelegate) in d.asleep = false }),
                       (NSWorkspace.sessionDidResignActiveNotification, { (d: AppDelegate) in d.away = true }),
                       (NSWorkspace.sessionDidBecomeActiveNotification, { (d: AppDelegate) in d.away = false })] {
            ws.addObserver(forName: n, object: nil, queue: .main) { [weak self] _ in
                guard let self else { return }; f(self); self.pushPaused() }
        }
        NotificationCenter.default.addObserver(forName: NSWindow.didChangeOcclusionStateNotification, object: nil, queue: .main) { [weak self] n in
            guard let self, let st = self.stage, let w = n.object as? NSWindow,
                  let i = st.screens.firstIndex(where: { $0.panel === w }) else { return }
            let occ = !w.occlusionState.contains(.visible)
            if occ != st.screens[i].occluded { st.setOccluded(i, occ); self.pushPaused() }
        }

        // Click-through except over a sprite: the cursor is polled (no TCC grant needed) by the shared tick above, and at
        // 30 Hz while it is near a sprite so click-through flips in time.
        Timer.scheduledTimer(withTimeInterval: 1.0 / 30, repeats: true) { [weak self] _ in
            guard let self, self.mouseNear else { return }
            self.trackMouse()
        }.tolerance = 0.005
        // CLICK-2 (measured 2026-11-05): polling alone armed capture TOO LATE. A click arriving in the same breath as
        // the move found ignoresMouseEvents still true and fell through to the desktop — the click was posted at T and
        // capture armed at T+24..81 ms, losing 4 of 5 move-then-click gestures. A global mouse-moved monitor needs no
        // TCC grant and arms synchronously with the move, so the panel is already capturing when the click lands.
        // It fires on every move anywhere, so the handler is deliberately cheap: hit geometry only (captureNeeded),
        // reusing the blocker verdict the poll above maintains. No CGWindowList read here.
        mouseMonitor = NSEvent.addGlobalMonitorForEvents(matching: [.mouseMoved, .leftMouseDragged]) { [weak self] _ in
            self?.armCapture()
        }

        ws.addObserver(forName: NSWorkspace.didActivateApplicationNotification, object: nil, queue: .main) { [weak self] _ in
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.15) { self?.pushFocus(); self?.pushWindows() }
        }
        NotificationCenter.default.addObserver(forName: NSApplication.didChangeScreenParametersNotification,
                                               object: nil, queue: .main) { [weak self] _ in
            guard let self else { return }
            if !self.qaSecond { self.dim.layout() }
            self.pushVisible()   // R1_SPEC S4: the Dock moved or resized, or the menu bar changed
            // also fires on Dock and menu-bar changes: rebuild (reload) the stages only when the layout changed (R1 #18)
            let sig = screenSigs()
            if screensChanged(self.builtFor, sig) { self.buildStages() }
        }
        let dnc = DistributedNotificationCenter.default()
        dnc.addObserver(forName: .init("com.apple.screenIsLocked"), object: nil, queue: .main) { [weak self] _ in
            self?.locked = true; self?.applyVisibility()
        }
        dnc.addObserver(forName: .init("com.apple.screenIsUnlocked"), object: nil, queue: .main) { [weak self] _ in
            self?.locked = false; self?.applyVisibility()
        }
        signal(SIGTERM, SIG_IGN)
        let term = DispatchSource.makeSignalSource(signal: SIGTERM, queue: .main)
        term.setEventHandler { NSApp.terminate(nil) }
        term.resume()
        termSource = term
        if CommandLine.arguments.contains("--settings") { openSettings() }   // smoke tests
    }
    var termSource: DispatchSourceSignal?

    /// Push the snapshot text as-is; the stage adapter drops stale snapshots via valid_until.
    func pushState(_ text: String?) {
        if text == lastState { return }
        lastState = text
        settings?.mirrorSnapshot(text)
        if demo { return }
        broadcast("SpritesStage.update(\(text ?? "null"))")
    }

    // MARK: stages

    var builtFor: [ScreenSig] = []
    func screenSigs() -> [ScreenSig] {
        NSScreen.screens.map { s in
            ScreenSig(id: (s.deviceDescription[NSDeviceDescriptionKey("NSScreenNumber")] as? NSNumber)?.uint32Value ?? 0,
                      frame: s.frame, scale: s.backingScaleFactor)
        }
    }

    func buildStages() {
        let sig = screenSigs()
        let span = currentSpan()
        // SPAN: an arrangement change that keeps the world size re-fits in place — no teardown, so nothing flashes and
        // no creature is stranded mid-walk (the ticket's hot-plug requirement).
        if let st = stage, !builtFor.isEmpty, st.refit(span: span, screens: NSScreen.screens) {
            builtFor = sig
            lastCursor = ""; lastWindows = ""; lastFocus = ""
            applyVisibility(); pushFocus(); pushWindows()
            return
        }
        builtFor = sig
        stage?.close()
        lastCursor = ""; lastWindows = ""; lastFocus = ""
        stage = {
            let s = Stage(span: span, screens: NSScreen.screens)
            s.onClick = { [weak self] hit, id, pid, project, key, ghost, count in
                let p = pid != 0 ? pid : (hit?.pid ?? 0)
                // CLICK-3 (owner, 2026-11-05): the gesture is a double-click, so the second click acts at once; a lone
                // click still acts after the user's double-click interval, so no click is ever eaten (R3-SPEC #1, #2).
                if debugClicks { log("click received \(project) \(id) count=\(count) ghost=\(ghost)") }
                switch clickGesture(count: count) {
                case .alreadyActed: return
                case .act: self?.pendingClick = nil
                case .waitForSecond:
                    let token = UUID()
                    self?.pendingClick = token
                    let delay = singleClickDelay(doubleClickInterval: NSEvent.doubleClickInterval)
                    DispatchQueue.main.asyncAfter(deadline: .now() + delay) { [weak self] in
                        guard let self, self.pendingClick == token else { return }   // a second click arrived and acted
                        self.pendingClick = nil
                        self.act(id: id, pid: p, project: project, key: key, ghost: ghost)
                    }
                    return
                }
                self?.act(id: id, pid: p, project: project, key: key, ghost: ghost)
            }
            s.js("SpritesStage.setProjects && SpritesStage.setProjects(\(ProjectTable.shared.current().1))")   // R1 #2: before the cast
            if let c = lastCast { s.js("SpritesStage.setCast(\(c))") }
            s.js("SpritesStage.setBehaviors(\(lastBehaviors))")
            s.js("SpritesStage.setDemo(\(demo))")
            s.js("SpritesStage.setScale && SpritesStage.setScale(\(size))")
            if !demo, let st = lastState { s.js("SpritesStage.update(\(st))") }
            s.js("SpritesStage.setPaused(\(hidden))")
            return s
        }()
        applyVisibility()
        pushFocus()
    }

    /// The pending single click (CLICK-3). Non-nil while a lone click waits out the double-click window; cleared by
    /// the second click of a double-click, so one gesture runs one action.
    var pendingClick: UUID?

    /// Open or focus what this click names. review R1 #8: a stale snapshot is unclickable, and the pid must still be
    /// the process the id names (pid@start). R2_MACOS #2: in demo every click is ignored (a demo ghost's key can name
    /// a real project).
    func act(id: String, pid: pid_t, project: String, key: String, ghost: Bool) {
        switch clickAction(id: id, pid: pid, project: project, ghost: ghost, key: key, validUntil: snapshotValidUntil(lastState),
                           now: Date().timeIntervalSince1970, demo: hostDemoForClick(appDemo: demo), startOf: processStart) {
        case .ghost(let k): openGhost(key: k)
        case .focus(let fp): activateSession(pid: fp, startedAt: Int(id.split(separator: "@").last ?? "") ?? 0)
        case .ignore(let why): log("click \(project) \(id): \(why)")
        }
    }

    /// One world, one JS call (it reaches every panel because they share the simulation).
    func broadcast(_ js: String) { stage?.js(js) }
    /// R1_SPEC S4 + SPAN: the world's walkable area. Stage.pushVisible owns the geometry and the de-duplication.
    func pushVisible() { stage?.pushVisible() }
    var lastProjects = ""
    func pushProjects() {
        let j = ProjectTable.shared.current().1
        if j != lastProjects { lastProjects = j; broadcast("SpritesStage.setProjects && SpritesStage.setProjects(\(j))") }
    }

    var hostTick = 0, mouseNear = false
    /// CLICK-2: the poll's verdict on "is a menu, sheet, banner or prompt holding the cursor" (R2_MACOS #1). The
    /// mouse-moved monitor reuses it rather than reading the window list on every move.
    var blockedByOverlay = false
    var mouseMonitor: Any?

    /// CLICK-2: arm or disarm each panel's mouse capture from the hit geometry alone — cheap enough to run on every
    /// mouse-moved event, which is what makes the panel already capturing when a click lands after a move.
    func armCapture() {
        guard !hidden, !blockedByOverlay else { return }
        guard let st = stage else { return }
        let p = NSEvent.mouseLocation
        // Only the panel under the cursor may capture; the others must stay click-through (R3-SPEC #1/#2).
        let over = st.overSprite(p), i = st.screenIndex(p)
        for (k, s) in st.screens.enumerated() {
            let want = over && k == i
            if s.panel.ignoresMouseEvents == want { s.panel.ignoresMouseEvents = !want }
        }
    }

    func trackMouse() {
        guard !hidden, let st = stage else { return }
        let p = NSEvent.mouseLocation
        mouseNear = st.near(p, margin: 160)
        var over = st.overSprite(p)
        var blocked = false
        if over {   // R2_MACOS #1: a menu, sheet, banner or prompt (not ours, layer > 0) under the cursor keeps the click
            let primaryTop = NSScreen.screens.first?.frame.maxY ?? 0
            over = captureAllowed(cursor: CGPoint(x: p.x, y: primaryTop - p.y), windows: allWindows(), me: getpid(),
                                  screens: NSScreen.screens.map(cgFrame))
            if !over { blocked = true }
        }
        let i = st.screenIndex(p)
        for (k, s) in st.screens.enumerated() {
            let want = over && k == i
            if s.panel.ignoresMouseEvents == want {
                s.panel.ignoresMouseEvents = !want
                if debugClicks { log("capture \(want ? "ON" : "off") screen \(k) at (\(Int(p.x)),\(Int(p.y))) overSprite=\(st.overSprite(p)) blocked=\(blocked)") }
            }
        }
        blockedByOverlay = blocked
        // SPAN: one cursor in WORLD px (or null when it is off every screen), not one per panel.
        let cur: String = i < 0 ? "null" : { let q = st.world(p); return "{\"x\":\(Int(q.x)),\"y\":\(Int(q.y))}" }()
        if cur != lastCursor { lastCursor = cur; st.js("SpritesStage.setCursor(\(cur))") }
    }

    var lastFocus = ""
    var focusedID = 0, focusedRect: CGRect? = nil
    /// Handoff item 3: the 2 Hz tick reads the focused window alone; the shared full list only when it moved, or every
    /// 2 s as the safety net for other windows' moves (no move notification exists without an AX grant).
    func hostWindowTick(_ n: Int) {
        guard !hidden else { return }
        let now = focusedID > 0 ? windowBounds(focusedID) : nil
        if tickNeedsFullRead(tick: n, focusedBefore: focusedRect, focusedNow: now) { pushFocus(); pushWindows() }
    }
    func pushFocus() {
        guard !hidden else { return }
        let f = focusedWindow(list: windowList())
        focusedID = f?.id ?? 0; focusedRect = f?.rect
        guard let st = stage else { return }
        // SPAN: the focused window in WORLD px, once — it may straddle the seam.
        let msg: String = {
            guard let r = f?.rect else { return "null" }
            let wr = worldRectFromCG(r, world: st.span.world, primaryMaxY: NSScreen.screens.first?.frame.maxY ?? 0)
            return "{\"x\":\(Int(wr.minX)),\"y\":\(Int(wr.minY)),\"w\":\(Int(wr.width)),\"h\":\(Int(wr.height))}"
        }()
        if msg == lastFocus { return }
        lastFocus = msg
        st.js("SpritesStage.setFocus(\(msg))")
    }

    /// typing = a key or scroll in the last 1.5 s; idleSec = seconds since any input. Both from
    /// HID idle counters (no Input Monitoring grant). Sent only on change.
    func pushActivity() {
        guard !hidden else { return }
        let typing = min(secondsSince(.keyDown), secondsSince(.scrollWheel)) < 1.5
        let idle = Int(secondsSince(anyInputEvent))
        let msg = "{\"typing\":\(typing),\"idleSec\":\(idle)}"
        if msg == lastActivity { return }
        lastActivity = msg
        broadcast("SpritesStage.setActivity(\(msg))")
    }

    /// Session pids from the latest state (demo: none).
    func sessionPids() -> [pid_t] {
        guard !demo, let st = lastState?.data(using: .utf8),
              let o = try? JSONSerialization.jsonObject(with: st) as? [String: Any],
              let ss = o["sessions"] as? [[String: Any]] else { return [] }
        return ss.compactMap { num($0["pid"]).map { pid_t($0) } }.filter { $0 > 0 }
    }

    /// Windows per screen, front to back (stage px). sessionPid (followOwnWindow): an iTerm2 window gets the session
    /// whose tty one of its sessions has (R1_SPEC S7, cached tty -> window, refreshed off main only once Automation is
    /// granted); otherwise only when unambiguous (the app holds exactly one session and shows exactly one window).
    /// Also drives the full-screen fade.
    func pushWindows() {
        guard !hidden else { return }
        let withID = onScreenWindowsWithID()
        let wins = withID.map { (rect: $0.rect, pid: $0.pid) }
        let pids = sessionPids()
        appOfSession = appOfSession.filter { pids.contains($0.key) }
        for p in pids where appOfSession[p] == nil { appOfSession[p] = owningApp(p)?.processIdentifier ?? -1 }
        var sessionsByApp: [pid_t: [pid_t]] = [:]
        for (s, a) in appOfSession where a > 0 { sessionsByApp[a, default: []].append(s) }
        var winsByApp: [pid_t: Int] = [:]
        for w in wins { winsByApp[w.pid, default: 0] += 1 }
        let iterm = Set(NSRunningApplication.runningApplications(withBundleIdentifier: "com.googlecode.iterm2").map { $0.processIdentifier })
        let itermSessions = appOfSession.filter { iterm.contains($0.value) }.keys
        if !itermSessions.isEmpty { ttyWindows.refresh(now: CACurrentMediaTime()) }
        var ttys: [pid_t: String] = [:]
        for p in itermSessions { if let t = processTTY(p) { ttys[p] = t } }
        let byWindow = sessionWindows(ttyOf: ttys, ttyWindow: ttyWindows.map)
        let fade = behaviorOn("fullScreenFade")
        guard let st = stage else { return }
        // SPAN: every window once, in WORLD px (a window may straddle the seam, so it is no longer clipped per screen).
        let primaryMaxY = NSScreen.screens.first?.frame.maxY ?? 0
        let items = withID.compactMap { w -> String? in
            let r = worldRectFromCG(w.rect, world: st.span.world, primaryMaxY: primaryMaxY)
            guard r.width >= 1, r.height >= 1 else { return nil }
            var j = "{\"x\":\(Int(r.minX)),\"y\":\(Int(r.minY)),\"w\":\(Int(r.width)),\"h\":\(Int(r.height)),\"pid\":\(w.pid)"
            if let sp = byWindow[w.id] { j += ",\"sessionPid\":\(sp)" }
            else if !iterm.contains(w.pid), let ss = sessionsByApp[w.pid], ss.count == 1, winsByApp[w.pid] == 1 { j += ",\"sessionPid\":\(ss[0])" }
            if darkApp(w.pid) { j += ",\"dark\":true" }   // hover-label ground proxy (docs/HOVER_LABELS.md): terminals are dark
            return j + "}"
        }
        let msg = "[" + items.joined(separator: ",") + "]"
        if msg != lastWindows { lastWindows = msg; st.js("SpritesStage.setWindows(\(msg))") }
        // The fade stays PER PANEL: full-screen video on one monitor hides the sprites there and nowhere else.
        for (i, sc) in st.screens.enumerated() { setFade(i, fade && isFullScreen(sc.screen, windows: wins)) }
    }

    /// Terminal apps draw dark grounds; every other window is assumed bright (hover-label halo, owner ruling 2026-11-01).
    var darkApps: [pid_t: Bool] = [:]
    func darkApp(_ pid: pid_t) -> Bool {
        if let v = darkApps[pid] { return v }
        let id = NSRunningApplication(processIdentifier: pid)?.bundleIdentifier ?? ""
        let v = ["com.googlecode.iterm2", "com.apple.Terminal", "dev.warp.Warp-Stable", "net.kovidgoyal.kitty",
                 "com.mitchellh.ghostty", "org.alacritty", "com.github.wez.wezterm"].contains(id)
        darkApps[pid] = v; return v
    }

    /// Fade one PANEL (by screen index), not the world: only that monitor's sprites go.
    func setFade(_ i: Int, _ on: Bool) {
        guard let st = stage, i < st.screens.count, st.screens[i].fsFaded != on else { return }
        st.setFaded(i, on)
        let panel = st.screens[i].panel
        if on { panel.ignoresMouseEvents = true }
        NSAnimationContext.runAnimationGroup({ c in
            c.duration = on ? 0.8 : 0.5
            panel.animator().alphaValue = on ? 0 : 1
        })
        pushPaused()
    }

    func applyVisibility() {
        backdrop.hidden = qaSecond || visibilityPlan(userHidden: userHidden, meeting: meeting, locked: locked).backdropHidden   // review R1 #10
        for s in stage?.screens ?? [] {
            if hidden { s.panel.ignoresMouseEvents = true; s.panel.orderOut(nil) }
            else { s.panel.orderFrontRegardless() }
        }
        pushPaused()
        if !hidden { lastFocus = ""; pushFocus() }
        showItem?.title = userHidden ? "Show Sprites" : "Hide Sprites"
        meetingItem?.state = meeting ? .on : .off
        demoItem?.state = demo ? .on : .off
        status?.button?.appearsDisabled = hidden
        settings?.mirrorVisibility(hidden: userHidden, meeting: meeting)
    }

    // MARK: menu

    func buildMenu() {
        status = NSStatusBar.system.statusItem(withLength: NSStatusItem.squareLength)
        if let b = status.button {
            let img = NSImage(systemSymbolName: "sparkles", accessibilityDescription: "Sprites")
            img?.isTemplate = true
            b.image = img
            b.toolTip = "Sprites"
        }
        let m = NSMenu()
        showItem = NSMenuItem(title: "Hide Sprites", action: #selector(toggleShow), keyEquivalent: "")
        meetingItem = NSMenuItem(title: "Meeting Mode  (⌃⌥⌘S)", action: #selector(toggleMeeting), keyEquivalent: "")
        demoItem = NSMenuItem(title: "Demo Mode", action: #selector(toggleDemo), keyEquivalent: "")
        let set = NSMenuItem(title: "Sprites Settings…", action: #selector(openSettings), keyEquivalent: ",")
        let quit = NSMenuItem(title: "Quit Sprites", action: #selector(quit), keyEquivalent: "q")
        let stir = NSMenuItem(title: "Stir the Aether", action: #selector(stirAether), keyEquivalent: "")
        for i in [showItem!, meetingItem!, demoItem!, stir, NSMenuItem.separator(), set, NSMenuItem.separator(), quit] {
            i.target = self; m.addItem(i)
        }
        status.menu = m
    }

    @objc func stirAether() { backdrop.aetherStir() }
    @objc func toggleShow() { userHidden.toggle(); applyVisibility() }
    @objc func toggleMeeting() { meeting.toggle(); applyVisibility() }
    @objc func toggleDemo() { setDemo(!demo) }
    func setDemo(_ on: Bool) {
        demo = on; settings?.demo = on; demoItem?.state = on ? .on : .off
        UserDefaults.standard.set(demo, forKey: "demo")
        broadcast("SpritesStage.setDemo(\(demo))")
        if !demo { broadcast("SpritesStage.update(\(lastState ?? "null"))") }
        applyVisibility()
    }
    var size: Double = { let v = UserDefaults.standard.double(forKey: "size"); return v > 0 ? v : 1.0 }()
    func setSize(_ z: Double) {   // owner: one Sprite Size bar for the scale of all sprites
        size = min(2.0, max(0.5, z)); UserDefaults.standard.set(size, forKey: "size")
        broadcast("SpritesStage.setScale && SpritesStage.setScale(\(size))")
    }
    @objc func quit() { NSApp.terminate(nil) }

    @objc func openSettings() {
        if settings == nil {
            let w = SettingsWindow()
            w.onSaveCast = { [weak self] cast in self?.saveCast(cast) }
            w.onSaveBehaviors = { [weak self] b in self?.saveBehaviors(b) }
            w.onSetDemo = { [weak self] d in self?.setDemo(d) }
            w.onSetSize = { [weak self] z in self?.setSize(z) }
            w.onSetHidden = { [weak self] h in self?.userHidden = h; self?.applyVisibility() }
            w.onSetMeeting = { [weak self] v in self?.meeting = v; self?.applyVisibility() }
            w.onSetProjectColour = { key, alias, hex in setProjectColour(key: key, alias: alias, hex: hex) }
            w.onSetProjectFocus = { key, alias, on, name, dir in setProjectFocus(key: key, alias: alias, on: on, name: name, dir: dir) }
            settings = w
        }
        settings?.demo = demo; settings?.size = size
        settings?.hidden = userHidden; settings?.meeting = meeting; settings?.hotkeyOK = hotKeyOK
        settings?.show()
    }

    func saveCast(_ cast: Any) {
        guard JSONSerialization.isValidJSONObject(cast),
              let d = try? JSONSerialization.data(withJSONObject: cast, options: [.prettyPrinted, .sortedKeys]) else {
            log("saveCast: not a JSON object"); return
        }
        do { try writeAtomically(d, to: Paths.cast) } catch { log("saveCast: \(error.localizedDescription)"); return }
        let s = String(data: d, encoding: .utf8) ?? "null"
        lastCast = s
        broadcast("SpritesStage.setCast(\(s))")
    }

    func saveBehaviors(_ b: Any) {
        guard JSONSerialization.isValidJSONObject(b),
              let d = try? JSONSerialization.data(withJSONObject: b, options: [.prettyPrinted, .sortedKeys]) else {
            log("saveBehaviors: not a JSON object"); return
        }
        do { try writeAtomically(d, to: Paths.behaviors) } catch { log("saveBehaviors: \(error.localizedDescription)"); return }
        lastBehaviors = String(data: d, encoding: .utf8) ?? "{}"
        broadcast("SpritesStage.setBehaviors(\(lastBehaviors))")
        if !qaSecond { applyDim(); backdrop.apply(lastBehaviors) }
        pushWindows()
    }

    // MARK: hotkey (Carbon RegisterEventHotKey: no Input Monitoring / Accessibility grant)

    func registerHotKey() {
        var spec = EventTypeSpec(eventClass: OSType(kEventClassKeyboard), eventKind: UInt32(kEventHotKeyPressed))
        let me = Unmanaged.passUnretained(self).toOpaque()
        InstallEventHandler(GetApplicationEventTarget(), { _, _, ud in
            guard let ud else { return noErr }
            let d = Unmanaged<AppDelegate>.fromOpaque(ud).takeUnretainedValue()
            DispatchQueue.main.async { d.toggleMeeting() }
            return noErr
        }, 1, &spec, me, nil)
        let id = EventHotKeyID(signature: OSType(0x53505254), id: 1)   // 'SPRT'
        let mods = UInt32(controlKey | optionKey | cmdKey)
        let err = RegisterEventHotKey(UInt32(kVK_ANSI_S), mods, id, GetApplicationEventTarget(), 0, &hotKey)
        hotKeyOK = err == noErr
        if err != noErr { log("hotkey ctrl-opt-cmd-S unavailable (\(err)); menu only") }
    }
}
