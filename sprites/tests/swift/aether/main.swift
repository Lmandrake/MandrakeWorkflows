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

// MARK: settings plumbing (behaviors.json "aether")
do {
    let d = AetherSettings.parse(behaviorsJSON: "{}")
    check(d.motion == .settleWhileTyping, "default motion is living, settles while typing (ruling 1)")
    check(d.boundary == .thermal, "default boundary is thermal walls (ruling 2)")
    check(d.chains == .rare, "default chains rare (ruling 5: release 1 has chains)")
    check(d.rmsSpeed == 27.5 && d.densityPerMpt2 == 100 && d.particleDiameter == 2.5, "defaults: the owner's 27.5 pt/s (Cool was too slow), Sparse 2.5 pt")
    let a = AetherSettings.parse(behaviorsJSON: #"{"aether":{"motion":"living","boundary":"reservoir","temperature":"warm","density":"dense","chains":"often","fieldStrength":"vivid","colour":"amber","brightness":7}}"#)
    check(a.motion == .living, "always-living is a setting (ruling 1)")
    check(a.boundary == .reservoir && a.rmsSpeed == 16 && a.densityPerMpt2 == 1000 && a.particleDiameter == 1.5,
          "named presets: reservoir, warm, dense 1.5 pt")
    check(a.chains == .often && a.fieldStrength == 1 && a.colour == "amber" && a.brightness == 3, "chains, field, colour, brightness clamps")
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
    let s = settings { $0.boundary = .reflect; $0.densityPerMpt2 = 0; $0.chains = .never; $0.fieldStrength = 0 }
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
    let s = settings { $0.boundary = .reflect; $0.rmsSpeed = 20; $0.collisionDiameter = 2; $0.chains = .never; $0.fieldStrength = 0 }
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
    let s = settings { $0.boundary = .reflect; $0.rmsSpeed = 8; $0.densityPerMpt2 = 2000; $0.chains = .never; $0.fieldStrength = 0 }
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
                           $0.fieldStrength = 0; $0.stirring = stirring; $0.chains = .never; $0.densityPerMpt2 = 1500 }
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
        let s = AetherSim(bounds: laptop, settings: settings { $0.motion = .stirAndSettle; $0.coolingSeconds = secs; $0.chains = .never }, seed: 31)
        run(s, 10); return rms(s)
    }
    let slow = stirred(45), quick = stirred(6)
    check(slow > 3 * quick, "Cooling (drag) slows the settle: 45 s keeps the gas moving after 10 s, 6 s does not", "\(slow) vs \(quick)")
    // After a long settle (typing, and stir-and-settle) the gas never freezes: RMS stays at or above the floor.
    for m in [AetherMotion.settleWhileTyping, .stirAndSettle] {
        let s = AetherSim(bounds: laptop, settings: settings { $0.motion = m; $0.coolingSeconds = 5; $0.minRmsSpeed = 1.5; $0.chains = .never }, seed: 32)
        var lowest = Double.infinity
        for k in 0..<(30 * 60) { s.step(typing: true); if k > 30 * 20 { lowest = min(lowest, rms(s)) } }
        let resting = s.pos.indices.filter { s.phase[$0] == .active && s.vel[$0] == .zero }.count
        check(lowest >= 1.5 - 1e-6, "\(m.rawValue): after a long settle RMS stays at or above the floor", "\(lowest)")
        check(resting == 0, "\(m.rawValue): no point is snapped to rest above a floor", "\(resting)")
        check(s.frameInterval() != nil, "\(m.rawValue): a floored gas keeps presenting (never a frozen frame)")
    }
    // Typing still calms the gas: from the entry temperature down toward the floor.
    let t = AetherSim(bounds: laptop, settings: settings { $0.motion = .settleWhileTyping; $0.chains = .never }, seed: 33)
    run(t, 2); let before = rms(t)
    for _ in 0..<(30 * 3) { t.step(typing: true) }
    check(rms(t) < 0.3 * before && rms(t) >= t.settings.minRmsSpeed - 1e-6, "typing calms the gas, to the floor", "\(before) -> \(rms(t))")
}

// MARK: smooth presentation (owner, 2026-11-08: "discrete jumps")
do {
    // Slow drift at the shipped temperature, presented the way the host does: advance by the frame interval it asks
    // for, draw presentedPos. No presented point may jump more than ~1 pt between frames (a step is 1/30 s).
    let s = settings { $0.motion = .living; $0.rmsSpeed = 27.5; $0.chains = .never }
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
    check(worst <= 1.2, "interpolated output never jumps more than ~1 pt between frames", "\(worst) pt (raw \(worstRaw))")
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
    let hot = settings { $0.boundary = .thermal; $0.rmsSpeed = 3; $0.densityPerMpt2 = 400; $0.chains = .never }
    let sim = AetherSim(bounds: AetherRect(x: 0, y: 0, width: 300, height: 300), settings: hot, seed: 8, tuning: t)
    sim.stir(); sim.stir(); sim.stir()
    let T0 = sim.meanSigma2()
    run(sim, 60)
    check(sim.meanSigma2() < T0 * 0.6, "thermal walls cool a stirred gas toward the entry temperature", "\(T0) -> \(sim.meanSigma2())")
    let res = AetherSim(bounds: AetherRect(x: 0, y: 0, width: 400, height: 400),
                        settings: settings { $0.boundary = .reservoir; $0.rmsSpeed = 8; $0.densityPerMpt2 = 1000; $0.chains = .never },
                        seed: 8, population: 0)
    run(res, 60)
    let want = 1000.0 / 1e6 * 160_000
    check(Double(res.activeCount()) > 0.5 * want && Double(res.activeCount()) < 1.5 * want, "reservoir fills an empty screen toward density",
          "\(res.activeCount()) vs \(want)")
}

// MARK: chains (correction 9, ruling 5)
do {
    var t = AetherTuning(); t.thermostatTau = .infinity; t.reserveEnabled = false
    let s = settings { $0.boundary = .reflect; $0.rmsSpeed = 3; $0.chains = .rare; $0.fieldStrength = 0 }
    let box = AetherRect(x: 0, y: 0, width: 400, height: 400)
    // momentum conserved at bonding
    let a = AetherSim(bounds: box, settings: s, seed: 9, tuning: t, population: 0)
    a.nextFormation = 0
    let p = a.injectPoint(at: SIMD2(197, 200), velocity: SIMD2(0.5, 0.2))!
    let q = a.injectPoint(at: SIMD2(203, 200), velocity: SIMD2(-0.4, 0.0))!
    let before = a.vel[p] + a.vel[q]
    for _ in 0..<300 where a.stats.bonds == 0 { a.step() }
    run(a, 0.5)
    check(a.aliveChains == 1 && a.chainOf[p] == a.chainOf[q] && a.chainOf[p] >= 0, "a slow collision bonds", "\(a.stats.bonds)")
    let after = a.vel[p] + a.vel[q]
    check(abs(after.x - before.x) < 1e-9 && abs(after.y - before.y) < 1e-9, "momentum conserved at bonding and in the constraint",
          "\(before) -> \(after)")
    let d = a.pos[q] - a.pos[p]
    check(abs((d.x * d.x + d.y * d.y).squareRoot() - a.bondLength) < 0.05, "bond holds its length")
    // fast collisions do not bond
    let b = AetherSim(bounds: box, settings: s, seed: 9, tuning: t, population: 0)
    b.nextFormation = 0
    b.injectPoint(at: SIMD2(190, 200), velocity: SIMD2(4, 0)); b.injectPoint(at: SIMD2(210, 200), velocity: SIMD2(-4, 0))
    run(b, 5)
    check(b.stats.bonds == 0, "a fast collision does not bond")
    // never: no chains at all
    let n = AetherSim(bounds: box, settings: settings { $0.chains = .never; $0.boundary = .reflect }, seed: 9, tuning: t, population: 0)
    n.nextFormation = 0
    n.injectPoint(at: SIMD2(195, 200), velocity: SIMD2(0.5, 0)); n.injectPoint(at: SIMD2(205, 200), velocity: SIMD2(-0.5, 0))
    run(n, 10)
    check(n.stats.bonds == 0, "chains: never forms none")
    // length 2-5 and the alive cap, under a dense cool gas with formation always open
    var t2 = t; t2.growProbability = 1
    let dense = AetherSim(bounds: box, settings: settings { $0.boundary = .thermal; $0.rmsSpeed = 3; $0.densityPerMpt2 = 3000; $0.chains = .rare },
                          seed: 10, tuning: t2)
    var maxAlive = 0, maxLen = 0, minLen = 99, maxSpan = 0.0
    run(dense, 120) { sim in
        sim.nextFormation = min(sim.nextFormation, sim.time)    // force chances: test the caps, not the rarity
        maxAlive = max(maxAlive, sim.aliveChains)
        for c in sim.chains.compactMap({ $0 }) {
            maxLen = max(maxLen, c.members.count); minLen = min(minLen, c.members.count)
            let e = sim.pos[c.members.last!] - sim.pos[c.members.first!]
            maxSpan = max(maxSpan, (e.x * e.x + e.y * e.y).squareRoot())
        }
    }
    check(dense.stats.bonds > 0, "chains form in a cool dense gas", "\(dense.stats.bonds)")
    check(maxAlive <= 2, "at most two chains alive (rare)", "\(maxAlive)")
    check(minLen >= 2 && maxLen <= 5, "chain lengths 2-5", "\(minLen)-\(maxLen)")
    check(maxSpan <= dense.tuning.chainSpan, "chain span within 60 pt", "\(maxSpan)")
    check(dense.stats.lifetimes.allSatisfy { $0 <= dense.tuning.chainCap + dense.tuning.dt + 1e-9 }, "hard lifetime cap",
          "\(dense.stats.lifetimes.max() ?? 0)")
    let lt = dense.stats.lifetimes
    if !lt.isEmpty {
        let mean = lt.reduce(0, +) / Double(lt.count)
        check(mean > 2 && mean < 16, "lifetime typical 4-12 s at the entry temperature", "\(mean) over \(lt.count)")
    }
    // breakup release is bounded and momentum-free
    let c = AetherSim(bounds: box, settings: s, seed: 11, tuning: t, population: 0)
    let m = (0..<4).map { c.injectPoint(at: SIMD2(200 + Double($0) * 4, 200), velocity: SIMD2(1, 0))! }
    check(c.formChain(m), "formChain")
    let p0 = m.reduce(SIMD2<Double>.zero) { $0 + c.vel[$1] }
    c.breakChainForTest(0)
    let p1 = m.reduce(SIMD2<Double>.zero) { $0 + c.vel[$1] }
    let kick = m.map { ((c.vel[$0].x - 1) * (c.vel[$0].x - 1) + c.vel[$0].y * c.vel[$0].y).squareRoot() }.max()!
    check(abs(p1.x - p0.x) < 1e-9 && abs(p1.y - p0.y) < 1e-9, "breakup conserves momentum")
    check(kick <= c.tuning.releaseMaxFraction * c.settings.rmsSpeed + 1e-9, "breakup release bounded", "\(kick)")
    check(!c.formChain(Array(0..<1)) , "a chain of one is refused")
    // formation is rare: chances are 20-60 s apart
    let r = AetherSim(bounds: box, settings: s, seed: 12, tuning: t, population: 0)
    check(r.nextFormation >= 20 && r.nextFormation <= 60, "first formation chance in 20-60 s", "\(r.nextFormation)")
}

// MARK: sprite field does no work
do {
    var t = AetherTuning(); t.thermostatTau = .infinity
    let s = settings { $0.boundary = .reflect; $0.fieldStrength = 2; $0.stirring = 0; $0.chains = .never }
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
        let s = settings { $0.densityPerMpt2 = 1000; $0.particleDiameter = 1.5; $0.chains = .never; $0.motion = .living }
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
    let s = settings { $0.boundary = .reflect; $0.densityPerMpt2 = 0; $0.chains = .never; $0.fieldStrength = 0 }
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
    let ps = settings { $0.densityPerMpt2 = 1500; $0.particleDiameter = 1.5; $0.chains = .never; $0.motion = .living }
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

// MARK: determinism
do {
    func fingerprint(_ seed: UInt64) -> Double {
        let s = AetherSim(bounds: laptop, settings: settings { $0.densityPerMpt2 = 400 }, seed: seed)
        run(s, 3); return s.pos.indices.reduce(0) { $0 + s.pos[$1].x * Double($1 % 7 + 1) }
    }
    check(fingerprint(42) == fingerprint(42), "same seed, same run")
    check(fingerprint(42) != fingerprint(43), "different seed, different run")
}

print("\(passed) passed, \(failed) failed")
exit(failed == 0 ? 0 : 1)
