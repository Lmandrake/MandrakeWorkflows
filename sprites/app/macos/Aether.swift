import Foundation

/// The Aether's simulation core (design: docs/design/2026-11-08-aether/03-merged.md, rulings 2026-11-08). Pure: no
/// AppKit, no window, no Metal, no clock of its own, so tests/swift/aether/ can drive it headless and seeded. The host
/// (AetherHost.swift) feeds it window rectangles, sprite positions and elapsed time, and draws `pos`/`alpha`.
///
/// Units: logical points and seconds; mass 1; "temperature" is the per-component velocity variance σ².
/// Engine choice (merge recommendation A): native Swift arrays + uniform grid hash, CPU only; Metal only draws.
/// Specified for Dense (~1 500 points, 1.5 pt, capacity 3 000) even though Sparse (~150) is the usual setting.
///
/// What the merge's corrections became here:
///  1. Walls are the union of window rectangles expanded by the collision radius, swept between geometry samples:
///     every face moves linearly within a substep, and a point's entry is found exactly (slab test on linear functions).
///     Every plausible window move is a sweep, calm 2 Hz reads included (a face faster than `teleportSpeed` snaps).
///     A window that APPEARS on top of points (no motion: it cannot push) sends them dormant; any other point that
///     ends inside a window is pushed out to the nearest free side; dormant only if no free side exists.
///  2. Three clocks: geometry (`AetherClocks.geometryInterval`), simulation (fixed `tuning.dt`, bounded substeps and
///     catch-up, `advance`), presentation (`frameInterval`, from the 90th-percentile speed, capped at 30 fps calm and
///     60 only while pushed: owner card 2026-11-08 ~18:35 PST, "30 calm, 60 when pushed").
///  3. Strict speed ceiling, with one exception: windows PUSH (owner ruling, 2026-11-08, "Push, replace wipe"). A face
///     faster than the ceiling carries the point on it at the face's normal speed (no 2w bounce), tangential speed
///     kept; a pressed point may exceed the ceiling only while pressed, and its excess bleeds off in `pushReleaseTau`
///     once free. Pressed points collide inelastically (the pile moves as one) and are pushed toward the face's
///     nearer corner in proportion to local crowding, so a pile spills round the window; the crowding cap spares
///     them. The old absorb-above-ceiling rule (the "wipe") is gone.
///  4. Revealed-space reserve: exposed desktop is reseeded gently from the dormant pool at the gas's temperature.
///  5. Temperature VARIES (owner ruling 7, 2026-11-08: "Let's not relax particles to the 'correct' temperature. Let
///     it vary more."). "Temperature variation" (0-1, default 0.85) scales the old per-point Ornstein-Uhlenbeck
///     relaxation (velocity relative to the LOCAL flow, toward the target) to τ/(1-v)², off at 1; 0 is the old uniform
///     gas. Above 0, energy leaves through Cooling (drag: flow damping, and the settle paths as pure damping, no kick)
///     and comes in from windows, sprite stirring, the tray Stir and the screen edges, which are a weak, slow source
///     (a hit re-emits at the Temperature with probability 1-v+v x edgeAccommodationFree, else reflects). The
///     Temperature is the start, the edge emission and the floor's partner; the floor is a global uniform rescale of
///     the mean; hot pockets (hotFactor x target) are only damped down to that ceiling (hotTau), never kicked; the
///     rewarm after typing rescales uniformly back to the pre-typing energy, so a hot/cold pattern survives typing.
///  6. Density is defined once, per million logical square points; population = density x screen area; points under
///     windows are dormant, so a covered region's share is what the reserve gives back.
///  9. Bonding is FORCES, not constraints (owner ruling 8, 2026-11-08: "a short-range attraction and a long range
///     repulsion... reproduce the bonding through actual forces rather than constraints. Relax those constraints.").
///     Short range: a pair well in pair() (hard core at the collision diameter, depth Attraction x the Temperature's
///     σ², smooth taper to 0 at Attraction range x diameter; the grid cell is sized for the widest range, so the
///     neighbour search stays one ring), with a well friction on the pair's normal relative velocity, set by Cooling,
///     so a passing pair can be captured (two bodies cannot bind without losing energy). Long range: particle-in-cell
///     on the coarse grid (cloud-in-cell deposit, binomial smoothing over Repulsion range cells, central-difference
///     gradient, the same weights back: no self-force), O(N + cells). Needles: "Chain forming" mixes in a dipole term,
///     each point carrying an orientation that turns toward its neighbours' dipole field (overdamped, with rotational
///     noise from the local temperature): head-to-tail attracts, side-by-side repels, so chains form and break
///     thermally, with no lifetimes, caps or rest lengths. A work counter (`work`) bounds the cost without a benchmark.

// MARK: - Geometry

struct AetherRect: Equatable {
    var minX, minY, maxX, maxY: Double
    init(minX: Double, minY: Double, maxX: Double, maxY: Double) { self.minX = minX; self.minY = minY; self.maxX = maxX; self.maxY = maxY }
    init(x: Double, y: Double, width: Double, height: Double) { self.init(minX: x, minY: y, maxX: x + width, maxY: y + height) }
    var width: Double { maxX - minX }
    var height: Double { maxY - minY }
    var area: Double { max(0, width) * max(0, height) }
    func expanded(by r: Double) -> AetherRect { AetherRect(minX: minX - r, minY: minY - r, maxX: maxX + r, maxY: maxY + r) }
    /// Strict interior.
    func contains(_ p: SIMD2<Double>) -> Bool { p.x > minX && p.x < maxX && p.y > minY && p.y < maxY }
    func intersection(_ o: AetherRect) -> AetherRect? {
        let r = AetherRect(minX: max(minX, o.minX), minY: max(minY, o.minY), maxX: min(maxX, o.maxX), maxY: min(maxY, o.maxY))
        return (r.maxX > r.minX && r.maxY > r.minY) ? r : nil
    }
    /// self minus o, as at most four disjoint rectangles.
    func subtracting(_ o: AetherRect) -> [AetherRect] {
        guard let i = intersection(o) else { return [self] }
        var out: [AetherRect] = []
        if i.minY > minY { out.append(AetherRect(minX: minX, minY: minY, maxX: maxX, maxY: i.minY)) }
        if i.maxY < maxY { out.append(AetherRect(minX: minX, minY: i.maxY, maxX: maxX, maxY: maxY)) }
        if i.minX > minX { out.append(AetherRect(minX: minX, minY: i.minY, maxX: i.minX, maxY: i.maxY)) }
        if i.maxX < maxX { out.append(AetherRect(minX: i.maxX, minY: i.minY, maxX: maxX, maxY: i.maxY)) }
        return out
    }
    static func lerp(_ a: AetherRect, _ b: AetherRect, _ f: Double) -> AetherRect {
        AetherRect(minX: a.minX + (b.minX - a.minX) * f, minY: a.minY + (b.minY - a.minY) * f,
                   maxX: a.maxX + (b.maxX - a.maxX) * f, maxY: a.maxY + (b.maxY - a.maxY) * f)
    }
}

/// The union of rects as disjoint fragments.
func aetherDisjoint(_ rs: [AetherRect]) -> [AetherRect] {
    var frags: [AetherRect] = []
    for r in rs where r.area > 0 {
        var pieces = [r]
        for f in frags { pieces = pieces.flatMap { $0.subtracting(f) } }
        frags += pieces
    }
    return frags
}

/// union(rs) minus union(cut), as disjoint fragments.
func aetherSubtract(_ rs: [AetherRect], _ cut: [AetherRect]) -> [AetherRect] {
    var pieces = aetherDisjoint(rs)
    for c in cut { pieces = pieces.flatMap { $0.subtracting(c) } }
    return pieces
}

struct AetherObstacle: Equatable { var id: Int; var rect: AetherRect }
/// A sprite's hit circle. `id` (the stage's hit id) lets the sim track it between updates and estimate its velocity;
/// an empty id is a stationary body.
/// species (the stage's concept, e.g. "c2_siphon") and key (the project key) are identity only: they shape the wake
/// and its handedness, never anything about the sprite's work or status (owner card 2026-11-08 18:30 PST).
struct AetherSprite {
    var pos: SIMD2<Double>; var radius: Double; var id = ""; var species = ""; var key = ""
    init(pos: SIMD2<Double>, radius: Double, id: String = "", species: String = "", key: String = "") {
        self.pos = pos; self.radius = radius; self.id = id; self.species = species; self.key = key
    }
}

@inline(__always) func dot2(_ a: SIMD2<Double>, _ b: SIMD2<Double>) -> Double { a.x * b.x + a.y * b.y }
@inline(__always) func len2(_ a: SIMD2<Double>) -> Double { (a.x * a.x + a.y * a.y).squareRoot() }

/// SplitMix64: seeded, deterministic, cheap.
struct AetherRNG {
    var state: UInt64
    init(seed: UInt64) { state = seed }
    mutating func next() -> UInt64 {
        state &+= 0x9E37_79B9_7F4A_7C15
        var z = state
        z = (z ^ (z >> 30)) &* 0xBF58_476D_1CE4_E5B9
        z = (z ^ (z >> 27)) &* 0x94D0_49BB_1331_11EB
        return z ^ (z >> 31)
    }
    mutating func uniform() -> Double { Double(next() >> 11) * (1.0 / 9_007_199_254_740_992.0) }
    mutating func gaussian() -> Double {
        let u1 = max(uniform(), 1e-300), u2 = uniform()
        return (-2 * log(u1)).squareRoot() * cos(2 * Double.pi * u2)
    }
    /// |normal component| of a wall-emitted Maxwell flux in 2-D: Rayleigh, in units of σ.
    mutating func rayleigh() -> Double { (-2 * log(max(uniform(), 1e-300))).squareRoot() }
}

// MARK: - Engine constants (not user settings; tests override some)

struct AetherTuning {
    var dt = 1.0 / 30                      // simulation clock: fixed step
    var maxSubsteps = 4
    var maxCatchUp = 4                     // steps per advance(); older time is held, never raced through
    var capacity = 3000                    // point slots (Dense full screen, reservoir headroom)
    /// Bulk relaxation time constant; nil = by boundary (reflect 60 s, thermal/reservoir 20 s); .infinity = off.
    var thermostatTau: Double? = nil
    var flowTau: Double? = nil             // damping of bulk flow; nil = from settings.coolingSeconds / 3
    var hotFactor = 4.0, hotTau = 1.5      // trapped/forced pockets hotter than hotFactor x target relax fast
    var edgeAccommodationFree = 0.1        // thermal-edge re-emission probability at variation 1 (1 at variation 0)
    var spriteGrid = true                  // sprites read only the grid cells under their reach (false: every point)
    var settleTau = 0.4                    // "settles fully while typing"
    var stirSettleTau: Double? = nil       // stir-and-settle relaxation; nil = from settings.coolingSeconds / 3
    var rewarmTau = 3.0                    // after typing stops
    var typingHold = 1.5                   // keys or scroll in the last 1.5 s = typing
    var snapSpeed = 0.05                   // below this, a settling point is set to rest
    var ceilingFloor = 40.0, ceilingPerRms = 2.0
    var ceilingOverride: Double? = nil     // tests only
    /// A face whose implied speed over the sweep is above this snaps (a true teleport); its points are pushed out.
    var teleportSpeed = 10_000.0
    var pushReleaseTau = 0.08              // s: a released pushed point's speed above the ceiling decays with this
    var pressHold = 0.5                    // s after a fast face's last contact that a point (and its pile) is pressed
    var spillGain = 0.8                    // tangential spill toward the nearer corner, x face speed, at full crowding
    var crowdHold = 4.0                    // s after a press that a point's coarse cell is spared by the crowding cap
    var reserveEnabled = true
    var refillTau = 3.0                    // revealed space refills with this time constant
    var regionLife = 20.0
    var maxRegions = 64
    var fadeIn = 1.0, fadeOut = 0.5
    var coarseCell = 48.0                  // thermostat, local temperature and crowding grid
    var crowdFactor = 4.0, crowdMin = 8.0, crowdEvery = 0.5
    /// Presentation while anything moves: never below presentMinFps (owner, 2026-11-08: 2-24 fps read as discrete
    /// jumps), up to the cap as the 90th-percentile displacement passes ptPerFrame. Frames interpolate between sim steps.
    var presentCapFps = 60.0, presentMinFps = 30.0, fadeFps = 30.0
    /// Owner card 2026-11-08 ~18:35 PST, "30 calm, 60 when pushed": a calm, drifting gas presents at calmFps; only
    /// while a window face pushes the gas or a moving sprite stirs it (and pushHold s after) may it go up to the cap.
    var calmFps = 30.0, pushHold = 1.0
    var ptPerFrame = 0.25
    var stillSpeed = 0.05                  // nothing faster than this: no frames at all
    // sprite stirring: entrainment along the sprite's motion within stirReach x radius, plus its body as a moving wall
    var stirReach = 3.0                    // x sprite radius
    var stirRate = 6.0                     // 1/s at the body's edge at stirring 1: how fast nearby gas picks up its speed
    var stirTrack = 0.6                    // s without a position change before a sprite's velocity estimate decays
    // sprite field (one family: a magnetic-style sideways deflection that does no work)
    var fieldOmegaMax = 1.5                // rad/s at a sprite's centre at strength 1
    var fieldReach = 4.0                   // x sprite radius
    // forces (ruling 8)
    var wellFriction = 45.0                // well friction rate = this / coolingTau (1/s; 3/s at the default cooling)
    var maxPairAccel = 600.0               // pt/s²: no pair force above this (nothing explodes)
    var maxRepelAccel = 120.0              // pt/s²: the particle-in-cell push is capped here
    var orientRate = 8.0                   // 1/s: how fast a dipole turns toward its neighbours' field at strength 1
    // knots (owner card 2026-11-08 18:30 PST): a coarse cell two different sprites' wakes reached within wakeLife s of
    // each other is a crossing; with probability `knots` it is a knot for knotLife s: capture threshold and well friction x knotGain
    var wakeLife = 6.0, knotLife = 5.0, knotGain = 4.0
    // window dew: a band dewBand x collision diameter outside a still window's face; slow dots there are pulled to the
    // face at dewPull x σ0² / band x dew and their motion damped at dewFriction x dew (1/s); a move kicks them off at dewShake x σ0
    var dewBand = 2.0, dewPull = 2.0, dewFriction = 3.0, dewShake = 0.8
    // at most (1 + dewCap x dew) x the band's even share (and at least one bead per dewSpacing pt of edge) are held, so
    // beads never close into an outline of the window
    var dewCap = 6.0, dewSpacing = 60.0
    // handedness: the curl's rate at the body's edge, rad/s at handedness 1 and a sprite speed of curlSpeed pt/s
    var curlRate = 1.2, curlSpeed = 60.0
    // wake reader: a wake counts as leftover between these ages, s
    var readerMinAge = 3.0, readerMaxAge = 30.0
}

enum AetherPhase: UInt8 { case dormant, active, fading }

// MARK: - The simulation

final class AetherSim {
    let bounds: AetherRect
    var settings: AetherSettings          // density and boundary changes need a new sim (population is set at init)
    var tuning: AetherTuning
    var rng: AetherRNG
    var time = 0.0
    var stepStartTime = 0.0

    // Point state, struct-of-arrays. Dormant slots are the reserve.
    var pos: [SIMD2<Double>]
    /// Positions at the start of the last step: frames draw lerp(prevPos, pos, interpolation) so the fixed 30 Hz
    /// step never shows. A point placed out of nowhere (seeded, injected) gets prevPos = pos.
    var prevPos: [SIMD2<Double>]
    var vel: [SIMD2<Double>]
    var alpha: [Double]
    var phase: [AetherPhase]
    var charge: [Double]
    /// Per point: the dipole orientation (unit vector) and its neighbours' field, integrated over the step.
    var orient: [SIMD2<Double>]
    var dipoleField: [SIMD2<Double>]
    /// Deterministic cost counters, cumulative (tests bound them; no clock involved).
    struct Work { var steps = 0, pointSteps = 0, pairChecks = 0, cellsTouched = 0, forceEvals = 0, globalScans = 0 }
    var work = Work()
    var subH = 0.0
    var frozen = false             // a settle to rest (floor 0): forces hold off so the gas can stop
    var rho: [Double], rhoTmp: [Double]
    /// Per point: the speed allowed above the ceiling (0 = none; set by a push, bleeds off) and the last press time.
    var boost: [Double]
    var pressedAt: [Double]
    let population: Int
    /// Designed density, points per pt² (density is defined once: settings.densityPerMpt2 / 1e6).
    let designDensity: Double

    /// covered: dormant because a window appeared on top; trapped: dormant because no free side existed; pushedOut:
    /// placed outside a window it ended up inside; pressed: contacts with a face faster than the press speed.
    struct Stats { var covered = 0, trapped = 0, pushedOut = 0, pressed = 0, seeded = 0, injected = 0, removed = 0, crowded = 0 }
    var stats = Stats()
    var heldTime = 0.0
    /// Weather fronts (aetherFronts): per coarse cell local constants, or nil (the settings everywhere).
    var fronts: AetherFronts? = nil
    func setFronts(_ f: AetherFronts?) { fronts = (f.map { $0.attraction.count == cw * ch } ?? false) ? f : nil }

    struct Wall {
        var id: Int; var from: AetherRect; var to: AetherRect; var t0: Double; var dur: Double
        var born = 0.0                    // when this id first appeared: in that substep it covers, it cannot push
        var still = 0.0                   // when its rect last changed (window dew forms after settings.dewAfterSeconds)
        func rect(_ t: Double) -> AetherRect {
            (dur <= 0 || t >= t0 + dur) ? to : AetherRect.lerp(from, to, max(0, (t - t0) / dur))
        }
    }
    var walls: [Wall] = []
    var sprites: [AetherSprite] = []
    /// Per sprite id: last seen position, when it last changed, and a smoothed velocity (hits arrive at ~10 Hz).
    struct Track { var pos: SIMD2<Double>; var changed: Double; var vel: SIMD2<Double> }
    var tracks: [String: Track] = [:]
    var spriteVel: [SIMD2<Double>] = []
    struct Region { var rect: AetherRect; var density: Double; var expires: Double; var carry: Double }
    var regions: [Region] = []
    var lastTyping = -Double.infinity
    var accumulator = 0.0
    var nextCrowdCheck = 0.0
    var edgeCarry = [Double](repeating: 0, count: 4)
    var dormantCursor = 0

    // Collision grid (cell >= collision diameter) and coarse grid.
    let cell: Double, gw: Int, gh: Int
    var cellStart: [Int], cellItems: [Int], cellOfPoint: [Int]
    var gridBuilt = false
    /// True from buildGrid until positions next change outside it (the sprite passes read it at substep start).
    var gridFresh = false
    var nearSeen: [Int], nearStamp = 0, nearBuf: [Int] = [], nearMoved: [Int] = []
    enum Thermo { case relax, rewarm, settle }
    var lastThermo = Thermo.relax
    var restSigma2 = Double.nan     // mean σ² when the last typing settle began (the rewarm's goal)
    let cc: Double, cw: Int, ch: Int
    var cCount: [Double], cSum: [SIMD2<Double>], cSum2: [Double]
    /// Knots: per coarse cell, the last sprite whose wake reached it (an id hash), when, and when two wakes last crossed.
    var wakeBy: [UInt64], wakeAt: [Double], crossAt: [Double], wakeCross: [Double]
    /// Crossings so far, and how many became knots (tests and QA).
    var crossings = 0, knotsFormed = 0
    /// One line of QA state for the host's debug log (SPRITES_DEBUG_AETHER=1): the effects a screenshot cannot show.
    var debugLine: String {
        let cells = fronts.map { f in String(format: "fronts att %.2f-%.2f", f.attraction.min() ?? 0, f.attraction.max() ?? 0) } ?? "fronts none"
        // Not `let dewy`: a local of that name shadows dewy(_:) inside its own initializer and the file stops compiling.
        let dewyCount = walls.filter { dewy($0) }.count
        return "t \(Int(time)) active \(activeCount()) pushed \(pushed) fps \(frameInterval().map { Int((1 / $0).rounded()) } ?? 0) \(cells) " +
               "dewy windows \(dewyCount) dew held \(dewHeld) shaken \(dewShaken) crossings \(crossings) knots \(knotsFormed) sprites \(sprites.count) " +
               "currents \(leftoverCurrents().count)"
    }
    /// Coarse cells where two wakes crossed in the last knotLife seconds (tests and QA).
    var knotCells: Int { crossAt.filter { time - $0 < tuning.knotLife }.count }
    /// Coarse cells that are crossings now (knotted or not).
    var crossCells: Int { wakeCross.filter { time - $0 < tuning.knotLife }.count }
    var coarseCellCount: Int { cw * ch }

    var radius: Double { settings.collisionDiameter / 2 }
    var ceiling: Double { tuning.ceilingOverride ?? max(tuning.ceilingFloor, tuning.ceilingPerRms * settings.rmsSpeed) }
    var sigma0Squared: Double { settings.rmsSpeed * settings.rmsSpeed / 2 }
    /// The floor every settle path stops at (never above the entry temperature).
    var floorSigma2: Double { let f = min(settings.minRmsSpeed, settings.rmsSpeed); return f * f / 2 }
    /// The cooling time constant: settle time / 3.
    var coolingTau: Double { max(0.1, settings.coolingSeconds / 3) }
    var isTyping: Bool { time - lastTyping < tuning.typingHold }

    init(bounds: AetherRect, settings: AetherSettings, seed: UInt64, tuning: AetherTuning = AetherTuning(),
         obstacles: [AetherObstacle] = [], population: Int? = nil) {
        self.bounds = bounds; self.settings = settings; self.tuning = tuning
        rng = AetherRNG(seed: seed)
        designDensity = settings.densityPerMpt2 / 1e6
        let pop = max(0, population ?? Int((designDensity * bounds.area).rounded()))
        let cap = max(tuning.capacity, settings.boundary == .reservoir ? 2 * pop : pop)
        self.population = pop
        pos = Array(repeating: .zero, count: cap); vel = pos; prevPos = pos
        alpha = Array(repeating: 0, count: cap); phase = Array(repeating: .dormant, count: cap)
        charge = (0..<cap).map { $0 % 2 == 0 ? 1 : -1 }
        dipoleField = Array(repeating: .zero, count: cap)
        boost = Array(repeating: 0, count: cap); pressedAt = Array(repeating: -.infinity, count: cap)
        cell = max(2 * settings.collisionDiameter, 12, AetherSettings.maxAttractionRange * settings.collisionDiameter)
        gw = max(1, Int((bounds.width / cell).rounded(.up))); gh = max(1, Int((bounds.height / cell).rounded(.up)))
        cellStart = Array(repeating: 0, count: gw * gh + 1); cellItems = Array(repeating: 0, count: cap)
        cellOfPoint = Array(repeating: 0, count: cap); nearSeen = Array(repeating: 0, count: cap)
        cc = tuning.coarseCell
        cw = max(1, Int((bounds.width / cc).rounded(.up))); ch = max(1, Int((bounds.height / cc).rounded(.up)))
        cCount = Array(repeating: 0, count: cw * ch); cSum = Array(repeating: .zero, count: cw * ch)
        cSum2 = Array(repeating: 0, count: cw * ch)
        rho = Array(repeating: 0, count: cw * ch); rhoTmp = rho
        wakeBy = Array(repeating: 0, count: cw * ch); wakeAt = Array(repeating: -.infinity, count: cw * ch); crossAt = wakeAt; wakeCross = wakeAt
        walls = obstacles.map { Wall(id: $0.id, from: $0.rect, to: $0.rect, t0: 0, dur: 0) }
        var orng = AetherRNG(seed: seed ^ 0xD1B5_4A32_D192_ED03)
        orient = (0..<cap).map { _ in let a = 2 * Double.pi * orng.uniform(); return SIMD2(cos(a), sin(a)) }
        let r = radius, s = sigma0Squared.squareRoot()
        let expanded = walls.map { $0.to.expanded(by: r) }
        let capSpeed = max(tuning.ceilingOverride ?? 0, max(tuning.ceilingFloor, tuning.ceilingPerRms * settings.rmsSpeed))
        for i in 0..<pop {
            let p = SIMD2(bounds.minX + r + rng.uniform() * (bounds.width - 2 * r),
                          bounds.minY + r + rng.uniform() * (bounds.height - 2 * r))
            var v = SIMD2(rng.gaussian(), rng.gaussian()) * s
            let l = len2(v)
            if l > capSpeed { v *= capSpeed / l }
            pos[i] = p; vel[i] = v
            if !expanded.contains(where: { $0.contains(p) }) { phase[i] = .active; alpha[i] = 1 }
        }
        prevPos = pos
    }

    // MARK: inputs

    /// A geometry sample (the geometry clock). `sweep`: seconds over which the walls travel to the new rects (pass the
    /// geometry interval in effect; 0, a reconcile, sweeps over the drag interval). Every plausible move is a sweep, at
    /// calm reads too, so points in the path are pushed. The teleport rule is PER FACE: only a face whose implied speed
    /// exceeds `teleportSpeed` snaps. A new id appears in place. Space left by any window becomes a revealed region.
    func setGeometry(_ obstacles: [AetherObstacle], sweep: Double = AetherClocks.calmGeometry) {
        let now = time
        let old = walls.map { $0.rect(now) }
        let dur = sweep > 0 ? sweep : AetherClocks.dragGeometry
        let limit = tuning.teleportSpeed * dur
        var next: [Wall] = []
        for o in obstacles {
            if let w = walls.first(where: { $0.id == o.id }) {
                let c = w.rect(now), n = o.rect
                func pick(_ a: Double, _ b: Double) -> Double { abs(a - b) <= limit ? a : b }   // a teleported face snaps
                let from = AetherRect(minX: pick(c.minX, n.minX), minY: pick(c.minY, n.minY),
                                      maxX: pick(c.maxX, n.maxX), maxY: pick(c.maxY, n.maxY))
                let moved = c != n
                if moved && dewy(w) { shakeDew(c) }   // the window moves: its dew shakes off into the gas
                let still = moved ? now : w.still
                if from != n && from.maxX > from.minX && from.maxY > from.minY {
                    next.append(Wall(id: o.id, from: from, to: n, t0: now, dur: dur, born: w.born, still: still)); continue
                }
                next.append(Wall(id: o.id, from: n, to: n, t0: now, dur: 0, born: w.born, still: still)); continue
            }
            next.append(Wall(id: o.id, from: o.rect, to: o.rect, t0: now, dur: 0, born: now, still: now))
        }
        walls = next
        guard tuning.reserveEnabled else { return }
        let minArea = 4 * settings.collisionDiameter * settings.collisionDiameter
        for f in aetherSubtract(old, obstacles.map { $0.rect }) {
            guard let r = f.intersection(bounds), r.area >= minArea else { continue }
            regions.append(Region(rect: r, density: designDensity, expires: now + tuning.regionLife, carry: 0))
        }
        if regions.count > tuning.maxRegions { regions.removeFirst(regions.count - tuning.maxRegions) }
    }

    /// Sprite circles, as often as the host likes (the same positions repeated are fine): velocity is estimated from
    /// position CHANGES per id, smoothed, and decays to zero when a sprite stops.
    func setSprites(_ s: [AetherSprite]) {
        sprites = s
        var next: [String: Track] = [:]
        spriteVel = s.map { sp in
            guard !sp.id.isEmpty else { return .zero }
            guard var t = tracks[sp.id] else { next[sp.id] = Track(pos: sp.pos, changed: time, vel: .zero); return .zero }
            let gap = time - t.changed
            if sp.pos != t.pos {
                let raw = gap > 1e-6 ? (sp.pos - t.pos) / max(gap, tuning.dt) : .zero
                let teleport = len2(sp.pos - t.pos) > 6 * max(sp.radius, 10)   // a jump (screen change, respawn) is not motion
                t.vel = teleport ? .zero : (t.vel * 0.4 + raw * 0.6)
                t.pos = sp.pos; t.changed = time
            } else if gap > tuning.stirTrack { t.vel = .zero }
            next[sp.id] = t
            return t.vel
        }
        tracks = next
    }
    /// The estimated velocity of each sprite last set (tests).
    var spriteVelocities: [SIMD2<Double>] { spriteVel }
    func noteTyping() { lastTyping = time }

    /// Tray "Stir": one gentle heat pulse at the entry temperature.
    func stir() {
        let s = max(sigma0Squared, 0.5).squareRoot()
        for i in pos.indices where phase[i] == .active { vel[i] += SIMD2(rng.gaussian(), rng.gaussian()) * s }
        enforceCeiling()
    }

    /// The simulation clock: fixed steps, at most `maxCatchUp` per call; time beyond that is held, never raced through.
    func advance(by seconds: Double, typing: Bool = false) {
        accumulator += max(0, seconds)
        var n = 0
        while accumulator >= tuning.dt && n < tuning.maxCatchUp { step(typing: typing); accumulator -= tuning.dt; n += 1 }
        if accumulator >= tuning.dt {
            let keep = accumulator.truncatingRemainder(dividingBy: tuning.dt)
            heldTime += accumulator - keep; accumulator = keep
        }
    }

    /// Fraction of a step elapsed since the last one (the accumulator), for frame interpolation.
    var interpolation: Double { min(1, max(0, accumulator / tuning.dt)) }
    /// Where a frame draws point i now: between the last two steps, by `interpolation`.
    @inline(__always) func presentedPos(_ i: Int) -> SIMD2<Double> {
        let a = interpolation; return prevPos[i] + (pos[i] - prevPos[i]) * a
    }

    /// Last time a window face pushed a dot (a contact faster than the press speed) or a moving sprite stirred the gas.
    var lastPush = -Double.infinity
    /// True while the gas is being pushed, or was within pushHold s (owner card 2026-11-08 ~18:35 PST).
    var pushed: Bool { time - lastPush < tuning.pushHold }

    /// The presentation clock: seconds to the next frame, or nil when nothing moves (hold the last frame). Follows the
    /// 90th-percentile speed (one fast outlier cannot raise it), clamped to [presentMinFps, cap]; the cap is calmFps
    /// unless the gas is pushed (owner card 2026-11-08 ~18:35 PST: "30 calm, 60 when pushed").
    func frameInterval(capFps: Double? = nil) -> Double? {
        var speeds: [Double] = []; speeds.reserveCapacity(population)
        var fading = false, vmax = 0.0
        for i in pos.indices {
            switch phase[i] {
            case .active: let v = len2(vel[i]); speeds.append(v); vmax = max(vmax, v); if alpha[i] < 1 { fading = true }
            case .fading: fading = true
            case .dormant: break
            }
        }
        if vmax < tuning.stillSpeed && !fading { return nil }
        speeds.sort()
        let v90 = speeds.isEmpty ? 0 : speeds[min(speeds.count - 1, Int(0.9 * Double(speeds.count)))]
        var fps = v90 / tuning.ptPerFrame
        if fading { fps = max(fps, tuning.fadeFps) }
        let cap = min(capFps ?? tuning.presentCapFps, pushed ? tuning.presentCapFps : tuning.calmFps)
        fps = min(cap, max(min(tuning.presentMinFps, cap), fps))
        return 1 / fps
    }

    // MARK: test and QA hooks

    /// Activate a dormant slot at p with velocity v (QA: "leave one fast point alive").
    @discardableResult func injectPoint(at p: SIMD2<Double>, velocity v: SIMD2<Double>) -> Int? {
        guard let i = dormantSlot() else { return nil }
        pos[i] = p; prevPos[i] = p; vel[i] = v; phase[i] = .active; alpha[i] = 1
        boost[i] = 0; pressedAt[i] = -.infinity
        return i
    }

    var currentWallRects: [AetherRect] { walls.map { $0.rect(time) } }
    func activeCount(in r: AetherRect? = nil) -> Int {
        var n = 0
        for i in pos.indices where phase[i] == .active && (r?.contains(pos[i]) ?? true) { n += 1 }
        return n
    }
    /// Mean per-component velocity variance of active points (in a rect, if given), not flow-relative.
    func meanSigma2(in r: AetherRect? = nil) -> Double {
        work.globalScans += 1
        var s = 0.0, n = 0.0
        for i in pos.indices where phase[i] == .active && (r?.contains(pos[i]) ?? true) { s += dot2(vel[i], vel[i]) / 2; n += 1 }
        return n > 0 ? s / n : 0
    }
    /// True if an active point sits inside any (collision-expanded) wall: a missed sweep or an invalid placement.
    func activeInsideWall(_ i: Int) -> Bool {
        let r = radius
        return phase[i] == .active && walls.contains { $0.rect(time).expanded(by: r).contains(pos[i]) }
    }
    /// The attraction cutoff, pt, and the well depth, pt²/s².
    var attractionCutoff: Double { settings.attractionRange * settings.collisionDiameter }
    var wellDepth: Double { settings.attraction * max(sigma0Squared, 0.5) }

    /// Bonds as the forces make them (tests and QA): pairs closer than the well's midpoint. Mean bonded neighbours per
    /// point; chains = components joined by head-to-tail bonds (pair dipole factor (3ab - m_i.m_j)/2 above 0.5:
    /// 1 is head-to-tail, -0.5 side-by-side), their mean size (components of 2+); cluster centroids = components of 3+ joined by any bond.
    func bondStats() -> (neighbours: Double, chainLength: Double, chains: Int, clusters: [SIMD2<Double>]) {
        buildGrid()
        let D = settings.collisionDiameter, lim = D + 0.5 * (attractionCutoff - D), lim2 = lim * lim
        var any = Array(0..<pos.count), head = any
        func find(_ u: inout [Int], _ x: Int) -> Int { var r = x; while u[r] != r { r = u[r] }; var y = x; while u[y] != r { let n = u[y]; u[y] = r; y = n }; return r }
        var nb = 0, n = 0
        for i in pos.indices where phase[i] == .active {
            n += 1
            let c = cellIndex(pos[i]), cx = c % gw, cy = c / gw
            for oy in -1...1 { for ox in -1...1 {
                let nx = cx + ox, ny = cy + oy
                guard nx >= 0, nx < gw, ny >= 0, ny < gh else { continue }
                let m = ny * gw + nx
                for b in cellStart[m]..<cellStart[m + 1] {
                    let j = cellItems[b]; guard j != i else { continue }
                    let dv = pos[j] - pos[i], d2 = dot2(dv, dv); guard d2 < lim2 else { continue }
                    nb += 1
                    guard j > i else { continue }
                    let ra = find(&any, i), rb = find(&any, j); if ra != rb { any[ra] = rb }
                    let rh = dv / max(d2.squareRoot(), 1e-9), a = dot2(orient[i], rh), bb = dot2(orient[j], rh)
                    if (3 * a * bb - dot2(orient[i], orient[j])) / 2 > 0.5 { let ha = find(&head, i), hb = find(&head, j); if ha != hb { head[ha] = hb } }
                }
            } }
        }
        var hs: [Int: Int] = [:], cs: [Int: (Int, SIMD2<Double>)] = [:]
        for i in pos.indices where phase[i] == .active {
            hs[find(&head, i), default: 0] += 1
            let r = find(&any, i), e = cs[r] ?? (0, .zero); cs[r] = (e.0 + 1, e.1 + pos[i])
        }
        let ch = hs.values.filter { $0 >= 2 }
        let cl = cs.values.filter { $0.0 >= 3 }.map { $0.1 / Double($0.0) }
        return (n > 0 ? Double(nb) / Double(n) : 0, ch.isEmpty ? 0 : Double(ch.reduce(0, +)) / Double(ch.count), ch.count, cl)
    }

    // MARK: window dew (owner card 2026-11-08 18:30 PST)

    /// A real window (not the menu-bar or Dock band) that has stood still long enough for dew.
    func dewy(_ w: Wall) -> Bool { settings.dew > 0 && w.id >= 0 && time >= w.t0 + w.dur && time - w.still >= settings.dewAfterSeconds }
    /// Dots held by dew in the last step (tests and QA readout).
    var dewHeld = 0, dewShaken = 0

    /// Distance from p to the outside of R (0 inside), and the outward normal of the nearest face.
    @inline(__always) static func outside(_ p: SIMD2<Double>, _ R: AetherRect) -> (Double, SIMD2<Double>) {
        let dx = max(R.minX - p.x, 0, p.x - R.maxX), dy = max(R.minY - p.y, 0, p.y - R.maxY)
        if dx > 0 && dy > 0 { let d = (dx * dx + dy * dy).squareRoot(); return (d, SIMD2(p.x < R.minX ? -dx : dx, p.y < R.minY ? -dy : dy) / d) }
        if dx > 0 { return (dx, SIMD2(p.x < R.minX ? -1 : 1, 0)) }
        if dy > 0 { return (dy, SIMD2(0, p.y < R.minY ? -1 : 1)) }
        return (0, .zero)
    }

    /// Dew: a slow dot in the band outside a still window's face is pulled onto the face and its motion damped, as a
    /// weak adhesion (only a dot whose speed is under the band's capture speed is held, so the fast gas passes by).
    /// O(N x still windows) once per step, nothing while no window is still long enough.
    func dewStep(_ dt: Double) {
        dewHeld = 0
        let still = walls.filter { dewy($0) }
        guard !still.isEmpty else { return }
        let r = radius, band = tuning.dewBand * settings.collisionDiameter, s2 = max(sigma0Squared, 0.5)
        let pull = tuning.dewPull * settings.dew * s2 / band, capture2 = 2 * settings.dew * s2
        let damp = exp(-tuning.dewFriction * settings.dew * dt)
        let rects = still.map { $0.to.expanded(by: r) }
        // The band's occupancy first: a band already holding its share is full, and holds nothing more this step (the
        // attraction keeps a cold bead gathering partners, so a per-dot cap alone let the edge fill into an outline).
        var count = [Double](repeating: 0, count: rects.count), inBand = [Int](repeating: -1, count: 0)
        inBand.reserveCapacity(64)
        for i in pos.indices where phase[i] == .active {
            for (w, R) in rects.enumerated() {
                let (d, _) = AetherSim.outside(pos[i], R)
                if d > 0 && d < band { count[w] += 1; inBand.append(i); break }
            }
        }
        let full = rects.indices.map { w -> Bool in
            let edge = 2 * (rects[w].width + rects[w].height)
            return count[w] >= (1 + tuning.dewCap * settings.dew) * max(edge * band * designDensity, edge / tuning.dewSpacing)
        }
        for i in inBand {
            for (w, R) in rects.enumerated() {
                let (d, n) = AetherSim.outside(pos[i], R)
                guard d > 0, d < band else { continue }
                let u = vel[i], un = dot2(u, n)
                guard dot2(u, u) < capture2, !full[w] else { break }   // a fast dot is not held; a full edge holds none
                vel[i] = (u - n * un) * damp + n * (min(un, 0) * damp) - n * (pull * (1 - d / band) * dt)
                dewHeld += 1; work.forceEvals += 1
                break
            }
        }
    }

    /// A dewy window moved (seen at a geometry read): the dots beaded on its old edges shake off into the gas.
    func shakeDew(_ old: AetherRect) {
        let r = radius, band = tuning.dewBand * settings.collisionDiameter, R = old.expanded(by: r)
        let kick = tuning.dewShake * max(sigma0Squared, 0.5).squareRoot()
        for i in pos.indices where phase[i] == .active {
            let (d, n) = AetherSim.outside(pos[i], R)
            guard d > 0, d < band else { continue }
            vel[i] += n * (kick * rng.rayleigh()) + SIMD2(-n.y, n.x) * (kick * rng.gaussian())
            dewShaken += 1
        }
        enforceCeiling()
    }

    /// "Wake reader" (owner card 2026-11-08 18:30 PST): the leftover current near p that ANOTHER sprite left, pt/s:
    /// the mean flow of the coarse cells within `radius` whose last wake was not this sprite's and is between
    /// readerMinAge and readerMaxAge seconds old (left behind, so its maker has moved on), weighted by their dots. nil
    /// when there is none. The stage nudges an idle sprite a little along it, rarely. O(cells in the patch).
    func leftoverCurrent(at p: SIMD2<Double>, radius: Double = 80, excluding id: String) -> SIMD2<Double>? {
        buildCoarse(); return leftover(p, radius, id)
    }
    /// Every sprite's leftover current (one coarse build for all), by sprite id; sprites with none are left out.
    func leftoverCurrents(radius: Double = 80) -> [String: SIMD2<Double>] {
        buildCoarse()
        var out: [String: SIMD2<Double>] = [:]
        for s in sprites where !s.id.isEmpty { if let v = leftover(s.pos, radius, s.id) { out[s.id] = v } }
        return out
    }
    func leftover(_ p: SIMD2<Double>, _ radius: Double, _ id: String) -> SIMD2<Double>? {
        guard p.x.isFinite, p.y.isFinite else { return nil }
        let me = id.utf8.reduce(0xCBF2_9CE4_8422_2325 as UInt64) { ($0 ^ UInt64($1)) &* 0x100_0000_01B3 }
        func cl(_ v: Double, _ n: Int) -> Int { Int(min(Double(n - 1), max(0, v))) }
        let x0 = cl((p.x - radius - bounds.minX) / cc, cw), x1 = cl((p.x + radius - bounds.minX) / cc, cw)
        let y0 = cl((p.y - radius - bounds.minY) / cc, ch), y1 = cl((p.y + radius - bounds.minY) / cc, ch)
        var v = SIMD2<Double>.zero, n = 0.0
        for y in y0...y1 { for x in x0...x1 {
            let c = y * cw + x, age = time - wakeAt[c]
            guard wakeBy[c] != me, age >= tuning.readerMinAge, age <= tuning.readerMaxAge, cCount[c] > 0 else { continue }
            v += cSum[c]; n += cCount[c]
        } }
        return n >= 2 ? v / n : nil
    }

    /// Knots: the coarse cells under a moving sprite's stir reach remember it; a cell another sprite's wake reached
    /// less than wakeLife s ago becomes a crossing. O(cells under the reach) per moving sprite per substep.
    func markWake(_ s: AetherSprite, _ R: Double) {
        let id = s.id.utf8.reduce(0xCBF2_9CE4_8422_2325 as UInt64) { ($0 ^ UInt64($1)) &* 0x100_0000_01B3 }
        func cl(_ v: Double, _ n: Int) -> Int { Int(min(Double(n - 1), max(0, v))) }
        let x0 = cl((s.pos.x - R - bounds.minX) / cc, cw), x1 = cl((s.pos.x + R - bounds.minX) / cc, cw)
        let y0 = cl((s.pos.y - R - bounds.minY) / cc, ch), y1 = cl((s.pos.y + R - bounds.minY) / cc, ch)
        guard s.pos.x.isFinite, s.pos.y.isFinite else { return }
        for y in y0...y1 { for x in x0...x1 {
            let c = y * cw + x
            if settings.knots > 0 && wakeBy[c] != id && time - wakeAt[c] < tuning.wakeLife && time - wakeCross[c] >= tuning.knotLife {
                // a new crossing here: a knot with probability `knots`, rolled from the cell and the moment (seeded,
                // and it leaves the main random stream alone)
                crossings += 1; wakeCross[c] = time
                var r = AetherRNG(seed: UInt64(c) &* 0x9E37_79B9_7F4A_7C15 ^ UInt64(bitPattern: Int64((time * 30).rounded())))
                if r.uniform() < settings.knots { crossAt[c] = time; knotsFormed += 1 }
            }
            wakeBy[c] = id; wakeAt[c] = time
            work.cellsTouched += 1
        } }
    }

    /// One field family for release 1: a sideways (magnetic-style) deflection near each sprite, an exact rotation of
    /// the velocity (does no work, like the Boris push), ω = strength x ωmax x (a²/(d²+a²))^{3/2} x q, faded to 0 at
    /// fieldReach x radius. Opposite charges curl opposite ways: two counter-curling wakes.
    func applyField(_ h: Double) {
        let wmax = tuning.fieldOmegaMax * settings.fieldStrength
        for s in sprites {
            let a = max(s.radius, 1), R = tuning.fieldReach * a, R2 = R * R
            func touch(_ i: Int) {
                let dv = pos[i] - s.pos, d2 = dot2(dv, dv)
                guard d2 < R2 else { return }
                let f = a * a / (d2 + a * a)
                let theta = wmax * f * f.squareRoot() * charge[i] * h * (1 - d2 / R2)
                let c = cos(theta), sn = sin(theta), v = vel[i]
                vel[i] = SIMD2(c * v.x - sn * v.y, sn * v.x + c * v.y)
            }
            if gatherNear(s.pos, R) { for i in nearBuf { touch(i) } }
            else { for i in pos.indices where phase[i] == .active { touch(i) } }
        }
    }
}
