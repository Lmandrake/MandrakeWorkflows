import Foundation

extension AetherSim {
    // MARK: recovery, thermostat, reserve

    func retire(_ i: Int, _ to: AetherPhase) {
        phase[i] = to
        if to == .dormant { alpha[i] = 0 }
        vel[i] = .zero; boost[i] = 0; pressedAt[i] = -.infinity
    }

    func freeSpot(_ q: SIMD2<Double>, _ rects: [AetherRect]) -> Bool {
        let r = radius
        guard q.x >= bounds.minX + r, q.x <= bounds.maxX - r, q.y >= bounds.minY + r, q.y <= bounds.maxY - r else { return false }
        return !rects.contains { $0.contains(q) }
    }

    /// After all moves: an active point inside a wall is pushed out to the nearest free side (two levels deep, so a
    /// point squeezed between windows or against a screen edge goes round), taking that face's motion. Only a window
    /// that appeared this substep covers points without pushing (dormant: nobody saw it move), and a point with no free
    /// side anywhere near goes dormant. Nothing fades here (owner ruling 2026-11-08: push, never wipe).
    func validate(_ h: Double, _ A: [AetherRect], _ B: [AetherRect]) {
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
    func pushOut(_ p: SIMD2<Double>, _ B: [AetherRect]) -> (SIMD2<Double>, Int, Int)? {
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
    func releaseBoost(_ dt: Double) {
        let cap = ceiling, k = exp(-dt / tuning.pushReleaseTau)
        for i in pos.indices where boost[i] > 0 {
            if phase[i] != .active { boost[i] = 0; continue }
            if time - pressedAt[i] < tuning.dt { continue }
            boost[i] = cap + (boost[i] - cap) * k
            if boost[i] - cap < 0.5 { boost[i] = 0 }
        }
        enforceCeiling()
    }

    func enforceCeiling() {
        let cap = ceiling
        for i in pos.indices where phase[i] == .active {
            let lim = max(cap, boost[i]), v2 = dot2(vel[i], vel[i])
            if v2 > lim * lim { vel[i] *= lim / v2.squareRoot() }
        }
    }

    @inline(__always) func coarseIndex(_ p: SIMD2<Double>) -> Int {
        let x = min(cw - 1, max(0, Int((p.x - bounds.minX) / cc))), y = min(ch - 1, max(0, Int((p.y - bounds.minY) / cc)))
        return y * cw + x
    }

    func buildCoarse() {
        for c in cCount.indices { cCount[c] = 0; cSum[c] = .zero; cSum2[c] = 0 }
        for i in pos.indices where phase[i] == .active {
            let c = coarseIndex(pos[i]); cCount[c] += 1; cSum[c] += vel[i]; cSum2[c] += dot2(vel[i], vel[i])
        }
    }


    /// Ornstein-Uhlenbeck relaxation of each point's velocity relative to its cell's (shrunk) mean flow, toward σ²
    /// with time constant τ (scaled by Temperature variation; a settle is pure damping above variation 0); the flow
    /// itself decays with flowTau; pockets hotter than hotFactor x target damp with hotTau (kicked only at variation 0).
    func thermostat(_ dt: Double, sigma2: Double, tau: Double, kind: Thermo) {
        buildCoarse()
        guard tau.isFinite, tau > 0 else { return }
        let v = settings.temperatureVariation, free = v > 0
        let ouTau = kind == .settle || !free ? tau : (v >= 1 ? Double.infinity : tau / ((1 - v) * (1 - v)))
        let flowTau = tuning.flowTau ?? coolingTau
        let fdecay = exp(-dt / (sigma2 == 0 ? min(flowTau, tau) : flowTau))   // a frozen settle stops flow too
        let hotLimit = tuning.hotFactor * max(sigma2, sigma0Squared, 0.5)
        for i in pos.indices where phase[i] == .active {
            let c = coarseIndex(pos[i]), n = cCount[c]
            let ubar = cSum[c] / (n + 3)
            let m = n > 0 ? cSum[c] / n : SIMD2<Double>.zero
            let local = n >= 2 ? max(0, (cSum2[c] / n - dot2(m, m)) / 2) : dot2(vel[i] - ubar, vel[i] - ubar) / 2
            let hot = local > hotLimit
            let t = hot ? min(ouTau, tuning.hotTau) : ouTau
            let kicked = !free || (kind != .settle && !hot)
            let decay = exp(-dt / t), kick = kicked ? (sigma2 * (1 - decay * decay)).squareRoot() : 0
            var v = ubar * fdecay + (vel[i] - ubar) * decay
            if kick > 0 { v += SIMD2(rng.gaussian(), rng.gaussian()) * kick }
            if sigma2 == 0 && dot2(v, v) < tuning.snapSpeed * tuning.snapSpeed { v = .zero }
            vel[i] = v
        }
        // After typing, a varying gas is rescaled uniformly back toward the energy it had when typing began (its hot
        // and cold regions survive); a gas settled to rest has no pattern left and rewarms by the kicks above.
        let goal = max(restSigma2.isNaN ? sigma0Squared : restSigma2, floorSigma2)
        if free && kind == .rewarm {
            let now = meanSigma2()
            if now > 1e-6 && now < goal {
                let k = (1 + (goal / now - 1) * (1 - exp(-dt / tuning.rewarmTau))).squareRoot()
                for i in pos.indices where phase[i] == .active { vel[i] *= k }
            }
        }
        // The floor is a global guarantee: a gas whose mean energy sits below it is scaled back up to it (a uniform
        // rescale: shapes, wakes and hot/cold regions are kept, nothing is snapped to rest).
        let lo = floorSigma2
        if lo > 0 {
            let now = meanSigma2()
            if now > 1e-12 && now < lo { let k = (lo / now).squareRoot(); for i in pos.indices where phase[i] == .active { vel[i] *= k } }
            else if 0 <= now, now <= 1e-12 {
                // A gas at exactly zero energy cannot be recovered by a uniform rescale: give each active point a
                // deterministic velocity of magnitude sqrt(2 lo) along its dipole orientation (mean per-component
                // variance equals lo).
                let mag = (2 * lo).squareRoot()
                for i in pos.indices where phase[i] == .active { vel[i] = orient[i] * mag }
            }
        }
        enforceCeiling()
    }

    func fades(_ dt: Double) {
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

    func dormantSlot() -> Int? {
        let n = pos.count
        for k in 0..<n {
            let i = (dormantCursor + k) % n
            if phase[i] == .dormant { dormantCursor = (i + 1) % n; return i }
        }
        return nil
    }

    func overlapsPoint(_ q: SIMD2<Double>, batch: [SIMD2<Double>] = []) -> Bool {
        let d2 = settings.collisionDiameter * settings.collisionDiameter
        for p in batch { let dv = p - q; if dot2(dv, dv) < d2 { return true } }
        guard gridBuilt else { return false }
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

    /// Clip a velocity to the speed ceiling (a Gaussian/Rayleigh tail must not enter above the ceiling).
    func clipToCeiling(_ v: SIMD2<Double>) -> SIMD2<Double> {
        let l = len2(v)
        return l > ceiling ? v * (ceiling / l) : v
    }

    func activate(_ i: Int, _ q: SIMD2<Double>, sigma: Double) {
        pos[i] = q; prevPos[i] = q
        vel[i] = clipToCeiling(SIMD2(rng.gaussian(), rng.gaussian()) * sigma)
        phase[i] = .active; alpha[i] = 0; boost[i] = 0; pressedAt[i] = -.infinity
    }

    /// Revealed-space reserve (merge correction 4): top each exposed region up toward the design density from the
    /// dormant pool, with time constant refillTau, at the gas's current temperature. Declared visual physics.
    func seedRegions(_ dt: Double) {
        guard tuning.reserveEnabled, !regions.isEmpty else { return }
        regions.removeAll { $0.expires <= time }
        let r = radius
        let rects = walls.map { $0.rect(time).expanded(by: r) }
        let sigma = meanSigma2().squareRoot()
        // Closed boundaries conserve N: the reserve only gives back what windows took (dormant points).
        var budget = settings.boundary == .reservoir ? Int.max : population - activeCount()
        var placed: [SIMD2<Double>] = []
        var willPlace = false
        for region in regions where region.expires > time {
            let free = aetherSubtract([region.rect], rects).reduce(0) { $0 + $1.area }
            let deficit = region.density * free - Double(activeCount(in: region.rect))
            if deficit >= 1 && (settings.boundary == .reservoir || budget > 0) { willPlace = true; break }
        }
        if willPlace { buildGrid() }
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
                var placedOk = false
                for _ in 0..<8 {
                    let q = SIMD2(R.minX + rng.uniform() * R.width, R.minY + rng.uniform() * R.height)
                    if freeSpot(q, rects) && !overlapsPoint(q, batch: placed) {
                        activate(slot, q, sigma: sigma); stats.seeded += 1; budget -= 1; placed.append(q); placedOk = true; break
                    }
                }
                if !placedOk { break }
            }
        }
        for ri in done.reversed() { regions.remove(at: ri) }
    }

    /// Reservoir edges: effusion inflow n0 σ / √(2π) per pt of edge per second, Maxwell flux velocities.
    func injectEdges(_ dt: Double, sigma2: Double) {
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
                pos[i] = q; prevPos[i] = q
                vel[i] = clipToCeiling(inward * (s * rng.rayleigh()) + tangent * (s * rng.gaussian()))
                phase[i] = .active; alpha[i] = 0; boost[i] = 0; pressedAt[i] = -.infinity
                stats.injected += 1
            }
        }
    }

    /// Capacity policy for crowded pockets: a coarse cell over crowdFactor x the design density fades its excess. A cell
    /// holding a point pressed in the last crowdHold seconds is spared: a pile a window pushed disperses, never fades.
    func crowding() {
        guard time >= nextCrowdCheck else { return }
        nextCrowdCheck = time + tuning.crowdEvery
        buildCoarse()
        let cap = crowdCap
        var spared = Set<Int>()
        for i in pos.indices where phase[i] == .active && time - pressedAt[i] < tuning.crowdHold { spared.insert(coarseIndex(pos[i])) }
        for i in pos.indices.reversed() where phase[i] == .active {
            let c = coarseIndex(pos[i])
            if cCount[c] > cap && !spared.contains(c) { retire(i, .fading); cCount[c] -= 1; stats.crowded += 1 }
        }
    }

    /// The crowding cap, points per coarse cell (tests).
    /// With attraction on, droplets are the point: the cap rises to half of hexagonal close packing in the cell.
    var crowdCap: Double {
        let base = max(tuning.crowdFactor * designDensity * cc * cc, tuning.crowdMin)
        let d = settings.collisionDiameter
        return settings.attraction > 0 ? max(base, 0.5 * cc * cc / (0.866 * d * d)) : base
    }
    func maxCoarseCount() -> Double { buildCoarse(); return cCount.max() ?? 0 }

    /// Sprite stirring (owner, 2026-11-08). Entrainment: within stirReach x radius of a moving sprite, each point's
    /// velocity component along the sprite's motion is pulled up toward the sprite's speed (never braked: a sprite
    /// only drags gas forward), weight (1 - d/R)², so the gas behind it carries a wake. Body: a point inside the
    /// sprite's circle is moved to its edge and given at least the body's outward speed there (a moving round wall).
    /// The ceiling still holds (enforceCeiling after every substep); the wake settles under Cooling.
    func applyStirring(_ h: Double) {
        let k = settings.stirring, r = radius
        for (si, s) in sprites.enumerated() {
            let a = max(s.radius, 1), body = a + r, R = tuning.stirReach * a, R2 = R * R
            let vs = si < spriteVel.count ? spriteVel[si] : .zero, speed = len2(vs)
            let dir = speed > 1e-6 ? vs / speed : .zero
            if speed > 0.5 { lastPush = time }   // a moving sprite stirs the gas: present at the cap (and pushHold after)
            if speed > 0.5 && !s.id.isEmpty { markWake(s, R) }   // knots and the wake reader read these marks
            let shape = settings.speciesWakes > 0 ? AetherWakeShape.of(species: s.species) : .round, sk = settings.speciesWakes
            let side = SIMD2(-dir.y, dir.x)
            // handedness: the stirred gas turns round a moving sprite one way, by project (an exact rotation: no work)
            let curl = settings.handedness * aetherHandedness(key: s.key, id: s.id) * tuning.curlRate * min(1, speed / tuning.curlSpeed)
            func touch(_ i: Int) {
                let dv = pos[i] - s.pos, d2 = dot2(dv, dv)
                guard d2 < R2 else { return }
                let d = d2.squareRoot()
                if speed > 0.5 {
                    let (m, push) = shape == .round ? (1.0, 0.0) : shape.shape(a: dot2(dv, dir) / R, b: dot2(dv, side) / R, k: sk)
                    let w = (1 - max(0, d - a) / (R - a)), f = 1 - exp(-h * tuning.stirRate * k * w * w * m)
                    let along = dot2(vel[i], dir)
                    if along < speed { vel[i] += dir * ((speed - along) * f) }
                    if curl != 0 {
                        let th = curl * w * h, c = cos(th), sn = sin(th), v = vel[i]
                        vel[i] = SIMD2(c * v.x - sn * v.y, sn * v.x + c * v.y)
                    }
                    if push != 0 {   // the species' sideways push, toward push x speed, never past it
                        let target = push * speed, across = dot2(vel[i], side)
                        if (target > 0 && across < target) || (target < 0 && across > target) { vel[i] += side * ((target - across) * (1 - exp(-h * tuning.stirRate * k * w))) }
                    }
                }
                if d < body {
                    let n = d > 1e-9 ? dv / d : SIMD2(1, 0)
                    pos[i] = s.pos + n * (body + 1e-6); nearMoved.append(i)
                    let wn = dot2(vs, n), un = dot2(vel[i], n)
                    if un < wn { vel[i] += n * (wn - un) }
                    if wn <= 0 && un < 0 { vel[i] -= n * un }   // a still body: no motion into it
                }
            }
            if gatherNear(s.pos, R) { for i in nearBuf { touch(i) } }
            else { for i in pos.indices where phase[i] == .active { touch(i) } }
        }
    }

}
