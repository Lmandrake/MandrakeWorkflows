import Foundation

extension AetherSim {
    // MARK: the step

    func step(typing: Bool = false) {
        let dt = tuning.dt
        if typing { lastTyping = time }
        prevPos = pos
        let (target, tau, kind) = motionTarget()
        if kind == .settle && lastThermo == .relax { restSigma2 = meanSigma2() }
        lastThermo = kind
        var vmax = 0.0
        for i in pos.indices where phase[i] == .active { vmax = max(vmax, dot2(vel[i], vel[i])) }
        vmax = vmax.squareRoot()
        var k = max(1, Int((vmax * dt / (0.5 * settings.collisionDiameter)).rounded(.up)))
        if settings.attraction > 0 {   // a stiff well: keep ω h under ~0.5 (ω from the steepest part of the taper)
            let depth = fronts.map { max($0.maxAttraction, settings.attraction) * max(sigma0Squared, 0.5) } ?? wellDepth   // the stickiest front
            let w = (1.54 * depth).squareRoot() / max(attractionCutoff - settings.collisionDiameter, 0.5)
            k = max(k, Int((dt * w / 0.5).rounded(.up)))
        }
        k = min(tuning.maxSubsteps, k)
        let h = dt / Double(k)
        frozen = target == 0
        if !frozen { repel(dt) }
        for _ in 0..<k { substep(h, edgeSigma2: target); time += h }
        thermostat(dt, sigma2: target, tau: tau, kind: kind)
        if !frozen { dewStep(dt) }
        turnDipoles(dt)
        work.steps += 1; work.pointSteps += activeCount()
        releaseBoost(dt)
        fades(dt)
        seedRegions(dt)
        if settings.boundary == .reservoir { injectEdges(dt, sigma2: target) }
        crowding()
    }

    /// (target σ², relaxation τ, kind) for the motion style. Settling targets the floor, never below it.
    func motionTarget() -> (Double, Double, Thermo) {
        let s2 = sigma0Squared, lo = floorSigma2
        let modeTau = tuning.thermostatTau ?? (settings.boundary == .reflect ? 60 : 20)
        switch settings.motion {
        case .living: return (s2, modeTau, .relax)
        case .settleWhileTyping:
            let since = time - lastTyping
            if since < tuning.typingHold { return (lo, tuning.settleTau, .settle) }
            if since < tuning.typingHold + 3 * tuning.rewarmTau { return (s2, min(modeTau, tuning.rewarmTau), .rewarm) }
            return (s2, modeTau, .relax)
        case .stirAndSettle: return (lo, tuning.stirSettleTau ?? coolingTau, .settle)
        }
    }

    /// Thermal-edge re-emission probability: 1 at variation 0 (a full heat bath), edgeAccommodationFree at 1.
    var edgeAccommodation: Double {
        let v = settings.temperatureVariation
        return v <= 0 ? 1 : (1 - v) + v * tuning.edgeAccommodationFree
    }

    func substep(_ h: Double, edgeSigma2: Double) {
        let r = radius
        let A = walls.map { $0.rect(time).expanded(by: r) }
        let B = walls.map { $0.rect(time + h).expanded(by: r) }
        let fieldOn = settings.fieldStrength > 0 && !sprites.isEmpty, stirOn = settings.stirring > 0 && !sprites.isEmpty
        if (fieldOn || stirOn) && tuning.spriteGrid { buildGrid() }   // current positions, before anything moves them
        if fieldOn { applyField(h) }
        if stirOn { applyStirring(h) }
        gridFresh = false
        let acc = edgeAccommodation
        for i in pos.indices where phase[i] == .active { sweepMove(i, h, A, B) }
        for i in pos.indices where phase[i] == .active { screenEdge(i, edgeSigma2, acc) }
        buildGrid()
        subH = h
        collide()
        validate(h, A, B)
        enforceCeiling()
        gridFresh = false   // collisions and validate moved points: the grid is a snapshot now
    }

    /// Outward normal of face k (0 minX, 1 maxX, 2 minY, 3 maxY) and that face's outward speed over the substep.
    @inline(__always) func face(_ k: Int, _ a: AetherRect, _ b: AetherRect, _ h: Double) -> (SIMD2<Double>, Double) {
        switch k {
        case 0: return (SIMD2(-1, 0), -(b.minX - a.minX) / h)
        case 1: return (SIMD2(1, 0), (b.maxX - a.maxX) / h)
        case 2: return (SIMD2(0, -1), -(b.minY - a.minY) / h)
        default: return (SIMD2(0, 1), (b.maxY - a.maxY) / h)
        }
    }

    /// Earliest entry time τ in [0, 1] of a point into a rect whose faces move linearly, or nil. c: signed distances
    /// inside each face at τ = 0; g: their change over the interval. Inside = all four positive.
    @inline(__always) static func entry(_ c: SIMD4<Double>, _ g: SIMD4<Double>) -> (Double, Int)? {
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
    func sweepMove(_ i: Int, _ h: Double, _ A: [AetherRect], _ B: [AetherRect]) {
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
    func faceContact(_ i: Int, _ u: SIMD2<Double>, _ p: SIMD2<Double>, _ R: AetherRect, _ k: Int,
                             _ n: SIMD2<Double>, _ wn: Double, normal un2: Double) -> SIMD2<Double> {
        let cap = ceiling
        var t = u - n * dot2(u, n)
        var lim = cap
        if wn > 0.5 { lastPush = time }   // a moving window face is pushing the gas: present at the cap (and pushHold after)
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

    /// Screen edges: reflect (specular), thermal (diffuse re-emission at the target temperature with probability acc,
    /// else specular: a weak, slow source when the temperature may vary), reservoir (leave).
    func screenEdge(_ i: Int, _ sigma2: Double, _ acc: Double) {
        let r = radius
        var p = pos[i], u = vel[i]
        let lo = SIMD2(bounds.minX + r, bounds.minY + r), hi = SIMD2(bounds.maxX - r, bounds.maxY - r)
        for ax in 0..<2 where p[ax] < lo[ax] || p[ax] > hi[ax] {
            if settings.boundary == .reservoir { retire(i, .dormant); stats.removed += 1; return }
            let low = p[ax] < lo[ax]
            p[ax] = min(hi[ax], max(lo[ax], low ? 2 * lo[ax] - p[ax] : 2 * hi[ax] - p[ax]))
            let inward = low ? 1.0 : -1.0
            if settings.boundary == .thermal && sigma2 > 0 && (acc >= 1 || rng.uniform() < acc) {
                let s = sigma2.squareRoot() * (fronts.map { $0.edge[coarseIndex(p)] } ?? settings.edgeTemperature)
                u[ax] = inward * s * rng.rayleigh(); u[1 - ax] = s * rng.gaussian()
            } else { u[ax] = inward * abs(u[ax]) }
        }
        pos[i] = p; vel[i] = u
    }

    @inline(__always) func cellIndex(_ p: SIMD2<Double>) -> Int {
        let x = min(gw - 1, max(0, Int((p.x - bounds.minX) / cell))), y = min(gh - 1, max(0, Int((p.y - bounds.minY) / cell)))
        return y * gw + x
    }

    func buildGrid() {
        for c in cellStart.indices { cellStart[c] = 0 }
        for i in pos.indices where phase[i] == .active { let c = cellIndex(pos[i]); cellOfPoint[i] = c; cellStart[c + 1] += 1 }
        for c in 0..<(gw * gh) { cellStart[c + 1] += cellStart[c] }
        var fill = cellStart
        for i in pos.indices where phase[i] == .active { let c = cellOfPoint[i]; cellItems[fill[c]] = i; fill[c] += 1 }
        gridBuilt = true; gridFresh = true; nearMoved.removeAll(keepingCapacity: true)
    }

    /// The active points that may lie within R of c, into nearBuf: every collision-grid cell under the disk's bounding
    /// box (positions as of buildGrid) plus the points a sprite body moved since. false = no current grid (loop over all).
    func gatherNear(_ c: SIMD2<Double>, _ R: Double) -> Bool {
        guard gridFresh, c.x.isFinite, c.y.isFinite, R.isFinite else { return false }
        nearBuf.removeAll(keepingCapacity: true); nearStamp &+= 1
        let m = R + 1e-6   // a hair over R: a rounding at a cell boundary can only widen the set
        func cl(_ v: Double, _ n: Int) -> Int { Int(min(Double(n - 1), max(0, v))) }   // == cellIndex's clamp
        let x0 = cl((c.x - m - bounds.minX) / cell, gw), x1 = cl((c.x + m - bounds.minX) / cell, gw)
        let y0 = cl((c.y - m - bounds.minY) / cell, gh), y1 = cl((c.y + m - bounds.minY) / cell, gh)
        for cy in y0...y1 { for cx in x0...x1 {
            let n = cy * gw + cx
            for b in cellStart[n]..<cellStart[n + 1] { let i = cellItems[b]; nearSeen[i] = nearStamp; nearBuf.append(i) }
        } }
        for i in nearMoved where nearSeen[i] != nearStamp && phase[i] == .active { nearSeen[i] = nearStamp; nearBuf.append(i) }
        return true
    }

    func collide() {
        let offsets = [(0, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]
        for cy in 0..<gh { for cx in 0..<gw {
            let c = cy * gw + cx
            work.cellsTouched += 1
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

    /// One neighbour pair: the hard core (collision) inside the collision diameter, then the attraction well out to
    /// the cutoff: U = -ε w(d) F, w = (1 - s²)² with s = (d - D)/(Rc - D) (flat at the core, zero slope at the cutoff),
    /// F = (1 - c) + c (3 a b - m_i.m_j)/2, the dipole mix (a, b: each orientation along the bond). The kick is
    /// symplectic Euler at the substep; the well friction damps the pair's normal relative velocity (momentum kept).
    func pair(_ i: Int, _ j: Int) {
        work.pairChecks += 1
        let d = settings.collisionDiameter
        let dv = pos[j] - pos[i], dist2 = dot2(dv, dv)
        let rc = settings.attraction > 0 && !frozen ? max(attractionCutoff, d) : d
        guard dist2 < rc * rc else { return }
        if dist2 <= 1e-18 {
            // Coincident points: deterministic symmetric fallback normal, push apart by the collision-diameter overlap
            let n = SIMD2(1.0, 0.0)
            let rel = vel[j] - vel[i], vn = dot2(rel, n)
            if vn < 0 {
                let pa = max(pressedAt[i], pressedAt[j])
                if time - pa < tuning.pressHold {
                    vel[i] += n * (vn / 2); vel[j] -= n * (vn / 2)
                    pressedAt[i] = pa; pressedAt[j] = pa
                    let b = max(boost[i], boost[j]); boost[i] = b; boost[j] = b
                } else { vel[i] += n * vn; vel[j] -= n * vn }
            }
            let half = d / 2
            pos[i] -= n * half; pos[j] += n * half
            return
        }
        let dist = dist2.squareRoot(), n = dv / dist
        if dist < d {
            let rel = vel[j] - vel[i], vn = dot2(rel, n)
            if vn < 0 {
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
            return
        }
        work.forceEvals += 1
        let h = subH, L = rc - d
        var eps = wellDepth, c = settings.chainForming
        if let fr = fronts { let ci = coarseIndex(pos[i]); eps = fr.attraction[ci] * max(sigma0Squared, 0.5); c = fr.chain[ci] }   // this region's front
        let sv = (dist - d) / L, w = (1 - sv * sv) * (1 - sv * sv), wp = -4 * sv * (1 - sv * sv) / L
        let mi = orient[i], mj = orient[j], a = dot2(mi, n), b = dot2(mj, n), p = dot2(mi, mj)
        let g = (3 * a * b - p) / 2, F = (1 - c) + c * g
        // force on j: -dU/dr_j = ε [w' F n + w c dg/dr], dg/dr = (3/2)(b (m_i - a n) + a (m_j - b n)) / d
        var f = n * (eps * wp * F)
        if c > 0 {
            let q: Double = eps * w * c * 1.5 / dist
            let ta: SIMD2<Double> = (mi - n * a) * (q * b), tb: SIMD2<Double> = (mj - n * b) * (q * a)
            f += ta + tb
        }
        let fl = len2(f); if fl > tuning.maxPairAccel { f *= tuning.maxPairAccel / fl }
        vel[j] += f * h; vel[i] -= f * h
        // Friction only for a pair slow enough to be held (relative normal energy under the local well): a capture,
        // never a drag on the fast gas passing through.
        let vn = dot2(vel[j] - vel[i], n)
        var knot = 1.0
        if settings.knots > 0, time - crossAt[coarseIndex(pos[i])] < tuning.knotLife { knot = tuning.knotGain }   // a knot: two wakes crossed here
        let gamma = vn * vn / 4 < knot * eps * w * max(F, 0) ? knot * tuning.wellFriction / coolingTau * w : 0
        if gamma > 0 {
            let dvn = vn * (1 - exp(-gamma * h)) / 2
            vel[j] -= n * dvn; vel[i] += n * dvn
        }
        if c > 0 {   // the dipole field each feels from the other, -dU/dm / ε, integrated over the step
            dipoleField[i] += (n * (3 * b) - mj) * (w * c / 2 * h)
            dipoleField[j] += (n * (3 * a) - mi) * (w * c / 2 * h)
        }
    }

    /// Orientations turn toward their neighbours' field (overdamped: dθ = rate (m x h) dt) with rotational noise at
    /// the local temperature in units of the well depth (variance 2 rate σ²_local / ε dt): the Langevin pair of the
    /// well, so alignment goes as exp(ε h cos θ / σ²_local), as in a real dipolar gas.
    func turnDipoles(_ dt: Double) {
        guard settings.chainForming > 0, settings.attraction > 0, !frozen else { return }
        let eps = max(wellDepth, 1e-9), rate = tuning.orientRate
        // needle memory: a dot with no neighbours turns slowly (noise x 0.01^memory: at 0.5 it keeps its direction for
        // ~10 s at the default temperature, at 1 for many minutes; 0 is the old free rotation)
        let lone = pow(0.01, min(1, max(0, settings.needleMemory)))
        var gMean: Double? = nil
        for i in pos.indices where phase[i] == .active {
            let m = orient[i], hf = dipoleField[i]
            let torque = m.x * hf.y - m.y * hf.x
            let c = coarseIndex(pos[i])
            let n2 = cCount[c]
            let lSigma2: Double
            if n2 >= 2 {
                let cellMean = cSum[c] / n2
                lSigma2 = max(0, (cSum2[c] / n2 - dot2(cellMean, cellMean)) / 2)
            } else {
                if gMean == nil { gMean = meanSigma2() }
                lSigma2 = gMean!
            }
            let noise = (2 * rate * min(50, lSigma2 / eps) * dt).squareRoot() * (hf == .zero ? lone : 1)
            let th = max(-1, min(1, rate * torque + noise * rng.gaussian()))
            let cs = cos(th), sn = sin(th)
            orient[i] = SIMD2(cs * m.x - sn * m.y, sn * m.x + cs * m.y)
            dipoleField[i] = .zero
        }
    }

    /// Long-range repulsion as particle-in-cell (ruling 8): cloud-in-cell deposit on the coarse cell centres, binomial
    /// smoothing (2 range² passes per axis: σ ≈ range cells; edges replicate, a mirror wall), central-difference
    /// gradient, gathered with the same weights (so no self-force), a = -strength σ0² ∇ρ / ρ̄. O(N + cells x passes).
    func repel(_ dt: Double) {
        guard settings.repulsion > 0 else { return }
        let nbar = max(designDensity * cc * cc, 1e-6)
        let k = settings.repulsion * max(sigma0Squared, 0.5) / nbar
        @inline(__always) func weights(_ p: SIMD2<Double>) -> (Int, Int, Double, Double) {
            let gx = (p.x - bounds.minX) / cc - 0.5, gy = (p.y - bounds.minY) / cc - 0.5
            let x0 = Int(floor(gx)), y0 = Int(floor(gy))
            return (x0, y0, gx - Double(x0), gy - Double(y0))
        }
        @inline(__always) func idx(_ x: Int, _ y: Int) -> Int { min(ch - 1, max(0, y)) * cw + min(cw - 1, max(0, x)) }
        for c in rho.indices { rho[c] = 0 }
        for i in pos.indices where phase[i] == .active {
            let (x0, y0, fx, fy) = weights(pos[i])
            rho[idx(x0, y0)] += (1 - fx) * (1 - fy); rho[idx(x0 + 1, y0)] += fx * (1 - fy)
            rho[idx(x0, y0 + 1)] += (1 - fx) * fy; rho[idx(x0 + 1, y0 + 1)] += fx * fy
        }
        let passes = max(1, Int((2 * settings.repulsionRange * settings.repulsionRange).rounded()))
        for _ in 0..<passes {
            for y in 0..<ch { for x in 0..<cw { rhoTmp[y * cw + x] = (rho[idx(x - 1, y)] + 2 * rho[y * cw + x] + rho[idx(x + 1, y)]) / 4 } }
            for y in 0..<ch { for x in 0..<cw { rho[y * cw + x] = (rhoTmp[idx(x, y - 1)] + 2 * rhoTmp[y * cw + x] + rhoTmp[idx(x, y + 1)]) / 4 } }
        }
        work.cellsTouched += 2 * passes * cw * ch
        @inline(__always) func grad(_ x: Int, _ y: Int) -> SIMD2<Double> {
            let xc = min(cw - 1, max(0, x)), yc = min(ch - 1, max(0, y))
            return SIMD2(rho[idx(xc + 1, yc)] - rho[idx(xc - 1, yc)], rho[idx(xc, yc + 1)] - rho[idx(xc, yc - 1)]) / (2 * cc)
        }
        let cap = tuning.maxRepelAccel
        for i in pos.indices where phase[i] == .active {
            let (x0, y0, fx, fy) = weights(pos[i])
            let g = grad(x0, y0) * ((1 - fx) * (1 - fy)) + grad(x0 + 1, y0) * (fx * (1 - fy))
                  + grad(x0, y0 + 1) * ((1 - fx) * fy) + grad(x0 + 1, y0 + 1) * (fx * fy)
            let kl = fronts.map { k * $0.repulsion[coarseIndex(pos[i])] / settings.repulsion } ?? k   // this region's front
            var a = g * (-kl); let al = len2(a); if al > cap { a *= cap / al }
            vel[i] += a * dt
            work.forceEvals += 1
        }
    }

}
