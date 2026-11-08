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
    /// Per-project colour and focus (owner, 2026-11-05). (key, alias, hex|focus) -> nil on success, else a
    /// message for the UI. Waypoint present: the waypoint CLI rewrites launches.md; absent: the local file.
    var onSetProjectColour: ((String, String, String) -> String?)?
    var onSetProjectFocus: ((String, String, Bool) -> String?)?
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
        // Without Waypoint the colour and focus a launch row would carry come from the local file instead
        // (Paths.projects), applied over the same table so the UI and the write-back agree on one shape.
        let hasWaypoint = waypointCLIPath() != nil
        var table = ProjectTable.shared.current().0
        if !hasWaypoint {
            // No Waypoint: there are no launch rows, so a project's colour and focus marker come from the
            // local settings file instead, over the registry projects (which Lodestar supplies either way).
            // A project with no colour yet gets the same neutral default waypointProjects() uses, so the row
            // is listable and the picker opens on something rather than being dropped for a missing hex.
            let local = loadLocalProjects()
            table = table.compactMap { row in
                guard let k = row["key"] as? String, !k.isEmpty else { return nil }
                var r = row
                let e = local[k] ?? [:]
                r["hex"] = (e["hex"] as? String) ?? (row["hex"] as? String) ?? "#8899AA"
                r["focus"] = (e["focus"] as? Bool) ?? false
                return r
            }
        }
        let listable = hasWaypoint ? table.contains { ($0["focus"] as? Bool) == true } : !table.isEmpty
        let projects: Any = listable ? table : (waypointProjects().map { $0 as Any } ?? ["waypoint": false])
        var behaviors: Any = [String: Any]()
        if let d = FileManager.default.contents(atPath: Paths.behaviors),
           let o = try? JSONSerialization.jsonObject(with: d) { behaviors = o }
        let arg = jsonString(["cast": cast, "projects": projects, "behaviors": behaviors, "demo": demo, "size": size,
                              "hidden": hidden, "meeting": meeting, "hotkey": "⌃⌥⌘S", "hotkeyOK": hotkeyOK,
                              "hasWaypoint": hasWaypoint])
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
        // Per-project colour / focus: the write can shell out to the waypoint CLI, so it runs off the
        // main thread and the result is reported back by id (the UI reverts the control on an error).
        if let o = body["setProjectColour"] as? [String: Any] {
            write(o) { [weak self] k, a in (self?.onSetProjectColour?(k, a, (o["hex"] as? String) ?? "")) ?? "no handler" }
        }
        if let o = body["setProjectFocus"] as? [String: Any] {
            write(o) { [weak self] k, a in (self?.onSetProjectFocus?(k, a, (o["focus"] as? Bool) ?? false)) ?? "no handler" }
        }
    }

    /// Run one project write off the main thread, then hand the UI {id, error} back.
    private func write(_ o: [String: Any], _ body: @escaping (String, String) -> String?) {
        let id = (o["id"] as? String) ?? ""
        let key = (o["key"] as? String) ?? "", alias = (o["alias"] as? String) ?? ""
        DispatchQueue.global(qos: .userInitiated).async {
            let err = body(key, alias)
            DispatchQueue.main.async { [weak self] in
                guard let self, self.window.isVisible else { return }
                let arg = jsonString(["id": id, "error": err as Any? ?? NSNull()] as [String: Any])
                self.web.evaluateJavaScript("window.SpritesSettings && SpritesSettings.writeResult(\(arg))",
                                            completionHandler: nil)
            }
        }
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
