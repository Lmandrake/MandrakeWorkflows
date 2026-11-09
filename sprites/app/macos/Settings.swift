import AppKit
import WebKit

/// The normal (activating) settings window hosting settings.html, same WebKit runtime as the stage.
/// `SPRITES_DEBUG_SETTINGS=1`: log every message between the host and settings.js (both directions, timestamped), turn on
/// the page's own trace (every programmatic write to a colour input, with its stack), and evaluate any JS dropped into
/// ~/agent-storage/sprites/run/settings-eval.js (read once, then deleted; the result is logged). Off by default. Built to
/// chase the colour picker revert (owner, 2026-11-08: "it reverts back to the previous color").
let debugSettings = ProcessInfo.processInfo.environment["SPRITES_DEBUG_SETTINGS"] == "1"
func dlog(_ msg: String) {
    guard debugSettings else { return }
    FileHandle.standardError.write(String(format: "sprites: [%.3f] settings %@\n", CFAbsoluteTimeGetCurrent(), msg).data(using: .utf8)!)
}

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
    var onSetProjectFocus: ((String, String, Bool, String, String) -> String?)?   // + name, dir (local-file fallback)
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
        if debugSettings {
            evalTimer = Timer.scheduledTimer(withTimeInterval: 0.25, repeats: true) { [weak self] _ in
                let f = Paths.home + "/agent-storage/sprites/run/settings-eval.js"
                guard let self, let d = FileManager.default.contents(atPath: f), let src = String(data: d, encoding: .utf8) else { return }
                try? FileManager.default.removeItem(atPath: f)
                self.js(src, "eval") { r, e in dlog("eval result: \(r.map { "\($0)" } ?? "nil") \(e.map { "error \($0)" } ?? "")") }
            }
        }
    }
    private var evalTimer: Timer?

    /// Every host -> page call goes through here, so a debug run logs them all.
    func js(_ src: String, _ tag: String, _ done: ((Any?, Error?) -> Void)? = nil) {
        dlog("-> js \(tag): \(src.prefix(160))")
        web.evaluateJavaScript(src, completionHandler: done)
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
        // Every active sprite is listed too (owner, 2026-11-08), so the table goes over whenever it has rows.
        let snapshot = FileManager.default.contents(atPath: Paths.state).flatMap { try? JSONSerialization.jsonObject(with: $0) } ?? NSNull()
        let listable = !table.isEmpty
        let projects: Any = listable ? table : (waypointProjects().map { $0 as Any } ?? ["waypoint": false])
        var behaviors: Any = [String: Any]()
        if let d = FileManager.default.contents(atPath: Paths.behaviors),
           let o = try? JSONSerialization.jsonObject(with: d) { behaviors = o }
        let arg = jsonString(["cast": cast, "projects": projects, "behaviors": behaviors, "demo": demo, "size": size,
                              "hidden": hidden, "meeting": meeting, "hotkey": "⌃⌥⌘S", "hotkeyOK": hotkeyOK,
                              "hasWaypoint": hasWaypoint, "snapshot": snapshot, "debug": debugSettings])
        js("try { SpritesSettings.init(\(arg)) } catch (e) { 'err:' + e }", "init") { r, _ in
            if let s = r as? String, s.hasPrefix("err:") { log("settings js: \(s)") }
        }
    }

    func userContentController(_ c: WKUserContentController, didReceive m: WKScriptMessage) {
        guard let body = m.body as? [String: Any] else { return }
        if let t = body["debugLog"] as? String { dlog("<- page: \(t)"); return }
        if debugSettings { dlog("<- post \(body.keys.sorted().joined(separator: ",")): \(jsonString(body).prefix(200))") }
        if let cast = body["saveCast"] { onSaveCast?(cast) }
        if let b = body["saveBehaviors"] { onSaveBehaviors?(b) }
        if let d = body["setDemo"] as? Bool { onSetDemo?(d) }
        if let z = body["setSize"] as? Double { onSetSize?(z) }
        if let h = body["setHidden"] as? Bool { onSetHidden?(h) }
        if let v = body["setMeeting"] as? Bool { onSetMeeting?(v) }
        // Per-project colour / focus: the write can shell out to the waypoint CLI, so it runs off the
        // main thread and the result is reported back by id (the UI reverts the control on an error).
        for kind in ["setProjectColour", "setProjectFocus"] {
            if let o = body[kind] as? [String: Any], let run = projectWrite(kind, o) { write(o) { _, _ in run() } }
        }
    }

    /// The write a {setProjectColour|setProjectFocus: o} message asks for, as a closure answering nil (it landed) or a
    /// message (tests/swift/host calls it with a stub handler).
    func projectWrite(_ kind: String, _ o: [String: Any]) -> (() -> String?)? {
        let k = (o["key"] as? String) ?? "", a = (o["alias"] as? String) ?? ""
        switch kind {
        case "setProjectColour":
            let h = onSetProjectColour
            return { projectWriteError(h.map { f in { f(k, a, (o["hex"] as? String) ?? "") } }) }
        case "setProjectFocus":
            let h = onSetProjectFocus
            return { projectWriteError(h.map { f in { f(k, a, (o["focus"] as? Bool) ?? false, (o["name"] as? String) ?? "", (o["dir"] as? String) ?? "") } }) }
        default: return nil
        }
    }

    /// Run one project write off the main thread, then hand the UI {id, error} back.
    /// 🔴 The handler's own nil IS success. It was `(self?.onSetProjectColour?(...)) ?? "no handler"`, where optional
    /// chaining flattens String?? to String?, so every successful write came back as "no handler" and the page reverted
    /// the picker under the open colour panel (owner, 2026-11-08). projectWriteError keeps the two nils apart.
    private let writeQueue = DispatchQueue(label: "com.mandrake.sprites.settings-write", qos: .userInitiated)
    private func write(_ o: [String: Any], _ body: @escaping (String, String) -> String?) {
        let id = (o["id"] as? String) ?? ""
        let key = (o["key"] as? String) ?? "", alias = (o["alias"] as? String) ?? ""
        writeQueue.async {   // serial: two rewrites of launches.md never race, and answers come back in send order
            let err = body(key, alias)
            DispatchQueue.main.async { [weak self] in
                guard let self, self.window.isVisible else { return }
                let arg = jsonString(["id": id, "error": err as Any? ?? NSNull()] as [String: Any])
                self.js("window.SpritesSettings && SpritesSettings.writeResult(\(arg))", "writeResult")
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

    /// The Augur snapshot changed: the window re-derives which sprites are active (its rows), only while open.
    func mirrorSnapshot(_ text: String?) {
        guard window.isVisible, let t = text, !t.isEmpty else { return }
        js("window.SpritesSettings && SpritesSettings.setSnapshot && SpritesSettings.setSnapshot(\(t))", "setSnapshot")
    }

    /// Mirror a change made from the menu or the hotkey into an open window.
    func mirrorVisibility(hidden h: Bool, meeting v: Bool) {
        hidden = h; meeting = v
        guard window.isVisible else { return }
        js("window.SpritesSettings && SpritesSettings.setVisibility({hidden: \(h), meeting: \(v)})", "setVisibility")
    }

    /// The Aether's drifting constants (AetherHost, about once a second while drift is on), into an open window.
    func mirrorAetherDrift(_ d: [String: Double]) {
        guard window.isVisible else { return }
        js("window.SpritesSettings && SpritesSettings.setAetherDrift && SpritesSettings.setAetherDrift(\(jsonString(d)))", "setAetherDrift")
    }
}

/// The error a project write reports: "no handler" only when there is no handler; otherwise the handler's own answer,
/// where nil means it succeeded.
func projectWriteError(_ run: (() -> String?)?) -> String? {
    guard let run else { return "no handler" }
    return run()
}
