import Foundation

// Seeded, headless tests for app/macos/Aether.swift (design docs/design/2026-11-08-aether/03-merged.md). Short runs
// only (simulated seconds, not wall clock; no window, no Metal, no animation). Run: tests/swift/aether/run.sh
var failed = 0, passed = 0
func check(_ ok: Bool, _ name: String, _ detail: @autoclosure () -> String = "") {
    if ok { passed += 1 } else { failed += 1; print("FAIL: \(name) \(detail())") }
}
func obj(_ s: String) -> [String: Any] { (try! JSONSerialization.jsonObject(with: s.data(using: .utf8)!)) as! [String: Any] }
func run(_ sim: AetherSim, _ seconds: Double, every: ((AetherSim) -> Void)? = nil) {
    let n = Int((seconds / sim.tuning.dt).rounded())
    for _ in 0..<n { sim.step(); every?(sim) }
}
func anyInside(_ sim: AetherSim) -> Int { sim.pos.indices.filter { sim.activeInsideWall($0) }.count }
func maxSpeed(_ sim: AetherSim) -> Double {
    sim.pos.indices.filter { sim.phase[$0] == .active }.map { (sim.vel[$0].x * sim.vel[$0].x + sim.vel[$0].y * sim.vel[$0].y).squareRoot() }.max() ?? 0
}
let laptop = AetherRect(x: 0, y: 0, width: 1512, height: 945)   // 14" MacBook Pro, logical points (~1.43 M pt²)
func settings(_ f: (inout AetherSettings) -> Void) -> AetherSettings { var s = AetherSettings(); f(&s); return s }

if ProcessInfo.processInfo.environment["AETHER_NEW_ONLY"] == "1" { newTests(); print("\(passed) passed, \(failed) failed"); exit(failed == 0 ? 0 : 1) }

// MARK: settings plumbing (behaviors.json "aether")
do {
    let d = AetherSettings.parse(behaviorsJSON: "{}")
    check(d.motion == .settleWhileTyping, "default motion is living, settles while typing (ruling 1)")
    check(d.boundary == .thermal, "default boundary is thermal walls (ruling 2)")
    check(d.rmsSpeed == 27.5 && d.densityPerMpt2 == 100 && d.particleDiameter == 2.5, "defaults: the owner's 27.5 pt/s (Cool was too slow), Sparse 2.5 pt")
    let a = AetherSettings.parse(behaviorsJSON: #"{"aether":{"motion":"living","boundary":"reservoir","temperature":"warm","density":"dense","fieldStrength":"vivid","colour":"amber","brightness":7}}"#)
    check(a.motion == .living, "always-living is a setting (ruling 1)")
    check(a.boundary == .reservoir && a.rmsSpeed == 16 && a.densityPerMpt2 == 1000 && a.particleDiameter == 1.5,
          "named presets: reservoir, warm, dense 1.5 pt")
    check(a.fieldStrength == 1 && a.colour == "amber" && a.brightness == 3, "field, colour, brightness clamps")
    check(AetherSettings.parse(behaviorsJSON: #"{"aether":{"motion":"stir-settle"}}"#).motion == .stirAndSettle, "stir and settle is a setting")
    let b = AetherSettings.parse(behaviorsJSON: #"{"aether":{"temperature":true,"density":1,"particleSize":0,"boundary":"bogus"}}"#)
    check(b.rmsSpeed == AetherSettings().rmsSpeed, "a Boolean temperature is not a number")
    check(b.densityPerMpt2 == 1 && b.particleDiameter == 0.5, "numeric density and size clamp")
    check(b.boundary == .thermal, "unknown boundary falls back")
    check(AetherSettings.parse(behaviorsJSON: "not json") == AetherSettings(), "unreadable: defaults")
    check(aetherSelected(behaviorsJSON: #"{"backdrop":"aether"}"#) && !aetherSelected(behaviorsJSON: #"{"backdrop":"b07"}"#),
          "the Aether is a backdrop choice")
    check(aetherSelected(behaviorsJSON: #"{"backdrop":"b07","aether":{"enabled":true}}"#)
          && !aetherSelected(behaviorsJSON: #"{"aether":{"enabled":false}}"#) && !aetherSelected(behaviorsJSON: #"{"aether":{"enabled":1}}"#),
          "the Settings switch turns the Aether on, over any backdrop")
}

// MARK: quiet plan and clocks
do {
    check(aetherQuietPlan(hidden: false, meeting: true, locked: false, covered: false, reduceMotion: false, lowPower: false, batteryBelow20: false, thermal: 0) == .off, "meeting mode draws nothing")
    check(aetherQuietPlan(hidden: false, meeting: false, locked: false, covered: false, reduceMotion: true, lowPower: false, batteryBelow20: false, thermal: 0) == .still, "Reduce Motion holds a still frame")
    check(aetherQuietPlan(hidden: false, meeting: false, locked: false, covered: false, reduceMotion: false, lowPower: false, batteryBelow20: false, thermal: 2) == .still, "thermal serious holds still")
    check(aetherQuietPlan(hidden: false, meeting: false, locked: false, covered: false, reduceMotion: false, lowPower: false, batteryBelow20: false, thermal: 0) == .draw(fpsCap: 60), "normal draws, capped at 60")
    check(AetherClocks.geometryInterval(dragging: false, reconcile: false) == 0.5, "geometry 2 Hz calm")
    check(abs(AetherClocks.geometryInterval(dragging: true, reconcile: false) - 1.0 / 12) < 1e-12, "geometry 12 Hz dragging")
    check(AetherClocks.geometryInterval(dragging: false, reconcile: true) == 0, "reconcile at once")
    let sim = AetherSim(bounds: laptop, settings: AetherSettings(), seed: 1)
    sim.advance(by: 10)
    check(abs(sim.time - 4 * sim.tuning.dt) < 1e-9 && sim.heldTime > 9.8, "simulation clock: bounded catch-up, the rest held")
}

// MARK: population and density (merge correction 6)
do {
    let sparse = AetherSim(bounds: laptop, settings: AetherSettings(), seed: 2)
    check((140...150).contains(sparse.population), "Sparse is ~150 on the laptop screen", "\(sparse.population)")
    let dense = AetherSim(bounds: laptop, settings: settings { $0.densityPerMpt2 = 1000 }, seed: 2)
    check((1400...1500).contains(dense.population), "Dense is ~1 500 on the laptop screen", "\(dense.population)")
    let win = AetherObstacle(id: 1, rect: AetherRect(x: 200, y: 100, width: 800, height: 600))
    let covered = AetherSim(bounds: laptop, settings: settings { $0.densityPerMpt2 = 1000 }, seed: 2, obstacles: [win])
    check(anyInside(covered) == 0, "no point starts inside a window")
    let frac = Double(covered.activeCount()) / Double(covered.population)
    check(abs(frac - (1 - win.rect.expanded(by: covered.radius).area / laptop.area)) < 0.05, "covered share is dormant", "\(frac)")
}

// MARK: wall reflection (moving-wall rule u_n' = 2 w_n - u_n)
do {
    var t = AetherTuning(); t.thermostatTau = .infinity; t.reserveEnabled = false
    let s = settings { $0.boundary = .reflect; $0.densityPerMpt2 = 0; $0.attraction = 0; $0.repulsion = 0; $0.fieldStrength = 0 }
    let box = AetherRect(x: 0, y: 0, width: 400, height: 400)
    let w0 = AetherRect(x: 200, y: 0, width: 100, height: 400)
    // static wall: specular
    let a = AetherSim(bounds: box, settings: s, seed: 3, tuning: t, obstacles: [AetherObstacle(id: 1, rect: w0)], population: 0)
    let i = a.injectPoint(at: SIMD2(150, 200), velocity: SIMD2(30, 5))!
    run(a, 2)
    check(abs(a.vel[i].x + 30) < 1e-9 && abs(a.vel[i].y - 5) < 1e-9, "static wall reflects specularly", "\(a.vel[i])")
    check(a.pos[i].x < 200 - a.radius + 1e-6, "point stays outside the expanded wall")
    // approaching wall: the point leaves faster by 2 w
    let b = AetherSim(bounds: box, settings: s, seed: 3, tuning: t, obstacles: [AetherObstacle(id: 1, rect: w0)], population: 0)
    let j = b.injectPoint(at: SIMD2(185, 200), velocity: SIMD2(10, 0))!
    b.setGeometry([AetherObstacle(id: 1, rect: AetherRect(x: 190, y: 0, width: 100, height: 400))], sweep: 2)  // face at -5 pt/s
    run(b, 3)
    check(abs(b.vel[j].x + 20) < 1e-6, "approaching wall (5 pt/s) returns 10 pt/s as 20 pt/s", "\(b.vel[j])")
    // receding wall: slower
    let c = AetherSim(bounds: box, settings: s, seed: 3, tuning: t, obstacles: [AetherObstacle(id: 1, rect: w0)], population: 0)
    let k = c.injectPoint(at: SIMD2(185, 200), velocity: SIMD2(10, 0))!
    c.setGeometry([AetherObstacle(id: 1, rect: AetherRect(x: 216, y: 0, width: 100, height: 400))], sweep: 4)  // +4 pt/s
    run(c, 4)
    check(abs(c.vel[k].x + 2) < 1e-6, "receding wall (4 pt/s) returns 10 pt/s as 2 pt/s", "\(c.vel[k])")
    // thin fast obstacle crossing a point between geometry samples: swept, not missed
    let d = AetherSim(bounds: AetherRect(x: 0, y: 0, width: 2000, height: 400), settings: s, seed: 3, tuning: t,
                      obstacles: [AetherObstacle(id: 1, rect: AetherRect(x: 100, y: 0, width: 4, height: 400))], population: 0)
    let m = d.injectPoint(at: SIMD2(300, 200), velocity: SIMD2(0, 0))!
    d.setGeometry([AetherObstacle(id: 1, rect: AetherRect(x: 600, y: 0, width: 4, height: 400))], sweep: 1.0 / 12)
    var crossedInside = false
    run(d, 0.2) { if $0.activeInsideWall(m) { crossedInside = true } }
    check(!crossedInside, "a 4 pt wall sweeping 500 pt in one sample never leaves the point inside")
    check(d.phase[m] == .active && d.pos[m].x > 604, "the point was pushed ahead, never tunnelled or removed", "\(d.pos[m]) \(d.phase[m])")
    run(d, 1.5); check(maxSpeed(d) <= d.ceiling + 1e-9, "once released, the pushed point is back under the ceiling", "\(maxSpeed(d))")
}

// MARK: adiabatic compression (slow piston, closed box, thermostat off): T x A ~ constant in 2-D (gamma = 2)
do {
    var t = AetherTuning(); t.thermostatTau = .infinity; t.reserveEnabled = false; t.ceilingOverride = 1000; t.crowdFactor = 1e9
    let s = settings { $0.boundary = .reflect; $0.rmsSpeed = 20; $0.collisionDiameter = 2; $0.attraction = 0; $0.repulsion = 0; $0.fieldStrength = 0 }
    let start = AetherRect(x: 400, y: 0, width: 200, height: 400)   // piston face at x = 400
    let lattice = AetherSim(bounds: AetherRect(x: 0, y: 0, width: 600, height: 400), settings: s, seed: 4, tuning: t,
                            obstacles: [AetherObstacle(id: 1, rect: start)], population: 0)
    for gy in 0..<20 { for gx in 0..<30 {
        lattice.injectPoint(at: SIMD2(8 + Double(gx) * 12.9, 8 + Double(gy) * 19.4), velocity: .zero)
    } }
    lattice.stir()
    run(lattice, 3)                      // equilibrate
    let r = lattice.radius
    // Hard discs are not ideal: subtract the excluded area N x (pi d^2 / 2) (second virial coefficient in 2-D).
    func area(_ x: Double) -> Double { (x - r - r) * (400 - 2 * r) - 600 * Double.pi * 4 / 2 }
    let T0 = lattice.meanSigma2(), A0 = area(400)
    var x = 400.0
    for _ in 0..<40 {                     // 400 -> 240 pt over 40 s: 4 pt/s against a ~20 pt/s RMS speed
        x -= 4
        lattice.setGeometry([AetherObstacle(id: 1, rect: AetherRect(minX: x, minY: 0, maxX: 600, maxY: 400))], sweep: 1)
        run(lattice, 1)
    }
    run(lattice, 1)
    let T1 = lattice.meanSigma2(), A1 = area(x)
    let ratio = (T1 * A1) / (T0 * A0)
    check(T1 > T0 * 1.4, "compression heats the gas", "T0 \(T0) T1 \(T1)")
    check(abs(ratio - 1) < 0.10, "adiabatic: T x A conserved within 10 %", "ratio \(ratio)")
    // Per-face jump rule: dragging the left face 8 pt while the off-screen right face jumps 200 pt still sweeps.
    let pf = AetherSim(bounds: AetherRect(x: 0, y: 0, width: 600, height: 400), settings: s, seed: 4, tuning: t,
                       obstacles: [AetherObstacle(id: 1, rect: start)], population: 0)
    for gy in 0..<20 { for gx in 0..<30 { pf.injectPoint(at: SIMD2(8 + Double(gx) * 12.9, 8 + Double(gy) * 19.4), velocity: .zero) } }
    pf.stir(); run(pf, 3)
    pf.setGeometry([AetherObstacle(id: 1, rect: AetherRect(minX: 392, minY: 0, maxX: 800, maxY: 400))], sweep: 0.8)
    run(pf, 1)
    check(pf.stats.covered == 0 && pf.stats.trapped == 0 && pf.activeCount() == 600, "a far face's jump does not teleport the near face", "\(pf.stats)")
    check(lattice.activeCount() == 600, "closed box conserves N under slow compression", "\(lattice.activeCount()) \(lattice.stats)")
}

// MARK: free expansion (partition removed, reserve off): no cooling
do {
    var t = AetherTuning(); t.thermostatTau = .infinity; t.reserveEnabled = false
    let s = settings { $0.boundary = .reflect; $0.rmsSpeed = 8; $0.densityPerMpt2 = 2000; $0.attraction = 0; $0.repulsion = 0; $0.fieldStrength = 0 }
    let box = AetherRect(x: 0, y: 0, width: 600, height: 400)
    let half = AetherObstacle(id: 1, rect: AetherRect(x: 300, y: 0, width: 300, height: 400))
    let sim = AetherSim(bounds: box, settings: s, seed: 5, tuning: t, obstacles: [half])
    run(sim, 2)
    let T0 = sim.meanSigma2(), N0 = sim.activeCount()
    sim.setGeometry([])                  // the window closes
    run(sim, 60)
    let right = sim.activeCount(in: AetherRect(x: 300, y: 0, width: 300, height: 400))
    check(abs(sim.meanSigma2() / T0 - 1) < 0.02, "free expansion does not cool", "\(T0) -> \(sim.meanSigma2())")
    check(sim.activeCount() == N0, "free expansion conserves N")
    check(right > N0 / 4, "the gas streams into the vacuum", "\(right) of \(N0)")
}

// MARK: speed limits and the presentation clock (correction 2, 3; acceptance 6)
do {
    let dense = settings { $0.densityPerMpt2 = 1000; $0.particleDiameter = 1.5 }
    let sim = AetherSim(bounds: laptop, settings: dense, seed: 6)
    run(sim, 2)
    let calm = sim.frameInterval()!
    check(1 / calm >= 30 - 1e-9 && 1 / calm <= 60 + 1e-9, "a moving gas presents at 30-60 fps (2-24 fps read as jumps)", "\(1 / calm) fps")
    let fast = sim.injectPoint(at: SIMD2(700, 400), velocity: SIMD2(5000, 3000))!
    run(sim, 0.1)
    check(maxSpeed(sim) <= sim.ceiling + 1e-9, "acceptance 6: a 5 800 pt/s point is held to the ceiling", "\(maxSpeed(sim))")
    let withFast = sim.frameInterval()!
    check(abs(1 / withFast - 1 / calm) < 1.5, "acceptance 6: one fast point does not raise the frame rate", "\(1 / calm) -> \(1 / withFast)")
    _ = fast
    // Dense step cost sanity is NOT measured here (no benchmarks off Lab Wi-Fi).
}

// MARK: sprites stir the gas (owner, 2026-11-08: "stir it with their passing rather than just moving over it")
do {
    check(AetherSettings.parse(behaviorsJSON: #"{"aether":{"stirring":"strong"}}"#).stirring == 1.2
          && AetherSettings.parse(behaviorsJSON: #"{"aether":{"stirring":"off"}}"#).stirring == 0
          && AetherSettings().stirring >= 0.5 && AetherSettings().stirring <= 0.9, "stirring: off / subtle / strong, default subtle-to-moderate")
    // A sprite (r 20) walks +x at 60 pt/s through a still, floor-free gas, positions arriving at 10 Hz as the stage
    // sends them. Points along its path must end with net velocity along +x, and none may sit inside its body.
    func walk(_ stirring: Double) -> (along: Double, across: Double, inside: Int, sim: AetherSim) {
        var t = AetherTuning(); t.thermostatTau = .infinity
        let s = settings { $0.boundary = .reflect; $0.rmsSpeed = 0; $0.minRmsSpeed = 0; $0.motion = .living
                           $0.fieldStrength = 0; $0.stirring = stirring; $0.attraction = 0; $0.repulsion = 0; $0.densityPerMpt2 = 1500 }
        let sim = AetherSim(bounds: AetherRect(x: 0, y: 0, width: 800, height: 300), settings: s, seed: 41, tuning: t)
        var x = 100.0, inside = 0
        for k in 0..<(30 * 6) {                    // 6 s, 100 -> 460
            if k % 3 == 0 { x = 100 + 60 * Double(k) / 30 }
            sim.setSprites([AetherSprite(pos: SIMD2(x, 150), radius: 20, id: "a")])
            sim.step()
            if k % 3 == 2 {
                for i in sim.pos.indices where sim.phase[i] == .active {
                    let d = sim.pos[i] - SIMD2(x, 150); if (d.x * d.x + d.y * d.y).squareRoot() < 20 - 1e-6 { inside += 1 }
                }
            }
        }
        let path = AetherRect(x: 150, y: 120, width: 250, height: 60)
        var vx = 0.0, vy = 0.0, n = 0.0
        for i in sim.pos.indices where sim.phase[i] == .active && path.contains(sim.pos[i]) { vx += sim.vel[i].x; vy += sim.vel[i].y; n += 1 }
        return (vx / max(n, 1), vy / max(n, 1), inside, sim)
    }
    let on = walk(0.7), off = walk(0)
    check(on.sim.spriteVelocities.first.map { abs($0.x - 60) < 15 && abs($0.y) < 1 } ?? false, "the sim estimates the sprite's velocity from 10 Hz positions",
          "\(on.sim.spriteVelocities)")
    check(on.along > 5 && on.along > 4 * abs(on.across), "a moving sprite leaves points with net velocity along its path", "vx \(on.along) vy \(on.across)")
    check(abs(off.along) < 0.5, "stirring off: the gas stays still", "\(off.along)")
    check(on.inside == 0, "no point stays inside a sprite's body", "\(on.inside)")
    check(on.sim.pos.indices.allSatisfy { on.sim.phase[$0] != .active || (on.sim.vel[$0].x * on.sim.vel[$0].x + on.sim.vel[$0].y * on.sim.vel[$0].y).squareRoot() <= on.sim.ceiling + 1e-9 },
          "the wake respects the speed ceiling")
    // The wake settles under Cooling (stir-and-settle, 10 s cooling, floor 0): after 20 s it is near still.
    let w = on.sim; w.settings.motion = .stirAndSettle; w.settings.coolingSeconds = 10; w.setSprites([])
    run(w, 20)
    check(w.meanSigma2() < 0.05 * max(1e-9, (on.along * on.along)), "the wake settles under the cooling setting", "\(w.meanSigma2())")
}

// MARK: colour picker (owner, 2026-11-08: "just make a color picker")
do {
    let h = AetherSettings.parse(behaviorsJSON: ##"{"aether":{"colour":"#FF8000"}}"##)
    check(h.colour == "#ff8000" && abs(h.rgb.x - 1) < 1e-9 && abs(h.rgb.y - 128.0 / 255) < 1e-9 && h.rgb.z == 0, "a picker hex is kept and drawn as given")
    check(AetherSettings.parse(behaviorsJSON: #"{"aether":{"colour":"amber"}}"#).rgb == SIMD3(1.0, 0.68, 0.18), "presets keep their phosphor tone")
    for bad in ["#12345", "#gggggg", "red", "#1234567"] {
        check(AetherSettings.parse(behaviorsJSON: "{\"aether\":{\"colour\":\"\(bad)\"}}").colour == "green", "a bad colour falls back: \(bad)")
    }
}

// MARK: cooling (drag) and the minimum temperature (owner, 2026-11-08)
do {
    let p = AetherSettings.parse(behaviorsJSON: #"{"aether":{"cooling":30,"minTemperature":2}}"#)
    check(p.coolingSeconds == 30 && p.minRmsSpeed == 2, "cooling and minimum temperature persist in behaviors.json")
    let q = AetherSettings.parse(behaviorsJSON: #"{"aether":{"cooling":1,"minTemperature":99}}"#)
    check(q.coolingSeconds == 5 && q.minRmsSpeed == 10, "and clamp")
    let d = AetherSettings()
    check(d.coolingSeconds >= 30 && d.coolingSeconds <= 60 && d.minRmsSpeed >= 1 && d.minRmsSpeed <= 2,
          "defaults: settles in 30-60 s (glides), floor 1-2 pt/s")
    func rms(_ s: AetherSim) -> Double { (2 * s.meanSigma2()).squareRoot() }
    // Slow cooling keeps a stirred gas moving far longer than quick cooling.
    func stirred(_ secs: Double) -> Double {
        let s = AetherSim(bounds: laptop, settings: settings { $0.motion = .stirAndSettle; $0.coolingSeconds = secs; $0.attraction = 0; $0.repulsion = 0 }, seed: 31)
        run(s, 10); return rms(s)
    }
    let slow = stirred(45), quick = stirred(6)
    check(slow > 3 * quick, "Cooling (drag) slows the settle: 45 s keeps the gas moving after 10 s, 6 s does not", "\(slow) vs \(quick)")
    // After a long settle (typing, and stir-and-settle) the gas never freezes: RMS stays at or above the floor.
    for m in [AetherMotion.settleWhileTyping, .stirAndSettle] {
        let s = AetherSim(bounds: laptop, settings: settings { $0.motion = m; $0.coolingSeconds = 5; $0.minRmsSpeed = 1.5; $0.attraction = 0; $0.repulsion = 0 }, seed: 32)
        var lowest = Double.infinity
        for k in 0..<(30 * 60) { s.step(typing: true); if k > 30 * 20 { lowest = min(lowest, rms(s)) } }
        let resting = s.pos.indices.filter { s.phase[$0] == .active && s.vel[$0] == .zero }.count
        check(lowest >= 1.5 - 1e-6, "\(m.rawValue): after a long settle RMS stays at or above the floor", "\(lowest)")
        check(resting == 0, "\(m.rawValue): no point is snapped to rest above a floor", "\(resting)")
        check(s.frameInterval() != nil, "\(m.rawValue): a floored gas keeps presenting (never a frozen frame)")
    }
    // Typing still calms the gas: from the entry temperature down toward the floor.
    let t = AetherSim(bounds: laptop, settings: settings { $0.motion = .settleWhileTyping; $0.attraction = 0; $0.repulsion = 0 }, seed: 33)
    run(t, 2); let before = rms(t)
    for _ in 0..<(30 * 3) { t.step(typing: true) }
    check(rms(t) < 0.3 * before && rms(t) >= t.settings.minRmsSpeed - 1e-6, "typing calms the gas, to the floor", "\(before) -> \(rms(t))")
}

// MARK: smooth presentation (owner, 2026-11-08: "discrete jumps")
do {
    // Slow drift at the shipped temperature, presented the way the host does: advance by the frame interval it asks
    // for, draw presentedPos. No presented point may jump more than ~1 pt between frames (a step is 1/30 s).
    let s = settings { $0.motion = .living; $0.rmsSpeed = 27.5; $0.attraction = 0; $0.repulsion = 0 }
    let sim = AetherSim(bounds: laptop, settings: s, seed: 21)
    run(sim, 1)
    var last = sim.pos.indices.map { sim.presentedPos($0) }, lastPhase = sim.phase
    var worst = 0.0, frames = 0, worstRaw = 0.0, rawLast = sim.pos
    var t = 0.0
    while t < 3 {
        let f = sim.frameInterval() ?? (1.0 / 30); sim.advance(by: f); t += f; frames += 1
        for i in sim.pos.indices where sim.phase[i] == .active && lastPhase[i] == .active {
            let q = sim.presentedPos(i), d = q - last[i], r = sim.pos[i] - rawLast[i]
            worst = max(worst, (d.x * d.x + d.y * d.y).squareRoot()); worstRaw = max(worstRaw, (r.x * r.x + r.y * r.y).squareRoot())
        }
        last = sim.pos.indices.map { sim.presentedPos($0) }; lastPhase = sim.phase; rawLast = sim.pos
    }
    check(Double(frames) / 3 >= 29, "slow drift presents at >= 30 fps", "\(Double(frames) / 3)")
    // Owner card 2026-11-08 ~18:35 PST ("30 calm, 60 when pushed"): calm drift now presents at 30 fps, so a dot at
    // the ceiling (55 pt/s here) moves up to ceiling / 30 = 1.83 pt per frame (it was ~0.9 pt at 60 fps). The bound is
    // that, not the old 1.2 pt: no presented point may move faster than the ceiling between frames.
    check(worst <= sim.ceiling / 30 + 1e-6, "interpolated output never jumps more than the ceiling allows in one 30 fps frame", "\(worst) pt (raw \(worstRaw))")
    // Interpolation is continuous across a step boundary: just before the step == just after it.
    let i = sim.pos.indices.first { sim.phase[$0] == .active }!
    sim.advance(by: sim.tuning.dt * (1 - sim.interpolation) - 1e-9)
    let before = sim.presentedPos(i); sim.advance(by: 2e-9); let after = sim.presentedPos(i)
    check(abs(before.x - after.x) < 0.05 && abs(before.y - after.y) < 0.05, "no step at the step boundary", "\(before) \(after)")
}

// MARK: motion styles
do {
    let living = AetherSim(bounds: laptop, settings: settings { $0.motion = .living }, seed: 7)
    run(living, 3)
    for _ in 0..<60 { living.step(typing: true) }
    check(living.meanSigma2() > 1, "always living keeps moving while typing", "\(living.meanSigma2())")
    let settle = AetherSim(bounds: laptop, settings: settings { $0.motion = .settleWhileTyping; $0.minRmsSpeed = 0 }, seed: 7)
    run(settle, 3)
    for _ in 0..<(30 * 3) { settle.step(typing: true) }
    check(settle.frameInterval() == nil, "with the floor at 0, settle-while-typing settles FULLY (no frames), not stepped", "\(settle.meanSigma2())")
    run(settle, 15)
    check(settle.meanSigma2() > 2, "and warms back after typing stops", "\(settle.meanSigma2())")
    let still = AetherSim(bounds: laptop, settings: settings { $0.motion = .stirAndSettle; $0.rmsSpeed = 3; $0.minRmsSpeed = 0; $0.coolingSeconds = 7.5 }, seed: 7)
    run(still, 15)
    check(still.frameInterval() == nil, "stir and settle: still within 15 s")
    still.stir(); still.step()
    check(still.frameInterval() != nil, "stir wakes it")
    run(still, 15)
    check(still.frameInterval() == nil, "and it settles again")
}

// MARK: thermal walls relax temperature, reflecting box conserves N, reservoir refills
do {
    var t = AetherTuning(); t.thermostatTau = .infinity
    let hot = settings { $0.boundary = .thermal; $0.rmsSpeed = 3; $0.densityPerMpt2 = 400; $0.attraction = 0; $0.repulsion = 0; $0.temperatureVariation = 0 }
    let sim = AetherSim(bounds: AetherRect(x: 0, y: 0, width: 300, height: 300), settings: hot, seed: 8, tuning: t)
    sim.stir(); sim.stir(); sim.stir()
    let T0 = sim.meanSigma2()
    run(sim, 60)
    check(sim.meanSigma2() < T0 * 0.6, "thermal walls cool a stirred gas toward the entry temperature", "\(T0) -> \(sim.meanSigma2())")
    let res = AetherSim(bounds: AetherRect(x: 0, y: 0, width: 400, height: 400),
                        settings: settings { $0.boundary = .reservoir; $0.rmsSpeed = 8; $0.densityPerMpt2 = 1000; $0.attraction = 0; $0.repulsion = 0 },
                        seed: 8, population: 0)
    run(res, 60)
    let want = 1000.0 / 1e6 * 160_000
    check(Double(res.activeCount()) > 0.5 * want && Double(res.activeCount()) < 1.5 * want, "reservoir fills an empty screen toward density",
          "\(res.activeCount()) vs \(want)")
}

// MARK: FORCES (ruling 8, owner 2026-11-08: "a short-range attraction and a long range repulsion... bonding through
// actual forces rather than constraints")
do {
    let p = AetherSettings.parse(behaviorsJSON: #"{"aether":{"attraction":2,"attractionRange":9,"repulsion":-1,"repulsionRange":3,"chainForming":0.4}}"#)
    check(p.attraction == 2 && p.attractionRange == AetherSettings.maxAttractionRange && p.repulsion == 0 && p.repulsionRange == 3 && p.chainForming == 0.4,
          "force settings persist in behaviors.json and clamp")
    let d = AetherSettings()
    check(d.attraction > 0 && d.repulsion > 0 && d.chainForming > 0, "forces are on by default")
    // Energy: default settings, 10 simulated minutes, no thermostat pinning it: bounded, never below the floor.
    let e = AetherSim(bounds: laptop, settings: AetherSettings(), seed: 61)
    let s0 = e.settings.rmsSpeed * e.settings.rmsSpeed / 2, lo = e.settings.minRmsSpeed * e.settings.minRmsSpeed / 2
    var peak = 0.0, low = Double.infinity
    run(e, 600) { peak = max(peak, $0.meanSigma2()); low = min(low, $0.meanSigma2()) }
    check(peak < 1.25 * s0, "defaults: mean energy stays bounded for 10 simulated minutes", "peak \(peak) vs entry \(s0)")
    check(low >= lo - 1e-9, "defaults: the floor holds with the forces on", "\(low)")
    // Settle under forces: typing and stir-and-settle still stop at the floor, not below it.
    let t = AetherSim(bounds: laptop, settings: settings { $0.motion = .stirAndSettle; $0.coolingSeconds = 5; $0.densityPerMpt2 = 600 }, seed: 62)
    var tl = Double.infinity; run(t, 60) { if $0.time > 20 { tl = min(tl, $0.meanSigma2()) } }
    check(tl >= lo - 1e-9, "stir-and-settle with forces: RMS stays at or above the floor", "\(tl)")
    // Clusters: attraction on (repulsion off) raises the mean bonded-neighbour count far above an ideal gas's.
    func cool(_ f: (inout AetherSettings) -> Void, secs: Double, seed: UInt64 = 63, bounds: AetherRect = laptop) -> AetherSim {
        let s = settings { $0.motion = .living; $0.densityPerMpt2 = 600; $0.rmsSpeed = 3; $0.attraction = 2; $0.chainForming = 0; $0.repulsion = 0; f(&$0) }
        let sim = AetherSim(bounds: bounds, settings: s, seed: seed); run(sim, secs); return sim
    }
    let ideal = cool({ $0.attraction = 0 }, secs: 60), drops = cool({ _ in }, secs: 60)
    check(drops.bondStats().neighbours > 0.5 && drops.bondStats().neighbours > 10 * ideal.bondStats().neighbours,
          "attraction on, repulsion off: clusters form (mean neighbour count rises)", "\(ideal.bondStats().neighbours) -> \(drops.bondStats().neighbours)")
    // Repulsion spreads the clusters apart: the median nearest-cluster distance rises.
    func spacing(_ sim: AetherSim) -> Double {
        let c = sim.bondStats().clusters
        var nn = c.indices.map { i in c.indices.filter { $0 != i }.map { j -> Double in let v = c[i] - c[j]; return (v.x * v.x + v.y * v.y).squareRoot() }.min() ?? 0 }
        nn.sort(); return nn.isEmpty ? 0 : nn[nn.count / 2]
    }
    let spread = cool({ $0.repulsion = 1 }, secs: 120), packed = cool({ _ in }, secs: 120)
    check(spacing(spread) > 1.12 * spacing(packed), "adding repulsion keeps clusters farther apart",
          "\(spacing(packed)) -> \(spacing(spread)) pt")
    // Needles: with chain forming on, head-to-tail chains average 3+ at a cool temperature, longer than droplets give.
    let box = AetherRect(x: 0, y: 0, width: 400, height: 400)
    let needles = cool({ $0.densityPerMpt2 = 3000; $0.chainForming = 1 }, secs: 60, seed: 9, bounds: box)
    let blobs = cool({ $0.densityPerMpt2 = 3000; $0.chainForming = 0 }, secs: 60, seed: 9, bounds: box)
    let nl = needles.bondStats(), bl = blobs.bondStats()
    check(nl.chainLength >= 3, "chain forming on: mean chain length >= 3 at a cool temperature", "\(nl.chainLength) over \(nl.chains)")
    check(nl.chainLength > 1.3 * bl.chainLength && nl.neighbours < bl.neighbours,
          "chain forming makes needles (longer chains, fewer neighbours) where attraction alone makes droplets",
          "len \(bl.chainLength) -> \(nl.chainLength), nb \(bl.neighbours) -> \(nl.neighbours)")
    // Momentum: the pair force and its friction are equal and opposite.
    var mt = AetherTuning(); mt.thermostatTau = .infinity
    let m = AetherSim(bounds: box, settings: settings { $0.boundary = .reflect; $0.rmsSpeed = 3; $0.minRmsSpeed = 0; $0.motion = .living
                                                          $0.repulsion = 0; $0.chainForming = 1 }, seed: 64, tuning: mt, population: 0)
    let a = m.injectPoint(at: SIMD2(196, 200), velocity: SIMD2(0.5, 0.2))!, b = m.injectPoint(at: SIMD2(203, 201), velocity: SIMD2(-0.4, 0))!
    let before = m.vel[a] + m.vel[b]; run(m, 0.5); let after = m.vel[a] + m.vel[b]
    check(abs(after.x - before.x) < 1e-9 && abs(after.y - before.y) < 1e-9, "the attraction conserves momentum", "\(before) -> \(after)")
    let dv = m.pos[b] - m.pos[a]
    check((dv.x * dv.x + dv.y * dv.y).squareRoot() < m.attractionCutoff, "a slow pair inside the well stays bound")
    // The widest reach still finds its partner: collision 8 pt, range 3 (cutoff 24 pt); two still points 16.2 pt apart
    // straddle two cells of an ungrown 16 pt grid. They must pull together.
    let w = AetherSim(bounds: box, settings: settings { $0.boundary = .reflect; $0.rmsSpeed = 3; $0.minRmsSpeed = 0; $0.motion = .living; $0.collisionDiameter = 8
                                                          $0.attractionRange = AetherSettings.maxAttractionRange; $0.repulsion = 0; $0.chainForming = 0 },
                      seed: 66, tuning: mt, population: 0)
    let wa = w.injectPoint(at: SIMD2(15.9, 200), velocity: .zero)!, wb = w.injectPoint(at: SIMD2(32.1, 200), velocity: .zero)!
    w.step()
    check(w.vel[wa].x > 1e-6 && w.vel[wb].x < -1e-6, "the widest attraction range is found in one ring of the grid", "\(w.vel[wa]) \(w.vel[wb])")
    // CPU budget without a benchmark: deterministic work counters per point per step.
    func cost(_ f: (inout AetherSettings) -> Void) -> (pairs: Double, forces: Double) {
        let sim = AetherSim(bounds: laptop, settings: settings { $0.motion = .living; $0.densityPerMpt2 = 1000; $0.particleDiameter = 1.5; f(&$0) }, seed: 65)
        run(sim, 30)
        return (Double(sim.work.pairChecks) / Double(sim.work.pointSteps), Double(sim.work.forceEvals) / Double(sim.work.pointSteps))
    }
    let dflt = cost { _ in }, worst = cost { $0.densityPerMpt2 = 2000; $0.attraction = 3; $0.attractionRange = AetherSettings.maxAttractionRange
                                             $0.repulsion = 2; $0.repulsionRange = 4; $0.collisionDiameter = 8; $0.chainForming = 1 }
    check(dflt.pairs < 15 && dflt.forces < 15, "Dense at default ranges: under 15 pair checks per point per step", "\(dflt)")
    check(worst.pairs < 45 && worst.forces < 45, "every slider at its maximum: under 3x that", "\(worst)")
}

// MARK: sprite field does no work
do {
    var t = AetherTuning(); t.thermostatTau = .infinity
    let s = settings { $0.boundary = .reflect; $0.fieldStrength = 2; $0.stirring = 0; $0.attraction = 0; $0.repulsion = 0 }
    let sim = AetherSim(bounds: AetherRect(x: 0, y: 0, width: 400, height: 400), settings: s, seed: 13, tuning: t, population: 0)
    let i = sim.injectPoint(at: SIMD2(180, 200), velocity: SIMD2(0, 3))!
    sim.setSprites([AetherSprite(pos: SIMD2(200, 200), radius: 30)])
    let v0 = sim.vel[i]
    run(sim, 2)
    let sp0 = (v0.x * v0.x + v0.y * v0.y).squareRoot(), sp1 = (sim.vel[i].x * sim.vel[i].x + sim.vel[i].y * sim.vel[i].y).squareRoot()
    check(abs(sp1 - sp0) < 1e-9, "the field deflects without changing speed")
    check(abs(sim.vel[i].x - v0.x) > 0.1, "and it does deflect")
}

// MARK: windows push, never wipe (owner ruling 2026-11-08, "Push, replace wipe")
do {
    // A 200 x 300 window's right face sweeps +x through a field at a given speed, sampled at 12 Hz (drag) or 2 Hz
    // (calm). Reserve off, so any loss would show: the count must hold, nothing may end inside, and after release
    // every speed is back under the ceiling with the total energy bounded.
    func sweepThrough(speed: Double, interval: Double, seconds: Double, seed: UInt64)
        -> (lost: Int, inside: Int, maxAfter: Double, energyRatio: Double, sim: AetherSim) {
        var t = AetherTuning(); t.reserveEnabled = false
        let s = settings { $0.densityPerMpt2 = 1000; $0.particleDiameter = 1.5; $0.attraction = 0; $0.repulsion = 0; $0.motion = .living }
        var w = AetherRect(x: 50, y: 300, width: 200, height: 300)
        let sim = AetherSim(bounds: laptop, settings: s, seed: seed, tuning: t, obstacles: [AetherObstacle(id: 9, rect: w)])
        run(sim, 1)
        let N0 = sim.activeCount(), E0 = sim.meanSigma2() * Double(N0)
        var inside = 0, elapsed = 0.0
        while elapsed < seconds - 1e-9 {
            w.minX += speed * interval; w.maxX += speed * interval
            sim.setGeometry([AetherObstacle(id: 9, rect: w)], sweep: interval)
            for _ in 0..<Int(interval / sim.tuning.dt + 0.5) { sim.step(); inside = max(inside, anyInside(sim)) }
            elapsed += interval
        }
        run(sim, 2) { inside = max(inside, anyInside($0)) }
        let E1 = sim.meanSigma2() * Double(sim.activeCount())
        return (N0 - sim.activeCount(), inside, maxSpeed(sim), E1 / max(E0, 1e-9), sim)
    }
    for (name, v, dt, secs) in [("slow 60 pt/s drag", 60.0, 1.0 / 12, 4.0), ("fast 2000 pt/s drag", 2000.0, 1.0 / 12, 0.5),
                                ("calm-read 600 pt/s (2 Hz)", 600.0, 0.5, 1.5)] {
        let r = sweepThrough(speed: v, interval: dt, seconds: secs, seed: 51)
        check(r.lost == 0, "push: \(name) removes no dots", "lost \(r.lost) \(r.sim.stats)")
        check(r.sim.stats.covered == 0 && r.sim.stats.trapped == 0 && r.sim.stats.crowded == 0, "push: \(name) covers, traps and fades none", "\(r.sim.stats)")
        check(r.inside == 0, "push: \(name) leaves no dot inside the window (no tunnelling)", "\(r.inside)")
        check(r.maxAfter <= r.sim.ceiling + 1e-9, "push: \(name) speeds back under the ceiling 2 s after release", "\(r.maxAfter)")
        check(r.energyRatio < 3, "push: \(name) energy bounded (no explosion)", "x\(r.energyRatio)")
    }
    // One dot directly in the path of a 2000 pt/s face: pushed ahead, outside the window, active.
    var t = AetherTuning(); t.reserveEnabled = false; t.thermostatTau = .infinity
    let s = settings { $0.boundary = .reflect; $0.densityPerMpt2 = 0; $0.attraction = 0; $0.repulsion = 0; $0.fieldStrength = 0 }
    let one = AetherSim(bounds: AetherRect(x: 0, y: 0, width: 2000, height: 400), settings: s, seed: 52, tuning: t,
                        obstacles: [AetherObstacle(id: 1, rect: AetherRect(x: 0, y: 100, width: 100, height: 200))], population: 0)
    let d = one.injectPoint(at: SIMD2(300, 200), velocity: .zero)!
    var x = 100.0
    for _ in 0..<6 { x += 2000.0 / 12; one.setGeometry([AetherObstacle(id: 1, rect: AetherRect(minX: x - 100, minY: 100, maxX: x, maxY: 300))], sweep: 1.0 / 12); run(one, 1.0 / 12) }
    check(one.phase[d] == .active && one.pos[d].x >= x + one.radius - 1e-6, "push: a 2000 pt/s face carries the dot ahead of it", "\(one.pos[d]) face \(x)")
    check(maxSpeed(one) > one.ceiling, "push: a pressed dot may exceed the ceiling while in contact", "\(maxSpeed(one))")
    run(one, 1)
    check(maxSpeed(one) <= one.ceiling + 1e-9, "push: once free it relaxes back under the ceiling", "\(maxSpeed(one))")

    // Pile-up: a 120 pt-tall face pushes a dense field at 150 pt/s for 4 s. The pile must spill round the corners: dots
    // that started ahead of the face end up beside or behind it, none are lost, and the pile ahead stays bounded.
    let ps = settings { $0.densityPerMpt2 = 1500; $0.particleDiameter = 1.5; $0.attraction = 0; $0.repulsion = 0; $0.motion = .living }
    var pt = AetherTuning(); pt.reserveEnabled = false
    var pw = AetherRect(x: 40, y: 400, width: 100, height: 120)
    let pile = AetherSim(bounds: laptop, settings: ps, seed: 53, tuning: pt, obstacles: [AetherObstacle(id: 2, rect: pw)])
    run(pile, 1)
    let ahead = pile.pos.indices.filter { pile.phase[$0] == .active && pile.pos[$0].x > 140 && pile.pos[$0].x < 740
                                           && pile.pos[$0].y > 400 && pile.pos[$0].y < 520 }
    let N0 = pile.activeCount()
    var worstPile = 0
    for k in 0..<48 {
        pw.minX += 150.0 / 12; pw.maxX += 150.0 / 12
        pile.setGeometry([AetherObstacle(id: 2, rect: pw)], sweep: 1.0 / 12)
        run(pile, 1.0 / 12)
        if k > 12 { worstPile = max(worstPile, pile.activeCount(in: AetherRect(minX: pw.maxX, minY: pw.minY, maxX: pw.maxX + 15, maxY: pw.maxY))) }
    }
    let spilled = ahead.filter { pile.phase[$0] == .active && pile.pos[$0].x < pw.maxX }.count
    check(pile.activeCount() == N0, "pile-up: no dot lost (none faded by the crowding cap)", "\(N0) -> \(pile.activeCount()) \(pile.stats)")
    check(ahead.count > 50 && spilled * 4 >= ahead.count * 3, "pile-up: three quarters of the dots ahead spill past the corners within 4 s (spill, not just diffusion)", "\(spilled) of \(ahead.count)")
    check(worstPile <= 45, "pile-up: the pile ahead of the face stays bounded (without the spill it reaches ~70)", "\(worstPile)")

    // A huge jump (reconcile, 1000 pt): the face snaps, and the dots it lands on are pushed out, not removed.
    let big = AetherSim(bounds: laptop, settings: ps, seed: 54, tuning: pt, obstacles: [AetherObstacle(id: 3, rect: AetherRect(x: 0, y: 0, width: 300, height: 300))])
    run(big, 1)
    let B0 = big.activeCount()
    big.setGeometry([AetherObstacle(id: 3, rect: AetherRect(x: 1000, y: 400, width: 300, height: 300))], sweep: 0)
    run(big, 1)
    check(big.activeCount() == B0 && big.stats.pushedOut > 20 && anyInside(big) == 0, "teleport: dots under a snapped window are pushed out, not removed",
          "\(B0) -> \(big.activeCount()) \(big.stats)")
    // A window that APPEARS on top of dots (a new id: it cannot push) sends them dormant; the reserve gives them back
    // where it later reveals.
    let app = AetherSim(bounds: laptop, settings: ps, seed: 55, tuning: pt)
    run(app, 1)
    app.setGeometry([AetherObstacle(id: 4, rect: AetherRect(x: 400, y: 200, width: 400, height: 300))])
    run(app, 0.2)
    check(app.stats.covered > 50 && app.stats.pushedOut < app.stats.covered && anyInside(app) == 0,
          "a window opened on top covers its dots (dormant), it does not push", "\(app.stats)")
}

// MARK: acceptance 1 (fast drag across the screen), 2 (close an 800 pt window, refill), 3 (gap closing)
do {
    let dense = settings { $0.densityPerMpt2 = 1000; $0.particleDiameter = 1.5 }
    // 1: a 600 x 500 window dragged across the whole laptop screen in one second, sampled at 12 Hz
    var w = AetherRect(x: 0, y: 200, width: 600, height: 500)
    let sim = AetherSim(bounds: laptop, settings: dense, seed: 14, obstacles: [AetherObstacle(id: 7, rect: w)])
    run(sim, 1)
    var inside = 0, fastest = 0.0
    for _ in 0..<12 {
        w.minX += 76; w.maxX += 76
        sim.setGeometry([AetherObstacle(id: 7, rect: w)], sweep: 1.0 / 12)
        for _ in 0..<Int((1.0 / 12) / sim.tuning.dt + 0.5) { sim.step(); inside = max(inside, anyInside(sim)); fastest = max(fastest, maxSpeed(sim)) }
    }
    run(sim, 3) { inside = max(inside, anyInside($0)) }
    check(inside == 0, "acceptance 1: no missed sweep (no point inside the window at any step)", "\(inside)")
    check(fastest <= 1.3 * 76 * 12, "acceptance 1: pushed points ride the face (plus a bounded spill), never launched past it", "\(fastest)")
    check(maxSpeed(sim) <= sim.ceiling + 1e-9, "acceptance 1: after release every point is back under the ceiling", "\(maxSpeed(sim))")
    let left = AetherRect(x: 0, y: 200, width: 500, height: 500)
    check(Double(sim.activeCount(in: left)) > 0.5 * sim.designDensity * left.area, "acceptance 1: the space the drag left refilled",
          "\(sim.activeCount(in: left))")

    // 2: close an 800 pt window at Cool: the exposed desktop refills on purpose, in seconds, not minutes
    let win = AetherRect(x: 300, y: 100, width: 800, height: 700)
    let s2 = AetherSim(bounds: laptop, settings: dense, seed: 15, obstacles: [AetherObstacle(id: 3, rect: win)])
    run(s2, 1)
    let N0 = s2.activeCount()
    s2.setGeometry([])
    run(s2, 10)
    let want = s2.designDensity * win.area
    check(Double(s2.activeCount(in: win)) > 0.85 * want, "acceptance 2: refilled to >85 % in 10 s", "\(s2.activeCount(in: win)) of \(want)")
    check(s2.activeCount() <= s2.population, "acceptance 2: thermal walls never exceed the population", "\(N0) -> \(s2.activeCount())")
    let fresh = s2.pos.indices.filter { s2.phase[$0] == .active && win.contains(s2.pos[$0]) }
    let T = fresh.map { (s2.vel[$0].x * s2.vel[$0].x + s2.vel[$0].y * s2.vel[$0].y) / 2 }.reduce(0, +) / Double(max(1, fresh.count))
    check(T < 3 * s2.meanSigma2() + 1, "acceptance 2: refill enters at the gas's temperature", "\(T)")

    // 3: trap points between two windows, then close the gap
    var t3 = AetherTuning(); t3.reserveEnabled = true
    var a = AetherRect(x: 100, y: 100, width: 500, height: 600), b = AetherRect(x: 640, y: 100, width: 500, height: 600)
    let s3 = AetherSim(bounds: laptop, settings: dense, seed: 16, tuning: t3,
                       obstacles: [AetherObstacle(id: 1, rect: a), AetherObstacle(id: 2, rect: b)])
    run(s3, 1)
    let gap = AetherRect(x: 600, y: 100, width: 40, height: 600)
    let trapped0 = s3.activeCount(in: gap)
    var bad = 0, worstCrowd = 0.0, worstSpeed = 0.0
    for _ in 0..<20 {                      // close 40 pt over 2 s, then hold
        a.maxX += 1; b.minX -= 1
        s3.setGeometry([AetherObstacle(id: 1, rect: a), AetherObstacle(id: 2, rect: b)], sweep: 0.1)
        for _ in 0..<3 { s3.step(); bad = max(bad, anyInside(s3)); worstSpeed = max(worstSpeed, maxSpeed(s3)) }
        worstCrowd = max(worstCrowd, s3.maxCoarseCount())
    }
    run(s3, 3) { bad = max(bad, anyInside($0)); worstSpeed = max(worstSpeed, maxSpeed($0)) }
    let gapNow = AetherRect(x: a.maxX, y: 100, width: b.minX - a.maxX, height: 600)
    check(trapped0 > 5, "acceptance 3: some points start trapped", "\(trapped0)")
    check(bad == 0, "acceptance 3: no invalid placement while the gap closes", "\(bad)")
    check(worstSpeed <= s3.ceiling + 1e-9, "acceptance 3: no jitter burst", "\(worstSpeed)")
    check(worstCrowd <= s3.crowdCap + 8, "acceptance 3: no density explosion", "\(worstCrowd) vs cap \(s3.crowdCap)")
    check(s3.activeCount(in: gapNow) == 0 || gapNow.width > 2 * s3.radius, "acceptance 3: a gap below the collision diameter holds nothing")
    check(s3.frameInterval() == nil || 1 / s3.frameInterval()! <= 60 + 1e-9, "presentation stays capped")
}

// MARK: sprite grid (the sprite passes read only the grid cells under their reach)
do {
    func spun(_ grid: Bool) -> AetherSim {
        var t = AetherTuning(); t.spriteGrid = grid
        let s = settings { $0.motion = .living; $0.densityPerMpt2 = 1000; $0.stirring = 1.2; $0.fieldStrength = 1.5; $0.attraction = 0; $0.repulsion = 0 }
        let sim = AetherSim(bounds: laptop, settings: s, seed: 51, tuning: t)
        for k in 0..<(30 * 4) {
            let a = Double(k) / 30
            sim.setSprites((k >= 30 ? [AetherSprite(pos: SIMD2(900, 300), radius: 60, id: "d")] : []) + [   // d first: it moves points before e reads
                            AetherSprite(pos: SIMD2(300 + 200 * a, 400), radius: 20, id: "a"),
                            AetherSprite(pos: SIMD2(330 + 200 * a, 410 + 20 * sin(a)), radius: 30, id: "b"),   // overlapping reach
                            AetherSprite(pos: SIMD2(1500, 900), radius: 25, id: "c"),                        // at the screen edge
                            // a big body that appears at 1 s pushes its interior out to its rim, into a small moving
                            // sprite's reach from cells outside that sprite's box (the moved-points list must catch them)
                            AetherSprite(pos: SIMD2(990 + 6 * cos(9 * a), 300 + 6 * sin(9 * a)), radius: 15, id: "e")])
            if k == 29 { for j in 0..<8 { sim.injectPoint(at: SIMD2(915 + 4 * Double(j), 294 + 1.5 * Double(j)), velocity: .zero) } }
            sim.step()
        }
        return sim
    }
    let g = spun(true), f = spun(false)
    var worst = 0.0
    for i in g.pos.indices where g.phase[i] == .active || f.phase[i] == .active {
        let d = g.vel[i] - f.vel[i], e = g.pos[i] - f.pos[i]
        worst = max(worst, abs(d.x), abs(d.y), abs(e.x), abs(e.y))
    }
    check(g.phase == f.phase && worst < 1e-9, "sprite grid gives the same velocities as the full loop (4 s, 3 sprites, dense)", "\(worst)")
}

// MARK: temperature varies (owner ruling 7, 2026-11-08: "Let it vary more.")
do {
    check(AetherSettings().temperatureVariation >= 0.8 && AetherSettings().temperatureVariation < 1, "default variation is high")
    check(AetherSettings.parse(behaviorsJSON: #"{"aether":{"temperatureVariation":0.3}}"#).temperatureVariation == 0.3
          && AetherSettings.parse(behaviorsJSON: #"{"aether":{"temperatureVariation":7}}"#).temperatureVariation == 1,
          "temperature variation persists in behaviors.json, clamped to 0-1")
    // A sprite paces the left side for 6 s, then leaves. Left vs right, flow-blind σ², measured 20 s later.
    func heated(_ variation: Double) -> (hot: Double, cold: Double, lowest: Double, sim: AetherSim) {
        let s = settings { $0.motion = .living; $0.densityPerMpt2 = 1000; $0.rmsSpeed = 8; $0.stirring = 1.5
                           $0.fieldStrength = 0; $0.attraction = 0; $0.repulsion = 0; $0.temperatureVariation = variation }
        let sim = AetherSim(bounds: laptop, settings: s, seed: 52)
        var lowest = Double.infinity
        for k in 0..<(30 * 6) {
            let a = Double(k) / 30
            if k % 3 == 0 { sim.setSprites([AetherSprite(pos: SIMD2(250 + 150 * cos(2 * a), 470 + 300 * sin(3 * a)), radius: 25, id: "a")]) }
            sim.step(); lowest = min(lowest, sim.meanSigma2())
        }
        sim.setSprites([])
        run(sim, 20) { lowest = min(lowest, $0.meanSigma2()) }
        let left = AetherRect(x: 0, y: 0, width: 450, height: 945), right = AetherRect(x: 1062, y: 0, width: 450, height: 945)
        return (sim.meanSigma2(in: left), sim.meanSigma2(in: right), lowest, sim)
    }
    let free = heated(1), uniform = heated(0)
    check(free.hot > 1.5 * free.cold, "variation 1: a region a sprite heated stays hotter 20 s later", "\(free.hot) vs \(free.cold)")
    check(free.lowest >= free.sim.settings.minRmsSpeed * free.sim.settings.minRmsSpeed / 2 - 1e-9, "variation 1: the mean never drops below the floor",
          "\(free.lowest)")
    check(free.hot / free.cold > uniform.hot / uniform.cold, "variation 0 evens it out more (the old uniform gas)",
          "\(free.hot / free.cold) vs \(uniform.hot / uniform.cold)")
    // No runaway: a free gas stirred hard and then left alone only loses energy, and never below the floor.
    let s = settings { $0.motion = .living; $0.rmsSpeed = 8; $0.attraction = 0; $0.repulsion = 0; $0.temperatureVariation = 1; $0.coolingSeconds = 30 }
    let sim = AetherSim(bounds: laptop, settings: s, seed: 53)
    sim.stir(); sim.stir(); sim.stir()
    let start = sim.meanSigma2(); var peak = start, low = Double.infinity
    run(sim, 300) { peak = max(peak, $0.meanSigma2()); low = min(low, $0.meanSigma2()) }
    check(peak <= start * 1.05 && sim.meanSigma2() < start, "variation 1: no runaway, a stirred gas left alone does not heat up", "\(start) peak \(peak) end \(sim.meanSigma2())")
    check(low >= 1.5 * 1.5 / 2 - 1e-9, "variation 1: 5 minutes left alone stay above the floor", "\(low)")
    // Free and cold, with nothing to stir it: the floor holds it moving (living, thermal edges barely re-emit).
    let cold = AetherSim(bounds: laptop, settings: settings { $0.motion = .living; $0.rmsSpeed = 0.5; $0.minRmsSpeed = 0.5; $0.temperatureVariation = 1; $0.attraction = 0; $0.repulsion = 0 }, seed: 54)
    var cl = Double.infinity; run(cold, 120) { cl = min(cl, $0.meanSigma2()) }
    check(cl >= 0.125 - 1e-9 && cold.frameInterval() != nil, "variation 1: a cold free gas stays at or above the floor and keeps presenting", "\(cl)")
}

// MARK: drifting constants (owner, 2026-11-08 ~5 PM: "the Universal Constants slowly vary over the course of tens of minutes")
do {
    let p = AetherSettings.parse(behaviorsJSON: #"{"aether":{"drift":"wild","driftPeriod":500,"edgeTemperature":0.1}}"#)
    check(p.drift == .wild && p.driftPeriodMinutes == 120 && p.edgeTemperature == 0.5, "drift settings parse and clamp")
    check(AetherSettings.parse(behaviorsJSON: #"{"aether":{"drift":"bogus"}}"#).drift == .off && AetherSettings().drift == .off, "drift is off by default")
    let base = AetherSettings(), seed: UInt64 = 0xAE7E_D21F_7000_0001
    check(aetherDrifted(base, seed: seed, phase: 3.7, amplitude: 0) == base, "amplitude 0: the owner's sliders exactly")
    func norm(_ k: AetherDriftKey, _ v: Double) -> Double { k.log ? (log(v) - log(k.lo)) / (log(k.hi) - log(k.lo)) : (v - k.lo) / (k.hi - k.lo) }
    // A simulated day at the default period, wild, sampled every 10 s: bounds, smoothness, and real variety.
    let day = 86_400.0, dtS = 10.0, P = 30.0
    var clock = AetherDriftClock(epochSeconds: 0, periodMinutes: P)
    var prev: AetherSettings? = nil, worstRate = 0.0, steadyRate = 0.0, inBounds = true
    var lo = [Double](repeating: 1, count: aetherDriftKeys.count), hi = [Double](repeating: 0, count: aetherDriftKeys.count)
    var samples: [AetherSettings] = []
    var t = 0.0
    while t < day {
        clock.advance(dtS, mode: .wild, periodMinutes: P)
        let d = aetherDrifted(base, seed: seed, phase: clock.phase, amplitude: clock.amplitude)
        for (k, key) in aetherDriftKeys.enumerated() {
            let v = d[keyPath: key.path]
            if !(v >= key.lo && v <= key.hi) { inBounds = false }
            let u = norm(key, v); lo[k] = min(lo[k], u); hi[k] = max(hi[k], u)
            if let q = prev { let r = abs(u - norm(key, q[keyPath: key.path])) / dtS; worstRate = max(worstRate, r); if t > 600 { steadyRate = max(steadyRate, r) } }
        }
        prev = d; if Int(t) % 1800 == 0 { samples.append(d) }
        t += dtS
    }
    check(inBounds, "drift never leaves any slider's range over a simulated day")
    // Bounds from the walk's own derivative: steady wild at 30 min is <= 1.5 x 9.2 / 4 / 30 ≈ 11.5 % of a range per
    // minute; easing in adds <= 1.5 / 180 s x 1/4 x 60 = 12.5 %. Under 0.4 % a second either way: nothing jolts.
    check(steadyRate * 60 < 0.12, "smooth: steady wild drift moves no constant faster than 12 % of its range per minute", "\(steadyRate * 60)")
    check(worstRate * 60 < 0.25, "smooth: easing in included, under 25 % of a range per minute", "\(worstRate * 60)")
    check(zip(lo, hi).allSatisfy { $1 - $0 > 0.3 }, "wild: every drifting constant wanders over at least 30 % of its range in a day",
          "\(zip(lo, hi).map { $1 - $0 })")
    // Combinations rarely repeat: the universe one base period later is not the same universe.
    func gap(_ a: AetherSettings, _ b: AetherSettings) -> Double { aetherDriftKeys.map { abs(norm($0, a[keyPath: $0.path]) - norm($0, b[keyPath: $0.path])) }.max()! }
    var same = 0
    for ph in stride(from: 0.0, to: 48, by: 1) {
        if gap(aetherDrifted(base, seed: seed, phase: ph, amplitude: 1.5), aetherDrifted(base, seed: seed, phase: ph + 1, amplitude: 1.5)) < 0.05 { same += 1 }
    }
    check(same <= 2, "one period later the constants are elsewhere (incommensurate periods)", "\(same) of 48")
    // Determinism by seed.
    check(aetherDrifted(base, seed: 7, phase: 12.3, amplitude: 1.5) == aetherDrifted(base, seed: 7, phase: 12.3, amplitude: 1.5), "drift: same seed, same universe")
    check(aetherDrifted(base, seed: 7, phase: 12.3, amplitude: 1.5) != aetherDrifted(base, seed: 8, phase: 12.3, amplitude: 1.5), "drift: different seed, different universe")
    // A constant set to off stays off; a slider at the top stays inside the range.
    let off = settings { $0.attraction = 0; $0.fieldStrength = 0; $0.stirring = 0; $0.repulsion = 0; $0.chainForming = 0 }
    check((0..<40).allSatisfy { let d = aetherDrifted(off, seed: seed, phase: Double($0) * 0.37, amplitude: 1.5)
                                return d.attraction == 0 && d.fieldStrength == 0 && d.stirring == 0 && d.repulsion == 0 }, "drift never turns on a constant the owner set to off")
    let top = settings { $0.attraction = 3; $0.coolingSeconds = 120; $0.chainForming = 1 }
    check((0..<40).allSatisfy { let d = aetherDrifted(top, seed: seed, phase: Double($0) * 0.37, amplitude: 1.5)
                                return d.attraction <= 3 && d.coolingSeconds <= 120 && d.chainForming <= 1 }, "a slider at its maximum: drift stays at or below it")
    // Easing: switching drift on, then off, never steps the amplitude by more than the ease rate.
    var c2 = AetherDriftClock(epochSeconds: 0, periodMinutes: P); var maxStep = 0.0, last = 0.0
    for k in 0..<800 { c2.advance(1, mode: k < 400 ? .wild : .off, periodMinutes: P); maxStep = max(maxStep, abs(c2.amplitude - last)); last = c2.amplitude }
    check(maxStep <= 1.5 / 180 + 1e-12 && c2.amplitude == 0, "drift eases in and out over ~3 minutes", "\(maxStep)")
    // Continuity at the slider ends (GPT code review, 2026-11-08): easing in from a slider at either end of its range
    // moves it by a hair, never jumps it (the first version clamped the working point and jumped 1 -> 0.98).
    let ends = settings { $0.temperatureVariation = 1; $0.attractionRange = 1.5; $0.coolingSeconds = 120 }
    let tiny = aetherDrifted(ends, seed: seed, phase: 0.3, amplitude: 1e-6)
    check(abs(tiny.temperatureVariation - 1) < 1e-5 && abs(tiny.attractionRange - 1.5) < 1e-5 && abs(tiny.coolingSeconds - 120) < 1e-3,
          "drift is continuous at the slider ends", "\(tiny.temperatureVariation) \(tiny.attractionRange) \(tiny.coolingSeconds)")
    check(aetherDrifted(settings { $0.chainForming = 0 }, seed: seed, phase: 0.3, amplitude: 1.5).chainForming == 0, "droplets (chain forming 0) stay droplets under drift")
    // CPU budget across the sampled day: Dense, every half hour of the day's drift (default and maxed sliders), the
    // work counters stay under the max-setting budget (45 pair checks and force evaluations per point per step).
    let maxed = settings { $0.attraction = 3; $0.attractionRange = AetherSettings.maxAttractionRange; $0.repulsion = 2; $0.repulsionRange = 4; $0.chainForming = 1; $0.fieldStrength = 2; $0.stirring = 2 }
    var worstPairs = 0.0, worstForces = 0.0, worstDefault = 0.0
    for (bi, b) in [AetherSettings(), maxed].enumerated() {
        var ds = b; ds.motion = .living; ds.densityPerMpt2 = 1000; ds.particleDiameter = 1.5
        let sim = AetherSim(bounds: laptop, settings: ds, seed: 77)
        for (si, _) in samples.enumerated() where si % 4 == 0 {
            sim.settings = aetherDrifted(ds, seed: seed, phase: Double(si) * 1800 / (60 * P), amplitude: 1.5)
            let w0 = sim.work; run(sim, 2)
            let ps = Double(sim.work.pointSteps - w0.pointSteps)
            let pr = Double(sim.work.pairChecks - w0.pairChecks) / ps, fe = Double(sim.work.forceEvals - w0.forceEvals) / ps
            worstPairs = max(worstPairs, pr); worstForces = max(worstForces, fe); if bi == 0 { worstDefault = max(worstDefault, pr) }
        }
    }
    check(worstPairs < 45 && worstForces < 45, "drift across a sampled day never pushes the work past the max-setting budget", "pairs \(worstPairs) forces \(worstForces)")
    check(worstDefault < 15, "drift around the default sliders stays inside the default budget", "\(worstDefault)")
    // Energy stays bounded under drift: a stirred free gas under wild drift (the period at its 10 min minimum) never
    // heats past what the hottest edge emission could give, and never falls below the floor.
    let es = settings { $0.motion = .living; $0.rmsSpeed = 8; $0.attraction = 0; $0.repulsion = 0; $0.temperatureVariation = 1; $0.coolingSeconds = 30 }
    let esim = AetherSim(bounds: laptop, settings: es, seed: 53)
    esim.stir(); esim.stir(); esim.stir()
    let start = esim.meanSigma2(); var peak = start, low = Double.infinity, ec = AetherDriftClock(epochSeconds: 0, periodMinutes: 10)
    run(esim, 300) { s in
        ec.advance(s.tuning.dt, mode: .wild, periodMinutes: 10)
        s.settings = aetherDrifted(es, seed: seed, phase: ec.phase, amplitude: ec.amplitude)
        peak = max(peak, s.meanSigma2()); low = min(low, s.meanSigma2())
    }
    check(peak <= max(start * 1.05, 4 * 32), "under drift: a stirred gas left alone never runs away", "\(start) peak \(peak)")
    check(low >= 1.5 * 1.5 / 2 - 1e-9, "under drift: the floor holds", "\(low)")
}

// MARK: drift coupling (owner card 2026-11-08 18:30 PST: "Couple the risky pairs", plus a sampled-day clumping test)
do {
    check(AetherSettings().driftCoupling == 1 && AetherSettings.parse(behaviorsJSON: #"{"aether":{"driftCoupling":-2}}"#).driftCoupling == 0,
          "drift coupling: on by default, parsed and clamped")
    let seed: UInt64 = 0xAE7E_D21F_7000_0001
    func norm(_ k: AetherDriftKey, _ v: Double) -> Double { (v - k.lo) / (k.hi - k.lo) }
    let ka = aetherDriftKeys.first { $0.name == "attraction" }!, kr = aetherDriftKeys.first { $0.name == "repulsion" }!
    let kar = aetherDriftKeys.first { $0.name == "attractionRange" }!, krr = aetherDriftKeys.first { $0.name == "repulsionRange" }!
    // Coupled: whenever attraction drifts stickier, repulsion drifts stronger, and a longer attraction reach brings a
    // sharper (shorter) repulsion; over a day the two walks move together (correlation of their offsets near 1).
    func corr(_ coupling: Double, _ a: AetherDriftKey, _ b: AetherDriftKey) -> Double {
        var s = AetherSettings(); s.driftCoupling = coupling
        var xs: [Double] = [], ys: [Double] = []
        for m in stride(from: 0.0, to: 1440, by: 5) { let d = aetherDrifted(s, seed: seed, phase: m / 30, amplitude: 1.5)
            xs.append(norm(a, d[keyPath: a.path]) - norm(a, s[keyPath: a.path])); ys.append(norm(b, d[keyPath: b.path]) - norm(b, s[keyPath: b.path])) }
        let mx = xs.reduce(0, +) / Double(xs.count), my = ys.reduce(0, +) / Double(ys.count)
        let c = zip(xs, ys).map { ($0 - mx) * ($1 - my) }.reduce(0, +)
        return c / (xs.map { ($0 - mx) * ($0 - mx) }.reduce(0, +) * ys.map { ($0 - my) * ($0 - my) }.reduce(0, +)).squareRoot()
    }
    check(corr(1, ka, kr) > 0.9 && corr(1, kar, krr) < -0.9, "coupled: repulsion strength drifts with attraction strength, repulsion range against attraction range",
          "\(corr(1, ka, kr)) \(corr(1, kar, krr))")
    check(abs(corr(0, ka, kr)) < 0.5, "coupling 0: the walks are independent again", "\(corr(0, ka, kr))")
    // A simulated day of desktop-wide clumping: sticky sliders (attraction 2.2 at range 2.4, weak repulsion, slow
    // cooling, free temperature), wild drift sampled every hour, Dense, 3 simulated minutes per sample. Clumping is the
    // share of all points in the fullest quarter of 8 x 5 desktop blocks (an even gas reads ~0.33, measured; the
    // uncoupled walk reached 0.60 at one hour of this day). Coupled, no hour may clump the desktop past 0.5.
    let box = AetherRect(x: 0, y: 0, width: 1008, height: 630)
    func clump(_ sim: AetherSim) -> Double {
        let c = 126.0; var n = [Double](repeating: 0, count: 40)
        for i in sim.pos.indices where sim.phase[i] == .active { n[min(4, Int(sim.pos[i].y / c)) * 8 + min(7, Int(sim.pos[i].x / c))] += 1 }
        return n.sorted(by: >).prefix(10).reduce(0, +) / max(1, n.reduce(0, +))
    }
    func day(_ coupling: Double) -> (worst: Double, pairs: Double) {
        var b = AetherSettings(); b.attraction = 2.2; b.attractionRange = 2.4; b.repulsion = 0.8; b.coolingSeconds = 90; b.temperatureVariation = 0.95
        b.driftCoupling = coupling; b.motion = .living; b.densityPerMpt2 = 1000; b.particleDiameter = 1.5
        var worst = 0.0, pairs = 0.0
        for h in 0..<24 {
            let sim = AetherSim(bounds: box, settings: aetherDrifted(b, seed: seed, phase: Double(h) * 2, amplitude: 1.5), seed: 5)
            run(sim, 180); worst = max(worst, clump(sim)); pairs = max(pairs, Double(sim.work.pairChecks) / Double(sim.work.pointSteps))
        }
        return (worst, pairs)
    }
    let coupled = day(1)
    check(coupled.worst < 0.5, "a sampled drift day never clumps the desktop (coupled, sticky sliders, every hour)", "\(coupled.worst)")
    check(coupled.pairs < 45, "and the sampled day stays inside the max work budget", "\(coupled.pairs)")
}

// MARK: weather fronts (owner card 2026-11-08 18:30 PST: "drift varies by region; borders wander over about an hour")
do {
    check(AetherSettings().fronts > 0 && AetherSettings().fronts <= 0.5 && AetherSettings.parse(behaviorsJSON: #"{"aether":{"fronts":3}}"#).fronts == 1,
          "fronts: subtle by default, parsed and clamped")
    let seed: UInt64 = 0xAE7E_D21F_7000_0001, cc = AetherTuning().coarseCell
    var b = AetherSettings(); b.drift = .wild
    check(aetherFronts(b, seed: seed, phase: 3, amplitude: 0, minutes: 0, bounds: laptop, cell: cc) == nil
          && aetherFronts(settings { $0.fronts = 0 }, seed: seed, phase: 3, amplitude: 1.5, minutes: 0, bounds: laptop, cell: cc) == nil,
          "no drift or fronts 0: one universe everywhere (no per-region values)")
    // Regional: at one moment the desktop holds different universes (sticky here, loose there); neighbouring cells
    // differ only a little (no seams), and over a day no front is desktop-wide: the spread never collapses to zero.
    func spread(_ f: AetherFronts) -> (range: Double, seam: Double) {
        let cw = Int((laptop.width / cc).rounded(.up)); var seam = 0.0
        for i in f.attraction.indices where i % cw < cw - 1 { seam = max(seam, abs(f.attraction[i] - f.attraction[i + 1])) }
        return (f.attraction.max()! - f.attraction.min()!, seam)
    }
    var lowest = Double.infinity, widest = 0.0, seam = 0.0
    for h in 0..<24 { let f = aetherFronts(b, seed: seed, phase: Double(h) * 2, amplitude: 1.5, minutes: Double(h) * 60, bounds: laptop, cell: cc)!
        let sp = spread(f); lowest = min(lowest, sp.range); widest = max(widest, sp.range); seam = max(seam, sp.seam) }
    check(widest > 0.3 && lowest > 0.05, "fronts: attraction differs by region at every sampled hour (up to \(String(format: "%.2f", widest)) of 3)", "\(lowest) \(widest)")
    check(seam < 0.1 * widest, "fronts: neighbouring regions differ only a little (no seam)", "\(seam) vs \(widest)")
    // The borders wander: one minute later a region is nearly where it was; an hour later the pattern has moved on.
    func fieldCorr(_ dm: Double) -> Double {
        var xs: [Double] = [], ys: [Double] = []
        for y in stride(from: 0.05, to: 0.6, by: 0.05) { for x in stride(from: 0.05, to: 1, by: 0.05) {
            xs.append(aetherFrontField(u: x, v: y, minutes: 600, seed: seed)); ys.append(aetherFrontField(u: x, v: y, minutes: 600 + dm, seed: seed)) } }
        let mx = xs.reduce(0, +) / Double(xs.count), my = ys.reduce(0, +) / Double(ys.count)
        let c = zip(xs, ys).map { ($0 - mx) * ($1 - my) }.reduce(0, +)
        return c / (xs.map { ($0 - mx) * ($0 - mx) }.reduce(0, +) * ys.map { ($0 - my) * ($0 - my) }.reduce(0, +)).squareRoot()
    }
    check(fieldCorr(1) > 0.98 && fieldCorr(30) < 0.5, "fronts: borders move smoothly and cross the screen in about an hour", "\(fieldCorr(1)) \(fieldCorr(30))")
    // The sim reads them: a sticky region (left) next to a loose one (right) at the same global settings clumps more.
    let s = settings { $0.motion = .living; $0.densityPerMpt2 = 600; $0.rmsSpeed = 3; $0.attraction = 1.5; $0.chainForming = 0; $0.repulsion = 0.5 }
    let sim = AetherSim(bounds: laptop, settings: s, seed: 63)
    let cw = Int((laptop.width / cc).rounded(.up)), ch = Int((laptop.height / cc).rounded(.up))
    var f = AetherFronts(attraction: [], chain: [], repulsion: [], edge: [], maxAttraction: 3)
    for _ in 0..<ch { for x in 0..<cw { let left = x < cw / 2; f.attraction.append(left ? 3 : 0.3); f.chain.append(0); f.repulsion.append(0.5); f.edge.append(1) } }
    sim.setFronts(f); run(sim, 60)
    let half = laptop.width / 2
    func nb(_ left: Bool) -> Double {
        let lim = 3.5 + 0.5 * (sim.attractionCutoff - 3.5); var n = 0.0, k = 0.0
        for i in sim.pos.indices where sim.phase[i] == .active && (sim.pos[i].x < half - 60) == left && abs(sim.pos[i].x - half) > 60 {
            k += 1; for j in sim.pos.indices where j != i && sim.phase[j] == .active { let d = sim.pos[j] - sim.pos[i]; if d.x * d.x + d.y * d.y < lim * lim { n += 1 } } }
        return n / max(k, 1)
    }
    check(nb(true) > 2 * nb(false) + 0.2, "fronts: the sticky region clumps, the loose one stays a gas (one sim, one moment)", "\(nb(true)) vs \(nb(false))")
    // Work budget with fronts, Dense, over the sampled day: default and maxed sliders.
    let maxed = settings { $0.attraction = 3; $0.attractionRange = AetherSettings.maxAttractionRange; $0.repulsion = 2; $0.repulsionRange = 4; $0.chainForming = 1; $0.fronts = 1 }
    var worstD = 0.0, worstM = 0.0
    for (bi, base) in [AetherSettings(), maxed].enumerated() {
        var ds = base; ds.motion = .living; ds.densityPerMpt2 = 1000; ds.particleDiameter = 1.5; ds.drift = .wild
        let sim = AetherSim(bounds: laptop, settings: ds, seed: 77)
        for h in stride(from: 0, to: 24, by: 4) {
            let ph = Double(h) * 2
            sim.settings = aetherDrifted(ds, seed: seed, phase: ph, amplitude: 1.5)
            sim.setFronts(aetherFronts(ds, seed: seed, phase: ph, amplitude: 1.5, minutes: Double(h) * 60, bounds: laptop, cell: cc))
            let w0 = sim.work; run(sim, 2)
            let pr = Double(sim.work.pairChecks - w0.pairChecks) / Double(sim.work.pointSteps - w0.pointSteps)
            if bi == 0 { worstD = max(worstD, pr) } else { worstM = max(worstM, pr) }
        }
    }
    check(worstD < 15 && worstM < 45, "fronts across a sampled drift day stay inside the work budget (default < 15, max < 45)", "\(worstD) \(worstM)")
}

// MARK: needle memory and knots (owner card 2026-11-08 18:30 PST)
do {
    let d = AetherSettings()
    check(d.needleMemory > 0 && d.needleMemory <= 0.5 && d.knots > 0 && d.knots <= 0.5
          && AetherSettings.parse(behaviorsJSON: #"{"aether":{"needleMemory":2,"knots":-1}}"#).needleMemory == 1
          && AetherSettings.parse(behaviorsJSON: #"{"aether":{"knots":-1}}"#).knots == 0, "needle memory and knots: subtle defaults, parsed and clamped")
    // Memory: a dot alone keeps its needle direction for a while (orientation autocorrelation over 5 s); memory 0 is
    // the old free rotation (measured ~0), the default holds most of it (measured 0.67).
    let box = AetherRect(x: 0, y: 0, width: 800, height: 600)
    func memory(_ m: Double) -> Double {
        let sim = AetherSim(bounds: box, settings: settings { $0.motion = .living; $0.needleMemory = m }, seed: 3)
        run(sim, 2); let o0 = sim.orient; run(sim, 5)
        var c = 0.0, n = 0.0
        for i in sim.pos.indices where sim.phase[i] == .active { c += o0[i].x * sim.orient[i].x + o0[i].y * sim.orient[i].y; n += 1 }
        return c / n
    }
    let m0 = memory(0), m5 = memory(0.5)
    check(abs(m0) < 0.2 && m5 > 0.5, "needle memory: a lone dot keeps its direction for seconds (0 forgets, as before)", "\(m0) \(m5)")
    // Knots: two sprites' wakes cross at the centre. Crossings are marked only where both wakes went (local, a few
    // cells), never by one sprite's own wake; the crossing gathers dots (more bonded neighbours there than with knots
    // off), and a minute later the knot has come apart (no lasting difference).
    func cross(_ knots: Double, _ seed: UInt64, two: Bool = true) -> (sim: AetherSim, cells: Int, during: Double, after: Double, rest: Double) {
        let sim = AetherSim(bounds: box, settings: settings { $0.motion = .living; $0.knots = knots; $0.densityPerMpt2 = 1000; $0.particleDiameter = 1.5 }, seed: seed)
        let zone = AetherRect(x: 330, y: 230, width: 140, height: 140)
        func nb(_ inZone: Bool = true) -> Double {
            let lim = 3.5 + 0.5 * (sim.attractionCutoff - 3.5); var n = 0.0, k = 0.0
            for i in sim.pos.indices where sim.phase[i] == .active && zone.contains(sim.pos[i]) == inZone { k += 1
                for j in sim.pos.indices where j != i && sim.phase[j] == .active { let v = sim.pos[j] - sim.pos[i]; if v.x * v.x + v.y * v.y < lim * lim { n += 1 } } }
            return n / max(k, 1)
        }
        run(sim, 10); var cells = 0, during = 0.0
        for k in 0..<(30 * 6) { let t = Double(k) / 30
            if k == 150 || k == 179 { during += nb() / 2 }   // while the wakes cross (measured: the knot peaks at 5-6 s)
            if k % 3 == 0 { sim.setSprites([AetherSprite(pos: SIMD2(100 + 100 * t, 300), radius: 20, id: "a")]
                                           + (two ? [AetherSprite(pos: SIMD2(400, 600 - 100 * t), radius: 20, id: "b")] : [])) }
            sim.step(); cells = max(cells, sim.crossCells) }
        sim.setSprites([]); run(sim, 60)
        return (sim, cells, during, nb(), nb(false))
    }
    let seeds: [UInt64] = [1, 2, 3, 4, 5, 6]
    let on = seeds.map { cross(1, $0) }, off = seeds.map { cross(0, $0) }
    let solo = cross(1, 1, two: false)
    check(solo.sim.crossings == 0, "knots: one sprite's own wake is never a crossing", "\(solo.sim.crossings)")
    check(on.allSatisfy { $0.cells > 0 && Double($0.cells) < 0.1 * Double($0.sim.coarseCellCount) }, "knots: crossings are local (a few cells where both wakes went)",
          "\(on.map { $0.cells }) of \(on[0].sim.coarseCellCount)")
    let dOn = on.map { $0.during }.reduce(0, +) / 6, dOff = off.map { $0.during }.reduce(0, +) / 6
    check(dOn > 1.3 * dOff, "knots: where two wakes cross, dots gather (bonded neighbours, 6 seeds, knots 1)", "\(dOff) -> \(dOn)")
    // A minute later the knot has come apart: the crossing is no more bonded than the rest of the same gas.
    let mark = on.map { $0.after / max($0.rest, 1e-9) }.reduce(0, +) / 6
    check(mark < 1.3, "knots: a minute later the crossing is no more bonded than the rest of the gas (no lasting mark)", "\(mark)")
    // Sometimes, never always: at the default, about that share of crossings knot (seeded per cell and moment).
    let dflt = seeds.map { cross(AetherSettings().knots, $0) }
    let share = Double(dflt.map { $0.sim.knotsFormed }.reduce(0, +)) / Double(max(1, dflt.map { $0.sim.crossings }.reduce(0, +)))
    check(share > 0.15 && share < 0.7, "knots: at the default only some crossings knot (sometimes, never always)", "\(share) of \(dflt.map { $0.sim.crossings }.reduce(0, +))")
    // Work budget: the crossing raises friction, not the search; Dense, default and max, with two sprites crossing.
    func cost(_ f: (inout AetherSettings) -> Void) -> Double {
        let sim = AetherSim(bounds: laptop, settings: settings { $0.motion = .living; $0.densityPerMpt2 = 1000; $0.particleDiameter = 1.5; f(&$0) }, seed: 65)
        for k in 0..<(30 * 10) { let t = Double(k) / 30
            if k % 3 == 0 { sim.setSprites([AetherSprite(pos: SIMD2(300 + 80 * t, 470), radius: 25, id: "a"), AetherSprite(pos: SIMD2(700, 100 + 80 * t), radius: 25, id: "b")]) }
            sim.step() }
        return Double(sim.work.pairChecks) / Double(sim.work.pointSteps)
    }
    let cd = cost { _ in }, cm = cost { $0.knots = 1; $0.needleMemory = 1; $0.attraction = 3; $0.attractionRange = AetherSettings.maxAttractionRange; $0.repulsion = 2; $0.repulsionRange = 4; $0.chainForming = 1; $0.stirring = 2 }
    check(cd < 15 && cm < 45, "knots and memory stay inside the work budget (default < 15, max < 45)", "\(cd) \(cm)")
}

// MARK: window dew (owner card 2026-11-08 18:30 PST: "dots bead along a window edge that hasn't moved for about 10 min")
do {
    let d = AetherSettings()
    check(d.dew > 0 && d.dew <= 0.4 && d.dewAfterSeconds == 600, "dew: subtle by default, after 10 minutes still")
    check(AetherSettings.parse(behaviorsJSON: #"{"aether":{"dew":4,"dewAfter":1}}"#).dew == 1 && AetherSettings.parse(behaviorsJSON: #"{"aether":{"dewAfter":1}}"#).dewAfterSeconds == 5,
          "dew settings parse and clamp")
    let win = AetherRect(x: 500, y: 300, width: 500, height: 350)
    func band(_ sim: AetherSim, _ R: AetherRect) -> Int {
        let E = R.expanded(by: sim.radius + 2 * sim.settings.collisionDiameter), I = R.expanded(by: sim.radius)
        return sim.pos.indices.filter { sim.phase[$0] == .active && E.contains(sim.pos[$0]) && !I.contains(sim.pos[$0]) }.count
    }
    // Dense, threshold shortened to 20 s for the test. Sampled at 15 s (before the threshold) and 80 s (after it).
    func still(_ dew: Double) -> (sim: AetherSim, early: Int, heldEarly: Int, late: Int) {
        let sim = AetherSim(bounds: laptop, settings: settings { $0.dew = dew; $0.dewAfterSeconds = 20; $0.densityPerMpt2 = 1000 }, seed: 4,
                            obstacles: [AetherObstacle(id: 7, rect: win), AetherObstacle(id: -1, rect: AetherRect(minX: -40, minY: -40, maxX: 1552, maxY: 30))])
        var heldEarly = 0
        run(sim, 15) { heldEarly += $0.dewHeld }
        let early = band(sim, win); run(sim, 65)
        return (sim, early, heldEarly, band(sim, win))
    }
    let off = still(0), on = still(AetherSettings().dew)
    check(on.heldEarly == 0, "dew: nothing beads before the window has been still long enough", "\(on.heldEarly)")
    check(Double(on.late) > 2 * Double(off.late), "dew: after the threshold, dots bead along the still window's edge", "\(off.late) -> \(on.late)")
    let solid = 2 * (win.width + win.height) / on.sim.settings.collisionDiameter
    check(Double(on.late) < 0.25 * solid, "dew: beads, never an outline (under a quarter of a solid edge)", "\(on.late) of \(Int(solid))")
    let menu = AetherRect(minX: 0, minY: 0, maxX: 1512, maxY: 30)
    check(Double(band(on.sim, menu)) < 1.5 * Double(max(1, band(off.sim, menu))) + 3, "dew: the menu-bar band never gathers dew (windows only)",
          "\(band(off.sim, menu)) vs \(band(on.sim, menu))")
    // Shake off: move the window 60 pt; within half a second the old edge has let go, and the moved window starts dry.
    let sim = on.sim, moved = AetherRect(x: 560, y: 300, width: 500, height: 350)
    sim.setGeometry([AetherObstacle(id: 7, rect: moved), AetherObstacle(id: -1, rect: AetherRect(minX: -40, minY: -40, maxX: 1552, maxY: 30))], sweep: 0.5)
    run(sim, 0.5)
    let leftEdge = AetherRect(x: 500 - 10, y: 300, width: 10, height: 350)
    check(sim.dewShaken > 0 && sim.activeCount(in: leftEdge) <= 2 + off.sim.activeCount(in: leftEdge), "dew: moving the window shakes its dew off into the gas",
          "shaken \(sim.dewShaken), left edge \(sim.activeCount(in: leftEdge))")
    var heldAfter = 0; run(sim, 10) { heldAfter += $0.dewHeld }
    check(heldAfter == 0, "dew: a window that just moved is dry again until it has been still for the threshold", "\(heldAfter)")
    // ... and once it has stood still again past the threshold (with no other geometry change: the host sends none), it
    // beads again (the first version kept a moved window's sweep forever and never let it bead again).
    var heldLater = 0; run(sim, 30) { heldLater += $0.dewHeld }
    check(heldLater > 0, "dew: a moved window that stands still again beads again", "\(heldLater)")
    // Work budget: dew adds one band test per point per step, no pair search; Dense with a dewy window, default and max.
    func cost(_ dew: Double, _ f: (inout AetherSettings) -> Void = { _ in }) -> Double {
        let sim = AetherSim(bounds: laptop, settings: settings { $0.motion = .living; $0.densityPerMpt2 = 1000; $0.particleDiameter = 1.5; $0.dew = dew; $0.dewAfterSeconds = 5; f(&$0) },
                            seed: 65, obstacles: [AetherObstacle(id: 7, rect: win)])
        run(sim, 30); return Double(sim.work.pairChecks) / Double(sim.work.pointSteps)
    }
    let cd = cost(AetherSettings().dew), cm = cost(1) { $0.attraction = 3; $0.attractionRange = AetherSettings.maxAttractionRange; $0.repulsion = 2; $0.repulsionRange = 4; $0.chainForming = 1 }
    check(cd < 15 && cm < 45, "dew stays inside the work budget (default < 15, max < 45)", "\(cd) \(cm)")
}

// MARK: species wakes (owner card 2026-11-08 18:30 PST: "each species shapes the gas its own way")
do {
    check(AetherSettings().speciesWakes > 0 && AetherSettings().speciesWakes <= 0.5 && AetherSettings.parse(behaviorsJSON: #"{"aether":{"speciesWakes":5}}"#).speciesWakes == 1,
          "species wakes: subtle by default, parsed and clamped")
    check(AetherWakeShape.of(species: "c2_siphon") == .comb && AetherWakeShape.of(species: "c1_choir") == .bow && AetherWakeShape.of(species: "c9_wild") == .round,
          "species table: Siphonophores comb, the Mothership a bow, glyph species round")
    // The wake in the sprite's own frame, averaged over 5 s of a walk at 60 pt/s through a still, dense gas: the aft
    // velocity profile across the track (12 bins over ±1 reach, 0.5-1.5 reach behind) and the outward speed ahead.
    func field(_ species: String, _ k: Double) -> (aft: [Double], out: Double, sim: AetherSim) {
        var t = AetherTuning(); t.thermostatTau = .infinity
        let s = settings { $0.boundary = .reflect; $0.rmsSpeed = 0; $0.minRmsSpeed = 0; $0.motion = .living; $0.fieldStrength = 0; $0.stirring = 0.7
                           $0.attraction = 0; $0.repulsion = 0; $0.densityPerMpt2 = 3000; $0.speciesWakes = k; $0.handedness = 0 }
        let sim = AetherSim(bounds: AetherRect(x: 0, y: 0, width: 900, height: 300), settings: s, seed: 41, tuning: t)
        var bins = [Double](repeating: 0, count: 12), cnt = bins, out = 0.0, no = 0.0
        for f in 0..<(30 * 6) {
            sim.setSprites([AetherSprite(pos: SIMD2(100 + 60 * Double(f / 3 * 3) / 30, 150), radius: 20, id: "a", species: species)]); sim.step()
            guard f >= 30 else { continue }
            let c = SIMD2(100 + 60 * Double(f) / 30, 150.0), R = 60.0
            for i in sim.pos.indices where sim.phase[i] == .active {
                let dv = sim.pos[i] - c, a = dv.x / R, b = dv.y / R
                if a > -1.5 && a < -0.5 && abs(b) < 1 { let j = min(11, Int((b + 1) * 6)); bins[j] += sim.vel[i].x; cnt[j] += 1 }
                if a > 0.3 && a < 1 && abs(b) > 0.35 && abs(b) < 1 { out += (b > 0 ? 1 : -1) * sim.vel[i].y; no += 1 }
            }
        }
        return (zip(bins, cnt).map { $0 / max($1, 1) }, out / max(no, 1), sim)
    }
    let round = field("c9_wild", 0.5), plain = field("c9_wild", 0), k = AetherSettings().speciesWakes
    check(round.sim.pos == plain.sim.pos, "a round species stirs exactly the old wake")
    check(field("c2_siphon", 0).sim.pos == plain.sim.pos, "species wakes 0: a Siphonophore stirs exactly the old round wake")
    let shapes = ["c2_siphon", "c1_choir", "c5_fireflies", "c4_kaleido"].map { ($0, field($0, k)) }
    func gap(_ a: [Double], _ b: [Double]) -> Double { zip(a, b).map { abs($0 - $1) }.reduce(0, +) / Double(a.count) }
    check(shapes.allSatisfy { gap($0.1.aft, round.aft) > 2 }, "every shaped species leaves its own wake (aft profile differs from the round one)",
          "\(shapes.map { ($0.0, gap($0.1.aft, round.aft)) })")
    var distinct = true
    for i in shapes.indices { for j in shapes.indices where j > i { if gap(shapes[i].1.aft, shapes[j].1.aft) < 1.5 && abs(shapes[i].1.out - shapes[j].1.out) < 0.3 { distinct = false } } }
    check(distinct, "no two shaped species leave the same wake")
    let choir = shapes[1].1, siphon = shapes[0].1
    check(choir.out > 0.5 && abs(round.out) < 0.2, "the Mothership parts the gas ahead like a bow (outward flow ahead)", "\(choir.out) vs \(round.out)")
    func troughs(_ f: [Double]) -> Double { (f[3] + f[4] + f[7] + f[8]) / 4 }
    check(troughs(siphon.aft) - troughs(round.aft) < -2 && troughs(choir.aft) - troughs(round.aft) > -1,
          "a Siphonophore combs the gas into strands (the wake thins between its aft lobes)", "\(troughs(siphon.aft) - troughs(round.aft))")
    check(shapes.allSatisfy { maxSpeed($0.1.sim) <= $0.1.sim.ceiling + 1e-9 }, "species wakes respect the speed ceiling")
    // Work budget: shapes reshape the same reach (no wider search); Dense, one sprite of each species walking, default and max.
    func cost(_ f: (inout AetherSettings) -> Void) -> Double {
        let sim = AetherSim(bounds: laptop, settings: settings { $0.motion = .living; $0.densityPerMpt2 = 1000; $0.particleDiameter = 1.5; f(&$0) }, seed: 65)
        let sp = ["c1_choir", "c2_siphon", "c4_kaleido", "c5_fireflies", "c9_wild"]
        for t in 0..<(30 * 10) { let a = Double(t) / 30
            if t % 3 == 0 { sim.setSprites(sp.enumerated().map { AetherSprite(pos: SIMD2(200 + 60 * a, 150 + 150 * Double($0.offset)), radius: 25, id: $0.element, species: $0.element) }) }
            sim.step() }
        return Double(sim.work.pairChecks) / Double(sim.work.pointSteps)
    }
    let cd = cost { _ in }, cm = cost { $0.speciesWakes = 1; $0.stirring = 2; $0.attraction = 3; $0.attractionRange = AetherSettings.maxAttractionRange; $0.repulsion = 2; $0.repulsionRange = 4; $0.chainForming = 1 }
    check(cd < 15 && cm < 45, "species wakes stay inside the work budget (default < 15, max < 45)", "\(cd) \(cm)")
}

// MARK: handedness by project (owner card 2026-11-08 18:30 PST: "each project always curls the gas the same way")
do {
    check(AetherSettings().handedness > 0 && AetherSettings().handedness <= 0.5 && AetherSettings.parse(behaviorsJSON: #"{"aether":{"handedness":9}}"#).handedness == 1,
          "handedness: subtle by default, parsed and clamped")
    let keys = (0..<40).map { "project\($0)" }
    let signs = keys.map { aetherHandedness(key: $0) }
    check(keys.allSatisfy { aetherHandedness(key: $0) == aetherHandedness(key: $0, id: "other") } && signs.allSatisfy { abs($0) == 1 },
          "a project's handedness comes from its key alone (not the session), always ±1")
    check(signs.filter { $0 > 0 }.count >= 10 && signs.filter { $0 < 0 }.count >= 10, "both hands occur across projects", "\(signs.filter { $0 > 0 }.count) of 40")
    let plus = keys.first { aetherHandedness(key: $0) > 0 } ?? keys[0], minus = keys.first { aetherHandedness(key: $0) < 0 } ?? keys[1]
    // Spin of the stirred gas (angular momentum about the wakes' centre), sprites walking +x through a still dense gas.
    func spin(_ ks: [String], _ hand: Double) -> (L: Double, sim: AetherSim) {
        var t = AetherTuning(); t.thermostatTau = .infinity
        let s = settings { $0.boundary = .reflect; $0.rmsSpeed = 0; $0.minRmsSpeed = 0; $0.motion = .living; $0.fieldStrength = 0; $0.stirring = 0.7
                           $0.attraction = 0; $0.repulsion = 0; $0.densityPerMpt2 = 3000; $0.handedness = hand; $0.speciesWakes = 0 }
        let sim = AetherSim(bounds: AetherRect(x: 0, y: 0, width: 900, height: 400), settings: s, seed: 41, tuning: t)
        for f in 0..<(30 * 6) { let x = 100 + 60 * Double(f / 3 * 3) / 30
            sim.setSprites(ks.enumerated().map { AetherSprite(pos: SIMD2(x, 170 + 60 * Double($0.offset)), radius: 20, id: "s\($0.offset)", key: $0.element) }); sim.step() }
        let c = SIMD2(400.0, 170 + 30 * Double(ks.count - 1)); var L = 0.0
        for i in sim.pos.indices where sim.phase[i] == .active { let d = sim.pos[i] - c; if abs(d.x) < 300 && abs(d.y) < 120 { L += d.x * sim.vel[i].y - d.y * sim.vel[i].x } }
        return (L, sim)
    }
    let p1 = spin([plus], 0.4).L, m1 = spin([minus], 0.4).L, z1 = spin([plus], 0).L
    check(p1 * m1 < 0 && min(abs(p1), abs(m1)) > 5 * abs(z1), "opposite-handed projects curl the gas opposite ways (off: no curl)", "\(p1) \(m1) off \(z1)")
    check(p1 == spin([plus], 0.4).L, "the same project curls the same way every time")
    let same = spin([plus, plus], 0.4).L, opp = spin([plus, minus], 0.4).L
    check(abs(same) > 1.2 * abs(p1) && abs(opp) < 0.35 * abs(same), "two wakes of one hand braid (spins add); of opposite hands they cancel", "same \(same) opposite \(opp)")
    let e = spin([plus, minus], 1).sim
    check(maxSpeed(e) <= e.ceiling + 1e-9, "handedness respects the speed ceiling")
}

// MARK: wake reader, sim side (owner card 2026-11-08 18:30 PST: "an idle sprite at play sometimes follows another
// sprite's leftover current a little")
do {
    check(AetherSettings().wakeReader > 0 && AetherSettings().wakeReader <= 0.3 && AetherSettings.parse(behaviorsJSON: #"{"aether":{"wakeReader":2}}"#).wakeReader == 1,
          "wake reader: rare by default, parsed and clamped")
    // Sprite a walks +x through a cool gas for 4 s and leaves; idle sprite b sits beside the track. b reads a's leftover
    // current (along +x); a never reads its own; a fresh wake (under 3 s old) is not yet leftover.
    let s = settings { $0.motion = .living; $0.rmsSpeed = 3; $0.minRmsSpeed = 0.5; $0.attraction = 0; $0.repulsion = 0; $0.densityPerMpt2 = 1500; $0.stirring = 1.2 }
    let sim = AetherSim(bounds: AetherRect(x: 0, y: 0, width: 900, height: 400), settings: s, seed: 8)
    let b = AetherSprite(pos: SIMD2(400, 240), radius: 20, id: "b")
    var fresh: SIMD2<Double>? = nil
    for f in 0..<(30 * 4) {
        if f % 3 == 0 { sim.setSprites([AetherSprite(pos: SIMD2(150 + 120 * Double(f) / 30, 200), radius: 20, id: "a"), b]) }
        sim.step()
        if f == 30 * 4 - 1 { fresh = sim.leftoverCurrent(at: SIMD2(600, 200), excluding: "b") }
    }
    sim.setSprites([AetherSprite(pos: SIMD2(870, 380), radius: 20, id: "a"), b]); run(sim, 4)
    let cur = sim.leftoverCurrent(at: b.pos, excluding: "b"), own = sim.leftoverCurrent(at: SIMD2(400, 200), excluding: "a")
    check(fresh == nil, "a wake under 3 s old is not leftover yet (its maker is still there)", "\(String(describing: fresh))")
    check((cur?.x ?? 0) > 3 && abs(cur?.y ?? 0) < (cur?.x ?? 0), "the idle sprite reads the other's leftover current, along its path", "\(String(describing: cur))")
    check(own == nil, "a sprite never reads its own wake", "\(String(describing: own))")
    check(sim.leftoverCurrents()["b"] != nil && sim.leftoverCurrents()["a"] == nil, "the host's map carries a current only for the sprite beside another's wake")
    run(sim, 30)
    check(sim.leftoverCurrent(at: b.pos, excluding: "b") == nil, "half a minute on, the leftover current is gone (wakes are not kept)")
}

// MARK: frame rate (owner card 2026-11-08 ~18:35 PST: "30 calm, 60 when pushed")
do {
    // A calm, drifting gas at the owner's 27.5 pt/s presents at 30 fps (the speed rule alone asks for 60).
    let sim = AetherSim(bounds: laptop, settings: settings { $0.motion = .living }, seed: 31, obstacles: [AetherObstacle(id: 1, rect: AetherRect(x: 400, y: 300, width: 400, height: 300))])
    run(sim, 3)
    func fps() -> Double { 1 / (sim.frameInterval() ?? .infinity) }
    check(abs(fps() - 30) < 1e-9 && !sim.pushed, "calm drift presents at 30 fps", "\(fps())")
    // A window drags 300 pt/s through the gas: 60 at once, held while it pushes.
    var up: [Double] = []
    for k in 1...6 { sim.setGeometry([AetherObstacle(id: 1, rect: AetherRect(x: 400 + 25 * Double(k), y: 300, width: 400, height: 300))], sweep: 1.0 / 12)
                     run(sim, 1.0 / 12); up.append(fps()) }
    check(up.allSatisfy { abs($0 - 60) < 1e-9 }, "a window pushing the gas switches it to 60 fps at once", "\(up)")
    // It stops: about 1 s of hold-off at 60, then back to 30.
    var after: [(Double, Double)] = []; let stop = sim.time
    for _ in 0..<60 { sim.step(); after.append((sim.time - stop, fps())) }
    let back = after.first { abs($0.1 - 30) < 1e-9 }?.0 ?? .infinity
    check(after.filter { $0.0 < 0.8 }.allSatisfy { abs($0.1 - 60) < 1e-9 }, "hold-off: 60 fps for ~1 s after the push ends", "\(after.prefix(4))")
    check(back > 0.8 && back < 1.3 && after.filter { $0.0 > 1.3 }.allSatisfy { abs($0.1 - 30) < 1e-9 }, "then back to 30 fps and stays there", "\(back)")
    // A moving sprite stirring the gas also lifts it to 60; a still sprite does not.
    let s2 = AetherSim(bounds: laptop, settings: settings { $0.motion = .living }, seed: 32)
    run(s2, 2)
    for _ in 0..<30 { s2.setSprites([AetherSprite(pos: SIMD2(700, 400), radius: 20, id: "z")]); s2.step() }
    let stillFps = 1 / s2.frameInterval()!
    for f in 0..<30 { if f % 3 == 0 { s2.setSprites([AetherSprite(pos: SIMD2(700 + 2 * Double(f), 400), radius: 20, id: "z")]) }; s2.step() }
    check(abs(stillFps - 30) < 1e-9 && abs(1 / s2.frameInterval()! - 60) < 1e-9, "a sprite stirring the gas lifts it to 60; a still sprite leaves it at 30", "\(stillFps) -> \(1 / s2.frameInterval()!)")
    // The host's thermal cap still wins (30 under thermal Fair), and positions stay blended between steps at 30 fps.
    check(abs(1 / sim.frameInterval(capFps: 30)! - 30) < 1e-9, "a host cap of 30 holds even when pushed")
}

// MARK: determinism
do {
    func fingerprint(_ seed: UInt64) -> Double {
        let s = AetherSim(bounds: laptop, settings: settings { $0.densityPerMpt2 = 400 }, seed: seed)
        run(s, 3); return s.pos.indices.reduce(0) { $0 + s.pos[$1].x * Double($1 % 7 + 1) }
    }
    check(fingerprint(42) == fingerprint(42), "same seed, same run")
    check(fingerprint(42) != fingerprint(43), "different seed, different run")
}

newTests()
print("\(passed) passed, \(failed) failed")
exit(failed == 0 ? 0 : 1)
