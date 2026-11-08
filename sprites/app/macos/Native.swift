import AppKit
import JavaScriptCore
import Metal
import QuartzCore
import ImageIO

func rusage_self() -> Double { var u = rusage(); getrusage(RUSAGE_SELF, &u)
    return Double(u.ru_utime.tv_sec + u.ru_stime.tv_sec) + Double(u.ru_utime.tv_usec + u.ru_stime.tv_usec) / 1e6 }

/// The stage's own JS (app/stage.html's script, the runtime, the pieces, labels) running in a JavaScriptCore context,
/// drawing through app/native/canvas.js's recording 2D context into Metal. No WebView.
final class NativeHost {
    let ctx: JSContext
    /// The panel's view, made on first use (on main). A headless host (the QoS bench, on a worker thread) never makes it.
    /// SPAN: sized to the primary viewport's OUTPUT (its panel), never to the world.
    lazy var view: NativeView = { let v = NativeView(frame: NSRect(origin: .zero, size: outSize)); v.metal = renderer
        v.metalLayer.contentsScale = outScale; return v }()
    let headless: Bool
    /// Timers fire on the run loop of the thread that made the host (main for the stage; the bench thread for the bench).
    private let loop = RunLoop.current
    private(set) var offThreadFires = 0, onThreadFires = 0
    /// The WORLD: the recording's size in stage px and the finest scale any panel needs. This is what the JS canvas is
    /// (`__native.w/h/dpr`), and it may be much bigger than any one screen.
    let size: CGSize, scale: CGFloat
    /// 🔴 SPAN: the PRIMARY VIEWPORT's own output — the size in points of the panel it feeds, and that panel's own
    /// backingScaleFactor. It is NOT the world. f48a980 conflated the two: `renderer` was built at world size, so on this
    /// Desktop (two 1920x1080 @2 screens, union 3840x1183) the primary panel's drawable became 7680x2366 device px inside
    /// a 3840x2160 layer. CAMetalLayer then squeezed the drawable into the layer bounds — a measured 2.000x horizontal
    /// and 1.095x vertical compression, i.e. the owner's "squished horizontally" plus the resampling "blurrier". QA
    /// (`--native-frames`, no panels) leaves these nil, so output == world and the offscreen path is unchanged.
    let outSize: CGSize, outScale: CGFloat
    var onMessage: (([String: Any]) -> Void)?
    private var timers: [Int: Timer] = [:]
    private var frameFn: JSValue?, presentedFn: JSValue?, fire: JSValue?
    // SPRITES_NATIVE_STATS=1: every 10 s, timer callbacks, presents and their time on the main thread
    private static let stats = ProcessInfo.processInfo.environment["SPRITES_NATIVE_STATS"] == "1"
    private var stT = CACurrentMediaTime(), stCalls = 0, stJS = 0.0, stPresents = 0, stPresentT = 0.0
    private func stat(_ t0: Double) {
        guard NativeHost.stats else { return }
        let now = CACurrentMediaTime(); stCalls += 1; stJS += now - t0
        if now - stT >= 10 { log(String(format: "native stats: %.1f callbacks/s, %.2f ms each, %.1f presents/s, %.2f ms each, js %.2f%%",
            Double(stCalls) / (now - stT), stJS * 1000 / Double(max(1, stCalls)), Double(stPresents) / (now - stT), stPresentT * 1000 / Double(max(1, stPresents)), stJS / (now - stT) * 100))
            log("native times (count, ms over 10 s): " + (ctx.evaluateScript("__nativeTimes()")?.toString() ?? ""))
            stT = now; stCalls = 0; stJS = 0; stPresents = 0; stPresentT = 0 } }
    fileprivate let renderer: MetalStage?
    /// 🔴 SPAN: ONE label store shared by every viewport. The JS `label` callback rasterizes a hover label once per
    /// frame and hands it to the host; f48a980 wrote it into `renderer` alone, so an extra screen's panel had an
    /// all-blank texture array and showed NO NAMES. One source of truth beats N uploads: the textures are replaced,
    /// never mutated, so a frame already on the GPU keeps the texture it was encoded with.
    fileprivate let labels = LabelStore()
    var loaded = false
    /// SPAN (SPRITES_UNIFY_MONITORS_AS_ONE): extra viewports onto the SAME world and the SAME recording — one per
    /// additional screen. The primary viewport is `renderer`/`view` above; these are built on demand by
    /// `addViewport`, and every present encodes the one recorded frame into each of them with its own world origin.
    /// There is still exactly ONE simulation, so a creature exists once across all monitors.
    fileprivate var extra: [(renderer: MetalStage, view: NativeView)] = []
    func viewportCount() -> Int { 1 + extra.count }

    /// Add a viewport of `size` points at `origin` (world stage px, top-left) rendering at `scale`. Returns its view,
    /// to be installed as another panel's content view; nil if Metal refused (the panel then simply shows nothing).
    func addViewport(size: CGSize, scale: CGFloat, origin: CGPoint) -> NativeView? {
        guard let r = MetalStage(width: Int((size.width * scale).rounded()), height: Int((size.height * scale).rounded()),
                                 labels: labels) else {
            log("span: no Metal device for an extra viewport"); return nil }
        r.origin = CGPoint(x: origin.x * scale, y: origin.y * scale)   // world device px
        r.onFree = { [weak self] in self?.present() }
        let v = NativeView(frame: NSRect(origin: .zero, size: size))
        v.metal = r
        v.metalLayer.contentsScale = scale
        extra.append((r, v))
        return v
    }

    /// Re-place an existing viewport across a screen change (no teardown, so nothing flashes). `index` 0 is the
    /// primary. Returns false when the size changed, which needs a fresh renderer (the caller rebuilds).
    func placeViewport(_ index: Int, origin: CGPoint, scale: CGFloat) -> Bool {
        let r: MetalStage? = index == 0 ? renderer : (index - 1 < extra.count ? extra[index - 1].renderer : nil)
        guard let r else { return false }
        r.origin = CGPoint(x: origin.x * scale, y: origin.y * scale)
        return true
    }

    func closeViewports() { extra.removeAll() }

    /// `outSize`/`outScale`: the PRIMARY PANEL's size in points and its own backing scale. nil (QA, the bench, a
    /// one-screen world) means the output is the world, exactly as before f48a980.
    init(size: CGSize, scale: CGFloat, query: String = "", headless: Bool = false,
         outSize: CGSize? = nil, outScale: CGFloat? = nil) {
        self.size = size; self.scale = scale; self.headless = headless
        self.outSize = outSize ?? size; self.outScale = outScale ?? scale
        let os = self.outSize, osc = self.outScale
        ctx = JSContext()!
        // 🔴 The renderer's target is the PANEL, not the world: a drawable bigger than the layer is silently rescaled.
        renderer = headless ? nil : MetalStage(width: Int((os.width * osc).rounded()), height: Int((os.height * osc).rounded()), labels: labels)
        renderer?.onFree = { [weak self] in self?.present() }
        ctx.exceptionHandler = { _, e in log("native js: \(e?.toString() ?? "?") @\(e?.objectForKeyedSubscript("line")?.toString() ?? "")") }
        install(query: query)
        loaded = load()
        if !headless { watchVisibility() }
    }

    /// R2_MACOS #8: the page is "hidden" (stage.html draws no frames) while the displays sleep, the session is switched
    /// away, or the stage panel is fully occluded, as WebKit hides a page. App.swift's setPaused (package C) still applies on top.
    private var asleep = false, away = false, occluded = false
    private var obs: [(NotificationCenter, NSObjectProtocol)] = []
    private func watchVisibility() {
        let ws = NSWorkspace.shared.notificationCenter, nc = NotificationCenter.default
        func on(_ c: NotificationCenter, _ n: Notification.Name, _ f: @escaping (NativeHost, Notification) -> Void) {
            obs.append((c, c.addObserver(forName: n, object: nil, queue: .main) { [weak self] note in if let self { f(self, note); self.syncHidden() } })) }
        on(ws, NSWorkspace.screensDidSleepNotification) { h, _ in h.asleep = true }
        on(ws, NSWorkspace.screensDidWakeNotification) { h, _ in h.asleep = false }
        on(ws, NSWorkspace.sessionDidResignActiveNotification) { h, _ in h.away = true }
        on(ws, NSWorkspace.sessionDidBecomeActiveNotification) { h, _ in h.away = false }
        on(nc, NSWindow.didChangeOcclusionStateNotification) { h, note in
            guard let w = note.object as? NSWindow, w === h.view.window else { return }
            h.occluded = !w.occlusionState.contains(.visible) }
    }
    var hidden: Bool { asleep || away || occluded }
    private var lastHidden = false
    private func syncHidden() { let hd = hidden; guard hd != lastHidden else { return }; lastHidden = hd
        ctx.objectForKeyedSubscript("__nativeSetHidden")?.call(withArguments: [hd]); presentedFn?.call(withArguments: []) }

    private func install(query: String) {
        let N = JSValue(newObjectIn: ctx)!
        let t0 = CACurrentMediaTime()
        let now: @convention(block) () -> Double = { (CACurrentMediaTime() - t0) * 1000 }
        let read: @convention(block) (String) -> Any = { rel in
            let u = Paths.sprites.appendingPathComponent(rel).standardizedFileURL
            guard u.path.hasPrefix(Paths.sprites.standardizedFileURL.path),
                  let s = try? String(contentsOf: u, encoding: .utf8) else { return NSNull() }
            return s
        }
        let post: @convention(block) (String) -> Void = { [weak self] s in
            guard let d = s.data(using: .utf8), let o = try? JSONSerialization.jsonObject(with: d) as? [String: Any] else { return }
            self?.onMessage?(o)
        }
        let timer: @convention(block) (Int, Double, Bool) -> Void = { [weak self] id, ms, rep in self?.arm(id, ms, rep) }
        let cancel: @convention(block) (Int) -> Void = { [weak self] id in self?.timers.removeValue(forKey: id)?.invalidate() }
        let say: @convention(block) (String) -> Void = { s in log("js: \(s)") }
        let present: @convention(block) () -> Void = { [weak self] in self?.present() }
        // hover labels (canvas.js __endLabel): rasterize cmdrec.js's ops with CoreGraphics into label texture `slot`
        // SPAN: into the SHARED store, so the label reaches EVERY viewport (it went to `renderer` alone, which is why
        // the second screen showed no names). A headless host has no Metal device and so no store: it returns false,
        // exactly as a nil renderer did.
        let label: @convention(block) (String, Int, Double, Double, Double, Double, Double) -> Bool = { [weak self] json, slot, x, y, w, h, dpr in
            guard let self, !self.headless,
                  let img = CGCanvas.render(json: json, width: Int(w), height: Int(h), scale: CGFloat(dpr), originX: CGFloat(x), originY: CGFloat(y))
            else { return false }
            return self.labels.set(slot, img) }
        for (k, v) in [("now", now as Any), ("read", read), ("post", post), ("timer", timer), ("cancel", cancel), ("log", say), ("present", present), ("label", label)] {
            N.setObject(v, forKeyedSubscript: k as NSString)
        }
        N.setObject(query, forKeyedSubscript: "query" as NSString)
        N.setObject(Double(scale), forKeyedSubscript: "dpr" as NSString)
        N.setObject(Double(size.width), forKeyedSubscript: "w" as NSString)
        N.setObject(Double(size.height), forKeyedSubscript: "h" as NSString)
        CGCanvas.install(into: N)
        ctx.setObject(N, forKeyedSubscript: "__native" as NSString)
    }

    /// canvas.js + shim.js, then the files stage.html loads, in its order, then stage.html's own script.
    private func load() -> Bool {
        let root = Paths.sprites
        func src(_ rel: String) -> String? { try? String(contentsOf: root.appendingPathComponent(rel), encoding: .utf8) }
        for rel in ["app/native/canvas.js", "app/native/cmdrec.js", "app/native/shim.js"] {
            guard let s = src(rel) else { log("native: missing \(rel)"); return false }
            ctx.evaluateScript(s, withSourceURL: URL(fileURLWithPath: root.appendingPathComponent(rel).path))
        }
        guard let html = src("app/stage.html") else { log("native: stage.html not found"); return false }
        // <script src="..."> in order (relative to app/), then the last inline <script> (the stage itself)
        let re = try! NSRegularExpression(pattern: "<script(?:\\s+src=\"([^\"]+)\")?[^>]*>([\\s\\S]*?)</script>")
        var inline: [String] = []
        for m in re.matches(in: html, range: NSRange(html.startIndex..., in: html)) {
            if let r = Range(m.range(at: 1), in: html) {
                let rel = "app/" + html[r]
                if let s = src(rel) { ctx.evaluateScript(s, withSourceURL: URL(fileURLWithPath: root.appendingPathComponent(rel).standardizedFileURL.path)) }
            } else if let r = Range(m.range(at: 2), in: html) { inline.append(String(html[r])) }
        }
        guard let stage = inline.last else { log("native: no stage script"); return false }
        ctx.evaluateScript(stage, withSourceURL: URL(fileURLWithPath: root.appendingPathComponent("app/stage.html").path))
        frameFn = ctx.objectForKeyedSubscript("__nativeFrame")
        presentedFn = ctx.objectForKeyedSubscript("__nativePresented")
        fire = ctx.objectForKeyedSubscript("__nativeFire")
        if NativeHost.stats { ctx.evaluateScript("__nativeTimesOn()")
            // the same frames in a tight loop, in this process, after 45 s: separates per-frame cost from cold/efficiency-core cost
            DispatchQueue.main.asyncAfter(deadline: .now() + 45) { [weak self] in
                let r = self?.ctx.evaluateScript("""
                  (() => { const L = __stage.layers, cs = Object.keys(L); let now = performance.now(), t0 = now;
                    for (let i = 0; i < 240; i++) { now += 1000 / 24; for (const c of cs) L[c].V._frame(now, false); }
                    return ((performance.now() - t0) / 240).toFixed(3) + " ms/frame tight"; })()
                  """)?.toString() ?? "?"
                log("native bench: \(r)")
                // bursts: k frames back to back every k/24 s, against the live 1-per-1/24 s (does a longer burst run faster?)
                } }
        return ctx.objectForKeyedSubscript("SpritesStage")?.isObject == true
    }

    private func arm(_ id: Int, _ ms: Double, _ rep: Bool) {
        let owner = Thread.current
        let t = Timer(timeInterval: max(0, ms) / 1000, repeats: rep) { [weak self] tm in
            guard let self else { return }
            if Thread.current !== owner { self.offThreadFires += 1 } else { self.onThreadFires += 1 }
            if !rep { self.timers.removeValue(forKey: id) }
            let t0 = CACurrentMediaTime()
            self.fire?.call(withArguments: [id])
            self.stat(t0)
        }
        t.tolerance = rep ? 0.01 : 0.002
        loop.add(t, forMode: .common)
        timers.removeValue(forKey: id)?.invalidate()
        timers[id] = t
    }

    /// Run host JS (SpritesStage.*); present if it changed the recording.
    func js(_ s: String) {
        _ = ctx.evaluateScript("try { \(s) } catch (e) { __native.log('stage js: ' + e) }")
        presentedFn?.call(withArguments: [])
    }

    /// `count` is the window server's clickCount (1, or 2 for the second click of a double-click): the stage sends it
    /// on to the host, which decides the gesture (Decide.swift clickGesture).
    func mouseDown(_ p: CGPoint, count: Int = 1) {
        ctx.objectForKeyedSubscript("__nativeMouse")?.call(withArguments: [Double(p.x), Double(p.y), count])
    }

    fileprivate func present() {
        guard let renderer, let fr = frameFn?.call(withArguments: []), fr.isObject else { return }
        let t0 = CACurrentMediaTime()
        renderer.draw(frame: fr, ctx: ctx, to: view.metalLayer)
        // SPAN: the same recorded frame into each extra viewport, each with its own world origin. One simulation.
        for e in extra { e.renderer.draw(frame: fr, ctx: ctx, to: e.view.metalLayer) }
        stPresents += 1; stPresentT += CACurrentMediaTime() - t0
    }

    func close() { timers.values.forEach { $0.invalidate() }; timers.removeAll(); obs.forEach { $0.0.removeObserver($0.1) }; obs.removeAll(); extra.removeAll() }

    /// Spin the main run loop (timers fire) for `sec` seconds.
    func run(_ sec: Double) { let end = Date().addingTimeInterval(sec); while Date() < end { loop.run(mode: .default, before: min(end, Date().addingTimeInterval(0.02))) } }

    /// QA: the current recording as a PNG (premultiplied pixels written as straight RGBA, as a browser screenshot).
    func savePNG(_ path: String) -> Bool {
        guard let renderer, let fr = frameFn?.call(withArguments: []), fr.isObject, var px = renderer.readback(frame: fr, ctx: ctx) else { return false }
        for i in stride(from: 0, to: px.count, by: 4) { let a = Int(px[i + 3]); if a > 0 && a < 255 {
            for k in 0..<3 { px[i + k] = UInt8(min(255, (Int(px[i + k]) * 255 + a / 2) / a)) } } }
        let w = renderer.w, h = renderer.h
        guard let prov = CGDataProvider(data: Data(px) as CFData),
              let img = CGImage(width: w, height: h, bitsPerComponent: 8, bitsPerPixel: 32, bytesPerRow: w * 4, space: CGColorSpace(name: CGColorSpace.sRGB)!,
                                bitmapInfo: CGBitmapInfo(rawValue: CGImageAlphaInfo.last.rawValue), provider: prov, decode: nil, shouldInterpolate: false, intent: .defaultIntent),
              let dst = CGImageDestinationCreateWithURL(URL(fileURLWithPath: path) as CFURL, "public.png" as CFString, 1, nil) else { return false }
        CGImageDestinationAddImage(dst, img, nil)
        return CGImageDestinationFinalize(dst)
    }

    /// QA (`Sprites --native-qos-bench SECONDS`): the live cast's frame JS at 24 Hz on threads of different QoS, offscreen,
    /// timing each frame. One JSContext per thread (contexts are not shared across threads). Prints ms/frame per QoS.
    static func qosBench(seconds: Double) -> Int32 {
        let snap = (try? String(contentsOfFile: Paths.state, encoding: .utf8)) ?? "null"
        for (name, q) in [("userInteractive", QualityOfService.userInteractive), ("userInitiated", .userInitiated), ("utility", .utility), ("default", .default)] {
            var result = ""; let sem = DispatchSemaphore(value: 0)
            let th = Thread {
                // headless: no NSView or CAMetalLayer off main; its timers run on this thread's own run loop (R2_MACOS #9)
                let host = NativeHost(size: CGSize(width: 1728, height: 1117), scale: 2, query: "stale=0", headless: true)
                host.js("SpritesStage.setSize(1728, 1117); SpritesStage.setPaused(true); SpritesStage.update(\(snap));")
                host.run(0.5)
                let f = host.ctx.evaluateScript("(() => { const L = __stage.layers; return () => { const now = performance.now(); for (const c in L) L[c].V._frame(now, false); }; })()")!
                var tot = 0.0, n = 0; let end = CACurrentMediaTime() + seconds
                let r0 = rusage_self()
                while CACurrentMediaTime() < end { let t0 = CACurrentMediaTime(); f.call(withArguments: []); tot += CACurrentMediaTime() - t0; n += 1
                    let nx = t0 + 1.0 / 24; let w = nx - CACurrentMediaTime(); if w > 0 { Thread.sleep(forTimeInterval: w) } }
                let r1 = rusage_self()
                result = String(format: "%@: %.3f ms/frame wall-in-frame, %.2f%% cpu (rusage, this process, all threads); timers fired on the host thread %d, off it %d", name, tot * 1000 / Double(max(1, n)), (r1 - r0) / seconds * 100, host.onThreadFires, host.offThreadFires)
                host.close(); sem.signal() }
            th.qualityOfService = q; th.start(); sem.wait(); log("qos-bench " + result)
        }
        return 0
    }

    /// QA (`Sprites --native-frames SPEC.json`): render fixed-seed frames offscreen, no window. SPEC = {w, h, dpr, query,
    /// scenes: [{name, setup (JS), settle (s), times: [t], out (dir)}]}. Each frame: `__stage.renderAt(t)` then the
    /// recording to <out>/<name>_t<t>_native.png; reports and unsupported-call counts to <out>/<name>_native.json.
    static func renderFrames(spec path: String) -> Int32 {
        guard let d = FileManager.default.contents(atPath: path), let o = try? JSONSerialization.jsonObject(with: d) as? [String: Any],
              let scenes = o["scenes"] as? [[String: Any]] else { log("native-frames: bad spec \(path)"); return 2 }
        let w = (o["w"] as? NSNumber)?.doubleValue ?? 1440, h = (o["h"] as? NSNumber)?.doubleValue ?? 900, dpr = (o["dpr"] as? NSNumber)?.doubleValue ?? 2
        var bad = 0
        for sc in scenes {
            let name = sc["name"] as? String ?? "scene", out = sc["out"] as? String ?? ".", setup = sc["setup"] as? String ?? ""
            let host = NativeHost(size: CGSize(width: w, height: h), scale: CGFloat(dpr), query: o["query"] as? String ?? "")
            guard host.loaded else { log("native-frames: stage did not load"); return 3 }
            host.js("SpritesStage.setSize(\(Int(w)), \(Int(h)));")
            host.js(setup)
            host.run((sc["settle"] as? NSNumber)?.doubleValue ?? 1.5)
            var rep: [String: Any] = [:]
            if let b = sc["bench"] as? String { let r = host.ctx.evaluateScript(b)?.toString() ?? "?"; log("native-frames: \(name) bench \(r)"); rep["bench"] = r }
            if sc["sleepProbe"] != nil {   // QA: screensDidSleep / Wake, posted to this process only, flip document.hidden
                let ws = NSWorkspace.shared.notificationCenter, hid = { host.ctx.evaluateScript("document.hidden")?.toBool() ?? false }
                let v0 = hid(); ws.post(name: NSWorkspace.screensDidSleepNotification, object: nil); host.run(0.2)
                let v1 = hid(), f0 = host.ctx.evaluateScript("__nativeVer()")?.toDouble() ?? 0; host.run(1.0)
                let f1 = host.ctx.evaluateScript("__nativeVer()")?.toDouble() ?? 0
                ws.post(name: NSWorkspace.screensDidWakeNotification, object: nil); host.run(0.2)
                rep["sleep"] = [v0, v1, hid()]; rep["framesWhileAsleep"] = f1 - f0
                if let j = try? JSONSerialization.data(withJSONObject: rep) { try? j.write(to: URL(fileURLWithPath: "\(out)/\(name)_native.json")) }
                host.close(); continue
            }
            if let k = (sc["presentProbe"] as? NSNumber)?.intValue {   // QA: worst main-thread time of one live present()
                // The view is in no window, so its drawables are never shown and the pool runs dry: the display-asleep case.
                var worst = 0.0, times: [Double] = []
                for i in 0..<k {
                    host.ctx.evaluateScript("(() => { const __c = __stage.canvas, x = __c.getContext('2d'); x.setTransform(1,0,0,1,0,0); x.clearRect(0,0,__c.width,__c.height); x.fillStyle = 'rgba(255,0,0,1)'; x.fillRect(\(i), 0, 10, 10); })()")
                    let t0 = CACurrentMediaTime(); host.present(); let dt = CACurrentMediaTime() - t0; worst = max(worst, dt); times.append(dt * 1000)
                }
                host.run(1.5)   // the render queue drains; a skipped last frame is re-presented
                rep["presentMaxMs"] = worst * 1000; rep["presentMs"] = times
                rep["finalVer"] = host.ctx.evaluateScript("__nativeVer()")?.toDouble() ?? -1
                rep["presentedVer"] = host.renderer?.shownVer ?? -2
                if let j = try? JSONSerialization.data(withJSONObject: rep) { try? j.write(to: URL(fileURLWithPath: "\(out)/\(name)_native.json")) }
                host.close(); continue
            }
            if let raw = sc["raw"] as? String {   // QA: draw JS straight into the stage canvas (primitive parity)
                host.ctx.evaluateScript("(() => { const __c = __stage.canvas, x = __c.getContext('2d'); x.setTransform(1,0,0,1,0,0); x.clearRect(0,0,__c.width,__c.height); x.setTransform(\(dpr),0,0,\(dpr),0,0); \(raw) })()")
                if !host.savePNG("\(out)/\(name)_native.png") { bad += 1 }
                rep["unsupported"] = host.ctx.evaluateScript("JSON.stringify(__nativeStats.unsupported)")?.toString() ?? ""
                if let j = try? JSONSerialization.data(withJSONObject: rep) { try? j.write(to: URL(fileURLWithPath: "\(out)/\(name)_native.json")) }
                host.close(); continue
            }
            for t in (sc["times"] as? [NSNumber]) ?? [3] {
                let tv = t.doubleValue, tag = tv == tv.rounded() ? String(Int(tv)) : String(tv)
                let r = host.ctx.evaluateScript("JSON.stringify(__stage.renderAt(\(tv)))")?.toString() ?? "null"
                rep[tag] = (try? JSONSerialization.jsonObject(with: Data(r.utf8))) ?? NSNull()
                if !host.savePNG("\(out)/\(name)_t\(tag)_native.png") { bad += 1 }
            }
            rep["errors"] = host.ctx.evaluateScript("JSON.stringify(window.__errors || [])")?.toString() ?? ""
            rep["unsupported"] = host.ctx.evaluateScript("JSON.stringify(__nativeStats.unsupported)")?.toString() ?? ""
            rep["instances"] = host.ctx.evaluateScript("__nativeFrame() && __nativeFrame().n")?.toInt32() ?? 0
            if let j = try? JSONSerialization.data(withJSONObject: rep, options: [.prettyPrinted, .sortedKeys]) {
                try? j.write(to: URL(fileURLWithPath: "\(out)/\(name)_native.json")) }
            host.close()
            log("native-frames: \(name) done")
        }
        return bad == 0 ? 0 : 1
    }
}

/// The panel's content view: one CAMetalLayer; a click over a creature goes to the stage's own mousedown listener.
final class NativeView: NSView {
    var metal: MetalStage?
    var onMouseDown: ((CGPoint, Int) -> Void)?
    let metalLayer = CAMetalLayer()
    override init(frame: NSRect) {
        super.init(frame: frame)
        wantsLayer = true
        layer = metalLayer
        metalLayer.isOpaque = false
        metalLayer.pixelFormat = .bgra8Unorm
        metalLayer.framebufferOnly = true
        metalLayer.colorspace = CGColorSpace(name: CGColorSpace.sRGB)
        metalLayer.backgroundColor = NSColor.clear.cgColor
        metalLayer.maximumDrawableCount = 2
        metalLayer.allowsNextDrawableTimeout = true
    }
    required init?(coder: NSCoder) { fatalError() }
    override var isFlipped: Bool { true }
    override func acceptsFirstMouse(for e: NSEvent?) -> Bool { true }
    override func mouseDown(with e: NSEvent) { onMouseDown?(convert(e.locationInWindow, from: nil), e.clickCount) }
}

/// 🔴 SPAN: the hover-label textures, owned by the HOST and shared by every viewport (one simulation, one recording,
/// one set of labels). It was a private array per `MetalStage`, so only the primary renderer ever received a label and
/// a second monitor's sprites had no names at all. Lazily makes its own device, since a viewport may not exist yet.
/// Textures are replaced, never mutated, so a frame already encoded keeps the texture it was drawn with.
final class LabelStore {
    static let maxLabels = 4
    private let device: MTLDevice?
    private var tex: [MTLTexture?] = Array(repeating: nil, count: LabelStore.maxLabels)
    private lazy var blank: MTLTexture? = {
        guard let device else { return nil }
        let t = MTLTextureDescriptor.texture2DDescriptor(pixelFormat: .rgba8Unorm, width: 1, height: 1, mipmapped: false); t.usage = .shaderRead
        return device.makeTexture(descriptor: t) }()
    init(device: MTLDevice? = MTLCreateSystemDefaultDevice()) { self.device = device }

    /// Upload a CGCanvas raster (premultiplied RGBA8, row 0 at the top) as label texture `slot`.
    func set(_ slot: Int, _ img: CGImage) -> Bool {
        guard slot >= 0 && slot < LabelStore.maxLabels, img.bitsPerPixel == 32, let device,
              let data = img.dataProvider?.data, let p = CFDataGetBytePtr(data) else { return false }
        let td = MTLTextureDescriptor.texture2DDescriptor(pixelFormat: .rgba8Unorm, width: img.width, height: img.height, mipmapped: false)
        td.usage = .shaderRead; td.storageMode = .shared
        guard let t = device.makeTexture(descriptor: td) else { return false }
        t.replace(region: MTLRegionMake2D(0, 0, img.width, img.height), mipmapLevel: 0, withBytes: p, bytesPerRow: img.bytesPerRow)
        tex[slot] = t; return true
    }
    /// The `n` live label slots this frame; every other slot reads as a 1x1 transparent texel.
    func textures(live n: Int) -> [MTLTexture?] { (0..<LabelStore.maxLabels).map { $0 < n ? (tex[$0] ?? blank) : blank } }
}

/// Metal renderer for the recorded display list (layout: app/native/canvas.js header). ONE instanced draw per frame;
/// programmable blending (tile memory) keeps canvas semantics: draws in order, "lighter" and source-over, a per-path
/// coverage union for strokes and multi-piece fills, and per-species layers composited source-over onto the frame.
final class MetalStage {
    let device: MTLDevice
    let queue: MTLCommandQueue
    let pipeline: MTLRenderPipelineState
    let w: Int, h: Int
    /// SPAN (SPRITES_UNIFY_MONITORS_AS_ONE): where this output's top-left sits in the shared world, in WORLD DEVICE px.
    /// One recording, one simulation; each panel encodes it with its own origin, so a creature exists once in the world
    /// and is drawn by whichever panel covers it. (0, 0) is the single-screen and QA case, i.e. exactly today.
    var origin: CGPoint = .zero
    private var layerTex: MTLTexture, covTex: MTLTexture
    private var bufs: [MTLBuffer] = [], pals: [MTLBuffer] = []
    private var slot = 0
    private let inflight = DispatchSemaphore(value: 2)
    private var wasEmpty = false
    /// Hover-label textures (canvas.js paint 3), premultiplied RGBA8, one device px per texel. SPAN: the store is the
    /// HOST's and is shared by every viewport, so one rasterized label paints on every monitor.
    static let maxLabels = LabelStore.maxLabels
    private let labels: LabelStore

    init?(width: Int, height: Int, labels: LabelStore = LabelStore()) {
        self.labels = labels
        guard let d = MTLCreateSystemDefaultDevice(), let q = d.makeCommandQueue() else { log("native: no Metal device"); return nil }
        device = d; queue = q; w = max(1, width); h = max(1, height)
        do {
            let lib = try d.makeLibrary(source: MetalStage.shader, options: nil)
            let p = MTLRenderPipelineDescriptor()
            p.vertexFunction = lib.makeFunction(name: "spVertex"); p.fragmentFunction = lib.makeFunction(name: "spFragment")
            p.colorAttachments[0].pixelFormat = .bgra8Unorm
            p.colorAttachments[1].pixelFormat = .rgba8Unorm
            p.colorAttachments[2].pixelFormat = .r16Float
            pipeline = try d.makeRenderPipelineState(descriptor: p)
        } catch { log("native: shader: \(error)"); return nil }
        func mk(_ f: MTLPixelFormat) -> MTLTexture {
            let t = MTLTextureDescriptor.texture2DDescriptor(pixelFormat: f, width: width, height: height, mipmapped: false)
            t.storageMode = .memoryless; t.usage = .renderTarget
            return d.makeTexture(descriptor: t)!
        }
        layerTex = mk(.rgba8Unorm); covTex = mk(.r16Float)
        for _ in 0..<2 { bufs.append(d.makeBuffer(length: 1 << 20, options: .storageModeShared)!); pals.append(d.makeBuffer(length: 1 << 16, options: .storageModeShared)!) }
    }

    /// Bytes of a JS typed array (no copy on the JS side).
    static func bytes(_ v: JSValue?, _ ctx: JSContext) -> (UnsafeMutableRawPointer, Int)? {
        guard let v, v.isObject, let ref = v.jsValueRef else { return nil }
        var ex: JSValueRef? = nil
        let g = ctx.jsGlobalContextRef
        guard let p = JSObjectGetTypedArrayBytesPtr(g, ref, &ex) else { return nil }
        let n = JSObjectGetTypedArrayByteLength(g, ref, &ex)
        return (p, n)
    }

    /// Live present. Main only copies the recording into a free slot and returns: it never waits for the GPU or a drawable
    /// (R2_MACOS #8: a dry drawable pool, e.g. while the displays sleep, used to block main up to 1.1 s a frame). With no
    /// free slot the frame is skipped and `onFree` asks for a re-present once one frees, so the last frame always lands.
    /// nextDrawable, encoding and commit run on `rq`.
    var onFree: (() -> Void)?
    private(set) var shownVer = -1.0
    private var skipped = false
    private let rq = DispatchQueue(label: "sprites.native.render", qos: .userInteractive)
    func draw(frame fr: JSValue, ctx: JSContext, to layer: CAMetalLayer) {
        let n = Int(fr.objectForKeyedSubscript("n")?.toInt32() ?? 0)
        if n == 0 && wasEmpty { return }
        guard inflight.wait(timeout: .now()) == .success else { skipped = true; return }
        skipped = false
        // 🔴 BOTH dimensions (SPAN): this tested WIDTH ONLY, and two 1920x1080 screens share a width — so a layer
        // sized for the other viewport, or for the union, was never corrected and the drawable kept a stale size.
        if drawableStale(layer.drawableSize, w: w, h: h) { layer.drawableSize = CGSize(width: w, height: h) }
        if layer.device == nil { layer.device = device }
        let st = stage(fr, ctx: ctx), ver = fr.objectForKeyedSubscript("ver")?.toDouble() ?? 0, sem = inflight
        wasEmpty = n == 0
        // shown: the frame reached a drawable (a dry pool drops it; the stage's pause, not a retry loop, handles sleep)
        let free: (Bool) -> Void = { [weak self] shown in sem.signal()
            DispatchQueue.main.async { guard let self else { return }; if shown { self.shownVer = max(self.shownVer, ver) }
                if self.skipped { self.skipped = false; self.onFree?() } } }
        rq.async { [weak self] in
            guard let self, let drawable = layer.nextDrawable(), let cb = self.queue.makeCommandBuffer() else { free(false); return }
            self.encode(st, into: drawable.texture, cb: cb)
            cb.addCompletedHandler { _ in free(true) }
            cb.present(drawable)
            cb.commit()
        }
    }

    /// QA: the same frame into an offscreen texture, read back as premultiplied RGBA8 (row-major, top row first).
    func readback(frame fr: JSValue, ctx: JSContext) -> [UInt8]? {
        let td = MTLTextureDescriptor.texture2DDescriptor(pixelFormat: .bgra8Unorm, width: w, height: h, mipmapped: false)
        td.usage = [.renderTarget, .shaderRead]; td.storageMode = .shared
        guard let tex = device.makeTexture(descriptor: td), let cb = queue.makeCommandBuffer() else { return nil }
        inflight.wait(); defer { inflight.signal() }   // QA only: its slot must not be one a live frame still uses
        encode(stage(fr, ctx: ctx), into: tex, cb: cb)
        cb.commit(); cb.waitUntilCompleted()
        var px = [UInt8](repeating: 0, count: w * h * 4)
        tex.getBytes(&px, bytesPerRow: w * 4, from: MTLRegionMake2D(0, 0, w, h), mipmapLevel: 0)
        for i in stride(from: 0, to: px.count, by: 4) { px.swapAt(i, i + 2) }   // BGRA -> RGBA
        return px
    }

    /// One frame's GPU inputs, copied out of JS on main (the caller holds an `inflight` slot, so slot's buffers are free).
    private struct Staged { let n: Int; let ib: MTLBuffer; let pb: MTLBuffer; let tex: [MTLTexture?] }
    private func stage(_ fr: JSValue, ctx: JSContext) -> Staged {
        let n = Int(fr.objectForKeyedSubscript("n")?.toInt32() ?? 0), paln = Int(fr.objectForKeyedSubscript("paln")?.toInt32() ?? 0)
        slot = (slot + 1) % bufs.count
        let ib = 24 * 4 * n, pb = 36 * 4 * paln
        if ib > bufs[slot].length { bufs[slot] = device.makeBuffer(length: ib * 2, options: .storageModeShared)! }
        if pb > pals[slot].length { pals[slot] = device.makeBuffer(length: pb * 2, options: .storageModeShared)! }
        if n > 0, let (p, len) = MetalStage.bytes(fr.objectForKeyedSubscript("f"), ctx) { memcpy(bufs[slot].contents(), p, min(ib, len)) }
        if paln > 0, let (p, len) = MetalStage.bytes(fr.objectForKeyedSubscript("pal"), ctx) { memcpy(pals[slot].contents(), p, min(pb, len)) }
        let nl = Int(fr.objectForKeyedSubscript("labn")?.toInt32() ?? 0)
        return Staged(n: n, ib: bufs[slot], pb: pals[slot], tex: labels.textures(live: nl))
    }
    private func encode(_ st: Staged, into target: MTLTexture, cb: MTLCommandBuffer) {
        let n = st.n
        let rp = MTLRenderPassDescriptor()
        rp.colorAttachments[0].texture = target; rp.colorAttachments[0].loadAction = .clear
        rp.colorAttachments[0].clearColor = MTLClearColor(red: 0, green: 0, blue: 0, alpha: 0); rp.colorAttachments[0].storeAction = .store
        rp.colorAttachments[1].texture = layerTex; rp.colorAttachments[1].loadAction = .clear; rp.colorAttachments[1].storeAction = .dontCare
        rp.colorAttachments[1].clearColor = MTLClearColor(red: 0, green: 0, blue: 0, alpha: 0)
        rp.colorAttachments[2].texture = covTex; rp.colorAttachments[2].loadAction = .clear; rp.colorAttachments[2].storeAction = .dontCare
        if let enc = cb.makeRenderCommandEncoder(descriptor: rp) {
            if n > 0 {
                enc.setRenderPipelineState(pipeline)
                var vp: [Float] = [Float(w), Float(h)]
                var org: [Float] = [Float(origin.x), Float(origin.y)]
                enc.setVertexBuffer(st.ib, offset: 0, index: 0)
                enc.setVertexBytes(&vp, length: 8, index: 1)
                enc.setVertexBytes(&org, length: 8, index: 2)
                enc.setFragmentBuffer(st.ib, offset: 0, index: 0)
                enc.setFragmentBuffer(st.pb, offset: 0, index: 1)
                enc.setFragmentBytes(&org, length: 8, index: 2)
                for i in 0..<MetalStage.maxLabels { enc.setFragmentTexture(st.tex[i], index: i) }
                enc.drawPrimitives(type: .triangleStrip, vertexStart: 0, vertexCount: 4, instanceCount: n)
            }
            enc.endEncoding()
        }
    }

    static let shader = """
    #include <metal_stdlib>
    using namespace metal;
    struct VOut { float4 pos [[position]]; uint iid [[flat]]; };
    vertex VOut spVertex(uint vid [[vertex_id]], uint iid [[instance_id]], const device float* I [[buffer(0)]], constant float2& vp [[buffer(1)]],
                         constant float2& org [[buffer(2)]]) {
      const device float* b = I + iid * 24 + 14;
      // SPAN: the recording is in WORLD device px; this viewport shows the world from `org` on (buffer 2).
      float2 p = float2((vid & 1) ? b[2] : b[0], (vid & 2) ? b[3] : b[1]) - org;
      VOut o; o.pos = float4(p.x / vp.x * 2.0 - 1.0, 1.0 - p.y / vp.y * 2.0, 0.0, 1.0); o.iid = iid; return o; }
    struct FOut { float4 c0 [[color(0)]]; float4 c1 [[color(1)]]; half c2 [[color(2)]]; };
    static float strip(float d, float lw) { return clamp(min(d + lw * 0.5, 0.5) - max(d - lw * 0.5, -0.5), 0.0, 1.0); }
    // exact area of (pixel square centred at p) inside triangle ABC: clip the square by the three edges (Sutherland-Hodgman)
    static float triArea(float2 p, float2 A, float2 B, float2 C) {
      float2 P[10], Q[10]; int n = 4;
      P[0] = p + float2(-0.5, -0.5); P[1] = p + float2(0.5, -0.5); P[2] = p + float2(0.5, 0.5); P[3] = p + float2(-0.5, 0.5);
      float s = sign((B.x - A.x) * (C.y - A.y) - (B.y - A.y) * (C.x - A.x));
      float2 E[4] = { A, B, C, A };
      for (int e = 0; e < 3; e++) {
        float2 a = E[e], v = E[e + 1] - a; int m = 0;
        for (int i = 0; i < n; i++) {
          float2 c = P[i], d = P[(i + 1) % n];
          float fc = s * (v.x * (c.y - a.y) - v.y * (c.x - a.x)), fd = s * (v.x * (d.y - a.y) - v.y * (d.x - a.x));
          if (fc >= 0.0) Q[m++] = c;
          if ((fc >= 0.0) != (fd >= 0.0)) Q[m++] = c + (d - c) * (fc / (fc - fd));
        }
        n = m; for (int i = 0; i < n; i++) P[i] = Q[i];
        if (n < 3) return 0.0;
      }
      float ar = 0.0; for (int i = 0; i < n; i++) { float2 c = P[i], d = P[(i + 1) % n]; ar += c.x * d.y - d.x * c.y; }
      return clamp(abs(ar) * 0.5, 0.0, 1.0); }
    static float4 paint(const device float* q, const device float* P, float2 p, uint pt) {
      if (pt == 0) { float a = q[12]; return float4(q[9] * a, q[10] * a, q[11] * a, a); }
      float t;
      if (pt == 1) { float d = distance(p, float2(q[9], q[10])); float r0 = q[11], r1 = q[12]; t = (d - r0) / max(r1 - r0, 1e-6); }
      else { float2 a = float2(q[9], q[10]), v = float2(q[11], q[12]) - a; t = dot(p - a, v) / max(dot(v, v), 1e-9); }
      // WebKit (the approved engine, CoreGraphics) interpolates a RADIAL gradient between PREMULTIPLIED stops when its
      // offsets are evenly spaced (i / (n - 1): 0,1 or 0,.5,1, ...), else between straight stops; linear gradients always
      // straight. Measured with getImageData, 2026-11-01 (tests/native/test_gradient.py holds the cases).
      const device float* s = P + uint(q[13]) * 36; int n = int(s[0]); bool pm = pt == 1;
      for (int i = 0; pm && i < n; i++) if (abs(s[1 + i * 5] - (n > 1 ? float(i) / float(n - 1) : 0.0)) > 1e-5) pm = false;
      #define STOP(i) (pm ? float4(float3(s[2 + (i) * 5], s[3 + (i) * 5], s[4 + (i) * 5]) * s[5 + (i) * 5], s[5 + (i) * 5]) : float4(s[2 + (i) * 5], s[3 + (i) * 5], s[4 + (i) * 5], s[5 + (i) * 5]))
      float4 c = STOP(0);
      if (t >= s[1]) {
        c = STOP(n - 1);
        for (int i = 0; i + 1 < n; i++) { float o0 = s[1 + i * 5], o1 = s[1 + (i + 1) * 5];
          if (t >= o0 && t < o1) { float f = (t - o0) / max(o1 - o0, 1e-6); c = mix(STOP(i), STOP(i + 1), f); break; } } }
      #undef STOP
      return pm ? c : float4(c.rgb * c.a, c.a); }
    fragment FOut spFragment(VOut in [[stage_in]], float4 d0 [[color(0)]], float4 d1 [[color(1)]], half d2 [[color(2)]],
                             const device float* I [[buffer(0)]], const device float* P [[buffer(1)]], constant float2& org [[buffer(2)]],
                             texture2d<float> L0 [[texture(0)]], texture2d<float> L1 [[texture(1)]], texture2d<float> L2 [[texture(2)]], texture2d<float> L3 [[texture(3)]]) {
      FOut o; o.c0 = d0; o.c1 = d1; o.c2 = d2;
      const device float* q = I + in.iid * 24; uint code = uint(q[0]);
      uint kind = code & 7, op = (code >> 3) & 3, blend = (code >> 5) & 3, pt = (code >> 7) & 3, tgt = (code >> 9) & 1;
      float2 p = in.pos.xy + org; float cov = 0.0;   // SPAN: back to world device px (q[] geometry is world space)
      if (kind == 5) { o.c0 = d1 + d0 * (1.0 - d1.a); o.c1 = float4(0.0); return o; }
      if (kind == 4) { cov = float(d2); o.c2 = 0.0h; }
      else if (kind == 0) { cov = clamp(min(q[3], p.x + 0.5) - max(q[1], p.x - 0.5), 0.0, 1.0) * clamp(min(q[4], p.y + 0.5) - max(q[2], p.y - 0.5), 0.0, 1.0); }
      else if (kind == 1) {
        float2 r = p - float2(q[1], q[2]); float ca = cos(q[5]), sa = sin(q[5]); float2 e = float2(ca * r.x + sa * r.y, -sa * r.x + ca * r.y);
        float rx = max(q[3], 1e-4), ry = max(q[4], 1e-4), d;
        if (abs(rx - ry) < 1e-3) d = length(e) - rx;
        else { float f = (e.x * e.x) / (rx * rx) + (e.y * e.y) / (ry * ry) - 1.0; float2 g = float2(2.0 * e.x / (rx * rx), 2.0 * e.y / (ry * ry)); d = f / max(length(g), 1e-6); }
        if (q[6] > 0.0) cov = strip(d, q[6]);
        else if (max(rx, ry) < 1.0) {   // sub-pixel discs: pixel-area coverage, 4x4 supersampled (distance AA over-weights them)
          cov = 0.0; for (int sy = 0; sy < 4; sy++) for (int sx = 0; sx < 4; sx++) { float2 o2 = float2(sx, sy) * 0.25 - 0.375; float2 rr2 = r + o2;
            float2 ee = float2(ca * rr2.x + sa * rr2.y, -sa * rr2.x + ca * rr2.y); cov += ((ee.x * ee.x) / (rx * rx) + (ee.y * ee.y) / (ry * ry) <= 1.0) ? 1.0 : 0.0; }
          cov /= 16.0; }
        else cov = clamp(0.5 - d, 0.0, 1.0);
      }
      else if (kind == 2) { float2 a = float2(q[1], q[2]), v = float2(q[3], q[4]) - a; float L = max(length(v), 1e-6); float2 t = v / L, nn = float2(-t.y, t.x);
        float2 pa = p - a; float al = dot(pa, t); cov = strip(dot(pa, nn), q[5]) * clamp(min(al + 0.5, L) - max(al - 0.5, 0.0), 0.0, 1.0); }
      else if (kind == 3) { cov = triArea(p, float2(q[1], q[2]), float2(q[3], q[4]), float2(q[5], q[6])); }
      // path union: fan triangles tile the polygon, so their exact areas add; overlapping stroke pieces take the max
      if (op == 1) { o.c2 = kind == 3 ? min(d2 + half(cov), 1.0h) : max(d2, half(cov)); return o; }
      if (cov <= 0.0) return o;
      float4 c;
      if (pt == 3) {   // hover label: one texel per device px from (q[9], q[10]), premultiplied (CGCanvas raster)
        uint s = uint(q[13]); int2 t = int2(floor(p - float2(q[9], q[10])));
        texture2d<float> T = s == 0 ? L0 : s == 1 ? L1 : s == 2 ? L2 : L3;
        c = (t.x < 0 || t.y < 0 || t.x >= int(T.get_width()) || t.y >= int(T.get_height())) ? float4(0.0) : T.read(uint2(t)) * (q[8] * cov);
      } else if (q[22] != 0.0) {   // drawImage of a sprite: bilinear over 8-bit premultiplied texels, as the canvas samples it
        float2 org = float2(q[20], q[21]), k = float2(q[22], q[23]); float2 t = (p - org) / k - 0.5, i0 = floor(t), f = t - i0;
        float sw = floor(q[18] / 65536.0), sh = q[18] - sw * 65536.0; float4 acc = float4(0.0);
        for (int j = 0; j < 4; j++) { float2 tc = i0 + float2(j & 1, j >> 1);
          if (tc.x < 0.0 || tc.y < 0.0 || tc.x >= sw || tc.y >= sh) continue;
          float2 sc = tc + 0.5; float tcv = 1.0;
          if (q[5] > 0.5) tcv = clamp(0.5 - (distance(sc, float2(q[6], q[7])) - q[19]), 0.0, 1.0);
          float4 v = round(paint(q, P, org + sc * k, pt) * tcv * 255.0) / 255.0;
          float w = ((j & 1) ? f.x : 1.0 - f.x) * ((j >> 1) ? f.y : 1.0 - f.y); acc += v * w; }
        c = acc * (q[8] * cov);
      } else c = paint(q, P, p, pt) * (q[8] * cov);
      float4 d = tgt == 1 ? d1 : d0;
      float4 r = blend == 1 ? min(d + c, float4(1.0)) : c + d * (1.0 - c.a);
      if (tgt == 1) o.c1 = r; else o.c0 = r;
      return o; }
    """
}
