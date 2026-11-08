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
    // CLICK-1 (measured 2026-11-05): WindowServer publishes the mouse POINTER as a window at
    // kCGCursorWindowLevel (2147483630), 20-40 px, always under the cursor by construction. It appeared in
    // CGWindowListCopyWindowInfo on ~7% of samples during motion; every time it did, capture was refused and
    // the click vanished. The pointer is never something a click should be held back for.
    let pointer = (layer: Int(CGWindowLevelForKey(.cursorWindow)), pid: pid_t(438),
                   rect: CGRect(x: 487, y: 390, width: 28, height: 40), alpha: 1.0)
    check(captureAllowed(cursor: CGPoint(x: 500, y: 400), windows: [pointer, ours, dockFull], me: me, screens: scr),
          "CLICK-1 the mouse pointer's own window never keeps the click")
    check(!captureAllowed(cursor: CGPoint(x: 500, y: 400), windows: [pointer, menu, ours], me: me, screens: scr),
          "CLICK-1 the pointer exemption does not let a real menu through")
    // CLICK-1: a drag image (level 500) and assistive overlays (1500) sit below the cursor level and still block.
    check(!captureAllowed(cursor: CGPoint(x: 500, y: 400), windows: [(layer: Int(CGWindowLevelForKey(.draggingWindow)), pid: 20, rect: menu.rect, alpha: 1.0)], me: me, screens: scr),
          "CLICK-1 a dragging window still keeps the click")
}

// CLICK-2 (measured 2026-11-05): the panel armed capture only on the cursor POLL, so a click arriving in the
// same breath as the move found ignoresMouseEvents still true and fell through to the desktop. Measured:
// the click was posted at T, capture armed at T+24..81 ms; 4 of 5 human move-then-click gestures were lost.
// The pure rule: arm from the hit geometry the moment the pointer is over a sprite, never only on a tick.
do {
    let hits = [Hit(id: "1@2", pid: 1, project: "P", x: 100, y: 100, r: 20)]
    check(captureNeeded(cursor: CGPoint(x: 100, y: 100), hits: hits, faded: false), "CLICK-2 over a hit: capture needed")
    check(captureNeeded(cursor: CGPoint(x: 118, y: 100), hits: hits, faded: false), "CLICK-2 inside the radius: capture needed")
    check(!captureNeeded(cursor: CGPoint(x: 140, y: 100), hits: hits, faded: false), "CLICK-2 outside the radius: not needed")
    check(!captureNeeded(cursor: CGPoint(x: 100, y: 100), hits: hits, faded: true), "CLICK-2 a faded (full-screen) stage never captures")
    check(!captureNeeded(cursor: CGPoint(x: 100, y: 100), hits: [], faded: false), "CLICK-2 no hits: never captures")
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
// 2026-11-05: the target window is now bound to `tw` (`first window whose id is wid`) rather than the loop's index
// reference `w` — the -1719 fix. The INVARIANT is unchanged and still asserted: un-minimise before selecting it.
do {
    let s = itermFocusScript(tty: "/dev/ttys005")
    let m = s.range(of: "set miniaturized of tw to false"), sel = s.range(of: "select tw")
    check(m != nil && sel != nil && m!.lowerBound < sel!.lowerBound, "R1M-17 un-minimise precedes select of the target window")
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
    // The call moved out of the stage's onClick closure into AppDelegate.act when the double-click gesture landed
    // (CLICK-3), so `self?.demo` became `demo`; what must hold is that the app's own flag still goes through
    // hostDemoForClick on the way into clickAction, and that no call site passes a bare `demo:` literal.
    let appSrc = source("App.swift")
    check(appSrc.contains("demo: hostDemoForClick(appDemo: demo)") || appSrc.contains("demo: hostDemoForClick(appDemo: self?.demo)"),
          "R2M-2 App passes demo into clickAction")
    check(!appSrc.contains("demo: true") && !appSrc.contains("demo: false"), "R2M-2 no call site hardcodes the demo flag")
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
    check(source("Stage.swift").contains("SpritesStage.setVisible") && app.contains("self.pushVisible()   // R1_SPEC S4"),
          "S4 sent on build and on screen-parameter change (via Stage.pushVisible since the span change)")
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
    check(body.contains("0.4) { self?.lastFocus = \"\"; self?.pushFocus(); self?.pushWindows()"), "S12 repeat pushes both")
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

// SPAN (SPRITES_UNIFY_MONITORS_AS_ONE): one cast across every monitor. Builds Stage.swift, so it can check that the new
// world helpers agree with the per-screen ones they replace — the Laptop regression guard.
do {
    // The single-screen case must come out of the world helpers EXACTLY as visibleStageRect/stagePoint did before.
    let f = NSRect(x: 0, y: 0, width: 1728, height: 1117), v = NSRect(x: 0, y: 0, width: 1728 - 70, height: 1117 - 33)
    let one = spanLayout(frames: [f], visibleFrames: [v])
    check(one.visible[0] == visibleStageRect(visible: v, frame: f), "SPAN one screen: world visible rect == visibleStageRect")
    check(spanVisibleRect(one) == visibleStageRect(visible: v, frame: f), "SPAN one screen: the walkable area is exactly today's visible rect")
    // A second screen must not change what the FIRST screen's own visible rect is in its own coordinates.
    let g = NSRect(x: -1920, y: -103, width: 1920, height: 1080), gv = NSRect(x: -1920, y: -103, width: 1920, height: 1050)
    let two = spanLayout(frames: [f, g], visibleFrames: [v, gv])
    check(two.visible[0].size == visibleStageRect(visible: v, frame: f).size, "SPAN the main screen's visible SIZE is unchanged by a second monitor")
    check(two.rects.count == 2 && two.visible.count == 2, "SPAN one rect and one visible rect per screen")

    // The world is ONE simulation: exactly one setSize and one world-sized NativeHost, never one per screen.
    let st = source("Stage.swift")
    check(st.contains("NativeHost(size: s.size"), "SPAN the host is sized to the WORLD, not to one screen")
    check(!st.contains("NSScreen.screens.map { Stage("), "SPAN no per-screen Stage array survives")
    check(st.contains("addViewport"), "SPAN extra screens are viewports onto the one recording")
    let ap = source("App.swift")
    check(ap.contains("var stage: Stage?"), "SPAN App holds ONE stage, not an array")
    check(!ap.contains("stages.forEach"), "SPAN nothing broadcasts to N independent stages any more")
    // A click must not be blocked on either monitor (R3-SPEC #1/#2): the capture rule is per panel, the hits are the world's.
    check(st.contains("func screenIndex"), "SPAN clicks resolve to exactly one panel")
    check(ap.contains("let want = over && k == i"), "SPAN only the panel under the cursor captures; the others stay click-through")
    // Hot-plug: a same-size arrangement change re-fits rather than rebuilding, so nothing flashes (ticket hazard 5).
    check(st.contains("func refit(span"), "SPAN an arrangement change re-fits in place")
    check(ap.contains("st.refit(span: span, screens: NSScreen.screens)"), "SPAN the screen-parameter path tries refit before rebuilding")
    // The per-panel fade must stay per panel: full-screen video on one monitor must not blank the other's sprites.
    check(ap.contains("for (i, sc) in st.screens.enumerated() { setFade(i,"), "SPAN the full-screen fade is still per screen")
    check(ap.contains("st.screens.allSatisfy"), "SPAN the one simulation pauses only when NO panel still needs frames")

    // The Metal viewport carries a world origin, so one recording paints both panels in the right places.
    let nt = source("Native.swift")
    check(nt.contains("var origin: CGPoint = .zero"), "SPAN each viewport knows where it sits in the world")
    check(nt.contains("for e in extra { e.renderer.draw(frame: fr"), "SPAN the SAME frame is encoded into every viewport")
    check(nt.contains("constant float2& org [[buffer(2)]]"), "SPAN the shader takes the viewport origin")
}

// MARK: the three f48a980 regressions the owner saw on screen (2026-11-05)
// "no longer show names above them ... when they cross, they get squished strangely horizontally ... blurrier perhaps".
do {
    let nt = source("Native.swift"), st = source("Stage.swift")

    // --- 1. LABELS REACH EVERY VIEWPORT ---
    // The JS `label` callback wrote into `self?.renderer` — the PRIMARY renderer only — while `labelTex` was a private
    // per-MetalStage array. An extra screen's panel therefore had an all-blank texture array: no names at all.
    check(!nt.contains("guard let r = self?.renderer, let img = CGCanvas.render"),
          "LABEL the label callback no longer writes into the primary renderer alone")
    check(nt.contains("final class LabelStore"), "LABEL there is ONE label store, not one array per viewport")
    check(nt.contains("self.labels.set(slot, img)"), "LABEL the callback uploads into the shared store")
    check(nt.contains("fileprivate let labels = LabelStore()"), "LABEL the HOST owns the store, so every viewport sees it")
    check(nt.contains("labels: labels"), "LABEL every renderer (primary and extra) is handed the shared store")
    check(nt.contains("tex: labels.textures(live: nl)"), "LABEL staging reads the shared store, not a private array")
    check(!nt.contains("private var labelTex"), "LABEL no private per-renderer label array survives")
    // A real store with a real device: a label set once is visible to every viewport that asks, and only `labn` slots
    // are live. Measured against Metal itself, not a stub.
    if let dev = MTLCreateSystemDefaultDevice() {
        let store = LabelStore(device: dev)
        // a 4x3 premultiplied RGBA8 raster, as CGCanvas.render returns
        let w = 4, h = 3
        let px = [UInt8](repeating: 200, count: w * h * 4)
        let prov = CGDataProvider(data: Data(px) as CFData)!
        let img = CGImage(width: w, height: h, bitsPerComponent: 8, bitsPerPixel: 32, bytesPerRow: w * 4,
                          space: CGColorSpace(name: CGColorSpace.sRGB)!,
                          bitmapInfo: CGBitmapInfo(rawValue: CGImageAlphaInfo.premultipliedLast.rawValue),
                          provider: prov, decode: nil, shouldInterpolate: false, intent: .defaultIntent)!
        check(store.set(1, img), "LABEL a raster uploads into slot 1")
        check(!store.set(-1, img) && !store.set(LabelStore.maxLabels, img), "LABEL an out-of-range slot is refused")
        let live2 = store.textures(live: 2)
        check(live2.count == LabelStore.maxLabels, "LABEL the store always returns one texture per slot")
        check(live2[1]?.width == w && live2[1]?.height == h, "LABEL slot 1 carries the uploaded raster's size")
        // slot 0 was never set, so it must read as the 1x1 blank rather than nil (the shader always samples 4 textures)
        check(live2[0]?.width == 1, "LABEL an unset but live slot reads as the 1x1 blank")
        check(live2[3]?.width == 1, "LABEL a slot beyond labn reads as the blank")
        // 🔴 the fan-out itself: two renderers sharing this store both see that same texture.
        let a = MetalStage(width: 64, height: 64, labels: store), b = MetalStage(width: 32, height: 48, labels: store)
        check(a != nil && b != nil, "LABEL two viewports build against one shared store")
        check(store.textures(live: 2)[1] === live2[1], "LABEL the shared store hands every viewport the SAME texture object")

    }

    // --- 2/3. THE SQUISH AND THE BLUR: output size, and the stale-drawable guard ---
    check(!nt.contains("if layer.drawableSize.width != CGFloat(w)"),
          "SQUISH the width-only drawable guard is gone (two 1920x1080 screens share a width)")
    check(nt.contains("if drawableStale(layer.drawableSize, w: w, h: h)"), "SQUISH the drawable guard tests BOTH dimensions")
    check(nt.contains("let outSize: CGSize, outScale: CGFloat"), "SQUISH the host knows its primary viewport's own output")
    check(nt.contains("MetalStage(width: Int((os.width * osc).rounded())"), "SQUISH the primary renderer is sized to its PANEL, not the world")
    check(nt.contains("NSRect(origin: .zero, size: outSize)") && nt.contains("v.metalLayer.contentsScale = outScale"),
          "SQUISH the primary view and its contentsScale follow the panel, so contentsScale and drawableSize agree")
    check(st.contains("viewportOutput(panelSize: $0.frame.size, backing: $0.backingScaleFactor)"),
          "SQUISH Stage passes screen 0's panel size and its own backing scale")
    check(st.contains("outSize: out?.size, outScale: out?.scale"), "SQUISH the host is built with that output")
    // refit reuses renderers whose target size is baked in, so it must refuse when any panel's output changed.
    check(st.contains("new.frame.size == old.screen.frame.size"), "SQUISH a re-fit refuses when a panel's size changed (it would reuse a wrong-sized renderer)")
    check(st.contains("panelScale(new.backingScaleFactor) == panelScale(old.screen.backingScaleFactor)"),
          "SQUISH a re-fit refuses when a panel's backing scale changed")

    // --- 4. THE iTERM TAB THAT COULD NOT BE FOUND (pre-existing, not from f48a980) ---
    // Live log: "317:323: execution error ... Can't get item 2 of every tab of item 3 of every window. Invalid index.
    // (-1719)" — offsets 317:323 are `tell t to select`, the statement right after `select w` reorders the windows.
    let fs = itermFocusScript(tty: "/dev/ttys005")
    check(fs.contains("\"/dev/ttys005\""), "FOCUS the tty is quoted into the script")
    // Everything is resolved BEFORE anything is mutated, and the window is addressed by id, not by index.
    let selW = fs.range(of: "select tw"), tellT = fs.range(of: "tell tt to select")
    check(selW != nil && tellT != nil, "FOCUS the script still selects a window and a tab")
    check(!fs.contains("tell t to select"), "FOCUS no `tell t` survives: an index reference invalidated by `select w` is what threw -1719")
    check(!fs.contains("tell s to select"), "FOCUS no `tell s` survives either (same stale reference)")
    check(fs.contains("set tw to first window whose id is wid"), "FOCUS the window is re-fetched BY ID after the search")
    check(fs.contains("set tt to item ti of tabs of (first window whose id is wid)"), "FOCUS the tab is re-fetched by index inside that window")
    check(fs.contains("item si of sessions of tt"), "FOCUS the ORIGINAL session is selected, not just the first (a tab may hold split panes)")
    // the window id must still be read before any mutation, and a miss must still be "none" and raise nothing
    if let idAt = fs.range(of: "set wid to id of w"), let selAt = selW {
        check(idAt.lowerBound < selAt.lowerBound, "FOCUS the window id is read BEFORE the window is selected (R1_MACOS: selecting reorders)")
    } else { check(false, "FOCUS the script reads a window id before selecting") }
    if let noneAt = fs.range(of: "return \"none\""), let selAt = selW {
        check(noneAt.lowerBound < selAt.lowerBound, "FOCUS a tty with no tab returns none and mutates NOTHING")
    } else { check(false, "FOCUS the script still has a `none` path") }
    check(fs.contains("if miniaturized of tw then set miniaturized of tw to false"), "FOCUS a minimised window is still un-minimised (R1_MACOS #17)")
    check(focusedWindow("ok 1173") == 1173 && focusedWindow("none") == nil, "FOCUS the reply parser is unchanged")
    check(activateAllAfterScript("none") == false, "FOCUS a miss NEVER raises every window (owner's rule)")
    // the script must parse as AppleScript at all — compile it, never run it (osadecompile would mutate nothing either)
    do {
        let p = Process(); p.executableURL = URL(fileURLWithPath: "/usr/bin/osacompile")
        let outPath = tmp + "/focus_script_syntax.scpt"
        p.arguments = ["-o", outPath, "-e", fs]
        let e = Pipe(); p.standardError = e; p.standardOutput = Pipe()
        try? p.run()
        let err = e.fileHandleForReading.readDataToEndOfFile()
        p.waitUntilExit()
        check(p.terminationStatus == 0, "FOCUS the script COMPILES as AppleScript (\(String(data: err, encoding: .utf8) ?? ""))")
    }
}

print("\(passed) passed, \(failed) failed")
exit(failed == 0 ? 0 : 1)
