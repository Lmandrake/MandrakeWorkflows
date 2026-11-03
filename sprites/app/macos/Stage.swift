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
func captureAllowed(cursor: CGPoint, windows: [(layer: Int, pid: pid_t, rect: CGRect, alpha: Double)], me: pid_t,
                    screens: [CGRect]) -> Bool {
    for w in windows where w.pid != me && w.layer > 0 && w.alpha > 0 && w.rect.contains(cursor) {
        if screens.contains(where: { w.rect.insetBy(dx: -1, dy: -1).contains($0) }) { continue }   // a screen-sized container
        return false
    }
    return true
}

/// NSScreen.visibleFrame (Cocoa, bottom-left origin) -> this screen's stage px (top-left origin), for
/// `SpritesStage.setVisible` (review R1_SPEC S4: the Dock on any side, the menu bar).
func visibleStageRect(visible v: NSRect, frame f: NSRect) -> CGRect {
    CGRect(x: v.minX - f.minX, y: f.maxY - v.maxY, width: v.width, height: v.height)
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

struct Hit { let id: String; let pid: pid_t; let project: String; let x, y, r: CGFloat }

/// One transparent, click-through panel covering one NSScreen, running stage.html's script natively (JavaScriptCore +
/// Metal, Native.swift; docs/NATIVE_PORT.md). The WKWebView renderer was removed at the swap (2026-11-01, owner's
/// no-duplicates rule); stage.html still runs in a browser for the headless tests.
final class Stage: NSObject {
    let screen: NSScreen
    let panel: StagePanel
    let native: NativeHost
    var hits: [Hit] = []
    var fsFaded = false
    var occluded = false   // panel fully covered (review R2_MACOS #8)
    var loaded = false
    private var pending = JSQueue()   // bounded, latest call per kind (Decide.swift; review R1 #18)
    var onClick: ((Hit?, String, pid_t, String, String, Bool) -> Void)?   // hit, id, pid, project, project_key, ghost (R1 #17)

    init(screen: NSScreen) {
        self.screen = screen
        panel = StagePanel(contentRect: screen.frame, styleMask: [.borderless, .nonactivatingPanel],
                           backing: .buffered, defer: false)
        panel.isOpaque = false
        panel.backgroundColor = .clear
        panel.hasShadow = false
        SpaceRules.applyStage(panel)
        panel.hidesOnDeactivate = false
        panel.ignoresMouseEvents = true
        panel.becomesKeyOnlyIfNeeded = true   // never key, never main: a click activates nothing here
        panel.isReleasedWhenClosed = false
        panel.setFrame(screen.frame, display: false)

        let h = NativeHost(size: screen.frame.size, scale: min(2, screen.backingScaleFactor))
        native = h
        super.init()
        h.onMessage = { [weak self] body in self?.handle(body) }
        h.view.onMouseDown = { [weak h] p in h?.mouseDown(p) }
        h.view.autoresizingMask = [.width, .height]
        panel.contentView = h.view
        if h.loaded {
            loaded = true
            js("SpritesStage.setSize(\(Int(screen.frame.width)), \(Int(screen.frame.height)))")
        } else { log("native stage failed to load (nothing to show)") }
    }

    func close() {
        native.close()
        panel.orderOut(nil); panel.close()
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
                           project: h["project"] as? String ?? "", x: x, y: y, r: r)
            }
        }
        if let c = body["click"] as? [String: Any] {
            let id = "\(c["id"] ?? "")"
            onClick?(hits.first { $0.id == id }, id, pid_t(num(c["pid"]) ?? 0), c["project"] as? String ?? "",
                     c["key"] as? String ?? "", (c["ghost"] as? Bool) == true)
        }
    }

    /// Is this Cocoa global point within `margin` of any hit circle (drives the fast cursor poll)?
    func near(_ p: NSPoint, margin: CGFloat) -> Bool {
        guard screen.frame.contains(p) else { return false }
        let s = stagePoint(p, on: screen)
        return hits.contains { h in let dx = s.x - h.x, dy = s.y - h.y, r = h.r + margin; return dx * dx + dy * dy <= r * r }
    }

    /// Is this Cocoa global point inside any reported hit circle?
    func overSprite(_ p: NSPoint) -> Bool {
        guard screen.frame.contains(p) else { return false }
        let s = stagePoint(p, on: screen)
        return hits.contains { h in let dx = s.x - h.x, dy = s.y - h.y; return dx * dx + dy * dy <= h.r * h.r }
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
