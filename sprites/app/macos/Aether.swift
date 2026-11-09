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
///     catch-up, `advance`), presentation (`frameInterval`, from the 90th-percentile speed, capped).
///  3. Strict speed ceiling, with one exception: windows PUSH (owner ruling, 2026-11-08, "Push, replace wipe"). A face
///     faster than the ceiling carries the point on it at the face's normal speed (no 2w bounce), tangential speed
///     kept; a pressed point may exceed the ceiling only while pressed, and its excess bleeds off in `pushReleaseTau`
///     once free. Pressed points collide inelastically (the pile moves as one) and are pushed toward the face's
///     nearer corner in proportion to local crowding, so a pile spills round the window; the crowding cap spares
///     them. The old absorb-above-ceiling rule (the "wipe") is gone.
///  4. Revealed-space reserve: exposed desktop is reseeded gently from the dormant pool at the gas's temperature.
///  5. Thermostat is an artistic control: an Ornstein-Uhlenbeck relaxation of velocity relative to the LOCAL flow
///     (a drifting cloud is not "hot"), a separate flow damping, a fast damping for hot trapped pockets, and thermal
///     screen edges as the heat bath.
///  6. Density is defined once, per million logical square points; population = density x screen area; points under
///     windows are dormant, so a covered region's share is what the reserve gives back.
///  9. Chains of 2-5 (release 1, owner ruling 5): straightening constraint, temperature-dependent stochastic lifetime
///     with a hard cap, momentum conserved at bonding, bounded momentum-free release at breakup, a capped count and a
///     formation opportunity every 20-60 s (rare).

// MARK: - Settings (behaviors.json "aether": {...})

enum AetherMotion: String { case living, settleWhileTyping = "settle-typing", stirAndSettle = "stir-settle" }
enum AetherBoundary: String { case thermal, reflect, reservoir }
enum AetherChains: String {
    case never, rare, sometimes, often
    var maxAlive: Int { self == .never ? 0 : (self == .often ? 3 : 2) }
    /// Seconds between chances for a NEW chain (uniform in the range).
    var formationWindow: (Double, Double) {
        switch self { case .never: return (.infinity, .infinity); case .rare: return (20, 60)
                      case .sometimes: return (10, 30); case .often: return (5, 15) }
    }
}

struct AetherSettings: Equatable {
    /// Owner ruling 1: all three ship; default "living, settles while typing" until he has seen it.
    var motion: AetherMotion = .settleWhileTyping
    /// Owner ruling 2: thermal walls.
    var boundary: AetherBoundary = .thermal
    /// Entry temperature as an RMS speed, pt/s: frozen 0.5 / cool 3 / mild 8 / warm 16 / hot 28. Default 27.5, the
    /// owner's own setting (2026-11-08: Cool was "way too slow"; "it reads much better now" after he raised it).
    var rmsSpeed = 27.5
    /// Points per million logical pt²: sparse 100 (~150 on a 14" laptop) / medium 270 (~400) / dense 1000 (~1 500).
    var densityPerMpt2 = 100.0
    /// Drawn core DIAMETER, pt (preset follows density: 2.5 / 2 / 1.5). Rendering only.
    var particleDiameter = 2.5
    /// Collision diameter, pt, separate from the drawn core (merge correction 7: 3-4 pt).
    var collisionDiameter = 3.5
    var chains: AetherChains = .rare
    /// Sprite field strength: off 0 / subtle 0.5 / vivid 1 (0-2).
    var fieldStrength = 0.5
    /// "Sprite stirring": a moving sprite drags nearby gas along its path and pushes it out of its body, leaving a wake
    /// that settles under Cooling (owner, 2026-11-08: sprites should "stir it with their passing"). off 0 / subtle 0.5 /
    /// strong 1.2 (0-2); default between subtle and moderate.
    var stirring = 0.7
    /// "Cooling (drag)": seconds for a disturbance to settle (about 3 time constants). Drives stir-and-settle's
    /// relaxation and the flow damping (wakes glide). Owner, 2026-11-08: "some drag but quite slow". 5-120.
    var coolingSeconds = 45.0
    /// "Minimum temperature": RMS speed, pt/s, below which no settle path cools the gas (owner, 2026-11-08: frozen
    /// "looks almost like something's wrong"). Typing still calms it, to here. 0 = may freeze (the old behaviour).
    var minRmsSpeed = 1.5
    var colour = "green"            // green | amber | white, or "#rrggbb" from the colour picker (rendering)
    var brightness = 2              // 1-3 (rendering)

    static let temperatures: [String: Double] = ["frozen": 0.5, "cool": 3, "mild": 8, "warm": 16, "hot": 28]
    static let densities: [String: (Double, Double)] = ["sparse": (100, 2.5), "medium": (270, 2.0), "dense": (1000, 1.5)]
    static let strengths: [String: Double] = ["off": 0, "subtle": 0.5, "vivid": 1]
    static let stirrings: [String: Double] = ["off": 0, "subtle": 0.5, "moderate": 0.8, "strong": 1.2]

    /// The "aether" object of a behaviors.json dictionary; anything missing, unknown or of the wrong type is the default.
    static func from(_ top: [String: Any]?) -> AetherSettings {
        var s = AetherSettings()
        guard let o = top?["aether"] as? [String: Any] else { return s }
        func clamp(_ v: Double, _ lo: Double, _ hi: Double) -> Double { min(hi, max(lo, v)) }
        if let v = (o["motion"] as? String).flatMap(AetherMotion.init(rawValue:)) { s.motion = v }
        if let v = (o["boundary"] as? String).flatMap(AetherBoundary.init(rawValue:)) { s.boundary = v }
        if let v = (o["chains"] as? String).flatMap(AetherChains.init(rawValue:)) { s.chains = v }
        if let n = jsonNumber(o["temperature"]) { s.rmsSpeed = clamp(n, 0, 40) }
        else if let k = o["temperature"] as? String, let v = temperatures[k] { s.rmsSpeed = v }
        var preset: Double? = nil
        if let n = jsonNumber(o["density"]) { s.densityPerMpt2 = clamp(n, 0, 2000); preset = 2.0 }
        else if let k = o["density"] as? String, let v = densities[k] { s.densityPerMpt2 = v.0; preset = v.1 }
        if let n = jsonNumber(o["particleSize"]) { s.particleDiameter = clamp(n, 0.5, 6) }
        else if let p = preset { s.particleDiameter = p }
        if let n = jsonNumber(o["collisionSize"]) { s.collisionDiameter = clamp(n, 2, 8) }
        if let n = jsonNumber(o["stirring"]) { s.stirring = clamp(n, 0, 2) }
        else if let k = o["stirring"] as? String, let v = stirrings[k] { s.stirring = v }
        if let n = jsonNumber(o["cooling"]) { s.coolingSeconds = clamp(n, 5, 120) }
        if let n = jsonNumber(o["minTemperature"]) { s.minRmsSpeed = clamp(n, 0, 10) }
        if let n = jsonNumber(o["fieldStrength"]) { s.fieldStrength = clamp(n, 0, 2) }
        else if let k = o["fieldStrength"] as? String, let v = strengths[k] { s.fieldStrength = v }
        if let c = o["colour"] as? String, ["green", "amber", "white"].contains(c) || aetherHex(c) != nil { s.colour = c.lowercased() }
        if let n = jsonNumber(o["brightness"]) { s.brightness = Int(clamp(n.rounded(), 1, 3)) }
        return s
    }

    /// The colour as linear-ish RGB 0-1 (presets are the phosphor tones; a hex is taken as given).
    var rgb: SIMD3<Double> {
        switch colour {
        case "amber": return SIMD3(1.0, 0.68, 0.18)
        case "white": return SIMD3(0.82, 0.88, 0.92)
        case "green": return SIMD3(0.28, 1.0, 0.45)   // phosphor green
        default: return aetherHex(colour) ?? SIMD3(0.28, 1.0, 0.45)
        }
    }

    static func parse(behaviorsJSON: String) -> AetherSettings {
        guard let d = behaviorsJSON.data(using: .utf8),
              let o = try? JSONSerialization.jsonObject(with: d) as? [String: Any] else { return AetherSettings() }
        return from(o)
    }
}

/// "#rrggbb" (case-insensitive) as RGB 0-1, else nil.
func aetherHex(_ s: String) -> SIMD3<Double>? {
    let h = Array(s.utf8)
    guard h.count == 7, h[0] == UInt8(ascii: "#"), let v = UInt32(String(s.dropFirst()), radix: 16) else { return nil }
    return SIMD3(Double((v >> 16) & 0xff), Double((v >> 8) & 0xff), Double(v & 0xff)) / 255
}

/// The Aether is on: the Settings tab's switch, behaviors.json "aether": {"enabled": true}, or "backdrop": "aether".
/// While on it replaces the moving backdrops (the chosen backdrop comes back when it is switched off).
func aetherSelected(behaviorsJSON: String) -> Bool {
    guard let d = behaviorsJSON.data(using: .utf8),
          let o = try? JSONSerialization.jsonObject(with: d) as? [String: Any] else { return false }
    // A JSON true only: JSONSerialization's 1 also casts to Bool; only the CFBoolean singletons are Booleans.
    guard (o["backdrop"] as? String) != "aether" else { return true }
    guard let n = (o["aether"] as? [String: Any])?["enabled"] as? NSNumber, CFGetTypeID(n) == CFBooleanGetTypeID() else { return false }
    return n.boolValue
}

// MARK: - Quiet behaviour and the geometry clock (pure decisions for the host)

enum AetherQuiet: Equatable { case off, still, draw(fpsCap: Double) }

/// Merge "quiet behaviour": hidden, meeting mode, locked and covered draw nothing; Reduce Motion, Low Power, battery
/// under 20 % and thermal Serious/Critical hold a still frame. thermal: ProcessInfo.ThermalState.rawValue (0-3).
func aetherQuietPlan(hidden: Bool, meeting: Bool, locked: Bool, covered: Bool, reduceMotion: Bool, lowPower: Bool,
                     batteryBelow20: Bool, thermal: Int) -> AetherQuiet {
    if hidden || meeting || locked || covered { return .off }
    if reduceMotion || lowPower || batteryBelow20 || thermal >= 2 { return .still }
    return .draw(fpsCap: thermal == 1 ? 30 : 60)
}

enum AetherClocks {
    static let calmGeometry = 0.5, dragGeometry = 1.0 / 12
    /// Seconds until the next window-geometry read: 2 Hz calm, 12 Hz while the drag monitor sees a drag, at once on app
    /// activation or a Space change (`reconcile`).
    static func geometryInterval(dragging: Bool, reconcile: Bool) -> Double {
        reconcile ? 0 : (dragging ? dragGeometry : calmGeometry)
    }
}

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
struct AetherSprite {
    var pos: SIMD2<Double>; var radius: Double; var id = ""
    init(pos: SIMD2<Double>, radius: Double, id: String = "") { self.pos = pos; self.radius = radius; self.id = id }
}

@inline(__always) private func dot2(_ a: SIMD2<Double>, _ b: SIMD2<Double>) -> Double { a.x * b.x + a.y * b.y }
@inline(__always) private func len2(_ a: SIMD2<Double>) -> Double { (a.x * a.x + a.y * a.y).squareRoot() }

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
    var ptPerFrame = 0.25
    var stillSpeed = 0.05                  // nothing faster than this: no frames at all
    // chains
    var chainMaxLength = 5, chainSpan = 60.0, bondLengthFactor = 1.15
    var bondSpeedFraction = 0.6            // bond only below 0.6 x the entry RMS speed (relative)
    var growProbability = 0.5
    var chainCap = 20.0, chainTau0 = 8.0, chainTauMin = 4.0, chainTauMax = 12.0
    var straighten = 0.1, constraintIterations = 3
    var releaseFraction = 0.3, releaseMaxFraction = 0.5
    // sprite stirring: entrainment along the sprite's motion within stirReach x radius, plus its body as a moving wall
    var stirReach = 3.0                    // x sprite radius
    var stirRate = 6.0                     // 1/s at the body's edge at stirring 1: how fast nearby gas picks up its speed
    var stirTrack = 0.6                    // s without a position change before a sprite's velocity estimate decays
    // sprite field (one family: a magnetic-style sideways deflection that does no work)
    var fieldOmegaMax = 1.5                // rad/s at a sprite's centre at strength 1
    var fieldReach = 4.0                   // x sprite radius
}

enum AetherPhase: UInt8 { case dormant, active, fading }

// MARK: - The simulation

final class AetherSim {
    let bounds: AetherRect
    var settings: AetherSettings          // density and boundary changes need a new sim (population is set at init)
    var tuning: AetherTuning
    private var rng: AetherRNG
    private(set) var time = 0.0

    // Point state, struct-of-arrays. Dormant slots are the reserve.
    private(set) var pos: [SIMD2<Double>]
    /// Positions at the start of the last step: frames draw lerp(prevPos, pos, interpolation) so the fixed 30 Hz
    /// step never shows. A point placed out of nowhere (seeded, injected) gets prevPos = pos.
    private(set) var prevPos: [SIMD2<Double>]
    private(set) var vel: [SIMD2<Double>]
    private(set) var alpha: [Double]
    private(set) var phase: [AetherPhase]
    private(set) var charge: [Double]
    private(set) var chainOf: [Int]
    /// Per point: the speed allowed above the ceiling (0 = none; set by a push, bleeds off) and the last press time.
    private(set) var boost: [Double]
    private var pressedAt: [Double]
    let population: Int
    /// Designed density, points per pt² (density is defined once: settings.densityPerMpt2 / 1e6).
    let designDensity: Double

    struct Chain { var members: [Int]; var born: Double }
    private(set) var chains: [Chain?] = []
    var nextFormation: Double

    /// covered: dormant because a window appeared on top; trapped: dormant because no free side existed; pushedOut:
    /// placed outside a window it ended up inside; pressed: contacts with a face faster than the press speed.
    struct Stats { var covered = 0, trapped = 0, pushedOut = 0, pressed = 0, seeded = 0, injected = 0, removed = 0, crowded = 0
                   var bonds = 0, breaks = 0; var lifetimes: [Double] = [] }
    private(set) var stats = Stats()
    private(set) var heldTime = 0.0

    private struct Wall {
        var id: Int; var from: AetherRect; var to: AetherRect; var t0: Double; var dur: Double
        var born = 0.0                    // when this id first appeared: in that substep it covers, it cannot push
        func rect(_ t: Double) -> AetherRect {
            (dur <= 0 || t >= t0 + dur) ? to : AetherRect.lerp(from, to, max(0, (t - t0) / dur))
        }
    }
    private var walls: [Wall] = []
    private var sprites: [AetherSprite] = []
    /// Per sprite id: last seen position, when it last changed, and a smoothed velocity (hits arrive at ~10 Hz).
    private struct Track { var pos: SIMD2<Double>; var changed: Double; var vel: SIMD2<Double> }
    private var tracks: [String: Track] = [:]
    private var spriteVel: [SIMD2<Double>] = []
    private struct Region { var rect: AetherRect; var density: Double; var expires: Double; var carry: Double }
    private var regions: [Region] = []
    private var lastTyping = -Double.infinity
    private var accumulator = 0.0
    private var nextCrowdCheck = 0.0
    private var edgeCarry = [Double](repeating: 0, count: 4)
    private var dormantCursor = 0

    // Collision grid (cell >= collision diameter) and coarse grid.
    private let cell: Double, gw: Int, gh: Int
    private var cellStart: [Int], cellItems: [Int], cellOfPoint: [Int]
    private var gridBuilt = false
    private let cc: Double, cw: Int, ch: Int
    private var cCount: [Double], cSum: [SIMD2<Double>], cSum2: [Double]

    var radius: Double { settings.collisionDiameter / 2 }
    var ceiling: Double { tuning.ceilingOverride ?? max(tuning.ceilingFloor, tuning.ceilingPerRms * settings.rmsSpeed) }
    private var sigma0Squared: Double { settings.rmsSpeed * settings.rmsSpeed / 2 }
    /// The floor every settle path stops at (never above the entry temperature).
    private var floorSigma2: Double { let f = min(settings.minRmsSpeed, settings.rmsSpeed); return f * f / 2 }
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
        chainOf = Array(repeating: -1, count: cap)
        boost = Array(repeating: 0, count: cap); pressedAt = Array(repeating: -.infinity, count: cap)
        cell = max(2 * settings.collisionDiameter, 12)
        gw = max(1, Int((bounds.width / cell).rounded(.up))); gh = max(1, Int((bounds.height / cell).rounded(.up)))
        cellStart = Array(repeating: 0, count: gw * gh + 1); cellItems = Array(repeating: 0, count: cap)
        cellOfPoint = Array(repeating: 0, count: cap)
        cc = tuning.coarseCell
        cw = max(1, Int((bounds.width / cc).rounded(.up))); ch = max(1, Int((bounds.height / cc).rounded(.up)))
        cCount = Array(repeating: 0, count: cw * ch); cSum = Array(repeating: .zero, count: cw * ch)
        cSum2 = Array(repeating: 0, count: cw * ch)
        nextFormation = 0
        walls = obstacles.map { Wall(id: $0.id, from: $0.rect, to: $0.rect, t0: 0, dur: 0) }
        nextFormation = drawFormationTime()
        let r = radius, s = sigma0Squared.squareRoot()
        let expanded = walls.map { $0.to.expanded(by: r) }
        for i in 0..<pop {
            let p = SIMD2(bounds.minX + r + rng.uniform() * (bounds.width - 2 * r),
                          bounds.minY + r + rng.uniform() * (bounds.height - 2 * r))
            pos[i] = p; vel[i] = SIMD2(rng.gaussian(), rng.gaussian()) * s
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
                if from != n && from.maxX > from.minX && from.maxY > from.minY {
                    next.append(Wall(id: o.id, from: from, to: n, t0: now, dur: dur, born: w.born)); continue
                }
                next.append(Wall(id: o.id, from: n, to: n, t0: now, dur: 0, born: w.born)); continue
            }
            next.append(Wall(id: o.id, from: o.rect, to: o.rect, t0: now, dur: 0, born: now))
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

    /// The presentation clock: seconds to the next frame, or nil when nothing moves (hold the last frame). Follows the
    /// 90th-percentile speed (one fast outlier cannot raise it), clamped to [presentMinFps, cap].
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
        fps = min(capFps ?? tuning.presentCapFps, max(tuning.presentMinFps, fps))
        return 1 / fps
    }

    // MARK: test and QA hooks

    /// Activate a dormant slot at p with velocity v (QA: "leave one fast point alive").
    @discardableResult func injectPoint(at p: SIMD2<Double>, velocity v: SIMD2<Double>) -> Int? {
        guard let i = dormantSlot() else { return nil }
        pos[i] = p; prevPos[i] = p; vel[i] = v; phase[i] = .active; alpha[i] = 1; chainOf[i] = -1
        boost[i] = 0; pressedAt[i] = -.infinity
        return i
    }

    /// Bond these active, free points into one chain (tests: rules after formation).
    @discardableResult func formChain(_ members: [Int]) -> Bool {
        guard (2...tuning.chainMaxLength).contains(members.count),
              members.allSatisfy({ phase[$0] == .active && chainOf[$0] < 0 }) else { return false }
        newChain(members); return true
    }

    func breakChainForTest(_ c: Int) { if chains.indices.contains(c), chains[c] != nil { breakChain(c, release: true) } }

    var aliveChains: Int { chains.reduce(0) { $0 + ($1 == nil ? 0 : 1) } }
    var currentWallRects: [AetherRect] { walls.map { $0.rect(time) } }
    func activeCount(in r: AetherRect? = nil) -> Int {
        var n = 0
        for i in pos.indices where phase[i] == .active && (r?.contains(pos[i]) ?? true) { n += 1 }
        return n
    }
    /// Mean per-component velocity variance of active points (in a rect, if given), not flow-relative.
    func meanSigma2(in r: AetherRect? = nil) -> Double {
        var s = 0.0, n = 0.0
        for i in pos.indices where phase[i] == .active && (r?.contains(pos[i]) ?? true) { s += dot2(vel[i], vel[i]) / 2; n += 1 }
        return n > 0 ? s / n : 0
    }
    /// True if an active point sits inside any (collision-expanded) wall: a missed sweep or an invalid placement.
    func activeInsideWall(_ i: Int) -> Bool {
        let r = radius
        return phase[i] == .active && walls.contains { $0.rect(time).expanded(by: r).contains(pos[i]) }
    }
    /// The bond rest length.
    var bondLength: Double { tuning.bondLengthFactor * settings.collisionDiameter }

    // MARK: the step

    func step(typing: Bool = false) {
        let dt = tuning.dt
        if typing { lastTyping = time }
        prevPos = pos
        let (target, tau) = motionTarget()
        var vmax = 0.0
        for i in pos.indices where phase[i] == .active { vmax = max(vmax, dot2(vel[i], vel[i])) }
        vmax = vmax.squareRoot()
        let k = min(tuning.maxSubsteps, max(1, Int((vmax * dt / (0.5 * settings.collisionDiameter)).rounded(.up))))
        let h = dt / Double(k)
        for _ in 0..<k { substep(h, edgeSigma2: target); time += h }
        thermostat(dt, sigma2: target, tau: tau)
        releaseBoost(dt)
        fades(dt)
        seedRegions(dt)
        if settings.boundary == .reservoir { injectEdges(dt, sigma2: target) }
        crowding()
        chainLifetimes(dt)
    }

    /// (target σ², relaxation τ) for the motion style. Settling targets the floor, never below it.
    private func motionTarget() -> (Double, Double) {
        let s2 = sigma0Squared, lo = floorSigma2
        let modeTau = tuning.thermostatTau ?? (settings.boundary == .reflect ? 60 : 20)
        switch settings.motion {
        case .living: return (s2, modeTau)
        case .settleWhileTyping:
            let since = time - lastTyping
            if since < tuning.typingHold { return (lo, tuning.settleTau) }
            if since < tuning.typingHold + 3 * tuning.rewarmTau { return (s2, min(modeTau, tuning.rewarmTau)) }
            return (s2, modeTau)
        case .stirAndSettle: return (lo, tuning.stirSettleTau ?? coolingTau)
        }
    }

    private func substep(_ h: Double, edgeSigma2: Double) {
        let r = radius
        let A = walls.map { $0.rect(time).expanded(by: r) }
        let B = walls.map { $0.rect(time + h).expanded(by: r) }
        if settings.fieldStrength > 0 && !sprites.isEmpty { applyField(h) }
        if settings.stirring > 0 && !sprites.isEmpty { applyStirring(h) }
        for i in pos.indices where phase[i] == .active { sweepMove(i, h, A, B) }
        for i in pos.indices where phase[i] == .active { screenEdge(i, edgeSigma2) }
        buildGrid()
        collide()
        constrainChains()
        validate(h, A, B)
        enforceCeiling()
    }

    /// Outward normal of face k (0 minX, 1 maxX, 2 minY, 3 maxY) and that face's outward speed over the substep.
    @inline(__always) private func face(_ k: Int, _ a: AetherRect, _ b: AetherRect, _ h: Double) -> (SIMD2<Double>, Double) {
        switch k {
        case 0: return (SIMD2(-1, 0), -(b.minX - a.minX) / h)
        case 1: return (SIMD2(1, 0), (b.maxX - a.maxX) / h)
        case 2: return (SIMD2(0, -1), -(b.minY - a.minY) / h)
        default: return (SIMD2(0, 1), (b.maxY - a.maxY) / h)
        }
    }

    /// Earliest entry time τ in [0, 1] of a point into a rect whose faces move linearly, or nil. c: signed distances
    /// inside each face at τ = 0; g: their change over the interval. Inside = all four positive.
    @inline(__always) private static func entry(_ c: SIMD4<Double>, _ g: SIMD4<Double>) -> (Double, Int)? {
        var tin = 0.0, tout = 1.0, k = -1
        for f in 0..<4 {
            let cf = c[f], gf = g[f]
            if cf > 0 { if gf < 0 { tout = min(tout, -cf / gf) } }
            else { if gf <= 0 { return nil }; let t = -cf / gf; if k < 0 || t > tin { tin = max(tin, t); k = f } }
        }
        return (k >= 0 && tin < tout && tin <= 1) ? (tin, k) : nil
    }

    /// Move one point through the substep against the swept walls (merge correction 1). A face at or below the ceiling
    /// reflects in its own frame, u_n' = 2 w_n - u_n, bounded by the ceiling (never below w_n); a faster face carries
    /// the point on it at w_n (owner ruling 2026-11-08: windows push, never wipe).
    private func sweepMove(_ i: Int, _ h: Double, _ A: [AetherRect], _ B: [AetherRect]) {
        var p = pos[i], u = vel[i]
        var f = 0.0, bounces = 0
        let cap = ceiling
        while bounces < 4 {
            let rem = 1 - f
            if rem <= 1e-12 { break }
            let dx = u.x * h * rem, dy = u.y * h * rem
            var best = Double.infinity, bw = -1, bk = -1
            for w in A.indices {
                let a0 = AetherRect.lerp(A[w], B[w], f), a1 = B[w]
                let c = SIMD4(p.x - a0.minX, a0.maxX - p.x, p.y - a0.minY, a0.maxY - p.y)
                if c[0] > 0 && c[1] > 0 && c[2] > 0 && c[3] > 0 { continue }   // started inside: validate() decides
                let g = SIMD4(dx - (a1.minX - a0.minX), (a1.maxX - a0.maxX) - dx,
                              dy - (a1.minY - a0.minY), (a1.maxY - a0.maxY) - dy)
                if let (t, k) = AetherSim.entry(c, g), t < best { best = t; bw = w; bk = k }
            }
            if bw < 0 { p += u * h * rem; f = 1; break }
            p += u * h * rem * best
            f += rem * best
            let (n, wn) = face(bk, A[bw], B[bw], h)
            let un = dot2(u, n)
            u = faceContact(i, u, p, B[bw], bk, n, wn, normal: wn > cap ? wn : max(wn, min(2 * wn - un, cap)))
            p += n * 1e-7
            bounces += 1
        }
        pos[i] = p; vel[i] = u
    }

    /// A face's contact: the normal speed becomes `normal`; a face faster than the press speed marks the point pressed,
    /// spills it toward the face's nearer corner by local crowding and lets it exceed the ceiling while pressed.
    private func faceContact(_ i: Int, _ u: SIMD2<Double>, _ p: SIMD2<Double>, _ R: AetherRect, _ k: Int,
                             _ n: SIMD2<Double>, _ wn: Double, normal un2: Double) -> SIMD2<Double> {
        let cap = ceiling
        var t = u - n * dot2(u, n)
        var lim = cap
        if wn > max(settings.rmsSpeed, 1) {
            pressedAt[i] = time; stats.pressed += 1
            let ax = k < 2 ? 1 : 0
            let lo = ax == 0 ? R.minX : R.minY, hi = ax == 0 ? R.maxX : R.maxY
            let dir: Double = (p[ax] - lo) < (hi - p[ax]) ? -1 : 1
            let c = coarseIndex(p), base = max(2, 1.5 * designDensity * cc * cc)
            let crowd = min(1, max(0, (cCount[c] - base) / max(3, 2 * base)))
            let target = tuning.spillGain * wn * crowd
            if dir * t[ax] < target { t[ax] = dir * target }
            if wn > cap { lim = (un2 * un2 + max(cap, target) * max(cap, target)).squareRoot() }
        }
        let tmax = max(0, lim * lim - un2 * un2).squareRoot(), tl = len2(t)
        if tl > tmax { t *= tmax / tl }
        let out = t + n * un2, sp = len2(out)
        if sp > cap { boost[i] = max(boost[i], sp) }
        return out
    }

    /// Screen edges: reflect (specular), thermal (diffuse re-emission at the target temperature), reservoir (leave).
    private func screenEdge(_ i: Int, _ sigma2: Double) {
        let r = radius
        var p = pos[i], u = vel[i]
        let lo = SIMD2(bounds.minX + r, bounds.minY + r), hi = SIMD2(bounds.maxX - r, bounds.maxY - r)
        for ax in 0..<2 where p[ax] < lo[ax] || p[ax] > hi[ax] {
            if settings.boundary == .reservoir { retire(i, .dormant); stats.removed += 1; return }
            let low = p[ax] < lo[ax]
            p[ax] = min(hi[ax], max(lo[ax], low ? 2 * lo[ax] - p[ax] : 2 * hi[ax] - p[ax]))
            let inward = low ? 1.0 : -1.0
            if settings.boundary == .thermal && sigma2 > 0 {
                let s = sigma2.squareRoot()
                u[ax] = inward * s * rng.rayleigh(); u[1 - ax] = s * rng.gaussian()
            } else { u[ax] = inward * abs(u[ax]) }
        }
        pos[i] = p; vel[i] = u
    }

    @inline(__always) private func cellIndex(_ p: SIMD2<Double>) -> Int {
        let x = min(gw - 1, max(0, Int((p.x - bounds.minX) / cell))), y = min(gh - 1, max(0, Int((p.y - bounds.minY) / cell)))
        return y * gw + x
    }

    private func buildGrid() {
        for c in cellStart.indices { cellStart[c] = 0 }
        for i in pos.indices where phase[i] == .active { let c = cellIndex(pos[i]); cellOfPoint[i] = c; cellStart[c + 1] += 1 }
        for c in 0..<(gw * gh) { cellStart[c + 1] += cellStart[c] }
        var fill = cellStart
        for i in pos.indices where phase[i] == .active { let c = cellOfPoint[i]; cellItems[fill[c]] = i; fill[c] += 1 }
        gridBuilt = true
    }

    private func collide() {
        let offsets = [(0, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]
        for cy in 0..<gh { for cx in 0..<gw {
            let c = cy * gw + cx
            for a in cellStart[c]..<cellStart[c + 1] {
                let i = cellItems[a]
                for (ox, oy) in offsets {
                    let nx = cx + ox, ny = cy + oy
                    guard nx >= 0, nx < gw, ny < gh else { continue }
                    let n = ny * gw + nx
                    let from = (ox == 0 && oy == 0) ? a + 1 : cellStart[n]
                    var b = from
                    while b < cellStart[n + 1] { pair(i, cellItems[b]); b += 1 }
                }
            }
        } }
    }

    private func pair(_ i: Int, _ j: Int) {
        if chainOf[i] >= 0 && chainOf[i] == chainOf[j] { return }
        let d = settings.collisionDiameter
        let dv = pos[j] - pos[i], dist2 = dot2(dv, dv)
        guard dist2 < d * d, dist2 > 1e-18 else { return }
        let dist = dist2.squareRoot(), n = dv / dist
        let rel = vel[j] - vel[i], vn = dot2(rel, n)
        if vn < 0 && !tryBond(i, j, rel) {
            let pa = max(pressedAt[i], pressedAt[j])
            if time - pa < tuning.pressHold {
                // A pressed pile moves as one: inelastic along the normal, momentum conserved; the press and its
                // allowance above the ceiling pass to the partner (the press time is the face's, so it cannot renew).
                vel[i] += n * (vn / 2); vel[j] -= n * (vn / 2)
                pressedAt[i] = pa; pressedAt[j] = pa
                let b = max(boost[i], boost[j]); boost[i] = b; boost[j] = b
            } else { vel[i] += n * vn; vel[j] -= n * vn }
        }
        let half = (d - dist) / 2
        pos[i] -= n * half; pos[j] += n * half
    }

    // MARK: chains

    private func drawFormationTime() -> Double {
        let (lo, hi) = settings.chains.formationWindow
        return lo.isFinite ? time + lo + rng.uniform() * (hi - lo) : .infinity
    }

    private func tryBond(_ i: Int, _ j: Int, _ rel: SIMD2<Double>) -> Bool {
        guard settings.chains != .never, !isTyping, alpha[i] >= 0.9, alpha[j] >= 0.9,
              len2(rel) < tuning.bondSpeedFraction * settings.rmsSpeed else { return false }
        let ci = chainOf[i], cj = chainOf[j]
        if ci < 0 && cj < 0 {
            guard time >= nextFormation, aliveChains < settings.chains.maxAlive else { return false }
            newChain([i, j]); nextFormation = drawFormationTime()
        } else if (ci < 0) != (cj < 0) {
            let (free, c, end) = ci < 0 ? (i, cj, j) : (j, ci, i)
            guard var ch = chains[c], ch.members.count < tuning.chainMaxLength,
                  Double(ch.members.count) * bondLength <= tuning.chainSpan else { return false }
            let atHead = ch.members.first == end, atTail = ch.members.last == end
            guard atHead || atTail, rng.uniform() < tuning.growProbability else { return false }
            if atTail { ch.members.append(free) } else { ch.members.insert(free, at: 0) }
            chains[c] = ch; chainOf[free] = c
        } else { return false }
        let m = (vel[i] + vel[j]) / 2         // perfectly inelastic: momentum conserved
        vel[i] = m; vel[j] = m
        stats.bonds += 1
        return true
    }

    private func newChain(_ members: [Int]) {
        let c = chains.firstIndex(where: { $0 == nil }) ?? { chains.append(nil); return chains.count - 1 }()
        chains[c] = Chain(members: members, born: time)
        for m in members { chainOf[m] = c }
    }

    private func breakChain(_ c: Int, release: Bool) {
        guard let ch = chains[c] else { return }
        chains[c] = nil
        stats.breaks += 1; stats.lifetimes.append(time - ch.born)
        for m in ch.members { chainOf[m] = -1 }
        guard release else { return }
        let live = ch.members.filter { phase[$0] == .active }
        guard live.count >= 2 else { return }
        let s = tuning.releaseFraction * settings.rmsSpeed / 2.0.squareRoot()
        var kicks = live.map { _ in SIMD2(rng.gaussian(), rng.gaussian()) * s }
        let mean = kicks.reduce(SIMD2<Double>.zero, +) / Double(kicks.count)
        kicks = kicks.map { $0 - mean }                 // momentum-free
        let bound = tuning.releaseMaxFraction * settings.rmsSpeed
        let worst = kicks.map(len2).max() ?? 0
        if worst > bound && worst > 0 { kicks = kicks.map { $0 * (bound / worst) } }   // bounded, still momentum-free
        for (k, m) in live.enumerated() { vel[m] += kicks[k] }
    }

    /// Distance constraints at the bond length plus a straightening pull on interior members (positions only), then
    /// rigid bonds: each bond's relative velocity along it is removed. Every correction is symmetric, so momentum is
    /// conserved. Position corrections are NOT fed back into velocity: at a fresh bond that kick is ~15 pt/s.
    private func constrainChains() {
        let L = bondLength
        for c in chains.indices {
            guard let ch = chains[c] else { continue }
            let m = ch.members
            for _ in 0..<tuning.constraintIterations {
                for k in 0..<(m.count - 1) {
                    let a = m[k], b = m[k + 1], dv = pos[b] - pos[a], dist = len2(dv)
                    guard dist > 1e-9 else { continue }
                    let corr = dv * ((dist - L) / (2 * dist))
                    pos[a] += corr; pos[b] -= corr
                }
                if m.count >= 3 {
                    for k in 1..<(m.count - 1) {
                        let delta = ((pos[m[k - 1]] + pos[m[k + 1]]) / 2 - pos[m[k]]) * tuning.straighten
                        pos[m[k]] += delta * (2.0 / 3); pos[m[k - 1]] -= delta / 3; pos[m[k + 1]] -= delta / 3
                    }
                }
            }
            for k in 0..<(m.count - 1) {
                let a = m[k], b = m[k + 1], dv = pos[b] - pos[a], dist = len2(dv)
                guard dist > 1e-9 else { continue }
                let n = dv / dist, rel = dot2(vel[b] - vel[a], n)
                vel[a] += n * (rel / 2); vel[b] -= n * (rel / 2)
            }
        }
    }

    private func chainLifetimes(_ dt: Double) {
        let s0 = sigma0Squared
        for c in chains.indices {
            guard let ch = chains[c] else { continue }
            if time - ch.born >= tuning.chainCap { breakChain(c, release: true); continue }
            let com = ch.members.reduce(SIMD2<Double>.zero) { $0 + pos[$1] } / Double(ch.members.count)
            let ratio = s0 > 0 ? localSigma2(com) / s0 : 1
            let tau = min(tuning.chainTauMax, max(tuning.chainTauMin, tuning.chainTau0 / max(ratio, 1e-4).squareRoot()))
            if rng.uniform() < dt / tau { breakChain(c, release: true) }
        }
    }

    // MARK: recovery, thermostat, reserve

    private func retire(_ i: Int, _ to: AetherPhase) {
        if chainOf[i] >= 0 { breakChain(chainOf[i], release: false) }
        phase[i] = to
        if to == .dormant { alpha[i] = 0 }
        vel[i] = .zero; boost[i] = 0; pressedAt[i] = -.infinity
    }

    private func freeSpot(_ q: SIMD2<Double>, _ rects: [AetherRect]) -> Bool {
        let r = radius
        guard q.x >= bounds.minX + r, q.x <= bounds.maxX - r, q.y >= bounds.minY + r, q.y <= bounds.maxY - r else { return false }
        return !rects.contains { $0.contains(q) }
    }

    /// After all moves: an active point inside a wall is pushed out to the nearest free side (two levels deep, so a
    /// point squeezed between windows or against a screen edge goes round), taking that face's motion. Only a window
    /// that appeared this substep covers points without pushing (dormant: nobody saw it move), and a point with no free
    /// side anywhere near goes dormant. Nothing fades here (owner ruling 2026-11-08: push, never wipe).
    private func validate(_ h: Double, _ A: [AetherRect], _ B: [AetherRect]) {
        let r = radius
        for i in pos.indices where phase[i] == .active {
            let p = pos[i]
            guard let w = B.firstIndex(where: { $0.contains(p) }) else { continue }
            let R = B[w]
            let pen = min(p.x - R.minX, R.maxX - p.x, p.y - R.minY, R.maxY - p.y)
            if pen > r + 1e-9 && walls[w].born >= time - 1e-12 { retire(i, .dormant); stats.covered += 1; continue }
            guard let (q, ww, k) = pushOut(p, B) else { retire(i, .dormant); stats.trapped += 1; continue }
            pos[i] = q
            if pen > r + 1e-9 { stats.pushedOut += 1; pressedAt[i] = time }   // a pushed-out pile is spared the cap
            let (n, wn) = face(k, A[ww], B[ww], h)
            let un = dot2(vel[i], n)
            if un < wn { vel[i] = faceContact(i, vel[i], q, B[ww], k, n, wn, normal: wn) }
            else { vel[i] = faceContact(i, vel[i], q, B[ww], k, n, 0, normal: un) }
        }
    }

    /// The nearest free spot just outside the walls containing p, and the (wall, face) it was pushed out of.
    private func pushOut(_ p: SIMD2<Double>, _ B: [AetherRect]) -> (SIMD2<Double>, Int, Int)? {
        func spots(_ q: SIMD2<Double>, _ R: AetherRect) -> [(SIMD2<Double>, Int, Double)] {
            [(SIMD2(R.minX - 1e-7, q.y), 0, q.x - R.minX), (SIMD2(R.maxX + 1e-7, q.y), 1, R.maxX - q.x),
             (SIMD2(q.x, R.minY - 1e-7), 2, q.y - R.minY), (SIMD2(q.x, R.maxY + 1e-7), 3, R.maxY - q.y)]
        }
        var best: (Double, SIMD2<Double>, Int, Int)? = nil
        for w in B.indices where B[w].contains(p) {
            for (q1, k1, d1) in spots(p, B[w]) {
                if let b = best, d1 >= b.0 { continue }
                if freeSpot(q1, B) { best = (d1, q1, w, k1); continue }
                for w2 in B.indices where B[w2].contains(q1) {
                    for (q2, k2, d2) in spots(q1, B[w2]) where best.map({ d1 + d2 < $0.0 }) ?? true && freeSpot(q2, B) {
                        best = (d1 + d2, q2, w2, k2)
                    }
                }
            }
        }
        return best.map { ($0.1, $0.2, $0.3) }
    }

    /// A released pushed point's allowance above the ceiling bleeds off with pushReleaseTau (it holds while pressed).
    private func releaseBoost(_ dt: Double) {
        let cap = ceiling, k = exp(-dt / tuning.pushReleaseTau)
        for i in pos.indices where boost[i] > 0 {
            if phase[i] != .active { boost[i] = 0; continue }
            if time - pressedAt[i] < tuning.dt { continue }
            boost[i] = cap + (boost[i] - cap) * k
            if boost[i] - cap < 0.5 { boost[i] = 0 }
        }
        enforceCeiling()
    }

    private func enforceCeiling() {
        let cap = ceiling
        for i in pos.indices where phase[i] == .active {
            let lim = max(cap, boost[i]), v2 = dot2(vel[i], vel[i])
            if v2 > lim * lim { vel[i] *= lim / v2.squareRoot() }
        }
    }

    @inline(__always) private func coarseIndex(_ p: SIMD2<Double>) -> Int {
        let x = min(cw - 1, max(0, Int((p.x - bounds.minX) / cc))), y = min(ch - 1, max(0, Int((p.y - bounds.minY) / cc)))
        return y * cw + x
    }

    private func buildCoarse() {
        for c in cCount.indices { cCount[c] = 0; cSum[c] = .zero; cSum2[c] = 0 }
        for i in pos.indices where phase[i] == .active {
            let c = coarseIndex(pos[i]); cCount[c] += 1; cSum[c] += vel[i]; cSum2[c] += dot2(vel[i], vel[i])
        }
    }

    /// Flow-relative per-component variance in the coarse cell at p (the gas's local temperature).
    private func localSigma2(_ p: SIMD2<Double>) -> Double {
        let c = coarseIndex(p), n = cCount[c]
        guard n >= 2 else { return meanSigma2() }
        let m = cSum[c] / n
        return max(0, (cSum2[c] / n - dot2(m, m)) / 2)
    }

    /// Ornstein-Uhlenbeck relaxation of each point's velocity relative to its cell's (shrunk) mean flow, toward σ²
    /// with time constant τ; the flow itself decays with flowTau; pockets hotter than hotFactor x target relax with hotTau.
    private func thermostat(_ dt: Double, sigma2: Double, tau: Double) {
        buildCoarse()
        guard tau.isFinite, tau > 0 else { return }
        let flowTau = tuning.flowTau ?? coolingTau
        let fdecay = exp(-dt / (sigma2 == 0 ? min(flowTau, tau) : flowTau))   // a frozen settle stops flow too
        let hotLimit = tuning.hotFactor * max(sigma2, sigma0Squared, 0.5)
        for i in pos.indices where phase[i] == .active {
            let c = coarseIndex(pos[i]), n = cCount[c]
            let ubar = cSum[c] / (n + 3)
            let m = n > 0 ? cSum[c] / n : SIMD2<Double>.zero
            let local = n >= 2 ? max(0, (cSum2[c] / n - dot2(m, m)) / 2) : dot2(vel[i] - ubar, vel[i] - ubar) / 2
            let t = local > hotLimit ? min(tau, tuning.hotTau) : tau
            let decay = exp(-dt / t), kick = (sigma2 * (1 - decay * decay)).squareRoot()
            var v = ubar * fdecay + (vel[i] - ubar) * decay
            if kick > 0 { v += SIMD2(rng.gaussian(), rng.gaussian()) * kick }
            if sigma2 == 0 && dot2(v, v) < tuning.snapSpeed * tuning.snapSpeed { v = .zero }
            vel[i] = v
        }
        // The floor is a guarantee, not just a target: a settling gas whose mean flow-relative energy sits below it
        // is scaled back up to it (a uniform rescale: shapes and wakes are kept, nothing is snapped to rest).
        let lo = floorSigma2
        if lo > 0 && sigma2 <= lo + 1e-12 {
            let now = meanSigma2()
            if now > 1e-12 && now < lo { let k = (lo / now).squareRoot(); for i in pos.indices where phase[i] == .active { vel[i] *= k } }
        }
        enforceCeiling()
    }

    private func fades(_ dt: Double) {
        for i in pos.indices {
            switch phase[i] {
            case .active where alpha[i] < 1: alpha[i] = min(1, alpha[i] + dt / tuning.fadeIn)
            case .fading:
                alpha[i] -= dt / tuning.fadeOut
                if alpha[i] <= 0 { alpha[i] = 0; phase[i] = .dormant }
            default: break
            }
        }
    }

    private func dormantSlot() -> Int? {
        let n = pos.count
        for k in 0..<n {
            let i = (dormantCursor + k) % n
            if phase[i] == .dormant { dormantCursor = (i + 1) % n; return i }
        }
        return nil
    }

    private func overlapsPoint(_ q: SIMD2<Double>) -> Bool {
        guard gridBuilt else { return false }
        let d2 = settings.collisionDiameter * settings.collisionDiameter
        let c = cellIndex(q), cx = c % gw, cy = c / gw
        for oy in -1...1 { for ox in -1...1 {
            let nx = cx + ox, ny = cy + oy
            guard nx >= 0, nx < gw, ny >= 0, ny < gh else { continue }
            let n = ny * gw + nx
            for b in cellStart[n]..<cellStart[n + 1] {
                let j = cellItems[b]
                if phase[j] == .active { let dv = pos[j] - q; if dot2(dv, dv) < d2 { return true } }
            }
        } }
        return false
    }

    private func activate(_ i: Int, _ q: SIMD2<Double>, sigma: Double) {
        pos[i] = q; prevPos[i] = q; vel[i] = SIMD2(rng.gaussian(), rng.gaussian()) * sigma
        let v = len2(vel[i]), cap = ceiling
        if v > cap { vel[i] *= cap / v }   // a Gaussian tail must not enter above the ceiling
        phase[i] = .active; alpha[i] = 0; chainOf[i] = -1; boost[i] = 0; pressedAt[i] = -.infinity
    }

    /// Revealed-space reserve (merge correction 4): top each exposed region up toward the design density from the
    /// dormant pool, with time constant refillTau, at the gas's current temperature. Declared visual physics.
    private func seedRegions(_ dt: Double) {
        guard tuning.reserveEnabled, !regions.isEmpty else { return }
        regions.removeAll { $0.expires <= time }
        let r = radius
        let rects = walls.map { $0.rect(time).expanded(by: r) }
        let sigma = meanSigma2().squareRoot()
        // Closed boundaries conserve N: the reserve only gives back what windows took (dormant points).
        var budget = settings.boundary == .reservoir ? Int.max : population - activeCount()
        var done: [Int] = []
        for ri in regions.indices {
            let R = regions[ri].rect
            let free = aetherSubtract([R], rects).reduce(0) { $0 + $1.area }
            let deficit = regions[ri].density * free - Double(activeCount(in: R))
            if deficit < 1 { if free >= R.area * 0.999 { done.append(ri) }; continue }
            regions[ri].carry += deficit * (1 - exp(-dt / tuning.refillTau))
            while regions[ri].carry >= 1 && budget > 0 {
                regions[ri].carry -= 1
                guard let slot = dormantSlot() else { break }
                var placed = false
                for _ in 0..<8 {
                    let q = SIMD2(R.minX + rng.uniform() * R.width, R.minY + rng.uniform() * R.height)
                    if freeSpot(q, rects) && !overlapsPoint(q) { activate(slot, q, sigma: sigma); stats.seeded += 1; budget -= 1; placed = true; break }
                }
                if !placed { break }
            }
        }
        for ri in done.reversed() { regions.remove(at: ri) }
    }

    /// Reservoir edges: effusion inflow n0 σ / √(2π) per pt of edge per second, Maxwell flux velocities.
    private func injectEdges(_ dt: Double, sigma2: Double) {
        guard sigma2 > 0 else { return }
        let s = sigma2.squareRoot(), r = radius
        let rects = walls.map { $0.rect(time).expanded(by: r) }
        let flux = designDensity * s / (2 * Double.pi).squareRoot()
        for e in 0..<4 {
            let horizontal = e < 2
            let length = horizontal ? bounds.width : bounds.height
            edgeCarry[e] += flux * length * dt
            while edgeCarry[e] >= 1 {
                edgeCarry[e] -= 1
                let t = rng.uniform()
                let q: SIMD2<Double>, inward: SIMD2<Double>
                switch e {
                case 0: q = SIMD2(bounds.minX + t * bounds.width, bounds.minY + r + 0.01); inward = SIMD2(0, 1)
                case 1: q = SIMD2(bounds.minX + t * bounds.width, bounds.maxY - r - 0.01); inward = SIMD2(0, -1)
                case 2: q = SIMD2(bounds.minX + r + 0.01, bounds.minY + t * bounds.height); inward = SIMD2(1, 0)
                default: q = SIMD2(bounds.maxX - r - 0.01, bounds.minY + t * bounds.height); inward = SIMD2(-1, 0)
                }
                guard freeSpot(q, rects), let i = dormantSlot() else { continue }
                let tangent = SIMD2(-inward.y, inward.x)
                pos[i] = q; prevPos[i] = q; vel[i] = inward * (s * rng.rayleigh()) + tangent * (s * rng.gaussian())
                phase[i] = .active; alpha[i] = 0; chainOf[i] = -1; boost[i] = 0; pressedAt[i] = -.infinity
                stats.injected += 1
            }
        }
    }

    /// Capacity policy for crowded pockets: a coarse cell over crowdFactor x the design density fades its excess. A cell
    /// holding a point pressed in the last crowdHold seconds is spared: a pile a window pushed disperses, never fades.
    private func crowding() {
        guard time >= nextCrowdCheck else { return }
        nextCrowdCheck = time + tuning.crowdEvery
        buildCoarse()
        let cap = max(tuning.crowdFactor * designDensity * cc * cc, tuning.crowdMin)
        var spared = Set<Int>()
        for i in pos.indices where phase[i] == .active && time - pressedAt[i] < tuning.crowdHold { spared.insert(coarseIndex(pos[i])) }
        for i in pos.indices.reversed() where phase[i] == .active {
            let c = coarseIndex(pos[i])
            if cCount[c] > cap && !spared.contains(c) { retire(i, .fading); cCount[c] -= 1; stats.crowded += 1 }
        }
    }

    /// The crowding cap, points per coarse cell (tests).
    var crowdCap: Double { max(tuning.crowdFactor * designDensity * cc * cc, tuning.crowdMin) }
    func maxCoarseCount() -> Double { buildCoarse(); return cCount.max() ?? 0 }

    /// Sprite stirring (owner, 2026-11-08). Entrainment: within stirReach x radius of a moving sprite, each point's
    /// velocity component along the sprite's motion is pulled up toward the sprite's speed (never braked: a sprite
    /// only drags gas forward), weight (1 - d/R)², so the gas behind it carries a wake. Body: a point inside the
    /// sprite's circle is moved to its edge and given at least the body's outward speed there (a moving round wall).
    /// The ceiling still holds (enforceCeiling after every substep); the wake settles under Cooling.
    private func applyStirring(_ h: Double) {
        let k = settings.stirring, r = radius
        for (si, s) in sprites.enumerated() {
            let a = max(s.radius, 1), body = a + r, R = tuning.stirReach * a, R2 = R * R
            let vs = si < spriteVel.count ? spriteVel[si] : .zero, speed = len2(vs)
            let dir = speed > 1e-6 ? vs / speed : .zero
            for i in pos.indices where phase[i] == .active {
                let dv = pos[i] - s.pos, d2 = dot2(dv, dv)
                guard d2 < R2 else { continue }
                let d = d2.squareRoot()
                if speed > 0.5 {
                    let w = (1 - max(0, d - a) / (R - a)) , f = 1 - exp(-h * tuning.stirRate * k * w * w)
                    let along = dot2(vel[i], dir)
                    if along < speed { vel[i] += dir * ((speed - along) * f) }
                }
                if d < body {
                    let n = d > 1e-9 ? dv / d : SIMD2(1, 0)
                    pos[i] = s.pos + n * (body + 1e-6)
                    let wn = dot2(vs, n), un = dot2(vel[i], n)
                    if un < wn { vel[i] += n * (wn - un) }
                    if wn <= 0 && un < 0 { vel[i] -= n * un }   // a still body: no motion into it
                }
            }
        }
    }

    /// One field family for release 1: a sideways (magnetic-style) deflection near each sprite, an exact rotation of
    /// the velocity (does no work, like the Boris push), ω = strength x ωmax x (a²/(d²+a²))^{3/2} x q, faded to 0 at
    /// fieldReach x radius. Opposite charges curl opposite ways: two counter-curling wakes.
    private func applyField(_ h: Double) {
        let wmax = tuning.fieldOmegaMax * settings.fieldStrength
        for s in sprites {
            let a = max(s.radius, 1), R = tuning.fieldReach * a, R2 = R * R
            for i in pos.indices where phase[i] == .active {
                let dv = pos[i] - s.pos, d2 = dot2(dv, dv)
                guard d2 < R2 else { continue }
                let f = a * a / (d2 + a * a)
                let theta = wmax * f * f.squareRoot() * charge[i] * h * (1 - d2 / R2)
                let c = cos(theta), sn = sin(theta), v = vel[i]
                vel[i] = SIMD2(c * v.x - sn * v.y, sn * v.x + c * v.y)
            }
        }
    }
}
