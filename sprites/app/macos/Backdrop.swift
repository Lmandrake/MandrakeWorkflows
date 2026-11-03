import AppKit
import Metal
import QuartzCore

/// Sprites backdrops (owner, 2026-11-01 08:05: "Implement them all as choices, with adjustable speed settings").
/// behaviors.json keys: "backdrop" ("none" | "b01".."b12"; missing = "none") and "backdropSpeed" ({"b07": 1.5, ...} or
/// one number; missing = the catalog's designed speed). Catalog and shader are read at runtime from
/// sprites/app/backdrops/ (catalog.json, backdrops.sl; the same source the settings previews compile as WebGL).
///  - speed 0, or a static concept: ONE full-resolution PNG per screen is rendered and set as the wallpaper
///    (NSWorkspace.setDesktopImageURL). That call changes the CURRENT Space only, so every Space is covered as it becomes
///    active. Each Space's previous wallpaper is recorded first (wallpaper_original.json) and put back on "none".
///  - speed > 0: a borderless, click-through window per screen at the desktop window level (above the wallpaper, below
///    the icons and the dim layer), drawing the shader at the concept's fixed low frame rate. Paused while occluded
///    (covered, full screen), locked, asleep or hidden; frozen under Reduce Motion.
/// Guide: visualize/docs/MACHINE_BACKGROUNDS.md.
final class Backdrop {
    struct Item { let id: String; let n: Int; let moving: Bool; let speed: Double; let max: Double; let fps: Double }
    private var catalog: [String: Item] = [:]
    private var source = ""
    private var current = "none", speed = 0.0, lastKey = ""
    private var windows: [BackdropWindow] = []
    private var timer: Timer?
    private var designT: Double = Date().timeIntervalSince1970.truncatingRemainder(dividingBy: 6 * 86400)
    private var lastTick = CACurrentMediaTime()
    private var locked = false, asleep = false
    var hidden = false { didSet { if hidden != oldValue { refreshPause() } } }
    private let device = MTLCreateSystemDefaultDevice()
    private var pipeline: MTLRenderPipelineState?, pipelineSrc = ""
    private lazy var queue = device?.makeCommandQueue()
    private let wall = Wallpaper()
    static var cacheDir: String { Paths.home + "/ClaudeWork/sprites/backdrops" }

    init() {
        let ws = NSWorkspace.shared.notificationCenter, dnc = DistributedNotificationCenter.default()
        dnc.addObserver(forName: .init("com.apple.screenIsLocked"), object: nil, queue: .main) { [weak self] _ in self?.locked = true; self?.refreshPause() }
        dnc.addObserver(forName: .init("com.apple.screenIsUnlocked"), object: nil, queue: .main) { [weak self] _ in self?.locked = false; self?.refreshPause() }
        ws.addObserver(forName: NSWorkspace.screensDidSleepNotification, object: nil, queue: .main) { [weak self] _ in self?.asleep = true; self?.refreshPause() }
        ws.addObserver(forName: NSWorkspace.screensDidWakeNotification, object: nil, queue: .main) { [weak self] _ in self?.asleep = false; self?.refreshPause() }
        ws.addObserver(forName: NSWorkspace.activeSpaceDidChangeNotification, object: nil, queue: .main) { [weak self] _ in
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) { self?.spaceChanged() } }
        ws.addObserver(forName: NSWorkspace.accessibilityDisplayOptionsDidChangeNotification, object: nil, queue: .main) { [weak self] _ in self?.refreshPause() }
        NotificationCenter.default.addObserver(forName: NSApplication.didChangeScreenParametersNotification, object: nil, queue: .main) { [weak self] _ in
            guard let self else { return }; self.lastKey = ""; self.applyCurrent() }
    }

    /// Called with the behaviours JSON text whenever it changes. Cheap when nothing backdrop-related changed.
    func apply(_ behaviorsJSON: String) {
        var id = "none", sp: Double? = nil
        if let d = behaviorsJSON.data(using: .utf8), let o = try? JSONSerialization.jsonObject(with: d) as? [String: Any] {
            if let s = o["backdrop"] as? String { id = s }
            sp = backdropSpeedOverride(o, id: id)   // Decide.swift (0 and 1 are numbers, review R1 #3)
        }
        if id != "none" && catalog.isEmpty { loadCatalog() }
        guard id == "none" || catalog[id] != nil else { log("backdrop: unknown \(id); none"); return set("none", 0) }
        let it = catalog[id]
        set(id, min(it?.max ?? 0, max(0, sp ?? it?.speed ?? 0)))
    }

    private func set(_ id: String, _ s: Double) {
        if current == "none" && id != "none" && !wall.backdropChosen(id) { log("backdrop: cannot snapshot the wallpaper store") }
        current = id; speed = s; applyCurrent()
    }

    private func applyCurrent() {
        let key = "\(current)|\(speed)"
        if key == lastKey { return }
        lastKey = key
        if current == "none" { stopLive(); wall.restoreCurrentSpace(); return }
        guard let it = catalog[current] else { return }
        if speed <= 0 || it.max <= 0 {
            stopLive()
            setStill(it)
        } else {
            wall.restoreCurrentSpace()
            startLive(it)
        }
    }

    private func spaceChanged() {
        guard current != "none", let it = catalog[current] else { wall.restoreCurrentSpace(); return }
        if speed <= 0 || it.max <= 0 { setStill(it) } else { wall.restoreCurrentSpace() }
    }

    // MARK: catalog + shader

    private func loadCatalog() {
        let dir = Paths.sprites.appendingPathComponent("app/backdrops")
        guard let d = try? Data(contentsOf: dir.appendingPathComponent("catalog.json")),
              let o = try? JSONSerialization.jsonObject(with: d) as? [String: Any],
              let arr = o["backdrops"] as? [[String: Any]] else { log("backdrop: no catalog in \(dir.path)"); return }
        for b in arr {
            guard let id = b["id"] as? String, let n = (b["n"] as? NSNumber)?.intValue else { continue }
            func f(_ k: String) -> Double { (b[k] as? NSNumber)?.doubleValue ?? 0 }
            catalog[id] = Item(id: id, n: n, moving: (b["moving"] as? Bool) ?? false, speed: f("speed"), max: f("max"), fps: f("fps"))
        }
        source = (try? String(contentsOf: dir.appendingPathComponent("backdrops.sl"), encoding: .utf8)) ?? ""
    }

    private func makePipeline() -> MTLRenderPipelineState? {
        if let p = pipeline, pipelineSrc == source { return p }
        guard let device else { log("backdrop: no Metal device"); return nil }
        let msl = """
        #include <metal_stdlib>
        using namespace metal;
        typedef float2 vec2; typedef float3 vec3; typedef float4 vec4;
        \(source)
        struct VOut { float4 pos [[position]]; };
        vertex VOut bdVertex(uint vid [[vertex_id]]) {
          float2 v[3] = { float2(-1.0, -1.0), float2(3.0, -1.0), float2(-1.0, 3.0) };
          VOut o; o.pos = float4(v[vid], 0.0, 1.0); return o; }
        struct BdU { float2 res; float id; float t; float nc; float mode; };
        fragment float4 bdFragment(VOut i [[stage_in]], constant BdU& u [[buffer(0)]]) {
          float2 p = i.pos.xy; vec3 lin = pick(u.id, p, u.res, u.t, u.nc);
          return float4(encodeOut(lin, p, u.mode, 0.0), 1.0); }
        """
        do {
            let lib = try device.makeLibrary(source: msl, options: nil)
            let d = MTLRenderPipelineDescriptor()
            d.vertexFunction = lib.makeFunction(name: "bdVertex"); d.fragmentFunction = lib.makeFunction(name: "bdFragment")
            d.colorAttachments[0].pixelFormat = .bgra8Unorm   // we encode sRGB + dither ourselves; the layer is tagged sRGB
            pipeline = try device.makeRenderPipelineState(descriptor: d); pipelineSrc = source
            return pipeline
        } catch { log("backdrop: shader: \(error)"); return nil }
    }

    private func encode(_ enc: MTLRenderCommandEncoder, n: Int, w: Int, h: Int, t: Double, nc: Bool) {
        var u: [Float] = [Float(w), Float(h), Float(n), Float(t), nc ? 1 : 0, 0]
        enc.setFragmentBytes(&u, length: MemoryLayout<Float>.size * u.count, index: 0)
        enc.drawPrimitives(type: .triangle, vertexStart: 0, vertexCount: 3)
    }

    /// QA (`Sprites --backdrop-export bNN W H T PATH`): one offscreen frame to a PNG, touching no window or wallpaper.
    func exportPNG(_ id: String, w: Int, h: Int, t: Double, to path: String) -> Bool {
        if catalog.isEmpty { loadCatalog() }
        guard let it = catalog[id] else { log("backdrop: unknown \(id)"); return false }
        return renderPNG(it, w: w, h: h, t: t, to: path, comets: true)
    }

    // MARK: still -> wallpaper

    private func setStill(_ it: Item) {
        let t = it.max > 0 ? (designT / 60).rounded() * 60 : 0   // a frozen moving concept keeps its current look
        var urls: [NSScreen: URL] = [:]
        for s in NSScreen.screens {
            let w = Int(s.frame.width * s.backingScaleFactor), h = Int(s.frame.height * s.backingScaleFactor)
            let tag = String(format: "%08x", fnv(source + "\(it.n)|\(t)"))
            let path = Self.cacheDir + "/\(it.id)_\(w)x\(h)_\(tag).png"
            if !FileManager.default.fileExists(atPath: path) {
                guard renderPNG(it, w: w, h: h, t: t, to: path) else { continue }
            }
            urls[s] = URL(fileURLWithPath: path)
        }
        wall.set(urls)
    }

    private func renderPNG(_ it: Item, w: Int, h: Int, t: Double, to path: String, comets: Bool = false) -> Bool {
        guard let device, let pipe = makePipeline(), let q = queue else { return false }
        let td = MTLTextureDescriptor.texture2DDescriptor(pixelFormat: .bgra8Unorm, width: w, height: h, mipmapped: false)
        td.usage = [.renderTarget]; td.storageMode = .shared
        guard let tex = device.makeTexture(descriptor: td), let cb = q.makeCommandBuffer() else { return false }
        let rp = MTLRenderPassDescriptor(); rp.colorAttachments[0].texture = tex
        rp.colorAttachments[0].loadAction = .dontCare; rp.colorAttachments[0].storeAction = .store
        guard let enc = cb.makeRenderCommandEncoder(descriptor: rp) else { return false }
        enc.setRenderPipelineState(pipe); encode(enc, n: it.n, w: w, h: h, t: t, nc: !comets); enc.endEncoding()
        cb.commit(); cb.waitUntilCompleted()
        var bytes = [UInt8](repeating: 0, count: w * h * 4)
        tex.getBytes(&bytes, bytesPerRow: w * 4, from: MTLRegionMake2D(0, 0, w, h), mipmapLevel: 0)
        let info = CGBitmapInfo(rawValue: CGImageAlphaInfo.noneSkipFirst.rawValue | CGBitmapInfo.byteOrder32Little.rawValue)
        guard let cs = CGColorSpace(name: CGColorSpace.sRGB),
              let ctx = CGContext(data: &bytes, width: w, height: h, bitsPerComponent: 8, bytesPerRow: w * 4, space: cs, bitmapInfo: info.rawValue),
              let img = ctx.makeImage() else { return false }
        try? FileManager.default.createDirectory(atPath: Self.cacheDir, withIntermediateDirectories: true)
        let rep = NSBitmapImageRep(cgImage: img)
        guard let png = rep.representation(using: .png, properties: [:]) else { return false }
        do { try png.write(to: URL(fileURLWithPath: path), options: .atomic) } catch { log("backdrop: \(error)"); return false }
        // keep the cache small: drop older renders of other sizes/versions beyond the newest 24
        if let all = try? FileManager.default.contentsOfDirectory(atPath: Self.cacheDir).filter({ $0.hasSuffix(".png") }), all.count > 24 {
            let dated = all.compactMap { f -> (String, Date)? in
                let p = Self.cacheDir + "/" + f
                return (try? FileManager.default.attributesOfItem(atPath: p)[.modificationDate] as? Date).map { (p, $0) } }
            let used = wall.inUse()   // every Space's, not only the current one (review R1 #9)
            for p in prunePaths(dated.map { (path: $0.0, date: $0.1) }, keep: 24, inUse: used) { try? FileManager.default.removeItem(atPath: p) }
        }
        return true
    }

    // MARK: live window

    private func startLive(_ it: Item) {
        guard makePipeline() != nil, let device else { return }
        let screens = NSScreen.screens
        while windows.count > screens.count { windows.removeLast().close() }
        while windows.count < screens.count { windows.append(BackdropWindow(device: device, owner: self)) }
        for (w, s) in zip(windows, screens) { w.fit(s); w.orderFrontRegardless() }
        timer?.invalidate()
        lastTick = CACurrentMediaTime()
        let fps = max(1, min(10, it.fps))
        let tm = Timer(timeInterval: 1 / fps, repeats: true) { [weak self] _ in self?.tick() }
        tm.tolerance = 0.2 / fps
        RunLoop.main.add(tm, forMode: .common); timer = tm
        drawAll()
        refreshPause()
    }

    private func stopLive() {
        timer?.invalidate(); timer = nil
        windows.forEach { $0.orderOut(nil); $0.close() }; windows = []
    }

    private var reduceMotion: Bool { NSWorkspace.shared.accessibilityDisplayShouldReduceMotion }
    private var paused: Bool { backdropPaused(locked: locked, asleep: asleep, hidden: hidden, reduceMotion: reduceMotion) }
    func refreshPause() { if !paused { lastTick = CACurrentMediaTime() } }

    private func tick() {
        let now = CACurrentMediaTime(), dt = min(2.0, now - lastTick); lastTick = now
        if paused { return }
        let visible = windows.filter { $0.occlusionState.contains(.visible) }
        if visible.isEmpty { return }   // covered or full screen: no drawing; design time also holds
        designT += dt * speed
        visible.forEach { draw($0) }
    }

    private func drawAll() { windows.forEach { draw($0) } }

    private func draw(_ w: BackdropWindow) {
        guard let it = catalog[current], let pipe = makePipeline(), let q = queue,
              let drawable = w.metal.nextDrawable(), let cb = q.makeCommandBuffer() else { return }
        let rp = MTLRenderPassDescriptor(); rp.colorAttachments[0].texture = drawable.texture
        rp.colorAttachments[0].loadAction = .dontCare; rp.colorAttachments[0].storeAction = .store
        guard let enc = cb.makeRenderCommandEncoder(descriptor: rp) else { return }
        enc.setRenderPipelineState(pipe)
        encode(enc, n: it.n, w: drawable.texture.width, h: drawable.texture.height, t: designT, nc: false)
        enc.endEncoding(); cb.present(drawable); cb.commit()
    }

    private func fnv(_ s: String) -> UInt32 { var h: UInt32 = 2166136261; for b in s.utf8 { h = (h ^ UInt32(b)) &* 16777619 }; return h }
}

/// One per screen at desktop window level + 1 (review R1_MACOS #10: at exactly the wallpaper's level a relaunched
/// WallpaperAgent orders its windows over it), so it draws above the wallpaper and below the icons (desktop icon
/// level = desktop + 20) and the Sprites dim layer (desktop icon + 1).
final class BackdropWindow: NSWindow {
    let metal = CAMetalLayer()
    init(device: MTLDevice, owner: Backdrop) {
        super.init(contentRect: .zero, styleMask: [.borderless], backing: .buffered, defer: false)
        level = NSWindow.Level(rawValue: backdropWindowLevel())   // Decide.swift
        collectionBehavior = [.canJoinAllSpaces, .stationary, .ignoresCycle]
        ignoresMouseEvents = true; isOpaque = true; hasShadow = false; backgroundColor = .black
        isReleasedWhenClosed = false; animationBehavior = .none
        metal.device = device; metal.pixelFormat = .bgra8Unorm; metal.framebufferOnly = true
        metal.colorspace = CGColorSpace(name: CGColorSpace.sRGB); metal.isOpaque = true
        metal.maximumDrawableCount = 2
        let v = NSView(); v.wantsLayer = true; v.layer = metal; contentView = v
        observers.observe(NotificationCenter.default, NSWindow.didChangeOcclusionStateNotification, object: self) { [weak owner] _ in
            DispatchQueue.main.async { owner?.refreshPause() } }
    }
    private let observers = ObserverBag()   // removed on close (review R1 #18: one leaked observer per window before)
    override func close() { observers.removeAll(); super.close() }
    func fit(_ s: NSScreen) {
        setFrame(s.frame, display: false)
        metal.contentsScale = s.backingScaleFactor
        metal.drawableSize = CGSize(width: s.frame.width * s.backingScaleFactor, height: s.frame.height * s.backingScaleFactor)
    }
    override var canBecomeKey: Bool { false }
    override var canBecomeMain: Bool { false }
}

/// The owner's wallpaper: set ours per screen on the current Space, remember what each Space showed before, put it back.
/// Records live in ~/ClaudeWork/sprites/config/wallpaper_original.json keyed "<display UUID>|<space id>", written before
/// the first change, so a crash or restart can still restore.
final class Wallpaper {
    /// macOS 14+ keeps the real choice (a colour, an aerial, a dynamic image) in this store; NSWorkspace reports only
    /// DefaultDesktop.heic for anything that is not a plain image file (2026-11-01: his black desktop is a systemColor).
    /// So the store's leaves are snapshotted and are what "none" puts back, only where a Sprites PNG shows, never over a
    /// newer choice (WallpaperBook in Decide.swift; review R1 #4). The NSWorkspace records are the fallback.
    private let book = WallpaperBook(store: Paths.home + "/Library/Application Support/com.apple.wallpaper/Store/Index.plist",
                                     snap: Paths.home + "/ClaudeWork/sprites/config/wallpaper_store_original.plist",
                                     originalsFile: Paths.home + "/ClaudeWork/sprites/config/wallpaper_original.json",
                                     cacheDir: Backdrop.cacheDir, connected: { Wallpaper.connectedDisplayUUIDs() })
    /// A restore whose WallpaperAgent restart has not been verified yet (review R1_MACOS #11); no second one meanwhile.
    private var restoring = false
    /// Bumped by every set(_:): a backdrop written while a restore is being verified wins (no retry, no fallback over it).
    private var generation = 0
    private func ours(_ u: URL?) -> Bool { book.isOurs(u?.path) }
    func inUse() -> Set<String> {
        book.storeImagePaths().union(NSScreen.screens.compactMap { NSWorkspace.shared.desktopImageURL(for: $0)?.path })
    }
    /// A backdrop chosen from "none": a fresh snapshot of the store.
    func backdropChosen(_ id: String) -> Bool { book.backdropChosen(from: "none", to: id) }

    func set(_ urls: [NSScreen: URL]) {
        generation += 1
        guard book.prepareWrite() else { log("backdrop: cannot snapshot wallpaper store; not changing the wallpaper"); return }
        for (s, u) in urls {
            let cur = NSWorkspace.shared.desktopImageURL(for: s)
            if cur == u { continue }
            let k = key(s)
            if !ours(cur), let cur {
                var rec: [String: Any] = ["url": cur.path]
                let o = NSWorkspace.shared.desktopImageOptions(for: s) ?? [:]
                if let v = o[.imageScaling] as? NSNumber { rec["scaling"] = v.intValue }
                if let v = o[.allowClipping] as? Bool { rec["clip"] = v }
                if let c = (o[.fillColor] as? NSColor)?.usingColorSpace(.sRGB) { rec["fill"] = [c.redComponent, c.greenComponent, c.blueComponent, c.alphaComponent] }
                rec["recorded"] = ISO8601DateFormatter().string(from: Date())
                book.record(k, rec)   // record BEFORE changing anything
            }
            do {
                try NSWorkspace.shared.setDesktopImageURL(u, for: s, options: [.imageScaling: NSNumber(value: NSImageScaling.scaleProportionallyUpOrDown.rawValue), .allowClipping: true])
            } catch { log("backdrop: set wallpaper: \(error.localizedDescription)") }
        }
    }

    /// Put back what showed before wherever a Sprites PNG shows: every Space at once through the store, then the
    /// NSWorkspace records for any current-Space screen the store could not resolve. Review R1_MACOS #11: the Store is
    /// rewritten, WallpaperAgent restarted, and then (off main, bounded) we wait for a NEW agent pid, re-read the Store and
    /// check the restore stuck before the fallback runs or the snapshot is dropped; a lost restore is retried once.
    func restoreCurrentSpace() {
        if restoring { return }
        let anyOurs = NSScreen.screens.contains { ours(NSWorkspace.shared.desktopImageURL(for: $0)) } || book.liveHasOurs()
        guard anyOurs, let r = book.restoreStore(finalize: false) else { return fallbackRestore() }
        if r.restored.isEmpty && r.removed.isEmpty { book.finalize(r); return fallbackRestore() }
        restoring = true
        let gen = generation
        DispatchQueue.global(qos: .utility).async { [weak self] in
            var r = r, stuck = false
            for attempt in 0..<2 {
                let ok = Wallpaper.restartAgent()
                if DispatchQueue.main.sync(execute: { self?.generation != gen }) { break }   // a backdrop was set meanwhile
                stuck = DispatchQueue.main.sync { self.map { $0.book.finalize(r) } ?? false }
                log("backdrop: wallpaper store restore (attempt \(attempt + 1), agent back \(ok)): \(r.restored.count) restored, \(r.removed.count) removed, kept \(r.kept.count), later \(r.later.count), stuck \(stuck)")
                if stuck { break }
                guard attempt == 0, let again = DispatchQueue.main.sync(execute: { self?.book.restoreStore(finalize: false) }) else { break }
                r = again
            }
            DispatchQueue.main.async {
                guard let self else { return }
                self.restoring = false
                if self.generation != gen { log("backdrop: a backdrop was set during the restore; it stands"); return }
                if !stuck { log("backdrop: the store restore did not stick twice; snapshot kept, no fallback"); return }
                if !r.unresolved.isEmpty { log("backdrop: \(r.unresolved.count) store entries show ours with no snapshot; trying the recorded originals") }
                self.fallbackRestore()
            }
        }
    }

    /// The NSWorkspace records, for current-Space screens that still show ours. Never the placeholder.
    private func fallbackRestore() {
        for s in NSScreen.screens {
            guard ours(NSWorkspace.shared.desktopImageURL(for: s)) else { continue }
            let k = key(s), disp = k.components(separatedBy: "|")[0]
            guard let rec = book.originals[k] ?? book.originals.first(where: { $0.key.hasPrefix(disp + "|") })?.value else { log("backdrop: no recorded wallpaper for \(k)"); continue }
            guard let p = fallbackRestorePath(rec) else { log("backdrop: record for \(k) is the macOS placeholder or unusable; not setting it"); continue }
            var opt: [NSWorkspace.DesktopImageOptionKey: Any] = [:]
            if let v = rec["scaling"] as? Int { opt[.imageScaling] = NSNumber(value: v) }
            if let v = rec["clip"] as? Bool { opt[.allowClipping] = v }
            if let f = rec["fill"] as? [Double], f.count == 4 { opt[.fillColor] = NSColor(srgbRed: f[0], green: f[1], blue: f[2], alpha: f[3]) }
            do { try NSWorkspace.shared.setDesktopImageURL(URL(fileURLWithPath: p), for: s, options: opt); book.forget(k) }
            catch { log("backdrop: restore wallpaper: \(error.localizedDescription)") }
        }
        book.dropSnapshotIfIdle()
    }

    /// killall WallpaperAgent (launchd relaunches it; it rereads the store), then wait up to 5 s for a new pid plus a
    /// short settle. Off main only. False = no new agent seen.
    static func restartAgent() -> Bool {
        let old = pidsNamed("WallpaperAgent")
        let k = Process(); k.executableURL = URL(fileURLWithPath: "/usr/bin/killall"); k.arguments = ["WallpaperAgent"]
        do { try k.run(); k.waitUntilExit() } catch { return false }
        let t0 = Date()
        while Date().timeIntervalSince(t0) < 5 {
            if relaunchedPid(old: old, now: pidsNamed("WallpaperAgent")) != nil { Thread.sleep(forTimeInterval: 0.5); return true }
            Thread.sleep(forTimeInterval: 0.1)
        }
        return false
    }

    static func connectedDisplayUUIDs() -> Set<String>? {
        var ids = [CGDirectDisplayID](repeating: 0, count: 16), n: UInt32 = 0
        guard CGGetOnlineDisplayList(16, &ids, &n) == .success else { return nil }
        return Set(ids.prefix(Int(n)).compactMap { id in
            CGDisplayCreateUUIDFromDisplayID(id).flatMap { CFUUIDCreateString(nil, $0.takeRetainedValue()) as String? } })
    }

    private func key(_ s: NSScreen) -> String {
        var disp = "main"
        if let n = s.deviceDescription[NSDeviceDescriptionKey("NSScreenNumber")] as? NSNumber,
           let u = CGDisplayCreateUUIDFromDisplayID(n.uint32Value)?.takeRetainedValue() {
            disp = (CFUUIDCreateString(nil, u) as String?) ?? "main"
        }
        return disp + "|" + (Wallpaper.managedSpaces().flatMap { currentSpace(displayUUID: disp, managed: $0) } ?? Wallpaper.activeSpace())
    }

    /// SkyLight's CGSCopyManagedDisplaySpaces (private; looked up at runtime): one entry per display, or one "Main"
    /// entry when a Space spans every display (review R1_MACOS #15). nil if absent.
    static func managedSpaces() -> [[String: Any]]? {
        typealias ConnFn = @convention(c) () -> Int32
        typealias CopyFn = @convention(c) (Int32) -> Unmanaged<CFArray>?
        guard let h = dlopen(nil, RTLD_NOW), let c = dlsym(h, "CGSMainConnectionID"), let f = dlsym(h, "CGSCopyManagedDisplaySpaces") else { return nil }
        return unsafeBitCast(f, to: CopyFn.self)(unsafeBitCast(c, to: ConnFn.self)())?.takeRetainedValue() as? [[String: Any]]
    }

    /// The main display's active Space id via SkyLight's CGSGetActiveSpace (the fallback; "?" if absent).
    static func activeSpace() -> String {
        typealias ConnFn = @convention(c) () -> Int32
        typealias SpaceFn = @convention(c) (Int32) -> UInt64
        guard let h = dlopen(nil, RTLD_NOW), let c = dlsym(h, "CGSMainConnectionID"), let g = dlsym(h, "CGSGetActiveSpace") else { return "?" }
        let conn = unsafeBitCast(c, to: ConnFn.self)(), sp = unsafeBitCast(g, to: SpaceFn.self)(conn)
        return String(sp)
    }
}
