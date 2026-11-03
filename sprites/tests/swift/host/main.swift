import AppKit
import WebKit

// Host-safety tests for package C (reviews/SPRITES_REVIEW_R2_MACOS.md, R1_MACOS, R1_SPEC). Built with every host source
// except App.swift (it holds @main). Run: tests/swift/host_run.sh. Truth is hand-derived from the review text, Apple's
// window-level keys, and measurements on this laptop (2026-11-01), not from the code under test.
var failed = 0, passed = 0
func check(_ ok: Bool, _ name: String) { if ok { passed += 1 } else { failed += 1; print("FAIL: \(name)") } }
let src = CommandLine.arguments[1]   // app/macos
func source(_ f: String) -> String { (try? String(contentsOfFile: src + "/" + f, encoding: .utf8)) ?? "" }
let tmp = CommandLine.arguments[2]
_ = NSApplication.shared

// R1M-1: the stage sits above app windows and below the Dock, menu bar, menus, modal panels and alerts.
do {
    let lv = SpaceRules.stageLevel.rawValue
    check(lv > Int(CGWindowLevelForKey(.normalWindow)), "R1M-1 stage above normal windows (\(lv))")
    for (k, n) in [(CGWindowLevelKey.dockWindow, "dock"), (.mainMenuWindow, "main menu"), (.popUpMenuWindow, "menus"),
                   (.modalPanelWindow, "modal panel"), (.statusWindow, "status bar"), (.utilityWindow, "utility (sheets, Settings)"),
                   (.screenSaverWindow, "screen saver")] {
        check(lv < Int(CGWindowLevelForKey(k)), "R1M-1 stage below \(n) (\(lv) < \(CGWindowLevelForKey(k)))")
    }
    let p = StagePanel(contentRect: .zero, styleMask: [.borderless, .nonactivatingPanel], backing: .buffered, defer: true)
    SpaceRules.applyStage(p)
    check(p.level.rawValue == lv && p.collectionBehavior.contains(.fullScreenAuxiliary), "R1M-1 panel gets the level, keeps fullScreenAuxiliary")
    check(!source("Stage.swift").contains("panel.level = .screenSaver"), "R1M-1 no .screenSaver panel level left")
    // Measured window list (2026-11-01): Dock 1728x1117 at layer 20, WindowServer menu bar 1728x33 at layer 24, Control
    // Center items 38x33 at layer 25. A menu (layer 101) under the cursor keeps the click.
    let scr = [CGRect(x: 0, y: 0, width: 1728, height: 1117)], me: pid_t = 999
    let dockFull = (layer: 20, pid: pid_t(10), rect: scr[0], alpha: 1.0)
    let menu = (layer: 101, pid: pid_t(20), rect: CGRect(x: 400, y: 300, width: 220, height: 300), alpha: 1.0)
    let ours = (layer: 3, pid: me, rect: scr[0], alpha: 1.0)
    let cc = (layer: 25, pid: pid_t(30), rect: CGRect(x: 989, y: 0, width: 38, height: 33), alpha: 1.0)
    check(captureAllowed(cursor: CGPoint(x: 500, y: 400), windows: [ours, dockFull], me: me, screens: scr), "R1M-1 Dock's screen-sized layer does not block")
    check(!captureAllowed(cursor: CGPoint(x: 500, y: 400), windows: [menu, ours, dockFull], me: me, screens: scr), "R1M-1 an open menu under the cursor keeps the click")
    check(captureAllowed(cursor: CGPoint(x: 900, y: 700), windows: [menu, ours, dockFull], me: me, screens: scr), "R1M-1 outside the menu, capture ok")
    check(!captureAllowed(cursor: CGPoint(x: 1000, y: 10), windows: [cc, ours], me: me, screens: scr), "R1M-1 a menu-bar item keeps the click")
    check(captureAllowed(cursor: CGPoint(x: 500, y: 400), windows: [(layer: 101, pid: 20, rect: menu.rect, alpha: 0.0)], me: me, screens: scr), "R1M-1 an invisible window does not block")
}

// R1M-14: never in a screen share; the dim layer too.
do {
    let p = StagePanel(contentRect: .zero, styleMask: [.borderless], backing: .buffered, defer: true)
    SpaceRules.applyStage(p)
    check(p.sharingType == .none, "R1M-14 stage panel sharingType none")
    check(DimLayer.make().sharingType == .none, "R1M-14 dim window sharingType none")
}

// R1M-3: one instance.
do {
    check(instancePlan(me: 5, sameBundle: [5], lockAcquired: true, qaSecond: false) == .run, "R1M-3 alone: run")
    if case .exitDuplicate = instancePlan(me: 5, sameBundle: [5, 1953], lockAcquired: true, qaSecond: false) {} else { check(false, "R1M-3 another pid with the bundle id: exit") }
    if case .exitDuplicate = instancePlan(me: 5, sameBundle: [5], lockAcquired: false, qaSecond: false) {} else { check(false, "R1M-3 lock held elsewhere: exit") }
    check(instancePlan(me: 5, sameBundle: [5, 1953], lockAcquired: false, qaSecond: true) == .runAsQASecond, "R1M-3 --qa-second-instance runs")
    let lp = tmp + "/run/sprites.lock"
    var a: InstanceLock? = InstanceLock(path: lp)
    check(a != nil, "R1M-3 first lock acquired")
    check(InstanceLock(path: lp) == nil, "R1M-3 second lock refused while the first is held")
    a = nil
    check(InstanceLock(path: lp) != nil, "R1M-3 lock free again once released")
    let app = source("App.swift")
    check(app.contains("if !qaSecond { registerHotKey() }") && app.contains("backdrop.hidden = qaSecond ||") && app.contains("if !qaSecond { dim.layout(); applyDim() }"),
          "R1M-3 QA second instance: no hotkey, backdrop or dim")
}

// R1M-2: orphaned iTermServer (ppid 1) still owns its shells.
do {
    check(terminalByAncestry(["claude", "-zsh", "login", "iTermServer-3.7.6"]) == "com.googlecode.iterm2", "R1M-2 iTermServer ancestor = iTerm2")
    check(terminalByAncestry(["claude", "zsh", "sshd"]) == nil, "R1M-2 no terminal ancestor = nil")
    // Live: every shell under an orphaned iTermServer (found from the kernel's process list, ps-equivalent).
    var n: Int32 = 4096, pids = [pid_t](repeating: 0, count: 4096)
    n = proc_listallpids(&pids, Int32(pids.count * MemoryLayout<pid_t>.size))
    let all = pids.prefix(Int(max(0, n))).filter { $0 > 0 }
    let servers = all.filter { procName($0).hasPrefix("iTermServer") && parentPID($0) == 1 }
    let iterm = !NSRunningApplication.runningApplications(withBundleIdentifier: "com.googlecode.iterm2").isEmpty
    if let s = servers.first, iterm {
        check(parentPID(s) == 1, "R1M-2 parentPID reports 1 for an orphan (was nil)")
        let shells = all.filter { p in parentPID(p).map { parentPID($0) == s } ?? false }   // server -> login -> shell
        check(!shells.isEmpty, "R1M-2 live: shells under orphaned iTermServer \(s)")
        for sh in shells.prefix(3) { check(owningApp(sh)?.bundleIdentifier == "com.googlecode.iterm2", "R1M-2 live: shell \(sh) owned by iTerm2") }
    } else { print("SKIP R1M-2 live: no orphaned iTermServer") }
}

// R1M-17: un-minimise before select; tmux named.
do {
    let s = itermFocusScript(tty: "/dev/ttys005")
    let m = s.range(of: "set miniaturized of w to false"), sel = s.range(of: "select w")
    check(m != nil && sel != nil && m!.lowerBound < sel!.lowerBound, "R1M-17 un-minimise precedes select w")
    check(s.contains("\"/dev/ttys005\""), "R1M-17 tty quoted")
    check(underTmux(["claude", "zsh", "tmux"]) && underTmux(["claude", "tmux: server"]) && !underTmux(["claude", "zsh", "login"]), "R1M-17 tmux ancestry")
    check(source("Activate.swift").contains("tmux session: not focusable"), "R1M-17 tmux logged by name")
}

// R1M-6: cooperative activation, then open -b.
do {
    check(activationFallback(activated: true, bundle: "com.microsoft.VSCode") == nil, "R1M-6 activated: no fallback")
    check(activationFallback(activated: false, bundle: "com.microsoft.VSCode") == ["/usr/bin/open", "-b", "com.microsoft.VSCode"], "R1M-6 refused: open -b")
    check(source("Activate.swift").contains("activate(from: NSRunningApplication.current"), "R1M-6 activate(from:) on 14+")
    check(!source("Activate.swift").contains("app.activate() }"), "R1M-6 no bare app.activate()")
}

// R1M-13: ghost launch off main; stamp before dispatch, clear on failure.
do {
    let g = GhostGate(), t = Date()
    check(g.begin("hestia", now: t), "R1M-13 first click goes")
    check(!g.begin("hestia", now: t.addingTimeInterval(1)), "R1M-13 a click queued 1 s later (prompt up, not yet ok) is debounced")
    g.failed("hestia")
    check(g.begin("hestia", now: t.addingTimeInterval(1.5)), "R1M-13 after a failure the next click retries")
    check(g.begin("orchard", now: t.addingTimeInterval(1.5)), "R1M-13 other key independent")
    check(!source("Activate.swift").contains("NSAppleScript(source"), "R1M-13 no NSAppleScript left (main-thread)")
}

// R2M-2-host: demo ignores every click.
do {
    check(hostDemoForClick(appDemo: true) && hostDemoForClick(appDemo: nil) && !hostDemoForClick(appDemo: false), "R2M-2 host demo flag (nil = gone = ignore)")
    let g = clickAction(id: "ghost:hestia", pid: 0, project: "Hestia", ghost: true, key: "hestia", validUntil: 2e9, now: 1e9,
                        demo: hostDemoForClick(appDemo: true), startOf: { _ in 1 })
    if case .ignore = g {} else { check(false, "R2M-2 demo ghost click ignored") }
    check(source("App.swift").contains("demo: hostDemoForClick(appDemo: self?.demo)"), "R2M-2 App passes demo into clickAction")
}

// R1M-8-host: pause on sleep, switch-away, occlusion.
do {
    check(!stagePaused(hidden: false, fsFaded: false, asleep: false, away: false, occluded: false), "R1M-8 visible: runs")
    check(stagePaused(hidden: false, fsFaded: false, asleep: true, away: false, occluded: false), "R1M-8 display sleep pauses")
    check(stagePaused(hidden: false, fsFaded: false, asleep: false, away: true, occluded: false), "R1M-8 fast user switch pauses")
    check(stagePaused(hidden: false, fsFaded: false, asleep: false, away: false, occluded: true), "R1M-8 occluded pauses")
    let app = source("App.swift")
    for n in ["screensDidSleepNotification", "sessionDidResignActiveNotification", "didChangeOcclusionStateNotification"] {
        check(app.contains(n), "R1M-8 App observes \(n)")
    }
}

// R1M-7: Settings close gives activation back.
do {
    check(settingsCloseAction(previous: 700, me: 5, isRunning: { _ in true }) == .reactivate(700), "R1M-7 back to the previous app")
    check(settingsCloseAction(previous: 700, me: 5, isRunning: { _ in false }) == .hide, "R1M-7 previous gone: hide")
    check(settingsCloseAction(previous: nil, me: 5, isRunning: { _ in true }) == .hide, "R1M-7 none: hide")
    check(settingsCloseAction(previous: 5, me: 5, isRunning: { _ in true }) == .hide, "R1M-7 never re-activates itself")
    check(source("Settings.swift").contains("func windowWillClose"), "R1M-7 windowWillClose implemented")
}

// R1M-9: per-screen full-screen fade, any app.
do {
    let a = CGRect(x: 0, y: 0, width: 1728, height: 1117), b = CGRect(x: 1728, y: 0, width: 1920, height: 1080)
    let video = (rect: b, pid: pid_t(77)), term = (rect: CGRect(x: 100, y: 100, width: 900, height: 700), pid: pid_t(66))
    check(coversScreen(b, windows: [term, video]), "R1M-9 full-screen video on display 2 fades it while a terminal is frontmost on display 1")
    check(!coversScreen(a, windows: [term, video]), "R1M-9 display 1 not faded")
    let zoomed = (rect: CGRect(x: 1728, y: 25, width: 1920, height: 1055), pid: pid_t(77))
    check(!coversScreen(b, windows: [zoomed]), "R1M-9 a zoomed window (below the menu bar) is not full screen")
    let small = (rect: CGRect(x: 1800, y: 100, width: 300, height: 300), pid: pid_t(9))
    check(!coversScreen(b, windows: [small, video]), "R1M-9 a window in front of the video on that screen: not faded (topmost decides)")
}

// R1M-16 (native stage, after the swap): no context menu; right/middle clicks are not handled by the stage view.
do {
    let v = NativeView(frame: NSRect(x: 0, y: 0, width: 10, height: 10))
    let e = NSEvent.mouseEvent(with: .rightMouseDown, location: .zero, modifierFlags: [], timestamp: 0, windowNumber: 0, context: nil,
                               eventNumber: 0, clickCount: 1, pressure: 1)!
    check(v.menu(for: e) == nil, "R1M-16 native stage: no context menu over a sprite")
}

// S4-host: visible frame in stage px, Dock on the right (owner's), menu bar 33 px (measured).
do {
    let f = NSRect(x: 0, y: 0, width: 1728, height: 1117), v = NSRect(x: 0, y: 0, width: 1728 - 70, height: 1117 - 33)
    check(visibleStageRect(visible: v, frame: f) == CGRect(x: 0, y: 33, width: 1658, height: 1084), "S4 right Dock: x 0, y 33, w 1658, h 1084")
    let f2 = NSRect(x: 1728, y: -200, width: 1920, height: 1080), v2 = NSRect(x: 1728 + 80, y: -200, width: 1840, height: 1055)
    check(visibleStageRect(visible: v2, frame: f2) == CGRect(x: 80, y: 25, width: 1840, height: 1055), "S4 second screen, left Dock")
    check(visibleMessage(CGRect(x: 0, y: 33, width: 1658, height: 1084)) == #"{"x":0,"y":33,"w":1658,"h":1084}"#, "S4 message")
    let app = source("App.swift")
    check(app.contains("SpritesStage.setVisible") && app.contains("self.pushVisible()   // R1_SPEC S4"), "S4 sent on build and on screen-parameter change")
}

// S7: tty -> iTerm2 window -> sessionPid.
do {
    let m = parseTTYWindows("/dev/ttys018\t9360\n/dev/ttys011\t3854\n/dev/ttys009\t3854\njunk\n")
    check(m == ["/dev/ttys018": 9360, "/dev/ttys011": 3854, "/dev/ttys009": 3854], "S7 parse")
    let sw = sessionWindows(ttyOf: [4100: "/dev/ttys018", 4200: "/dev/ttys011", 4150: "/dev/ttys009", 4300: "/dev/ttys099"], ttyWindow: m)
    check(sw == [9360: 4100, 3854: 4150], "S7 two sessions in two windows each get theirs; two tabs in one: lowest pid; unknown tty: none")
    check(source("App.swift").contains("if let sp = byWindow[w.id]"), "S7 App uses the per-window map")
}

// S12: a Space change pushes focus and windows at once, and again after 0.4 s.
do {
    let app = source("App.swift")
    guard let r = app.range(of: "activeSpaceDidChangeNotification") else { check(false, "S12 observer"); exit(1) }
    let body = String(app[r.upperBound...].prefix(400))
    let now = body.range(of: "self?.pushFocus(); self?.pushWindows()"), later = body.range(of: "asyncAfter(deadline: .now() + 0.4)")
    check(now != nil && later != nil && now!.lowerBound < later!.lowerBound, "S12 immediate focus+windows push before the 0.4 s repeat")
    check(body.contains("0.4) { self?.lastFocus = []; self?.pushFocus(); self?.pushWindows()"), "S12 repeat pushes both")
}

// H3-pushFocus: the tick gates the full read.
do {
    let r = CGRect(x: 10, y: 10, width: 500, height: 400)
    check(!tickNeedsFullRead(tick: 1, focusedBefore: r, focusedNow: r), "H3 focused window still: no full read")
    check(tickNeedsFullRead(tick: 1, focusedBefore: r, focusedNow: r.offsetBy(dx: 5, dy: 0)), "H3 moved: full read")
    check(tickNeedsFullRead(tick: 1, focusedBefore: r, focusedNow: nil), "H3 gone: full read")
    check(!tickNeedsFullRead(tick: 1, focusedBefore: nil, focusedNow: nil), "H3 none focused: no read")
    check(tickNeedsFullRead(tick: 4, focusedBefore: r, focusedNow: r), "H3 every 4th tick (2 s) full read")
    // live: the single-window read agrees with the full list
    if let w = windowList().first(where: { ($0[kCGWindowLayer as String] as? Int) == 0 }), let id = w[kCGWindowNumber as String] as? Int,
       let b = w[kCGWindowBounds as String] as? NSDictionary, let full = CGRect(dictionaryRepresentation: b) {
        check(windowBounds(id) == full, "H3 live: windowBounds(\(id)) equals the full list's bounds")
    } else { print("SKIP H3 live: no layer-0 window") }
}

// SWAP-2 (owner's no-duplicates rule; swap approved 2026-11-01): one renderer. The stage has no WebKit path and no switch.
do {
    let st = source("Stage.swift"), nat = source("Native.swift")
    check(!st.isEmpty && !nat.isEmpty, "SWAP-2 sources readable")
    for w in ["WKWebView(", "WKWebView?", "WKWebViewConfiguration", "StageWebView", "WKNavigationDelegate", "Renderer.native", "evaluateJavaScript", "loadFileURL"] {
        check(!st.contains(w), "SWAP-2 Stage.swift has no \(w)")
    }
    check(!nat.contains("SPRITES_RENDERER") && !nat.contains("enum Renderer"), "SWAP-2 no renderer switch in Native.swift")
    check(st.contains("NativeHost(size:"), "SWAP-2 the stage builds a NativeHost")
    check(!st.contains("class Stage: NSObject, WK"), "SWAP-2 Stage is no WebKit delegate")
}

print("\(passed) passed, \(failed) failed")
exit(failed == 0 ? 0 : 1)
