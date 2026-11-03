import AppKit
import WebKit

/// The normal (activating) settings window hosting settings.html, same WebKit runtime as the stage.
final class SettingsWindow: NSObject, WKScriptMessageHandler, WKNavigationDelegate, NSWindowDelegate {
    let window: NSWindow
    let web: WKWebView
    var onSaveCast: ((Any) -> Void)?
    var onSaveBehaviors: ((Any) -> Void)?
    var onSetDemo: ((Bool) -> Void)?
    var onSetSize: ((Double) -> Void)?
    var onSetHidden: ((Bool) -> Void)?, onSetMeeting: ((Bool) -> Void)?   // review R1 #13
    var size = 1.0
    var demo = false
    var hidden = false, meeting = false, hotkeyOK = true

    override init() {
        window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 1100, height: 760),
                          styleMask: [.titled, .closable, .miniaturizable, .resizable], backing: .buffered, defer: false)
        window.title = "Sprites Settings"
        window.appearance = NSAppearance(named: .darkAqua)
        window.backgroundColor = NSColor(calibratedRed: 0.04, green: 0.04, blue: 0.07, alpha: 1)
        window.isReleasedWhenClosed = false
        window.collectionBehavior = [.moveToActiveSpace, .fullScreenAuxiliary]
        let cfg = WKWebViewConfiguration()
        cfg.preferences.setValue(true, forKey: "allowFileAccessFromFileURLs")
        web = WKWebView(frame: window.contentView!.bounds, configuration: cfg)
        web.setValue(false, forKey: "drawsBackground")
        web.autoresizingMask = [.width, .height]
        super.init()
        cfg.userContentController.add(WeakHandler(self), name: "settings")
        web.navigationDelegate = self
        window.contentView = web
        window.delegate = self
        window.center()
        load()
    }

    func load() {
        let page = Paths.settings
        if FileManager.default.fileExists(atPath: page.path) {
            web.loadFileURL(page, allowingReadAccessTo: Paths.sprites)
        } else {
            web.loadHTMLString("""
            <html><body style="background:#0a0a12;color:#9fd;font:15px -apple-system;display:flex;
            align-items:center;justify-content:center;height:100vh;margin:0">
            <div style="text-align:center;text-shadow:0 0 12px #6fc">Sprites settings are not built yet.<br>
            <span style="opacity:.6">expected \(page.path)</span></div></body></html>
            """, baseURL: nil)
        }
    }

    /// The app that was frontmost before Settings took activation (review R1_MACOS #7).
    private var previousApp: pid_t?
    func show() {
        if !window.isVisible {
            load()
            let f = NSWorkspace.shared.frontmostApplication?.processIdentifier
            if f != getpid() { previousApp = f }
        }
        NSApp.activate(ignoringOtherApps: true)
        window.makeKeyAndOrderFront(nil)
    }

    func webView(_ w: WKWebView, didFinish n: WKNavigation!) {
        guard FileManager.default.fileExists(atPath: Paths.settings.path) else { return }
        var cast: Any = NSNull()
        if let d = FileManager.default.contents(atPath: Paths.cast),
           let o = try? JSONSerialization.jsonObject(with: d) { cast = o }
        // R1 #2: the shared project table (focus rows become the Settings rows; the cast is keyed by project_key)
        let table = ProjectTable.shared.current().0
        let projects: Any = table.contains { ($0["focus"] as? Bool) == true } ? table : (waypointProjects().map { $0 as Any } ?? ["waypoint": false])
        var behaviors: Any = [String: Any]()
        if let d = FileManager.default.contents(atPath: Paths.behaviors),
           let o = try? JSONSerialization.jsonObject(with: d) { behaviors = o }
        let arg = jsonString(["cast": cast, "projects": projects, "behaviors": behaviors, "demo": demo, "size": size,
                              "hidden": hidden, "meeting": meeting, "hotkey": "⌃⌥⌘S", "hotkeyOK": hotkeyOK])
        web.evaluateJavaScript("try { SpritesSettings.init(\(arg)) } catch (e) { 'err:' + e }") { r, _ in
            if let s = r as? String, s.hasPrefix("err:") { log("settings js: \(s)") }
        }
    }

    func userContentController(_ c: WKUserContentController, didReceive m: WKScriptMessage) {
        guard let body = m.body as? [String: Any] else { return }
        if let cast = body["saveCast"] { onSaveCast?(cast) }
        if let b = body["saveBehaviors"] { onSaveBehaviors?(b) }
        if let d = body["setDemo"] as? Bool { onSetDemo?(d) }
        if let z = body["setSize"] as? Double { onSetSize?(z) }
        if let h = body["setHidden"] as? Bool { onSetHidden?(h) }
        if let v = body["setMeeting"] as? Bool { onSetMeeting?(v) }
    }

    func windowWillClose(_ n: Notification) {
        switch settingsCloseAction(previous: previousApp, me: getpid(),
                                   isRunning: { NSRunningApplication(processIdentifier: $0).map { !$0.isTerminated } ?? false }) {
        case .reactivate(let p): if let a = NSRunningApplication(processIdentifier: p) { activateApp(a) }
        case .hide: NSApp.hide(nil)
        }
        previousApp = nil
    }

    /// Mirror a change made from the menu or the hotkey into an open window.
    func mirrorVisibility(hidden h: Bool, meeting v: Bool) {
        hidden = h; meeting = v
        guard window.isVisible else { return }
        web.evaluateJavaScript("window.SpritesSettings && SpritesSettings.setVisibility({hidden: \(h), meeting: \(v)})", completionHandler: nil)
    }
}
