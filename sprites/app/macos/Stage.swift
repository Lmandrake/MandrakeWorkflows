import AppKit
import WebKit   // WeakHandler only (Settings.swift's window); the stage itself has no WebKit

final class StagePanel: NSPanel {
    override var canBecomeKey: Bool { false }
    override var canBecomeMain: Bool { false }
}

enum SpaceRules {
    static let stage: NSWindow.CollectionBehavior = [.canJoinAllSpaces, .stationary, .fullScreenAuxiliary, .ignoresCycle]
    /// Review R2_MACOS #1: `.floating` (3). Above app windows (0), below the Dock (20), the menu bar (24), menus (101),
    /// sheets and modal panels (8), Notification Center and system alerts (TCC prompts). It was `.screenSaver` (1000), above
    /// all of those, so a sprite over a menu or a prompt took the click. `.fullScreenAuxiliary` keeps it on full-screen Spaces.
    static let stageLevel: NSWindow.Level = .floating
    /// Every overlay window of ours: level, Spaces, and never in a screen share or recording (review R1_MACOS #14:
    /// defence when meeting mode is forgotten).
    static func applyStage(_ w: NSWindow) {
        w.level = stageLevel
        w.collectionBehavior = stage
        w.sharingType = .none
    }
}

/// Review R2_MACOS #1: never take a click while a window that is not ours, above app level (a menu, the menu bar, a
/// sheet, a notification, a TCC prompt), contains the cursor. Full-screen containers (the Dock's and WindowServer's
/// screen-sized layers) and invisible windows do not count. `cursor` and rects in CG global coordinates.
/// CLICK-1 (measured 2026-11-05, macOS 26.7.1): WindowServer publishes the MOUSE POINTER ITSELF as a window at
/// kCGCursorWindowLevel, 20-40 px, which by construction always contains the cursor. It showed up in
/// CGWindowListCopyWindowInfo on ~7% of samples while the mouse moved, and every time it did this function refused
/// and the click was silently swallowed. The pointer is not a thing a click waits behind, so its level is exempt.
func captureAllowed(cursor: CGPoint, windows: [(layer: Int, pid: pid_t, rect: CGRect, alpha: Double)], me: pid_t,
                    screens: [CGRect]) -> Bool {
    let cursorLevel = Int(CGWindowLevelForKey(.cursorWindow))
    for w in windows where w.pid != me && w.layer > 0 && w.alpha > 0 && w.rect.contains(cursor) {
        if w.layer >= cursorLevel { continue }   // the pointer (and anything above it): never a reason to hold a click
        if screens.contains(where: { w.rect.insetBy(dx: -1, dy: -1).contains($0) }) { continue }   // a screen-sized container
        return false
    }
    return true
}

/// CLICK-2 (measured 2026-11-05): whether the panel must be capturing the mouse right now, from the hit geometry
/// alone. The 10/30 Hz cursor poll armed capture too late — a click arriving in the same breath as the move found
/// `ignoresMouseEvents` still true and fell through to the desktop (click posted at T, capture armed at T+24..81 ms;
/// 4 of 5 move-then-click gestures lost). The host now also arms on every mouse-moved event, so this is the one rule
/// both paths share. `cursor` is in this stage's px (stagePoint), as the hits are.
func captureNeeded(cursor: CGPoint, hits: [Hit], faded: Bool) -> Bool {
    if faded { return false }
    return hits.contains { h in let dx = cursor.x - h.x, dy = cursor.y - h.y; return dx * dx + dy * dy <= h.r * h.r }
}

/// NSScreen.visibleFrame (Cocoa, bottom-left origin) -> this screen's stage px (top-left origin), for
/// `SpritesStage.setVisible` (review R1_SPEC S4: the Dock on any side, the menu bar).
func visibleStageRect(visible v: NSRect, frame f: NSRect) -> CGRect {
    CGRect(x: v.minX - f.minX, y: f.maxY - v.maxY, width: v.width, height: v.height)
}

/// The shared world every panel renders a sub-rect of (SPRITES_UNIFY_MONITORS_AS_ONE). Read from the live screens; all
/// the geometry is in Decide.swift's `spanLayout` so the tests reach it without AppKit.
func currentSpan() -> SpanLayout {
    let screens = NSScreen.screens
    return spanLayout(frames: screens.map { $0.frame }, visibleFrames: screens.map { $0.visibleFrame })
}
func visibleMessage(_ r: CGRect) -> String {
    "{\"x\":\(Int(r.minX.rounded())),\"y\":\(Int(r.minY.rounded())),\"w\":\(Int(r.width.rounded())),\"h\":\(Int(r.height.rounded()))}"
}

/// Weak trampoline: WKUserContentController retains its handlers (used by Settings.swift).
final class WeakHandler: NSObject, WKScriptMessageHandler {
    weak var target: WKScriptMessageHandler?
    init(_ t: WKScriptMessageHandler) { target = t }
    func userContentController(_ c: WKUserContentController, didReceive m: WKScriptMessage) {
        target?.userContentController(c, didReceive: m)
    }
}

/// concept (the species) and key (the project key) ride along for the Aether's species wakes and handedness only.
struct Hit { let id: String; let pid: pid_t; let project: String; let x, y, r: CGFloat; var concept = "", key = "" }

/// One transparent, click-through panel covering one NSScreen, running stage.html's script natively (JavaScriptCore +
/// Metal, Native.swift; docs/NATIVE_PORT.md). The WKWebView renderer was removed at the swap (2026-11-01, owner's
/// no-duplicates rule); stage.html still runs in a browser for the headless tests.
final class Stage: NSObject {
    /// One panel per screen: the window, the screen it covers, and that screen's rect in world stage px.
    struct Screen {
        var screen: NSScreen
        let panel: StagePanel
        /// This screen's rect inside the shared world, world stage px (top-left origin of the world).
        var world: CGRect
        var fsFaded = false
        var occluded = false   // panel fully covered (review R2_MACOS #8)
    }
    private(set) var screens: [Screen] = []
    let native: NativeHost
    /// The shared world every panel is a viewport onto (SPRITES_UNIFY_MONITORS_AS_ONE).
    private(set) var span: SpanLayout
    /// Hits in WORLD stage px — one list for the whole cast, because there is one simulation.
    var hits: [Hit] = []
    var loaded = false
    private var pending = JSQueue()   // bounded, latest call per kind (Decide.swift; review R1 #18)
    /// hit, id, pid, project, project_key, ghost (R1 #17), clickCount (CLICK-3: the gesture)
    var onClick: ((Hit?, String, pid_t, String, String, Bool, Int) -> Void)?

    /// Build the world and one panel per screen. The JS world is the UNION of every screen, so the cast exists ONCE
    /// across all of them; each panel renders the sub-rect its screen covers (Native.swift viewports).
    init(span s: SpanLayout, screens scrs: [NSScreen]) {
        span = s
        // The world's own scale is the finest any panel needs, so the recording is never coarser than a screen shows.
        let scale = scrs.map { panelScale($0.backingScaleFactor) }.max() ?? 2
        // 🔴 SPAN: the host's PRIMARY VIEWPORT renders screen 0's panel, so it is sized to that PANEL, not to the world.
        // Passing only the world (f48a980) made the primary drawable the size of the union inside a one-screen layer,
        // which CAMetalLayer rescaled: the "squished horizontally" and "blurrier" regressions. With one screen the
        // panel IS the world, so the Laptop is bit-for-bit unchanged.
        let out = scrs.first.map { viewportOutput(panelSize: $0.frame.size, backing: $0.backingScaleFactor) }
        native = NativeHost(size: s.size, scale: scale, outSize: out?.size, outScale: out?.scale)
        super.init()
        native.onMessage = { [weak self] body in self?.handle(body) }
        if native.loaded {
            loaded = true
            js("SpritesStage.setSize(\(Int(s.size.width)), \(Int(s.size.height)))")
        } else { log("native stage failed to load (nothing to show)") }
        for (i, scr) in scrs.enumerated() {
            let wr = i < s.rects.count ? s.rects[i] : .zero
            let panel = Stage.makePanel(scr)
            // Viewport 0 is the host's own; the rest are extra outputs onto the same recording.
            let view: NativeView? = i == 0
                ? { _ = native.placeViewport(0, origin: viewportOrigin(wr), scale: panelScale(scr.backingScaleFactor)); return native.view }()
                : native.addViewport(size: scr.frame.size, scale: panelScale(scr.backingScaleFactor), origin: viewportOrigin(wr))
            if let view, viewportDraws(wr) {
                // Every panel's mouse-down is reported in WORLD px, so one click resolves against the one cast.
                view.onMouseDown = { [weak self] p, count in
                    guard let self else { return }
                    self.native.mouseDown(CGPoint(x: p.x + wr.minX, y: p.y + wr.minY), count: count)
                }
                view.autoresizingMask = [.width, .height]
                panel.contentView = view
            }
            // One line per panel: the world it is a viewport onto, and the output it actually renders. This is the
            // measurement that caught the squish — a viewport whose device px are not its screen's device px is
            // rescaled by CAMetalLayer, which no screenshot explains on its own.
            let po = viewportOutput(panelSize: scr.frame.size, backing: scr.backingScaleFactor)
            log("span: viewport \(i) \(scr.localizedName) world=(\(Int(wr.minX)),\(Int(wr.minY)) \(Int(wr.width))x\(Int(wr.height))) "
                + "out=\(Int(po.size.width))x\(Int(po.size.height))@\(po.scale) = \(Int(po.size.width * po.scale))x\(Int(po.size.height * po.scale)) device px")
            screens.append(Screen(screen: scr, panel: panel, world: wr))
        }
        log("span: world \(Int(s.size.width))x\(Int(s.size.height)) @\(scale) recording, \(native.viewportCount()) viewport(s)")
        pushVisible()
    }

    static func makePanel(_ scr: NSScreen) -> StagePanel {
        let panel = StagePanel(contentRect: scr.frame, styleMask: [.borderless, .nonactivatingPanel],
                               backing: .buffered, defer: false)
        panel.isOpaque = false
        panel.backgroundColor = .clear
        panel.hasShadow = false
        SpaceRules.applyStage(panel)
        panel.hidesOnDeactivate = false
        panel.ignoresMouseEvents = true
        panel.becomesKeyOnlyIfNeeded = true   // never key, never main: a click activates nothing here
        panel.isReleasedWhenClosed = false
        panel.setFrame(scr.frame, display: false)
        return panel
    }

    /// R1_SPEC S4 + SPAN: ONE visible rect for the whole world — the walkable area (`spanVisibleRect`), every point of
    /// which is on a real screen, below the menu bar and clear of the Dock. That is what keeps the cast out of the
    /// dead space a union of offset monitors contains.
    private var lastVisible = ""
    func pushVisible() {
        let m = visibleMessage(spanVisibleRect(span))
        guard m != lastVisible else { return }
        lastVisible = m
        js("SpritesStage.setVisible && SpritesStage.setVisible(\(m))")
    }

    /// Re-fit to a new screen arrangement, reusing panels and the ONE simulation where the world size is unchanged, so
    /// nothing flashes and no creature is stranded (DimLayer.refit is the precedent). Returns false when the world
    /// itself resized, which needs a rebuild (the recording's size is baked into the renderer).
    func refit(span s: SpanLayout, screens scrs: [NSScreen]) -> Bool {
        guard s.size == span.size, scrs.count == screens.count else { return false }
        // 🔴 Each viewport's render target size is BAKED INTO its MetalStage, so a re-fit may only reuse them when
        // every panel's output is unchanged. Two screens swapping places keeps the world size but changes the panels,
        // and reusing a renderer there is exactly the stale-drawable squish this pass fixed. Rebuild instead.
        guard zip(scrs, screens).allSatisfy({ new, old in
            new.frame.size == old.screen.frame.size && panelScale(new.backingScaleFactor) == panelScale(old.screen.backingScaleFactor)
        }) else { return false }
        span = s
        for (i, scr) in scrs.enumerated() {
            let wr = i < s.rects.count ? s.rects[i] : .zero
            screens[i].screen = scr
            screens[i].world = wr
            if screens[i].panel.frame != scr.frame { screens[i].panel.setFrame(scr.frame, display: false) }
            _ = native.placeViewport(i, origin: viewportOrigin(wr), scale: panelScale(scr.backingScaleFactor))
        }
        pushVisible()
        return true
    }

    func close() {
        native.close()
        for s in screens { s.panel.orderOut(nil); s.panel.close() }
        screens = []
    }

    /// Calls queue until the stage has loaded.
    func js(_ s: String) {
        guard loaded else { pending.add(s); return }
        native.js(s)
    }

    func handle(_ body: [String: Any]) {
        if let hs = body["hits"] as? [[String: Any]] {
            hits = hs.compactMap { h in
                guard let x = num(h["x"]), let y = num(h["y"]), let r = num(h["r"]) else { return nil }
                return Hit(id: "\(h["id"] ?? "")", pid: pid_t(num(h["pid"]) ?? 0),
                           project: h["project"] as? String ?? "", x: x, y: y, r: r,
                           concept: h["concept"] as? String ?? "", key: h["key"] as? String ?? "")
            }
            if debugClicks {
                log("hits world(\(Int(span.size.width))x\(Int(span.size.height))): " + hits.map {
                    "\($0.project)/\($0.id)@(\(Int($0.x)),\(Int($0.y)))r\(Int($0.r))" }.joined(separator: " "))
            }
        }
        if let c = body["click"] as? [String: Any] {
            let id = "\(c["id"] ?? "")"
            onClick?(hits.first { $0.id == id }, id, pid_t(num(c["pid"]) ?? 0), c["project"] as? String ?? "",
                     c["key"] as? String ?? "", (c["ghost"] as? Bool) == true, Int(num(c["count"]) ?? 1))
        }
    }

    /// Per-panel flags (the fade and the occlusion check stay per screen: a full-screen video on one monitor must
    /// not take the sprites off the other).
    func setFaded(_ i: Int, _ on: Bool) { guard i < screens.count else { return }; screens[i].fsFaded = on }
    func setOccluded(_ i: Int, _ on: Bool) { guard i < screens.count else { return }; screens[i].occluded = on }

    /// Cocoa global point -> world stage px. One conversion for every screen (the per-screen `stagePoint` could not
    /// express a coordinate that crosses panels).
    func world(_ p: NSPoint) -> CGPoint { worldPoint(p, world: span.world) }

    /// Is any panel faded out for full-screen content? (A click is never taken through a faded panel.)
    var anyFaded: Bool { screens.contains { $0.fsFaded } }

    /// Is this Cocoa global point within `margin` of any hit circle (drives the fast cursor poll)?
    func near(_ p: NSPoint, margin: CGFloat) -> Bool {
        guard screenIndex(p) >= 0 else { return false }
        let s = world(p)
        return hits.contains { h in let dx = s.x - h.x, dy = s.y - h.y, r = h.r + margin; return dx * dx + dy * dy <= r * r }
    }

    /// Which panel holds this Cocoa global point (-1 = none). Replaces the old `screen.frame.contains(p)` guards; the
    /// click path must still resolve to exactly one panel now that world coordinates cross panels (R3-SPEC #1/#2).
    func screenIndex(_ p: NSPoint) -> Int {
        for (i, s) in screens.enumerated() where s.screen.frame.contains(p) { return i }
        return -1
    }

    /// Is this Cocoa global point inside any reported hit circle? (CLICK-2: one rule, `captureNeeded`.)
    /// The panel under the cursor decides, but the hits are the world's, so a sprite straddling the seam is clickable
    /// from either side.
    func overSprite(_ p: NSPoint) -> Bool {
        let i = screenIndex(p)
        guard i >= 0 else { return false }
        return captureNeeded(cursor: world(p), hits: hits, faded: screens[i].fsFaded)
    }
}

func num(_ v: Any?) -> CGFloat? {
    if let n = v as? NSNumber { return CGFloat(truncating: n) }
    if let s = v as? String, let d = Double(s) { return CGFloat(d) }
    return nil
}

func jsonString(_ obj: Any) -> String {
    guard JSONSerialization.isValidJSONObject(obj),
          let d = try? JSONSerialization.data(withJSONObject: obj) else { return "null" }
    return String(data: d, encoding: .utf8) ?? "null"
}

/// Desktop-icon dimming (owner, 2026-11-01): one black, click-through window per screen at
/// desktop-icon level + 1 (measured on macOS 26: Finder's icon window is at exactly that key's
/// level, app windows at 0), so it shades the icons and labels and nothing above them.
final class DimLayer {
    static let level = NSWindow.Level(rawValue: Int(CGWindowLevelForKey(.desktopIconWindow)) + 1)
    static let rules: NSWindow.CollectionBehavior = [.canJoinAllSpaces, .stationary, .ignoresCycle]
    private var windows: [NSWindow] = []
    private(set) var alpha: CGFloat = 0

    /// Re-fit to the current screens; reuses windows so a screen change does not flash.
    func layout() {
        let screens = NSScreen.screens
        while windows.count > screens.count { let w = windows.removeLast(); w.orderOut(nil); w.close() }
        while windows.count < screens.count { windows.append(Self.make()) }
        for (w, s) in zip(windows, screens) where w.frame != s.frame { w.setFrame(s.frame, display: false) }
        apply()
    }

    /// 0...0.8; 0 orders every window out.
    func set(_ a: CGFloat) {
        let v = min(0.8, max(0, a))
        if v == alpha { return }
        alpha = v; apply()
    }

    private func apply() {
        for w in windows {
            if alpha <= 0 { w.orderOut(nil); continue }
            w.backgroundColor = NSColor.black.withAlphaComponent(alpha)
            if !w.isVisible { w.orderFrontRegardless() }
        }
    }

    static func make() -> NSWindow {
        let w = StagePanel(contentRect: .zero, styleMask: [.borderless, .nonactivatingPanel], backing: .buffered, defer: false)
        w.isOpaque = false
        w.hasShadow = false
        w.level = level
        w.collectionBehavior = rules
        w.sharingType = .none   // review R1_MACOS #14
        w.hidesOnDeactivate = false
        w.ignoresMouseEvents = true
        w.isReleasedWhenClosed = false
        w.animationBehavior = .none
        return w
    }
}
