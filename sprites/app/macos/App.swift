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

    var stages: [Stage] = []
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
    var lastCursor: [String] = []
    var behaviorsWatch: FileWatch?
    var lastBehaviors = "{}"
    var lastActivity = "", lastWindows: [String] = []
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
    func pauseState(_ s: Stage) -> Bool { stagePaused(hidden: hidden, fsFaded: s.fsFaded, asleep: asleep, away: away, occluded: s.occluded) }
    func pushPaused(_ s: Stage) { s.js("SpritesStage.setPaused(\(pauseState(s)))") }

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
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.4) { self?.lastFocus = []; self?.pushFocus(); self?.pushWindows() }
        }
        // R2_MACOS #8 (host half): display sleep and fast user switching pause the stages.
        for (n, f) in [(NSWorkspace.screensDidSleepNotification, { (d: AppDelegate) in d.asleep = true }),
                       (NSWorkspace.screensDidWakeNotification, { (d: AppDelegate) in d.asleep = false }),
                       (NSWorkspace.sessionDidResignActiveNotification, { (d: AppDelegate) in d.away = true }),
                       (NSWorkspace.sessionDidBecomeActiveNotification, { (d: AppDelegate) in d.away = false })] {
            ws.addObserver(forName: n, object: nil, queue: .main) { [weak self] _ in
                guard let self else { return }; f(self); self.stages.forEach(self.pushPaused) }
        }
        NotificationCenter.default.addObserver(forName: NSWindow.didChangeOcclusionStateNotification, object: nil, queue: .main) { [weak self] n in
            guard let self, let w = n.object as? NSWindow, let s = self.stages.first(where: { $0.panel === w }) else { return }
            let occ = !w.occlusionState.contains(.visible)
            if occ != s.occluded { s.occluded = occ; self.pushPaused(s) }
        }

        // Click-through except over a sprite: the cursor is polled (no TCC grant needed) by the shared tick above, and at
        // 30 Hz while it is near a sprite so click-through flips in time (a mouse-moved monitor needs no grant either but
        // fires on every move anywhere).
        Timer.scheduledTimer(withTimeInterval: 1.0 / 30, repeats: true) { [weak self] _ in
            guard let self, self.mouseNear else { return }
            self.trackMouse()
        }.tolerance = 0.005

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
        builtFor = screenSigs()
        stages.forEach { $0.close() }
        lastCursor = []; lastWindows = []; lastFocus = []
        stages = NSScreen.screens.map { scr in
            let s = Stage(screen: scr)
            s.onClick = { [weak self] hit, id, pid, project, key, ghost in
                let p = pid != 0 ? pid : (hit?.pid ?? 0)
                // review R1 #8: stale snapshot = unclickable; the pid must still be the process the id names (pid@start).
                // R2_MACOS #2: in demo every click is ignored (a demo ghost's key can name a real project).
                switch clickAction(id: id, pid: p, project: project, ghost: ghost, key: key, validUntil: snapshotValidUntil(self?.lastState),
                                   now: Date().timeIntervalSince1970, demo: hostDemoForClick(appDemo: self?.demo), startOf: processStart) {
                case .ghost(let k): openGhost(key: k)
                case .focus(let fp): activateSession(pid: fp, startedAt: Int(id.split(separator: "@").last ?? "") ?? 0)
                case .ignore(let why): log("click \(project) \(id): \(why)")
                }
            }
            s.js("SpritesStage.setProjects && SpritesStage.setProjects(\(ProjectTable.shared.current().1))")   // R1 #2: before the cast
            if let c = lastCast { s.js("SpritesStage.setCast(\(c))") }
            s.js("SpritesStage.setBehaviors(\(lastBehaviors))")
            s.js("SpritesStage.setDemo(\(demo))")
            s.js("SpritesStage.setScale && SpritesStage.setScale(\(size))")
            if !demo, let st = lastState { s.js("SpritesStage.update(\(st))") }
            s.js("SpritesStage.setPaused(\(hidden))")
            return s
        }
        lastVisible = []
        pushVisible()
        applyVisibility()
        pushFocus()
    }

    func broadcast(_ js: String) { stages.forEach { $0.js(js) } }
    /// R1_SPEC S4: each screen's visible frame (below the menu bar, clear of the Dock on any side), in stage px.
    var lastVisible: [String] = []
    func pushVisible() {
        let msgs = stages.map { visibleMessage(visibleStageRect(visible: $0.screen.visibleFrame, frame: $0.screen.frame)) }
        if msgs == lastVisible { return }
        lastVisible = msgs
        for (s, m) in zip(stages, msgs) { s.js("SpritesStage.setVisible && SpritesStage.setVisible(\(m))") }
    }
    var lastProjects = ""
    func pushProjects() {
        let j = ProjectTable.shared.current().1
        if j != lastProjects { lastProjects = j; broadcast("SpritesStage.setProjects && SpritesStage.setProjects(\(j))") }
    }

    var hostTick = 0, mouseNear = false
    func trackMouse() {
        guard !hidden else { return }
        let p = NSEvent.mouseLocation
        mouseNear = stages.contains { $0.near(p, margin: 160) }
        var others: [(layer: Int, pid: pid_t, rect: CGRect, alpha: Double)]? = nil   // read only when over a sprite
        for s in stages {
            var over = !s.fsFaded && s.overSprite(p)
            if over {   // R2_MACOS #1: a menu, sheet, banner or prompt (not ours, layer > 0) under the cursor keeps the click
                if others == nil { others = allWindows() }
                let primaryTop = NSScreen.screens.first?.frame.maxY ?? 0
                over = captureAllowed(cursor: CGPoint(x: p.x, y: primaryTop - p.y), windows: others!, me: getpid(),
                                      screens: NSScreen.screens.map(cgFrame))
            }
            if s.panel.ignoresMouseEvents == over { s.panel.ignoresMouseEvents = !over }
        }
        let cur = stages.map { s -> String in
            guard s.screen.frame.contains(p) else { return "null" }
            let q = stagePoint(p, on: s.screen)
            return "{\"x\":\(Int(q.x)),\"y\":\(Int(q.y))}"
        }
        if cur != lastCursor {
            for (i, s) in stages.enumerated() where i >= lastCursor.count || lastCursor[i] != cur[i] {
                s.js("SpritesStage.setCursor(\(cur[i]))")
            }
            lastCursor = cur
        }
    }

    var lastFocus: [String] = []
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
        let r = f?.rect
        let msgs = stages.map { s -> String in
            guard let r, let sr = stageRect(r, on: s.screen) else { return "null" }
            return "{\"x\":\(Int(sr.minX)),\"y\":\(Int(sr.minY)),\"w\":\(Int(sr.width)),\"h\":\(Int(sr.height))}"
        }
        if msgs == lastFocus { return }
        lastFocus = msgs
        for (s, m) in zip(stages, msgs) { s.js("SpritesStage.setFocus(\(m))") }
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
        for (i, s) in stages.enumerated() {
            let items = withID.compactMap { w -> String? in
                guard let r = stageRect(w.rect, on: s.screen) else { return nil }
                var j = "{\"x\":\(Int(r.minX)),\"y\":\(Int(r.minY)),\"w\":\(Int(r.width)),\"h\":\(Int(r.height)),\"pid\":\(w.pid)"
                if let sp = byWindow[w.id] { j += ",\"sessionPid\":\(sp)" }
                else if !iterm.contains(w.pid), let ss = sessionsByApp[w.pid], ss.count == 1, winsByApp[w.pid] == 1 { j += ",\"sessionPid\":\(ss[0])" }
                if darkApp(w.pid) { j += ",\"dark\":true" }   // hover-label ground proxy (docs/HOVER_LABELS.md): terminals are dark
                return j + "}"
            }
            let msg = "[" + items.joined(separator: ",") + "]"
            if i >= lastWindows.count { lastWindows.append("") }
            if msg != lastWindows[i] { lastWindows[i] = msg; s.js("SpritesStage.setWindows(\(msg))") }
            setFade(s, fade && isFullScreen(s.screen, windows: wins))
        }
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

    func setFade(_ s: Stage, _ on: Bool) {
        guard s.fsFaded != on else { return }
        s.fsFaded = on
        if on { s.panel.ignoresMouseEvents = true }
        NSAnimationContext.runAnimationGroup({ c in
            c.duration = on ? 0.8 : 0.5
            s.panel.animator().alphaValue = on ? 0 : 1
        })
        pushPaused(s)
    }

    func applyVisibility() {
        backdrop.hidden = qaSecond || visibilityPlan(userHidden: userHidden, meeting: meeting, locked: locked).backdropHidden   // review R1 #10
        for s in stages {
            if hidden { s.panel.ignoresMouseEvents = true; s.panel.orderOut(nil) }
            else { s.panel.orderFrontRegardless() }
            pushPaused(s)
        }
        if !hidden { lastFocus = []; pushFocus() }
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
        for i in [showItem!, meetingItem!, demoItem!, NSMenuItem.separator(), set, NSMenuItem.separator(), quit] {
            i.target = self; m.addItem(i)
        }
        status.menu = m
    }

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
