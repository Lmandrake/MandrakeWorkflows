import Foundation

// MARK: - Settings (behaviors.json "aether": {...})

enum AetherMotion: String { case living, settleWhileTyping = "settle-typing", stirAndSettle = "stir-settle" }
enum AetherBoundary: String { case thermal, reflect, reservoir }
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
    /// Short-range attraction (ruling 8): well depth in units of the Temperature's σ² (0 off, 0-3), and its reach in
    /// collision diameters (1.5-3). The grid cell is sized for the widest reach, so the slider never costs a wider search.
    var attraction = 1.0
    var attractionRange = 2.0
    /// Long-range repulsion (ruling 8): strength 0-2 (1 = an extra ideal-gas pressure at the design density), and the
    /// smoothing width in coarse cells (48 pt each, 1-4).
    var repulsion = 0.5
    var repulsionRange = 2.0
    /// "Chain forming" (ruling 8): 0 = isotropic attraction (droplets), 1 = dipole attraction (needles). 0-1.
    var chainForming = 0.5
    static let maxAttractionRange = 3.0
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
    /// "Temperature variation" (owner ruling 7): 0 = uniform (every point relaxed to the Temperature, the old gas),
    /// 1 = free (no relaxation; hot and cold regions persist and the temperature wanders). 0-1.
    var temperatureVariation = 0.85
    var colour = "green"            // green | amber | white, or "#rrggbb" from the colour picker (rendering)
    var brightness = 2              // 1-3 (rendering)
    /// "Drift" (owner, 2026-11-08 ~5 PM: "a mode where the Universal Constants slowly vary over the course of tens of
    /// minutes"): off / gentle / wild, and the base period in minutes (10-120). See aetherDrifted.
    var drift = AetherDrift.off
    var driftPeriodMinutes = 30.0
    /// Thermal-edge emission temperature as a multiple of the Temperature's RMS speed (0.5-2). No slider: drift moves
    /// it, and "Hold this universe" writes it.
    var edgeTemperature = 1.0
    /// "Drift coupling" (owner card 2026-11-08 18:30 PST, "Couple the risky pairs"): 0 = every constant walks on its
    /// own; 1 = repulsion strength follows attraction strength's walk and repulsion range follows attraction range's,
    /// so stickier never meets weaker repulsion. Default 1.
    var driftCoupling = 1.0
    /// "Weather fronts" (owner card 2026-11-08 18:30 PST): drift happens in places, not everywhere at once. 0 = one
    /// universe on the whole desktop; 1 = neighbouring regions run up to a quarter of a drift period apart, and the
    /// borders between them cross the screen over about an hour. Needs Drift on. 0-1, default 0.4 (subtle).
    var fronts = 0.4
    /// "Needle memory" (owner card 2026-11-08 18:30 PST): a dot that leaves a needle keeps its direction for a while
    /// (its rotational noise is turned down while it has no neighbours), so the next needle there tends to form the same
    /// way. 0 = forgets at once (the old gas); 1 = holds it for minutes. No trail is drawn. 0-1, default 0.5.
    var needleMemory = 0.5
    /// "Knots" (same card): where two sprites' wakes cross within a few seconds, a crossing cell becomes a knot with this
    /// probability (sometimes, never always); there the attraction well briefly captures faster pairs and damps them
    /// harder, so a small knot forms and later comes apart. 0-1, default 0.4.
    var knots = 0.4
    /// "Window dew" (owner card 2026-11-08 18:30 PST): slow dots bead along the edge of a window that has not moved for
    /// `dewAfterSeconds`, and shake off into the gas when it moves. 0 off - 1 strong; default 0.3 (subtle). Only slow
    /// dots are held (a capture, like the attraction well), so the edge never fills into an outline.
    var dew = 0.3
    /// "Species wakes" (owner card 2026-11-08 18:30 PST): each species shapes the stirring wake its own way (see
    /// AetherWakeShape): 0 = every sprite stirs a round wake (the old gas); 1 = full shapes. Identity only, never work
    /// or status. 0-1, default 0.5.
    var speciesWakes = 0.5
    /// "Handedness by project" (same card): each project's sprite curls the gas it stirs the same way every time
    /// (left- or right-handed, from its project key), so two wakes passing braid or cancel. A rotation of the stirred
    /// gas's velocity round the sprite (does no work). 0 off - 1 strong; default 0.4. Identity only, carries no data.
    var handedness = 0.4
    /// "Wake reader" (same card): an idle sprite at play sometimes follows another sprite's leftover current a little
    /// (the stage decides; the host hands it the currents). The chance a read happens at a sprite's rare read moments.
    /// 0 off - 1; default 0.3. Kept rare and small so it never reads as one project following another.
    var wakeReader = 0.3
    /// How long a window must stay still before dew forms, seconds. No Settings slider (10 min, the card's figure);
    /// behaviors.json "dewAfter" shortens it for a check. 5-3600.
    var dewAfterSeconds = 600.0

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
        if let n = jsonNumber(o["temperatureVariation"]) { s.temperatureVariation = clamp(n, 0, 1) }
        if let n = jsonNumber(o["attraction"]) { s.attraction = clamp(n, 0, 3) }
        if let n = jsonNumber(o["attractionRange"]) { s.attractionRange = clamp(n, 1.5, maxAttractionRange) }
        if let n = jsonNumber(o["repulsion"]) { s.repulsion = clamp(n, 0, 2) }
        if let n = jsonNumber(o["repulsionRange"]) { s.repulsionRange = clamp(n, 1, 4) }
        if let n = jsonNumber(o["chainForming"]) { s.chainForming = clamp(n, 0, 1) }
        if let n = jsonNumber(o["fieldStrength"]) { s.fieldStrength = clamp(n, 0, 2) }
        else if let k = o["fieldStrength"] as? String, let v = strengths[k] { s.fieldStrength = v }
        if let c = o["colour"] as? String, ["green", "amber", "white"].contains(c) || aetherHex(c) != nil { s.colour = c.lowercased() }
        if let n = jsonNumber(o["brightness"]) { s.brightness = Int(clamp(n.rounded(), 1, 3)) }
        if let v = (o["drift"] as? String).flatMap(AetherDrift.init(rawValue:)) { s.drift = v }
        if let n = jsonNumber(o["driftPeriod"]) { s.driftPeriodMinutes = clamp(n, 10, 120) }
        if let n = jsonNumber(o["edgeTemperature"]) { s.edgeTemperature = clamp(n, 0.5, 2) }
        if let n = jsonNumber(o["driftCoupling"]) { s.driftCoupling = clamp(n, 0, 1) }
        if let n = jsonNumber(o["fronts"]) { s.fronts = clamp(n, 0, 1) }
        if let n = jsonNumber(o["needleMemory"]) { s.needleMemory = clamp(n, 0, 1) }
        if let n = jsonNumber(o["knots"]) { s.knots = clamp(n, 0, 1) }
        if let n = jsonNumber(o["dew"]) { s.dew = clamp(n, 0, 1) }
        if let n = jsonNumber(o["speciesWakes"]) { s.speciesWakes = clamp(n, 0, 1) }
        if let n = jsonNumber(o["handedness"]) { s.handedness = clamp(n, 0, 1) }
        if let n = jsonNumber(o["wakeReader"]) { s.wakeReader = clamp(n, 0, 1) }
        if let n = jsonNumber(o["dewAfter"]) { s.dewAfterSeconds = clamp(n, 5, 3600) }
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

// MARK: - Drifting constants (owner, 2026-11-08 ~5 PM)

/// How far the constants wander, in logit units of each slider's normalised range (see aetherDrifted): gentle about
/// ±12 % of the range around a centred slider, wild about ±32 %.
enum AetherDrift: String {
    case off, gentle, wild
    var amplitude: Double { switch self { case .off: return 0; case .gentle: return 0.5; case .wild: return 1.5 } }
}

/// One drifting constant: its behaviors.json key, the slider's range (drift never leaves it), log-scaled or linear,
/// and whether the bottom of the range means "off" (then a constant set to off stays off).
struct AetherDriftKey {
    let name: String, lo: Double, hi: Double, log: Bool, offAtLo: Bool
    let path: WritableKeyPath<AetherSettings, Double>
    /// A coupled constant (owner card 2026-11-08 18:30 PST): the constant whose walk this one follows, by the
    /// settings' driftCoupling (0 its own walk, 1 the leader's), with this sign (+1 together, -1 opposite).
    var follows: String? = nil, followSign = 1.0
    /// The slider value c moved by x logit units: normalise (log or linear), take the logistic step from a working
    /// point kept off the ends, and add that step to c's own normalised value, clamped to the range. Exactly c at x = 0
    /// (so easing in from a slider at its end never jumps), smooth, inside the range, and |dv/dx| <= range / 4.
    func value(_ c: Double, _ x: Double) -> Double {
        let a = log ? Foundation.log(lo) : lo, b = log ? Foundation.log(hi) : hi
        let u0 = min(1, max(0, ((log ? Foundation.log(max(c, lo)) : c) - a) / (b - a)))
        let u = min(0.98, max(0.02, u0)), z = Foundation.log(u / (1 - u))
        let v = min(1, max(0, u0 + 1 / (1 + exp(-(z + x))) - u))
        let y = a + v * (b - a)
        return log ? exp(y) : y
    }
    /// The walk's seed id: from the name, so adding or reordering constants never changes another constant's walk.
    var seedId: UInt64 { name.utf8.reduce(0xCBF2_9CE4_8422_2325) { ($0 ^ UInt64($1)) &* 0x100_0000_01B3 } }
}

/// The universal constants that drift (owner's list: attraction strength and range, repulsion strength and range,
/// chain forming, cooling drag, temperature variation, edge temperature, field strength; stirring added). Density is
/// NOT drifted: the population is fixed when a sim is built, so a density walk would mean spawning and retiring points.
/// Collision size is not drifted either: it sizes the grid, and so the CPU budget.
let aetherDriftKeys: [AetherDriftKey] = [
    AetherDriftKey(name: "attraction", lo: 0, hi: 3, log: false, offAtLo: true, path: \.attraction),
    AetherDriftKey(name: "attractionRange", lo: 1.5, hi: AetherSettings.maxAttractionRange, log: false, offAtLo: false, path: \.attractionRange),
    AetherDriftKey(name: "repulsion", lo: 0, hi: 2, log: false, offAtLo: true, path: \.repulsion, follows: "attraction"),
    AetherDriftKey(name: "repulsionRange", lo: 1, hi: 4, log: false, offAtLo: false, path: \.repulsionRange, follows: "attractionRange", followSign: -1),
    AetherDriftKey(name: "chainForming", lo: 0, hi: 1, log: false, offAtLo: true, path: \.chainForming),
    AetherDriftKey(name: "cooling", lo: 5, hi: 120, log: true, offAtLo: false, path: \.coolingSeconds),
    AetherDriftKey(name: "temperatureVariation", lo: 0, hi: 1, log: false, offAtLo: false, path: \.temperatureVariation),
    AetherDriftKey(name: "edgeTemperature", lo: 0.5, hi: 2, log: true, offAtLo: false, path: \.edgeTemperature),
    AetherDriftKey(name: "fieldStrength", lo: 0, hi: 2, log: false, offAtLo: true, path: \.fieldStrength),
    AetherDriftKey(name: "stirring", lo: 0, hi: 2, log: false, offAtLo: true, path: \.stirring),
]

/// Constant k's walk at `phase` (in cycles of the base period): three sines at seeded, jittered period multiples
/// (0.45, 1, 2.3 x 0.8-1.2, so incommensurate across constants and combinations rarely repeat in a day) with seeded
/// phases, weights 1/4, 1/2, 1/4. In [-1, 1]; |d/dphase| <= 2π (0.25/0.36 + 0.5/0.8 + 0.25/1.84) ≈ 9.2.
func aetherDriftWave(seed: UInt64, key k: UInt64, phase: Double) -> Double {
    var r = AetherRNG(seed: seed ^ (k &* 0xA24B_AED4_963E_E407))
    var s = 0.0
    for (m, w) in [(0.45, 0.25), (1.0, 0.5), (2.3, 0.25)] {
        let period = m * (0.8 + 0.4 * r.uniform()), p0 = 2 * Double.pi * r.uniform()
        s += w * sin(2 * Double.pi * phase / period + p0)
    }
    return s
}

/// The drifted settings: every drifting constant moved along its own walk around the owner's slider value (the
/// centre), `amplitude` logit units at most (the host eases it in and out, so switching drift never jolts). Pure and
/// seeded: the same seed and phase give the same universe.
func aetherDrifted(_ base: AetherSettings, seed: UInt64, phase: Double, amplitude: Double) -> AetherSettings {
    guard amplitude > 0 else { return base }
    var s = base
    let k = min(1, max(0, base.driftCoupling))
    for key in aetherDriftKeys {
        let c = base[keyPath: key.path]
        if key.offAtLo && c <= key.lo { continue }
        var w = aetherDriftWave(seed: seed, key: key.seedId, phase: phase)
        if let lead = key.follows, k > 0, let l = aetherDriftKeys.first(where: { $0.name == lead }) {   // a convex mix: still in [-1, 1]
            w = (1 - k) * w + k * key.followSign * aetherDriftWave(seed: seed, key: l.seedId, phase: phase)
        }
        s[keyPath: key.path] = key.value(c, amplitude * w)
    }
    return s
}

/// The drift's clock, for the host: the phase advances at 1 / period (so changing the period changes the speed, never
/// jumps the phase) and the amplitude eases toward the mode's over `ease` seconds (switching drift on, off or between
/// gentle and wild never jolts: 0 to wild in 3 minutes). Starts from wall-clock time so the universe keeps moving across relaunches.
struct AetherDriftClock {
    var phase: Double
    var amplitude = 0.0
    var ease = 180.0
    init(epochSeconds: Double, periodMinutes: Double) { phase = epochSeconds / (60 * max(1, periodMinutes)) }
    mutating func advance(_ dt: Double, mode: AetherDrift, periodMinutes: Double) {
        phase += max(0, dt) / (60 * max(1, periodMinutes))
        let target = mode.amplitude, step = max(0, dt) * AetherDrift.wild.amplitude / ease
        amplitude = amplitude < target ? min(target, amplitude + step) : max(target, amplitude - step)
    }
}

