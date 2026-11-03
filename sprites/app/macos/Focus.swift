import AppKit
import CoreGraphics
import QuartzCore

/// The frontmost app's frontmost layer-0 window, in CG global coordinates (top-left origin of the
/// primary display). Window bounds need no Screen Recording grant; names would, and are not read.
/// The on-screen window list, read at most once per 50 ms and shared (focus, windows and full-screen all read it).
private var windowListCache: (t: CFTimeInterval, list: [[String: Any]])? = nil
func windowList() -> [[String: Any]] {
    let now = CACurrentMediaTime()
    if let c = windowListCache, now - c.t < 0.05 { return c.list }
    let list = (CGWindowListCopyWindowInfo([.optionOnScreenOnly, .excludeDesktopElements], kCGNullWindowID) as? [[String: Any]]) ?? []
    windowListCache = (now, list); return list
}

/// Every on-screen window of any layer (layer, pid, rect, alpha), front to back, from the shared read.
func allWindows() -> [(layer: Int, pid: pid_t, rect: CGRect, alpha: Double)] {
    windowList().compactMap { w in
        guard let layer = w[kCGWindowLayer as String] as? Int, let pid = w[kCGWindowOwnerPID as String] as? Int32,
              let b = w[kCGWindowBounds as String] as? NSDictionary, let r = CGRect(dictionaryRepresentation: b) else { return nil }
        return (layer, pid, r, (w[kCGWindowAlpha as String] as? Double) ?? 1)
    }
}

/// The frontmost app's frontmost layer-0 window: (window number, CG rect).
func focusedWindow(list: [[String: Any]]) -> (id: Int, rect: CGRect)? {
    guard let app = NSWorkspace.shared.frontmostApplication,
          app.processIdentifier != ProcessInfo.processInfo.processIdentifier else { return nil }
    let pid = app.processIdentifier
    for w in list {     // front to back
        guard (w[kCGWindowOwnerPID as String] as? Int32) == pid,
              (w[kCGWindowLayer as String] as? Int) == 0,
              ((w[kCGWindowAlpha as String] as? Double) ?? 1) > 0,
              let b = w[kCGWindowBounds as String] as? NSDictionary,
              let r = CGRect(dictionaryRepresentation: b),
              r.width > 50, r.height > 50 else { continue }
        return ((w[kCGWindowNumber as String] as? Int) ?? 0, r)
    }
    return nil
}
func focusedWindowRect() -> CGRect? { focusedWindow(list: windowList()).map { $0.rect } }

/// One window's current bounds alone (`.optionIncludingWindow`: ~0.11 ms vs 0.3-0.45 ms for the full list; handoff
/// item 3). nil = gone or off screen.
func windowBounds(_ id: Int) -> CGRect? {
    guard id > 0, let l = CGWindowListCopyWindowInfo([.optionIncludingWindow], CGWindowID(id)) as? [[String: Any]],
          let w = l.first, (w[kCGWindowIsOnscreen as String] as? Bool) ?? true,
          let b = w[kCGWindowBounds as String] as? NSDictionary else { return nil }
    return CGRect(dictionaryRepresentation: b)
}

/// The 2 Hz host tick (handoff item 3, pushFocus): read only the focused window's bounds; the full window list (focus,
/// windows, full-screen fade, all from one read) only when that window moved or changed, or every `fullEvery` ticks as a
/// safety net for other windows. App switches and Space changes push at once (notifications), not through this.
func tickNeedsFullRead(tick: Int, focusedBefore: CGRect?, focusedNow: CGRect?, fullEvery: Int = 4) -> Bool {
    if tick % fullEvery == 0 { return true }
    guard let a = focusedBefore, let b = focusedNow else { return focusedBefore != nil || focusedNow != nil }
    return a != b
}

/// CG global rect -> this screen's stage px (top-left origin), clipped; nil if it misses the screen.
func stageRect(_ cg: CGRect, on screen: NSScreen) -> CGRect? {
    guard let primary = NSScreen.screens.first else { return nil }
    let f = screen.frame
    // CG y is measured down from the primary's top; Cocoa y up from its bottom.
    let screenTopCG = primary.frame.maxY - f.maxY
    let r = CGRect(x: cg.minX - f.minX, y: cg.minY - screenTopCG, width: cg.width, height: cg.height)
    let clipped = r.intersection(CGRect(origin: .zero, size: f.size))
    return clipped.isNull || clipped.width < 1 || clipped.height < 1 ? nil : clipped
}

/// Cocoa global point -> this screen's stage px.
func stagePoint(_ p: NSPoint, on screen: NSScreen) -> CGPoint {
    CGPoint(x: p.x - screen.frame.minX, y: screen.frame.maxY - p.y)
}

/// On-screen layer-0 windows, front to back, in CG global coordinates, with their owner pid and window number.
func onScreenWindowsWithID() -> [(rect: CGRect, pid: pid_t, id: Int)] {
    let list = windowList()
    let me = ProcessInfo.processInfo.processIdentifier
    return list.compactMap { w in
        guard (w[kCGWindowLayer as String] as? Int) == 0,
              let pid = w[kCGWindowOwnerPID as String] as? Int32, pid != me,
              ((w[kCGWindowAlpha as String] as? Double) ?? 1) > 0,
              let b = w[kCGWindowBounds as String] as? NSDictionary,
              let r = CGRect(dictionaryRepresentation: b),
              r.width > 50, r.height > 50 else { return nil }
        return (r, pid, (w[kCGWindowNumber as String] as? Int) ?? 0)
    }
}
func onScreenWindows() -> [(rect: CGRect, pid: pid_t)] { onScreenWindowsWithID().map { ($0.rect, $0.pid) } }

/// A screen's frame in CG global coordinates (top-left origin of the primary display).
func cgFrame(_ screen: NSScreen) -> CGRect {
    let primary = NSScreen.screens.first?.frame ?? screen.frame
    let f = screen.frame
    return CGRect(x: f.minX, y: primary.maxY - f.maxY, width: f.width, height: f.height)
}

/// Full-screen content on this screen (review R1_MACOS #9): the topmost layer-0 window on this screen, of ANY app,
/// covers the whole screen, menu bar included (a zoomed window stops below the menu bar). So full-screen video on a
/// second display fades that display even while another app is frontmost elsewhere.
func isFullScreen(_ screen: NSScreen, windows: [(rect: CGRect, pid: pid_t)]) -> Bool {
    coversScreen(cgFrame(screen), windows: windows)
}
func coversScreen(_ sf: CGRect, windows: [(rect: CGRect, pid: pid_t)]) -> Bool {
    guard let w = windows.first(where: { $0.rect.intersects(sf) }) else { return false }
    return w.rect.insetBy(dx: -1, dy: -1).contains(sf)
}

/// Seconds since the last input of a kind; HID idle time, no TCC grant needed.
func secondsSince(_ t: CGEventType) -> Double {
    CGEventSource.secondsSinceLastEventType(.combinedSessionState, eventType: t)
}
let anyInputEvent = CGEventType(rawValue: ~0)!
