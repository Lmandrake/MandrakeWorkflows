import AppKit
import Metal
import QuartzCore

/// The Aether's host (design: docs/design/2026-11-08-aether/03-merged.md, option A: native Swift sim + Metal instanced
/// dots, in the existing black BackdropWindow, one per screen). Owned by Backdrop: while behaviors.json has
/// "aether": {"enabled": true} (or "backdrop": "aether"), it replaces the moving backdrop.
///
/// Per screen: one AetherSim in that screen's logical points, top-left origin (CG style). Inputs:
///  - obstacles: every real window of any app and layer (Sprites' own Settings window included, owner: "windows of any
///    kind"), plus the menu-bar and Dock bands from visibleFrame. Not: our stage, dim and backdrop windows, the cursor
///    window, screen-sized system containers. Desktop icons are ignored (owner ruling 4).
///  - sprites: the stage's hit circles, with ids (field family 1, a sideways deflection; stirring, from their motion).
///  - typing: HID idle counters (no grant), as pushActivity reads them.
/// Three clocks (correction 2): geometry 2 Hz calm / 12 Hz while a drag is seen / at once on a Space change; the sim's
/// fixed step; presentation from frameInterval (30 fps calm, 60 only while a window pushes or a sprite stirs the gas
/// and ~1 s after: owner card 2026-11-08 ~18:35 PST; positions interpolated between steps).
/// A still gas holds its frame (no draws).
/// Quiet plan (aetherQuietPlan): hidden, meeting, locked and covered draw nothing; Reduce Motion, Low Power and thermal
/// Serious hold a still frame. Battery under 20 % is not read yet (no IOKit here).
/// Release 1 is unmeasured on WindowServer cost: the owner waived that gate until he is back at Lab (2026-11-08).
/// One sprite for the Aether, CG global points: the stage's hit circle, its id, its species (concept) and project key.
/// Identity only (species wakes, handedness): nothing about its work or status reaches the gas.
struct AetherHit { var pos: CGPoint; var r: CGFloat; var id: String; var species = "", key = "" }

final class AetherHost {
    private struct Screen { let screen: NSScreen; let window: BackdropWindow; var sim: AetherSim; var last: [AetherObstacle] }
    private var screens: [Screen] = []
    private var settings = AetherSettings()
    private unowned let owner: Backdrop
    private let device: MTLDevice
    private let queue: MTLCommandQueue?
    private var pipeline: MTLRenderPipelineState?
    private var timer: Timer?
    private var lastTick = CACurrentMediaTime(), nextGeom = 0.0, lastDrag = -Double.infinity
    private var reconcile = true, needsDraw = true, stillDrawn = false, blanked = false
    private var dragMonitor: Any?
    /// CG-global sprite circles (centre, radius in points); set by the app from the stage's hits.
    var sprites: () -> [AetherHit] = { [] }
    var paused = false { didSet { if paused != oldValue { wake() } } }
    /// Drifting constants (owner, 2026-11-08 ~5 PM): the walk's clock (seeded, wall-clock phase), and a callback with
    /// the drifted values about once a second while drift is on or easing out (Settings shows them, faint).
    private var drift = AetherDriftClock(epochSeconds: Date().timeIntervalSince1970, periodMinutes: 30)
    static let driftSeed: UInt64 = 0xAE7E_D21F_7000_0001
    private var lastDriftReport = -Double.infinity
    var onDrift: (([String: Double]) -> Void)?
    /// Wake reader (owner card 2026-11-08 18:30 PST): every ~2 s, each sprite's leftover current from OTHER sprites'
    /// wakes, pt/s (CG and stage px point the same way), and the reader's strength, for the stage. Empty when off.
    var onCurrents: ((Double, [String: (Double, Double)]) -> Void)?
    private var lastCurrents = -Double.infinity, sentCurrents = false

    init(device: MTLDevice, owner: Backdrop) {
        self.device = device; self.owner = owner; queue = device.makeCommandQueue()
        pipeline = Self.makePipeline(device)
        dragMonitor = NSEvent.addGlobalMonitorForEvents(matching: [.leftMouseDragged]) { [weak self] _ in
            guard let self else { return }
            let calm = CACurrentMediaTime() - self.lastDrag > 0.3
            self.lastDrag = CACurrentMediaTime()
            if calm { self.wake() }   // a drag begins: read geometry at 12 Hz from now
        }
    }

    deinit { if let m = dragMonitor { NSEvent.removeMonitor(m) } }

    // MARK: lifecycle

    func apply(_ s: AetherSettings) {
        let rebuild = s.densityPerMpt2 != settings.densityPerMpt2 || s.boundary != settings.boundary ||
            s.collisionDiameter != settings.collisionDiameter || screens.isEmpty
        // "Hold this universe" writes the drifted values into the sliders and turns drift off: when the new centre is
        // the universe now running, the walk stops at once (no ease back), so holding never moves a single dot.
        if s.drift == .off && settings.drift != .off && drift.amplitude > 0 {
            let now = drifted()
            if aetherDriftKeys.allSatisfy({ abs(s[keyPath: $0.path] - now[keyPath: $0.path]) <= 0.02 * ($0.hi - $0.lo) }) { drift.amplitude = 0 }
        }
        settings = s
        if rebuild { build() } else { let d = drifted(); for i in screens.indices { screens[i].sim.settings = d } }
        refreshFronts()   // the fronts carry slider values: a moved slider (or drift off) must reach them at once
        needsDraw = true; wake()
    }

    /// Screens changed (or first start): one window and one fresh sim per screen.
    func build() {
        let scrs = NSScreen.screens
        var wins = screens.map { $0.window }
        while wins.count > scrs.count { wins.removeLast().close() }
        while wins.count < scrs.count { wins.append(BackdropWindow(device: device, owner: owner)) }
        let windows = windowObstacles()
        screens = zip(wins, scrs).enumerated().map { k, ws in
            let (w, s) = ws
            w.fit(s); w.orderFrontRegardless()
            let obs = obstacles(for: s, windows: windows)
            var t = AetherTuning(); t.maxCatchUp = 32   // a 2 fps frame is 15 steps; the sim still holds anything beyond 1 s
            let seed = UInt64(Date().timeIntervalSince1970 * 1000) ^ UInt64(k + 1) &* 0x9E37_79B9_7F4A_7C15
            let sim = AetherSim(bounds: AetherRect(x: 0, y: 0, width: s.frame.width, height: s.frame.height),
                                settings: drifted(), seed: seed, tuning: t, obstacles: obs)
            return Screen(screen: s, window: w, sim: sim, last: obs)
        }
        log("aether: \(screens.count) screen(s), \(screens.map { $0.sim.population }) points, motion \(settings.motion.rawValue)")
        lastTick = CACurrentMediaTime(); reconcile = true; needsDraw = true
    }

    func stop() {
        timer?.invalidate(); timer = nil
        screens.forEach { $0.window.orderOut(nil); $0.window.close() }; screens = []
    }

    /// Something changed (occlusion, visibility, a drag began, a Space change): run the clocks now.
    func wake(reconcileGeometry: Bool = false) {
        if reconcileGeometry { reconcile = true }
        schedule(0)
    }

    func stir() { for s in screens { s.sim.stir() }; wake() }

    private func schedule(_ seconds: Double) {
        timer?.invalidate()
        guard !screens.isEmpty else { return }
        let t = Timer(timeInterval: max(0, seconds), repeats: false) { [weak self] _ in self?.tick() }
        t.tolerance = min(0.05, max(0.004, seconds * 0.1))
        RunLoop.main.add(t, forMode: .common); timer = t
    }

    // MARK: the clocks

    private func quiet() -> AetherQuiet {
        let covered = !screens.contains { $0.window.occlusionState.contains(.visible) }
        return aetherQuietPlan(hidden: paused, meeting: false, locked: false, covered: covered,
                               reduceMotion: NSWorkspace.shared.accessibilityDisplayShouldReduceMotion,
                               lowPower: ProcessInfo.processInfo.isLowPowerModeEnabled, batteryBelow20: false,
                               thermal: ProcessInfo.processInfo.thermalState.rawValue)
    }

    private func tick() {
        let now = CACurrentMediaTime(), dt = min(1.0, max(0, now - lastTick)); lastTick = now
        let cap: Double
        switch quiet() {
        case .off:                                                  // occlusion/visibility changes wake us sooner
            if !blanked { blank(); blanked = true }                 // hidden/meeting: no points left on screen
            stillDrawn = false; return schedule(1.0)
        case .still:
            if !stillDrawn || needsDraw { drawAll(); stillDrawn = true; needsDraw = false }
            blanked = false
            return schedule(1.0)
        case .draw(let c): cap = c; stillDrawn = false; blanked = false
        }
        let typing = min(secondsSince(.keyDown), secondsSince(.scrollWheel)) < 1.5
        let dragging = now - lastDrag < 0.25
        if reconcile || now >= nextGeom {
            let interval = AetherClocks.geometryInterval(dragging: dragging, reconcile: false)
            readGeometry(sweep: reconcile ? 0 : interval)
            nextGeom = now + interval; reconcile = false
        }
        stepDrift(dt, now)
        let sp = sprites()
        defer { reportCurrents(now) }
        var next: Double? = nil
        for i in screens.indices {
            let o = cgFrame(screens[i].screen).origin
            screens[i].sim.setSprites(sp.map { AetherSprite(pos: SIMD2(Double($0.pos.x - o.x), Double($0.pos.y - o.y)), radius: Double($0.r), id: $0.id,
                                                            species: $0.species, key: $0.key) })
            screens[i].sim.advance(by: dt, typing: typing)
            if let f = screens[i].sim.frameInterval(capFps: cap) { next = min(next ?? f, f) }
        }
        if next != nil || needsDraw { drawAll(); needsDraw = false }
        schedule(min(next ?? .infinity, max(0.005, nextGeom - now)))
    }

    /// SPRITES_DEBUG_AETHER=1: one QA line per screen every 5 s (dew, knots, fronts, frame rate, currents).
    private let debug = ProcessInfo.processInfo.environment["SPRITES_DEBUG_AETHER"] == "1"
    private var lastDebug = -Double.infinity
    private func reportCurrents(_ now: Double) {
        if debug && now - lastDebug >= 5 { lastDebug = now; for (k, s) in screens.enumerated() { log("aether[\(k)]: \(s.sim.debugLine)") } }
        guard now - lastCurrents >= 2, let cb = onCurrents else { return }
        lastCurrents = now
        guard settings.wakeReader > 0 else { if sentCurrents { cb(0, [:]); sentCurrents = false }; return }
        var all: [String: (Double, Double)] = [:]
        for s in screens { for (id, v) in s.sim.leftoverCurrents() { all[id] = (v.x, v.y) } }
        cb(settings.wakeReader, all); sentCurrents = true
    }

    // MARK: drifting constants

    /// The settings the sims run: the owner's sliders moved along the drift walk (the sliders are the centre).
    private func drifted() -> AetherSettings {
        aetherDrifted(settings, seed: Self.driftSeed, phase: drift.phase, amplitude: drift.amplitude)
    }

    /// Advance the walk with the presentation clock (a still, held gas does not tick, and so does not drift: nothing
    /// would show it) and hand every sim the drifted constants. Once a second, report them to Settings.
    private func stepDrift(_ dt: Double, _ now: Double) {
        guard settings.drift != .off || drift.amplitude > 0 else { return }
        drift.advance(dt, mode: settings.drift, periodMinutes: settings.driftPeriodMinutes)
        let d = drifted()
        for i in screens.indices { screens[i].sim.settings = d }
        guard now - lastDriftReport >= 1 else { return }
        lastDriftReport = now
        refreshFronts()   // once a second: the borders move over an hour
        guard let cb = onDrift else { return }
        var out: [String: Double] = ["amplitude": drift.amplitude]
        for k in aetherDriftKeys { out[k.name] = d[keyPath: k.path] }
        cb(out)
    }

    /// Weather fronts (owner card 2026-11-08 18:30 PST): each region's own drift phase, or nil (drift off, fronts 0).
    private func refreshFronts() {
        let minutes = Date().timeIntervalSince1970 / 60
        for i in screens.indices {
            let sim = screens[i].sim
            sim.setFronts(aetherFronts(settings, seed: Self.driftSeed, phase: drift.phase, amplitude: drift.amplitude, minutes: minutes,
                                       bounds: sim.bounds, cell: sim.tuning.coarseCell))
        }
    }

    // MARK: geometry

    /// Every window that should be a wall, CG global rects, with a stable id (the window number).
    private func windowObstacles() -> [(id: Int, rect: CGRect)] {
        let me = ProcessInfo.processInfo.processIdentifier
        let scrFrames = NSScreen.screens.map { cgFrame($0) }
        return windowList().compactMap { w in
            guard let layer = w[kCGWindowLayer as String] as? Int, let pid = w[kCGWindowOwnerPID as String] as? Int32,
                  let b = w[kCGWindowBounds as String] as? NSDictionary, let r = CGRect(dictionaryRepresentation: b),
                  ((w[kCGWindowAlpha as String] as? Double) ?? 1) > 0, r.width >= 8, r.height >= 8 else { return nil }
            if layer < 0 || layer >= 1000 { return nil }                   // desktop levels (ours too), cursor, screen saver
            if pid == me && layer != 0 { return nil }                      // our stage and dim layer; Settings (layer 0) is a wall
            if layer == 24 || layer == 25 { return nil }                   // menu bar and status items: the band covers them
            if layer != 0, scrFrames.contains(where: { r.intersection($0).width * r.intersection($0).height >= 0.8 * $0.width * $0.height }) {
                return nil                                                 // screen-sized system containers (Dock, WindowServer)
            }
            return ((w[kCGWindowNumber as String] as? Int) ?? 0, r)
        }
    }

    /// One screen's obstacles in its local points: the windows on it, plus the menu-bar and Dock bands.
    private func obstacles(for s: NSScreen, windows: [(id: Int, rect: CGRect)]) -> [AetherObstacle] {
        let f = cgFrame(s), W = Double(s.frame.width), H = Double(s.frame.height)
        var out: [AetherObstacle] = []
        for w in windows {
            let r = w.rect.intersection(f.insetBy(dx: -40, dy: -40))
            guard !r.isNull, r.width > 0, r.height > 0 else { continue }
            out.append(AetherObstacle(id: w.id, rect: AetherRect(x: Double(r.minX - f.minX), y: Double(r.minY - f.minY),
                                                                  width: Double(r.width), height: Double(r.height))))
        }
        let v = s.visibleFrame, fr = s.frame
        let top = Double(fr.maxY - v.maxY), bottom = Double(v.minY - fr.minY)
        let left = Double(v.minX - fr.minX), right = Double(fr.maxX - v.maxX)
        if top > 0 { out.append(AetherObstacle(id: -1, rect: AetherRect(minX: -40, minY: -40, maxX: W + 40, maxY: top))) }
        if bottom > 0 { out.append(AetherObstacle(id: -2, rect: AetherRect(minX: -40, minY: H - bottom, maxX: W + 40, maxY: H + 40))) }
        if left > 0 { out.append(AetherObstacle(id: -3, rect: AetherRect(minX: -40, minY: -40, maxX: left, maxY: H + 40))) }
        if right > 0 { out.append(AetherObstacle(id: -4, rect: AetherRect(minX: W - right, minY: -40, maxX: W + 40, maxY: H + 40))) }
        return out
    }

    private func readGeometry(sweep: Double) {
        let windows = windowObstacles()
        for i in screens.indices {
            let obs = obstacles(for: screens[i].screen, windows: windows)
            if obs == screens[i].last { continue }
            screens[i].sim.setGeometry(obs, sweep: sweep)
            screens[i].last = obs
        }
    }

    // MARK: drawing (one instanced point draw per screen)

    private static func makePipeline(_ device: MTLDevice) -> MTLRenderPipelineState? {
        let msl = """
        #include <metal_stdlib>
        using namespace metal;
        struct P { float2 pos; float a; float pad; };
        struct U { float2 size; float px; float core; float4 col; };
        struct VO { float4 pos [[position]]; float ps [[point_size]]; float a; };
        vertex VO aeV(uint vid [[vertex_id]], const device P* p [[buffer(0)]], constant U& u [[buffer(1)]]) {
          VO o; float2 q = p[vid].pos / u.size; o.pos = float4(q.x * 2.0 - 1.0, 1.0 - q.y * 2.0, 0.0, 1.0);
          o.ps = u.px; o.a = p[vid].a; return o; }
        fragment float4 aeF(VO i [[stage_in]], float2 pc [[point_coord]], constant U& u [[buffer(1)]]) {
          float r = length(pc - 0.5) * 2.0;
          float core = 1.0 - smoothstep(u.core * 0.6, u.core, r);
          float halo = 0.18 * exp(-r * r * 5.0) * (1.0 - smoothstep(0.8, 1.0, r));
          float v = (core + halo) * i.a;
          return float4(u.col.rgb * v, 1.0); }
        """
        do {
            let lib = try device.makeLibrary(source: msl, options: nil)
            let d = MTLRenderPipelineDescriptor()
            d.vertexFunction = lib.makeFunction(name: "aeV"); d.fragmentFunction = lib.makeFunction(name: "aeF")
            let c = d.colorAttachments[0]!
            c.pixelFormat = .bgra8Unorm
            c.isBlendingEnabled = true                        // additive light on black
            c.rgbBlendOperation = .add; c.sourceRGBBlendFactor = .one; c.destinationRGBBlendFactor = .one
            c.alphaBlendOperation = .max; c.sourceAlphaBlendFactor = .one; c.destinationAlphaBlendFactor = .one
            return try device.makeRenderPipelineState(descriptor: d)
        } catch { log("aether: shader: \(error)"); return nil }
    }

    private var colour: SIMD4<Float> {
        let base = SIMD3<Float>(settings.rgb)   // a preset or the picker's hex
        let k: Float = [0.45, 0.7, 1.0][max(0, min(2, settings.brightness - 1))]
        return SIMD4(base * k, 1)
    }

    private func drawAll() { for s in screens where s.window.occlusionState.contains(.visible) || needsDraw { draw(s) } }

    private func blank() { for s in screens { draw(s, empty: true) } }

    private func draw(_ s: Screen, empty: Bool = false) {
        guard let pipe = pipeline, let q = queue, let drawable = s.window.metal.nextDrawable(), let cb = q.makeCommandBuffer() else { return }
        let sim = s.sim
        var pts: [Float] = []; pts.reserveCapacity(sim.pos.count * 4)
        for i in sim.pos.indices where !empty && sim.phase[i] != .dormant && sim.alpha[i] > 0.01 {
            let q = sim.presentedPos(i)   // between the last two steps: the 30 Hz step never shows
            pts.append(Float(q.x)); pts.append(Float(q.y)); pts.append(Float(sim.alpha[i])); pts.append(0)
        }
        let rp = MTLRenderPassDescriptor(); rp.colorAttachments[0].texture = drawable.texture
        rp.colorAttachments[0].loadAction = .clear; rp.colorAttachments[0].clearColor = MTLClearColor(red: 0, green: 0, blue: 0, alpha: 1)
        rp.colorAttachments[0].storeAction = .store
        guard let enc = cb.makeRenderCommandEncoder(descriptor: rp) else { return }
        let n = pts.count / 4
        if n > 0, let buf = device.makeBuffer(bytes: pts, length: pts.count * MemoryLayout<Float>.size, options: .storageModeShared) {
            let scale = Float(s.window.metal.contentsScale)
            let core = Float(settings.particleDiameter) * scale, px = max(3, core * 2.6)
            var u: [Float] = [Float(s.screen.frame.width), Float(s.screen.frame.height), px, core / px]
            let c = colour; u += [c.x, c.y, c.z, c.w]
            enc.setRenderPipelineState(pipe)
            enc.setVertexBuffer(buf, offset: 0, index: 0)
            enc.setVertexBytes(&u, length: u.count * 4, index: 1)
            enc.setFragmentBytes(&u, length: u.count * 4, index: 1)
            enc.drawPrimitives(type: .point, vertexStart: 0, vertexCount: n)
        }
        enc.endEncoding(); cb.present(drawable); cb.commit()
    }
}
