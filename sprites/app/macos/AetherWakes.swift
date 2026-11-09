import Foundation

// MARK: - Species wakes (owner card 2026-11-08 18:30 PST)

/// How a species shapes the gas it stirs, inside the same reach and never faster than the sprite: the entrainment
/// weight and a sideways push, in the sprite's own frame (a: along its motion, b: across it, both in reach units).
enum AetherWakeShape: String {
    case round   // the old wake (glyph species)
    case comb    // Siphonophores: three soft aft lobes comb the gas into loose strands
    case bow     // Mothership Choir: forward shoulders part the gas round the body like a bow
    case lee     // Firefly Murmurations: a narrow streak in the lee
    case swirl   // Kaleidoscope Seeds: the wake turns a little round the body
    static func of(species: String) -> AetherWakeShape {
        switch species {
        case "c2_siphon": return .comb
        case "c1_choir": return .bow
        case "c5_fireflies": return .lee
        case "c4_kaleido": return .swirl
        default: return .round
        }
    }
    /// (entrainment weight multiplier >= 0, sideways push as a fraction of the sprite's speed) at (a, b), strength k.
    func shape(a: Double, b: Double, k: Double) -> (Double, Double) {
        switch self {
        case .round: return (1, 0)
        case .comb:  // aft only: lobes at b = 0, ±2/3; the push gathers gas toward the lobes
            guard a < 0 else { return (1 - 0.5 * k, 0) }
            return (max(0, 1 + 0.9 * k * cos(3 * Double.pi * b)), -0.25 * k * sin(3 * Double.pi * b))
        case .bow:   // ahead: less drag, a push outward from the track; behind: the round wake
            guard a > 0 else { return (1, 0) }
            let side: Double = b >= 0 ? 1 : -1
            return (1 - 0.6 * k, 0.8 * k * side * min(1, 3 * abs(b)) * (1 - min(1, abs(b))) * min(1, 3 * a))
        case .lee:   // a narrow aft streak, little drag beside it
            guard a < 0 else { return (1 - 0.4 * k, 0) }
            return (max(0, 1 + k * (1.6 * exp(-b * b / 0.04) - 0.8)), 0)
        case .swirl: // a sideways push that turns with the side, so the wake rotates round the body
            return (1, 0.3 * k * (a >= 0 ? 1 : -1) * (1 - min(1, abs(b))))
        }
    }
}

/// A project's handedness: +1 (counter-clockwise in screen coordinates) or -1, fixed by its project key (FNV-1a; the
/// sprite id when there is no key). The same project curls the same way on every launch and every machine.
func aetherHandedness(key: String, id: String = "") -> Double {
    let k = key.isEmpty ? id : key
    guard !k.isEmpty else { return 0 }
    let h = k.utf8.reduce(0xCBF2_9CE4_8422_2325 as UInt64) { ($0 ^ UInt64($1)) &* 0x100_0000_01B3 }
    return (h >> 17) & 1 == 0 ? 1 : -1
}

// MARK: - Weather fronts (owner card 2026-11-08 18:30 PST)

/// The fronts' slow spatial field at a point (u, v in units of the screen's longer side) and wall-clock minutes: two
/// seeded plane waves about one and two wavelengths across the screen, each moving one wavelength per ~an hour (60 and
/// 47 min), weights 0.6 and 0.4. In [-1, 1], smooth in space and time.
func aetherFrontField(u: Double, v: Double, minutes: Double, seed: UInt64) -> Double {
    var r = AetherRNG(seed: seed ^ 0xF407_F407_0000_0001)
    var s = 0.0
    for (k, w, period) in [(1.1, 0.6, 60.0), (1.9, 0.4, 47.0)] {
        let a = 2 * Double.pi * r.uniform(), p0 = 2 * Double.pi * r.uniform()
        s += w * sin(2 * Double.pi * (k * (u * cos(a) + v * sin(a)) - minutes / period) + p0)
    }
    return s
}

/// Per coarse cell, the local values of the constants the pair, particle-in-cell and edge passes read.
struct AetherFronts: Equatable {
    var attraction: [Double], chain: [Double], repulsion: [Double], edge: [Double]
    var maxAttraction: Double
}

/// Weather fronts: each coarse cell runs the drift walk at its own phase, phase + fronts x 0.25 x field (a quarter of
/// a drift period apart at most), so a region can be stickier or warmer than its neighbour while the borders wander.
/// nil when fronts or the drift amplitude is 0 (one universe everywhere). The cell grid matches AetherSim's coarse grid.
func aetherFronts(_ base: AetherSettings, seed: UInt64, phase: Double, amplitude: Double, minutes: Double,
                  bounds: AetherRect, cell: Double) -> AetherFronts? {
    guard base.fronts > 0, amplitude > 0 else { return nil }
    let cw = max(1, Int((bounds.width / cell).rounded(.up))), ch = max(1, Int((bounds.height / cell).rounded(.up)))
    let side = max(bounds.width, bounds.height, 1)
    var f = AetherFronts(attraction: [], chain: [], repulsion: [], edge: [], maxAttraction: 0)
    f.attraction.reserveCapacity(cw * ch)
    for y in 0..<ch { for x in 0..<cw {
        let u = (Double(x) + 0.5) * cell / side, v = (Double(y) + 0.5) * cell / side
        let d = aetherDrifted(base, seed: seed, phase: phase + base.fronts * 0.25 * aetherFrontField(u: u, v: v, minutes: minutes, seed: seed), amplitude: amplitude)
        f.attraction.append(d.attraction); f.chain.append(d.chainForming); f.repulsion.append(d.repulsion); f.edge.append(d.edgeTemperature)
        f.maxAttraction = max(f.maxAttraction, d.attraction)
    } }
    return f
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

