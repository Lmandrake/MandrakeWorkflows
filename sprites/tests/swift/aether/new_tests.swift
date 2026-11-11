import Foundation

// Acceptance tests for the Aether speed-up tickets (2026-11-09). Seeded, headless. Goldens were captured from the
// code BEFORE the change (commit 3a23998) with a ceiling too high to clip, so they pin the physics bit for bit.
func aetherFingerprint(_ s: AetherSim) -> UInt64 {
    var h: UInt64 = 0xCBF2_9CE4_8422_2325
    func mix(_ d: Double) { h = (h ^ d.bitPattern) &* 0x100_0000_01B3 }
    for i in s.pos.indices { mix(s.pos[i].x); mix(s.pos[i].y); mix(s.vel[i].x); mix(s.vel[i].y); mix(s.alpha[i]); mix(s.orient[i].x); mix(s.orient[i].y) }
    return h
}
func goldenScene(_ boundary: AetherBoundary) -> AetherSim {
    var t = AetherTuning(); t.ceilingOverride = 1e9
    let s = AetherSim(bounds: laptop, settings: settings { $0.motion = .living; $0.boundary = boundary }, seed: 7, tuning: t,
                      obstacles: [AetherObstacle(id: 1, rect: AetherRect(x: 400, y: 300, width: 300, height: 200))])
    run(s, 1)
    s.setGeometry([AetherObstacle(id: 1, rect: AetherRect(x: 450, y: 320, width: 300, height: 200))])
    run(s, 1)
    s.setGeometry([])
    run(s, 2)
    return s
}
let goldenThermal: UInt64 = 340858634401020986
let goldenReservoir: UInt64 = 17366022188231343040

func newTests() {
    // MARK: slot-scan ticket (MANDRAKEWORKFLOWS_FIX_AETHER_SLOT_SCAN_AND_SIX_RULE_BREAKS)
    do {
        let a = goldenScene(.thermal), b = goldenScene(.reservoir)
        check(aetherFingerprint(a) == goldenThermal, "scan fix: thermal run is bit-identical to the pre-change sim", "\(aetherFingerprint(a))")
        check(aetherFingerprint(b) == goldenReservoir, "scan fix: reservoir run is bit-identical to the pre-change sim", "\(aetherFingerprint(b))")
        // The work counter: full-capacity temperature scans (meanSigma2 over every slot) per step. Before the fix a
        // sparse chain-enabled gas did one per lone point per step (about 100); after, the fallback is cached.
        let scans = Double(a.work.globalScans) / Double(max(1, a.work.steps))
        check(a.work.steps > 100 && scans <= 8, "scan fix: at most 8 global temperature scans per step", "\(scans) per step")
    }
    // MARK: rule break: boost release must not bleed a point's speed in the step that pressed it
    // (GPT code review 2026-11-08 finding 13, MANDRAKEWORKFLOWS_FIX_AETHER_THREE_LEFTOVER_RULE_BREAKS_NEXT_UP). releaseBoost
    // inferred "pressed this step" from `time - pressedAt < dt`, so a contact in a ONE-substep step (age exactly dt) was
    // decayed at once while a four-substep step's last-substep contact (age dt/4) was not: behaviour depended on the
    // substep count. A 2000 pt/s face hits a resting dot; the dot must leave every contact step at the face's speed.
    do {
        func pushRun(maxSub: Int) -> (contact: [Double], after: Double, cap: Double) {
            var t = AetherTuning(); t.reserveEnabled = false; t.thermostatTau = .infinity; t.maxSubsteps = maxSub
            let st = settings { $0.boundary = .reflect; $0.densityPerMpt2 = 0; $0.attraction = 0; $0.repulsion = 0; $0.fieldStrength = 0 }
            let s = AetherSim(bounds: AetherRect(x: 0, y: 0, width: 4000, height: 400), settings: st, seed: 52, tuning: t,
                              obstacles: [AetherObstacle(id: 1, rect: AetherRect(x: 0, y: 100, width: 100, height: 200))], population: 0)
            let d = s.injectPoint(at: SIMD2(300, 200), velocity: .zero)!
            var x = 100.0, speeds: [Double] = []
            for _ in 0..<12 {
                x += 2000.0 / 12
                s.setGeometry([AetherObstacle(id: 1, rect: AetherRect(minX: x - 100, minY: 100, maxX: x, maxY: 300))], sweep: 1.0 / 12)
                for _ in 0..<Int((1.0 / 12 / s.tuning.dt).rounded()) {
                    let before = s.stats.pressed
                    s.step()
                    if s.stats.pressed > before { speeds.append(len2(s.vel[d])) }
                }
            }
            run(s, 1.5)
            return (speeds, len2(s.vel[d]), s.ceiling)
        }
        for m in [1, 4] {
            let r = pushRun(maxSub: m)
            check(r.contact.count >= 5, "boost release (\(m) substeps): the face pressed the dot in several steps", "\(r.contact.count)")
            check(!r.contact.isEmpty && r.contact.allSatisfy { $0 >= 0.97 * 2000 }, "boost release (\(m) substeps): the dot leaves EVERY contact step at the face's speed", "\(r.contact.map { Int($0) })")
            check(r.after <= r.cap + 1e-9, "boost release (\(m) substeps): released, it decays back under the ceiling", "\(r.after) > \(r.cap)")
        }
        let a = pushRun(maxSub: 1).contact, b = pushRun(maxSub: 4).contact
        check(!a.isEmpty && !b.isEmpty && abs(a[0] - b[0]) < 1e-6 * 2000, "boost release: the first contact's carry does not depend on the substep cap", "\(a.first ?? -1) vs \(b.first ?? -1)")
    }
    // MARK: rule break: initial and injected velocities respect the ceiling
    do {
        for seed in 1...6 as ClosedRange<UInt64> {
            let s = AetherSim(bounds: laptop, settings: settings { $0.motion = .living }, seed: seed)
            check(maxSpeed(s) <= s.ceiling + 1e-9, "rule: initial speeds are under the ceiling (seed \(seed))", "\(maxSpeed(s)) > \(s.ceiling)")
        }
        let r = AetherSim(bounds: laptop, settings: settings { $0.motion = .living; $0.boundary = .reservoir }, seed: 5)
        var worst = 0.0
        for _ in 0..<150 { r.step(); worst = max(worst, maxSpeed(r)) }
        check(r.stats.injected > 5, "rule: the reservoir injected points in this run", "\(r.stats.injected)")
        check(worst <= r.ceiling + 1e-9, "rule: injected points are under the ceiling right after every step", "\(worst) > \(r.ceiling)")
    }
    // MARK: rule break: coincident points separate
    do {
        var t = AetherTuning(); t.thermostatTau = .infinity; t.reserveEnabled = false
        let s = AetherSim(bounds: laptop, settings: settings { $0.motion = .living; $0.attraction = 0; $0.repulsion = 0; $0.temperatureVariation = 1 },
                          seed: 11, tuning: t, population: 0)
        let p = SIMD2(700.0, 500.0)
        let i = s.injectPoint(at: p, velocity: .zero)!, j = s.injectPoint(at: p, velocity: .zero)!
        s.step()
        let d = s.pos[i] - s.pos[j], sep = (d.x * d.x + d.y * d.y).squareRoot()
        check(sep >= 0.9 * s.settings.collisionDiameter, "rule: two coincident points are pushed apart in one step", "\(sep)")
        let m = (s.pos[i] + s.pos[j]) / 2
        check(abs(m.x - p.x) < 1e-6 && abs(m.y - p.y) < 1e-6, "rule: the separation is symmetric about their shared spot", "\(m)")
    }
    // MARK: rule break: the minimum-temperature floor recovers from exactly zero energy
    do {
        let s = AetherSim(bounds: laptop, settings: settings { $0.motion = .living; $0.temperatureVariation = 1; $0.minRmsSpeed = 10
                                                                $0.attraction = 0; $0.repulsion = 0; $0.chainForming = 0 }, seed: 13, population: 0)
        for k in 0..<5 { _ = s.injectPoint(at: SIMD2(300 + 100 * Double(k), 400), velocity: .zero) }
        check(s.meanSigma2() == 0, "floor: the test gas starts at exactly zero energy")
        run(s, 0.2)
        check(s.meanSigma2() >= 0.99 * 50 && maxSpeed(s) <= s.ceiling + 1e-9, "floor: zero energy is brought up to the floor, under the ceiling", "\(s.meanSigma2())")
    }

    // MARK: rule break: reserve placement sees the points seeded earlier in the same batch
    do {
        var t = AetherTuning(); t.refillTau = 0.05; t.thermostatTau = .infinity
        let st = settings { $0.motion = .living; $0.boundary = .reflect; $0.attraction = 0; $0.repulsion = 0; $0.densityPerMpt2 = 3000 }
        let g = AetherSim(bounds: AetherRect(x: 0, y: 0, width: 300, height: 300), settings: st, seed: 21, tuning: t,
                          obstacles: [AetherObstacle(id: 1, rect: AetherRect(x: 50, y: 50, width: 200, height: 200))])
        g.setGeometry([])
        var worst = Double.infinity
        for _ in 0..<12 {
            g.step()
            let a = g.pos.indices.filter { g.phase[$0] == .active && g.alpha[$0] < 1 && g.alpha[$0] <= 1.0 / 30 / t.fadeIn + 1e-9 }
            for x in a { for y in a where y > x { let d = g.pos[x] - g.pos[y]; worst = min(worst, (d.x * d.x + d.y * d.y).squareRoot()) } }
        }
        check(worst >= g.settings.collisionDiameter - 1e-9, "reserve: points seeded in one step never overlap one another", "closest \(worst) < \(g.settings.collisionDiameter)")
    }
}
