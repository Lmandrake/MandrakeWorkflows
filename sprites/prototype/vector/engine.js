/* Vector Signals renderer: a glyph species drawn as crisp edge-only VECTOR outlines (the Choir stroke idiom).
 * ONE call per species, from that species' piece file:
 *     SpritesVectorEngine(V, GLYPHS)      GLYPHS = [[name, {loops: [[[x, y], ...], ...], lo: [...]}], ... x8]
 * The second renderer beside Living Sigils (prototype/sigils/engine.js), with the same contract: it calls V.piece()
 * itself, closes over its own state (G) and glow-sprite cache, and keeps that engine's layout, navigation and
 * behaviour hooks (homes, V.nav/V.navNeed/V.steer, huddle, knock, play, carry, place, lightSpots), ported unchanged,
 * so the stage and its tests treat a vector species exactly as they treat a sigil species.
 *
 * Why it exists: owner, 2026-11-07, on Night Signals: "we must go with the vector edges to preserve visual identity".
 * The LED grid cannot hold a crisp symbol at sprite size (docs/SYMBOL_RESOLUTION.md); an outline stroked as a
 * 1-2 px hairline resolves at device resolution at every size. Ported out of the round-2 experiment
 * (prototype/experiments/resolution/armC_vector.js, edge mode), with three deliberate changes:
 *   - NO clip(). The native renderer (app/native/canvas.js) does not implement clip, so the CPU sweep is drawn by
 *     stroking only the runs of the outline inside the rotating wedge, rather than clipping a second stroke.
 *   - no pilot light (an LED-panel artefact; on an outline it is a dot sitting on the symbol's interior).
 *   - two levels of detail: `lo` (coarser, fewer segments) below LOD_E CSS px of extent, `loops` above it.
 *
 * Data mapping (same meaning as the c6_night COLOPHON):
 *   identity  hue + which glyph (iv)                 memory    glyph extent E, area-proportional (as sigils)
 *   CPU       a twin wedge of light sweeping round the outline, speed = cores; still = idle
 *   tasks     satellite discs on an orbit outside the glyph, one per background process
 *   rx / tx   cool beads running rim -> core / gold beads core -> rim, inside the glyph; more Mbit/s = more, brighter
 *   net strain  beads stall and bunch at the rim, and the outer outline flickers as a jammed band
 *   machine strain  red ember wash behind, the outline turns ember, the figure shears and its loops slip apart
 *   needs you rippling stroked rings + the approach-and-knock     idle  dim slow breathing
 *   VPN lost  colour drains, huddle (the runtime draws the one searchlight + beacon live)   play  drift + one twirl
 * DOTS MODE (Made Marks, owner 2026-11-07): SpritesVectorEngine(V, GLYPHS, {dots: true}). A glyph then also carries
 * `dots: {"23"|"64"|"256": {d: dot edge in device px at dpr 2, p: [dx, dy, edge, ...] in device px from the centre}}`
 * (tools/species_glyph_sources.py lattices). The level nearest the extent is drawn as hard squares scaled by E / level;
 * the outline is NOT stroked (loops stay for the rim, beads and the strain flicker); the CPU sweep lights the dots in
 * its wedge. Everything else in the species is this engine unchanged.
 * iv wraps over the table length (every shipped table holds 8).
 * GLYPH TABLES carry no data (GRAMMAR_V2.md): which symbol it is means nothing about the session.
 *
 * Additive-safe: every layer composites with "lighter", so nothing here may be dark (a dark stroke adds nothing and
 * is invisible; round 1 lost the TARDIS panels that way). The glyph table is one file per species, deliberately
 * (prototype/vector/glyphs_*_vector.js): a trademark-bearing species is one file deletion plus its registrations. */
(function (root) {
"use strict";
root.SpritesVectorEngine = function (V, GLYPHS, OPT) {
  const TAU = Math.PI * 2, LOD_E = 90;
  const clamp = (x, a, b) => x < a ? a : x > b ? b : x;
  const lerp = (a, b, f) => a + (b - a) * f;
  let G = null;
  window.VARIANT_NAMES = GLYPHS.map(g => g[0]);

  // ---------- glyph prep (once per variant): both detail levels, plus a resampled copy for the sweep ----------
  function prepLevel(loops) {
    let rmax = 0; const rim = new Float32Array(72);              // rim[k]: the glyph's outer radius in angle bin k
    const fine = [];                                             // per loop: Float32Array [x, y, angle, ...] at <= 0.035 unit
    for (const l of loops) {
      const f = [];
      for (let k = 0; k < l.length; k++) { const a = l[k], b = l[(k + 1) % l.length], n = Math.max(1, Math.ceil(Math.hypot(b[0] - a[0], b[1] - a[1]) / 0.035));
        for (let s = 0; s < n; s++) { const x = a[0] + (b[0] - a[0]) * s / n, y = a[1] + (b[1] - a[1]) * s / n, r = Math.hypot(x, y), an = Math.atan2(y, x);
          f.push(x, y, an); if (r > rmax) rmax = r; const bin = ((Math.floor((an + Math.PI) / TAU * 72) % 72) + 72) % 72; if (r > rim[bin]) rim[bin] = r; } }
      fine.push(Float32Array.from(f));
    }
    for (let k = 0; k < 72; k++) if (!rim[k]) rim[k] = Math.max(rim[(k + 71) % 72], rim[(k + 1) % 72], 0.3);
    return { loops, fine, rmax: rmax || 1, rim };
  }
  const PREP = GLYPHS.map(([name, g]) => ({ name, hi: prepLevel(g.loops), lo: prepLevel(g.lo || g.loops) }));
  const DOTS = !!(OPT && OPT.dots);
  const DKEYS = [23, 64, 256];
  if (DOTS) GLYPHS.forEach(([, g], i) => { PREP[i].dl = {};
    for (const k of DKEYS) { const d = g.dots[String(k)], n = d.p.length / 3, a = new Float32Array(n * 4);
      for (let j = 0; j < n; j++) { const x = d.p[j * 3], y = d.p[j * 3 + 1]; a[j * 4] = x; a[j * 4 + 1] = y; a[j * 4 + 2] = Math.atan2(y, x); a[j * 4 + 3] = d.p[j * 3 + 2]; }
      PREP[i].dl[k] = { d: d.d, a, n }; } });
  const glyphOf = iv => PREP[((iv % PREP.length) + PREP.length) % PREP.length];
  const rimAt = (lv, a) => lv.rim[((Math.floor((a + Math.PI) / TAU * 72) % 72) + 72) % 72];

  // ---------- glow sprites (cached per colour string): the only rasters, all of them soft halos with no edge ----------
  const SPR = new Map();
  function sprite(col) {
    let c = SPR.get(col); if (c) return c;
    c = document.createElement("canvas"); c.width = c.height = 64; const x = c.getContext("2d");
    const g = x.createRadialGradient(32, 32, 0, 32, 32, 32);
    g.addColorStop(0, col); g.addColorStop(0.25, col.replace(/,[\d.]+\)$/, ",0.35)")); g.addColorStop(1, col.replace(/,[\d.]+\)$/, ",0)"));
    x.fillStyle = g; x.fillRect(0, 0, 64, 64); SPR.set(col, c); return c;
  }
  const q5 = v => Math.round(v / 5) * 5;

  // ---------- layout: homes in free space, away from focus, menu bar and dock (ported from the sigils engine) ----------
  function rectDist(x, y, f) { if (!f) return 1e4; const [rx, ry, rw, rh] = f;
    const dx = Math.max(rx - x, 0, x - (rx + rw)), dy = Math.max(ry - y, 0, y - (ry + rh)); return Math.hypot(dx, dy) * ((dx || dy) ? 1 : -1); }
  function computeHomes(V, f, all) {
    const sigs = all.filter(s => !s.ghost);
    if (sigs.length === all.length) return computeHomes0(V, f, sigs);
    const h = sigs.length ? computeHomes0(V, f, sigs) : [], out = []; let k = 0;
    for (const s of all) out.push(s.ghost ? [s.x, s.y] : h[k++]);
    return out;
  }
  function szOf(V, gal, crowd) { return V.P.size * (V.LIVE ? Math.min(V.W / 1280, V.H / 800) : gal ? V.H / 400 * 1.9 * crowd : 1); }
  function computeHomes0(V, f, sigs) {
    const n = sigs.length, gal = G.gal;
    if (!f && gal) {
      let bc = 1, bs = -1;
      for (let c = 1; c <= n; c++) { const r = Math.ceil(n / c), sc = Math.min(V.W / c, (V.H - V.TOP - V.BOT) / r); if (sc > bs + 0.5) { bs = sc; bc = c; } }
      const cols = bc, ch = (V.H - V.TOP - V.BOT) / Math.ceil(n / cols), cw = V.W / cols, out = [];
      for (let k = 0; k < n; k++) { const r = Math.floor(k / cols), inRow = Math.min(cols, n - r * cols), c = k % cols;
        out.push([V.W / 2 + (c - (inRow - 1) / 2) * cw, V.TOP + (r + 0.5) * ch]); }
      return out; }
    const R = (gal ? 50 : 80) * G.SZ, mx = gal ? R : 70, slots = [];
    const edge = (x, y) => Math.min(x, V.W - x, y - V.TOP, V.H - V.BOT - y);
    for (let y = V.TOP + R + 6; y <= V.H - V.BOT - R; y += 12) for (let x = mx; x <= V.W - mx; x += 12) {
      const d = rectDist(x, y, f); if (d > R) slots.push([x, y, gal ? Math.min(d, 2 * edge(x, y)) : d]); }
    if (!slots.length) for (let x = mx; x <= V.W - mx; x += 60) slots.push([x, V.H - V.BOT - R, 0]);
    const chosen = [];
    let best = slots[0]; for (const s of slots) if (s[2] > best[2]) best = s; chosen.push(best);
    while (chosen.length < sigs.length) {
      let bs = null, bd = -1;
      for (const s of slots) { let m = 1e9; for (const c of chosen) m = Math.min(m, Math.hypot(s[0] - c[0], s[1] - c[1]));
        m = Math.min(m, s[2] * 1.4 + 40 * G.SZ); if (m > bd) { bd = m; bs = s; } }
      chosen.push(bs);
    }
    const free = chosen.slice(), out = new Array(sigs.length);
    const order = sigs.map((s, i) => i).sort((a, b) => sigs[a].x - sigs[b].x);
    for (const i of order) { let bi = 0, bd = 1e9;
      free.forEach((c, j) => { const d = Math.hypot(c[0] - sigs[i].x, c[1] - sigs[i].y); if (d < bd) { bd = d; bi = j; } });
      out[i] = [free[bi][0], free[bi][1]]; free.splice(bi, 1); }
    return out;
  }
  function segHitsRect(x0, y0, x1, y1, rx, ry, rw, rh) {
    for (let k = 0; k <= 24; k++) { const u = k / 24, x = x0 + (x1 - x0) * u, y = y0 + (y1 - y0) * u;
      if (x > rx && x < rx + rw && y > ry && y < ry + rh) return true; } return false; }
  function sigRadius(V, s) { return s.E * 0.72 + 10 * G.SZ; }
  // strain: loop k slips by a small per-loop noise vector (declared before V.piece: __renderAt draws synchronously)
  const slipOf = (k, slip, t, hue) => slip ? [(V.vnoise(k * 3.7 + hue, t * 2.6) - 0.5) * slip, (V.vnoise(k * 5.1 + 40 + hue, t * 2.6) - 0.5) * slip] : [0, 0];
  const extentOf = (mem) => 9 * 6 * Math.sqrt(clamp(mem, 0.2, 2.6) / 0.8) * G.SZ;   // same E as sigils: area = memory

  V.piece({
    init(V, S) {
      const n = V.sessions.length, gal = !V.LIVE && (V.H < 700 || V.W < 1000);
      const old = G, oldSigs = new Map(old ? old.sigs.map(o => [o.id, o]) : []);
      const crowd = gal ? (n <= 2 ? 1 : n <= 3 ? 0.9 : clamp(Math.sqrt(3 / n) * 1.3, 0.78, 0.9)) : 1;
      G = { gal, crowd, SZ: szOf(V, gal, crowd) };
      const allZero = !V.LIVE && !new URLSearchParams(location.search).get("iv") && n > 1 && V.sessions.every(z => !z.iv);
      const sigs = V.sessions.map((ss, i) => {
        const a = (i + 0.5) / V.sessions.length, o = V.LIVE ? oldSigs.get(ss.id) : null;
        if (o && o.iv === ss.iv) { o.hue = ss.hue; o.ghost = !!ss.ghost; o.kept = true; return o; }
        const iv = allZero ? i : ss.iv;
        return { id: ss.id, ghost: !!ss.ghost, hue: ss.hue, iv, gl: glyphOf(iv), x: 760 + 420 * Math.cos(a * TAU) * 0.5, y: 400 + 260 * Math.sin(a * TAU) * 0.6,
          vx: 0, vy: 0, wx: 0, wy: 0, hx: 0, hy: 0, E: 54, spin: 0, orb: V.rand() * TAU,
          bright: 0.5, needT: -1, needAmt: 0, flare: 0, heatSm: 0, playAmt: 0, state: "idle", mem: 0.5, procs: 2, cpu: 0,
          pulses: [], inAcc: 0, outAcc: 0, bwS: 0, rx: 0, tx: 0 };
      });
      Object.assign(G, { sigs, embers: [], sparks: [], focusKey: "", homes: [], vpnAmt: S.net.vpn === "down" ? 1 : 0,
            prevVpn: S.net.vpn, playPhase: 0, beat: 0, beam: 0 });
      if (V.LIVE && old) for (const k of ["embers", "sparks", "vpnAmt", "prevVpn", "playPhase", "beat", "beam", "playT"]) if (old[k] !== undefined) G[k] = old[k];
      for (const s of sigs) if (!s.kept) { s.mem = S.s[s.id].mem; s.E = extentOf(s.mem); }
      G.homes = computeHomes(V, S.focus, sigs);
      sigs.forEach((s, i) => { if (!s.kept) { s.x = G.homes[i][0]; s.y = G.homes[i][1]; s.hx = s.x; s.hy = s.y; } delete s.kept; V.report(s.id, s.x, s.y, sigRadius(V, s)); });
      G.focusKey = (S.focus || []).map(Math.round).join();
    },
    carry(V, S, prev) {
      for (const s of G.sigs) { const p = prev[s.id]; if (!p) continue; s.x = p.x; s.y = p.y; V.report(s.id, s.x, s.y, sigRadius(V, s)); }
    },
    resize(V, S) { if (!G) return; G.SZ = szOf(V, G.gal, G.crowd); G.homes = computeHomes(V, S.focus, G.sigs); },
    place(V, id, x, y) { const s = G && G.sigs.find(z => z.id === id); if (s) { s.x = x; s.y = y; s.vx = s.vy = 0; } },
    // running lights: a row under the glyph's lowest point
    lightSpots(V, id, n) {
      const s = G && G.sigs.find(z => z.id === id); if (!s) return null;
      const gap = Math.max(5, Math.min(s.E / 9 * 0.9, 8)) * Math.sqrt(V.P.size), w = (n - 1) * gap, y = s.y + s.E * 0.5 + s.E / 6 + 4;
      const out = []; for (let i = 0; i < n; i++) out.push([s.x - w / 2 + i * gap, y]); return out;
    },

    step(V, S, dt) {
      const t = V.t, sigs = G.sigs, f = S.focus;
      const fk = (f || []).map(Math.round).join();
      if (fk !== G.focusKey) { G.focusKey = fk; G.homes = computeHomes(V, f, sigs); }
      const down = S.net.vpn === "down";
      if (G.prevVpn === "down" && !down && V.reconnected(S.net)) {   // reconnect: one joyful bloom
        for (const s of sigs) { if (s.ghost) continue; s.flare = 1; const n = Math.round(30 * V.P.density);
          for (let k = 0; k < n; k++) { const a = k / n * TAU + V.rand() * 0.2, sp = 120 + 120 * V.rand();
            G.sparks.push({ x: s.x, y: s.y, vx: Math.cos(a) * sp, vy: Math.sin(a) * sp, life: 1.4, max: 1.4, hue: s.hue }); } } }
      G.prevVpn = S.net.vpn;
      G.vpnAmt = clamp(G.vpnAmt + (down ? dt / 0.8 : -dt / 0.5), 0, 1);
      if (down) { G.beat += dt; G.beam += dt * 0.55; }
      const heat = clamp(S.m.level / 3, 0, 1), thermal = S.m.thermal || 0, mp = S.m.mempress || 0;
      const pair = (S.play && S.play.pair) || [], pamt = V.on("play") ? (S.play && S.play.amt) || 0 : 0;
      const onNeeds = V.on("needsApproach"), onHuddle = V.on("vpnHuddle"), onStrain = V.on("strainAgitation");
      G.playT = pamt > 0.6 ? (G.playT || 0) + dt : 0;
      { const u = clamp((G.playT - 1.2) / 2.6, 0, 1); G.playPhase = Math.PI * u * u * (3 - 2 * u) - Math.PI / 2; }
      const pi = pair.map(id => sigs.findIndex(s => s.id === id && !s.ghost));
      let cx = 0, cy = 0, nh = 0; G.homes.forEach((h, k) => { if (sigs[k].ghost) return; cx += h[0]; cy += h[1]; nh++; }); nh = Math.max(1, nh); cx /= nh; cy /= nh;
      if (V.LIVE && V.huddlePt) { cx = V.huddlePt[0]; cy = V.huddlePt[1]; }
      G.hud = [cx, cy];
      const hudIdx = sigs.filter(z => !z.ghost);
      sigs.forEach((s, i) => {
        const d = S.s[s.id];
        s.cpu = d.cpu; s.mem = d.mem; s.procs = d.procs;
        if (d.state === "needs" && s.state !== "needs") s.needT = 0;
        s.state = d.state;
        if (s.state === "needs") s.needT += dt;
        s.needAmt = clamp(s.needAmt + (s.state === "needs" ? dt / 0.4 : -dt / 0.8), 0, 1);
        const tgtB = s.state === "idle" ? 0.5 : s.state === "needs" ? 1 : 0.85;
        s.bright += (tgtB - s.bright) * Math.min(1, dt * 3);
        s.flare = Math.max(0, s.flare - dt / 0.9);
        s.heatSm += (heat - s.heatSm) * Math.min(1, dt * 2);
        s.E += (extentOf(s.mem) - s.E) * Math.min(1, dt * 2.5);
        s.spin += dt * TAU * 0.85 * s.cpu;
        // ---- bandwidth: beads inside the glyph. rx = rim -> core (cool), tx = core -> rim (gold); jam at the rim ----
        s.rx = d.rx || 0; s.tx = d.tx || 0;
        const moving = clamp(Math.log10(1 + s.rx + s.tx) / 0.8, 0, 1), bwT = (S.net.strain || 0) * moving * (1 - G.vpnAmt);
        s.bwS += (bwT - s.bwS) * Math.min(1, dt * 3);
        const thr = 1 - 0.5 * s.bwS, live = 1 - G.vpnAmt;
        s.inAcc += dt * 5.5 * Math.log10(1 + s.rx) * thr * live; s.outAcc += dt * 5.5 * Math.log10(1 + s.tx) * thr * live;
        const brIn = 0.55 + 0.45 * clamp(Math.log10(1 + s.rx) / 1.4, 0, 1), brOut = 0.55 + 0.45 * clamp(Math.log10(1 + s.tx) / 1.4, 0, 1);
        while (s.inAcc >= 1) { s.inAcc -= 1; s.pulses.push({ dir: -1, a: V.rand() * TAU, u: 1.0, br: brIn, sd: V.rand() * 50 }); }
        while (s.outAcc >= 1) { s.outAcc -= 1; s.pulses.push({ dir: 1, a: V.rand() * TAU, u: 0.05, br: brOut, sd: V.rand() * 50 }); }
        for (const p of s.pulses) { let sp = 1.0;
          if (s.bwS > 0.02) { const go = V.vnoise(p.sd, t * 4) > 0.55 ? 1 : 0.08, rim = p.u > 0.66; sp *= lerp(1, (rim ? 0.10 : 0.55) * go, s.bwS); }
          p.u += p.dir * sp * dt; }
        s.pulses = s.pulses.filter(p => p.dir < 0 ? p.u > 0.02 : p.u < 1.0);
        if (s.pulses.length > 36) s.pulses.splice(0, s.pulses.length - 36);
        if (G.vpnAmt > 0.5) s.pulses.length = 0;
        s.orb += dt * (s.state === "working" ? 0.6 : 0) * (1 + mp * 0.5);
        // ---- home for this frame (ported from the sigils engine: play, needs-you knock, VPN huddle) ----
        let hx = G.homes[i][0], hy = G.homes[i][1];
        const k = pi.indexOf(i);
        if (k >= 0 && pi[1 - k] >= 0 && pamt > 0) {
          const o = G.homes[pi[1 - k]], mx = (hx + o[0]) / 2, my = (hy + o[1]) / 2;
          const sep = (sigRadius(V, s) + sigRadius(V, sigs[pi[1 - k]])) * (G.gal ? 0.5 : 0.75) + 18, a = G.playPhase + (k ? Math.PI : 0);
          hx = lerp(hx, mx + Math.cos(a) * sep, pamt); hy = lerp(hy, my + Math.sin(a) * sep * 0.8, pamt);
          if (rectDist(hx, hy, f) < sigRadius(V, s) + 20) { hx = G.homes[i][0]; hy = G.homes[i][1]; }
        }
        s.playAmt = k >= 0 ? pamt : 0;
        if (s.needAmt > 0 && f && onNeeds) {
          const [rx, ry, rw, rh] = f, r = sigRadius(V, s) + 30;
          let nx, ny = clamp(G.homes[i][1], Math.max(ry + 50, V.TOP + r), Math.min(ry + rh - 50, V.H - V.BOT - r)), dir;
          if (G.homes[i][0] > rx + rw / 2 && rx + rw + r < V.W - 20) { nx = rx + rw + r; dir = -1; }
          else if (rx - r > 20) { nx = rx - r; dir = 1; }
          else { nx = rx + rw + r; dir = -1; }
          s.knockDir = dir;
          const e = s.needAmt; hx = lerp(hx, nx, e); hy = lerp(hy, ny, e);
        }
        if (G.vpnAmt > 0 && onHuddle && !s.ghost) {
          const a = hudIdx.indexOf(s) / hudIdx.length * TAU + 0.6, rr = (G.gal ? 0.85 : 1) * (34 + 14 * hudIdx.length) * G.SZ;
          hx = lerp(hx, cx + Math.cos(a) * rr, G.vpnAmt * (1 - s.needAmt)); hy = lerp(hy, cy + Math.sin(a) * rr * 0.8, G.vpnAmt * (1 - s.needAmt));
        }
        s.hx = hx; s.hy = hy;
        if (f && !V.LIVE) { const [rx, ry, rw, rh] = f, m = sigRadius(V, s) + 16;
          if (segHitsRect(s.x, s.y, hx, hy, rx - m, ry - m, rw + 2 * m, rh + 2 * m)) {
            if (s.y > ry - m && s.y < ry + rh + m) {
              const up = ry - m, dn = ry + rh + m, okU = up > V.TOP + m * 0.6, okD = dn < V.H - V.BOT - m * 0.6;
              hy = (okU && (!okD || Math.abs(s.y - up) < Math.abs(s.y - dn))) ? up : dn; hx = s.x + Math.sign(hx - s.x) * 30;
            } else { hy = s.y; } } }
        // ---- idle wander (curl noise, the only data-free motion; restless under strain) ----
        const agit = onStrain ? 1 + 2.2 * s.heatSm * s.heatSm : 1, still = 1 - 0.8 * G.vpnAmt;
        const [ux, uy] = V.curl(s.x + i * 300, s.y, t * (0.4 + (onStrain ? 1.2 : 0) * s.heatSm));
        s.wx += (ux * 7 * V.P.drift * agit * still - s.wx * 0.08) * dt;
        s.wy += (uy * 7 * V.P.drift * agit * still - s.wy * 0.08) * dt;
        const wr = Math.hypot(s.wx, s.wy), wmax = 45 * V.P.drift * (1 - s.needAmt) * still * (s.state === "idle" && (!onStrain || s.heatSm < 0.2) ? 0.55 : 1) + 2;
        if (wr > wmax) { s.wx *= wmax / wr; s.wy *= wmax / wr; }
        const rr0 = sigRadius(V, s);
        let tx = clamp(hx + s.wx, 6 + rr0, V.W - 6 - rr0), ty = clamp(hy + s.wy, V.TOP + 4 + rr0, V.H - V.BOT - 4 - rr0);
        if (V.LIVE && (s.ghost || (s.needAmt < 0.01 && !(G.vpnAmt > 0.01 && onHuddle) && s.playAmt < 0.01))) [tx, ty] = V.steer(s.id, tx, ty, rr0);
        if (V.LIVE) [tx, ty] = (s.needAmt < 0.5 ? V.nav : V.navNeed)(s.id, s.x, s.y, tx, ty, rr0);
        const K = (V.LIVE && V.huddlePt && G.vpnAmt > 0.3 && onHuddle) ? 9 : 5, C = 2 * Math.sqrt(K);
        let ax = K * (tx - s.x) - C * s.vx, ay = K * (ty - s.y) - C * s.vy;
        const r = sigRadius(V, s);
        const [fx, fy] = V.avoid(s.x, s.y, r + 20); ax += fx * 500; ay += fy * 500;
        if (V.insideFocus(s.x, s.y, r * 0.5)) { ax += fx * 1500; ay += fy * 1500; }
        for (let j = 0; j < sigs.length; j++) if (j !== i && !sigs[j].ghost && !s.ghost) { const o = sigs[j], dx = s.x - o.x, dy = s.y - o.y, dd = Math.hypot(dx, dy) + 1e-3;
          const want = (r + sigRadius(V, o)) * ((G.vpnAmt > 0.5 && onHuddle) || s.playAmt > 0.5 ? 0.55 : 0.95);
          if (dd < want) { ax += dx / dd * (want - dd) * 6; ay += dy / dd * (want - dd) * 6; } }
        s.vx += ax * dt; s.vy += ay * dt;
        const vm = Math.hypot(s.vx, s.vy), vcap = 520; if (vm > vcap) { s.vx *= vcap / vm; s.vy *= vcap / vm; }
        s.x += s.vx * dt; s.y += s.vy * dt;
        V.report(s.id, s.x, s.y, r);
        if (thermal > 0.05 && G.vpnAmt < 0.5 && !s.ghost) {
          s.emAcc = (s.emAcc || 0) + dt * thermal * 1.6 * V.P.density;
          while (s.emAcc >= 1) { s.emAcc -= 1; G.embers.push({ x: s.x + (V.rand() - 0.5) * s.E, y: s.y - s.E * 0.3, vx: (V.rand() - 0.5) * 14, vy: -30 - 40 * V.rand(), life: 1.6, max: 1.6 }); }
        }
      });
      for (const e of G.embers) { e.x += e.vx * dt; e.y += e.vy * dt; e.life -= dt; }
      G.embers = G.embers.filter(e => e.life > 0);
      for (const p of G.sparks) { p.x += p.vx * dt; p.y += p.vy * dt; p.vx *= 0.97; p.vy *= 0.97; p.life -= dt; }
      G.sparks = G.sparks.filter(p => p.life > 0);
    },

    draw(V, S, ctx) {
      const sigs = G.sigs, P = V.P, vpn = G.vpnAmt;
      ctx.save(); ctx.globalCompositeOperation = "lighter";
      if (vpn > 0.01 && V.on("vpnHuddle") && !V.LIVE) {   // live: the runtime draws the one searchlight + beacon
        const [cx, cy] = G.hud, a = G.beam, L = 0.4 * Math.hypot(V.W, V.H);
        ctx.globalAlpha = 0.10 * vpn * P.glow;
        const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, L);
        g.addColorStop(0, V.hsl(205, 25, 75, 0.9)); g.addColorStop(1, V.hsl(205, 25, 60, 0));
        ctx.fillStyle = g; ctx.beginPath(); ctx.moveTo(cx, cy); ctx.arc(cx, cy, L, a - 0.12, a + 0.12); ctx.closePath(); ctx.fill();
        const on = G.beat % 1.5 < 0.22 ? 1 : 0, rs = sprite(V.hsl(0, 95, 55, 1)), rr = 13 * Math.sqrt(P.glow * G.SZ);
        ctx.globalAlpha = vpn * (0.12 + 0.75 * on); ctx.drawImage(rs, cx - rr, cy - rr, rr * 2, rr * 2);
        ctx.globalAlpha = vpn * (0.3 + 0.7 * on); ctx.fillStyle = V.hsl(0, 95, 62, 1); ctx.beginPath(); ctx.arc(cx, cy, 2.2, 0, TAU); ctx.fill();
      }
      for (const s of sigs) V.creature(s.id, () => drawOne(V, S, ctx, s));
      for (const e of G.embers) { const u = e.life / e.max; ctx.globalAlpha = 0.7 * u; ctx.fillStyle = V.hsl(8 + 18 * (1 - u), 95, 60, 1);
        ctx.beginPath(); ctx.arc(e.x, e.y, 1.2, 0, TAU); ctx.fill(); }
      for (const p of G.sparks) { const u = p.life / p.max; ctx.globalAlpha = u * 0.9; ctx.fillStyle = V.hsl(p.hue, 90, 70, 1);
        ctx.beginPath(); ctx.arc(p.x, p.y, 1.5, 0, TAU); ctx.fill(); }
      ctx.restore();
    },
  });

  // the outline as one path: each loop closed. `slip` (strain) offsets loop k by a small per-loop noise vector
  function outlinePath(ctx, lv, R, slip, t, hue) {
    ctx.beginPath();
    lv.loops.forEach((l, k) => {
      const [ox, oy] = slipOf(k, slip, t, hue);
      ctx.moveTo(l[0][0] * R + ox, l[0][1] * R + oy);
      for (let q = 1; q < l.length; q++) ctx.lineTo(l[q][0] * R + ox, l[q][1] * R + oy);
      ctx.closePath(); });
  }
  // the CPU sweep: the runs of the (resampled) outline whose angle lies inside the twin wedge, as open polylines.
  // Clip-free on purpose: app/native/canvas.js does not implement clip().
  function sweepPath(ctx, lv, R, spin, cut, slip, t, hue) {
    ctx.beginPath(); let any = false;
    lv.fine.forEach((f, li) => { const n = f.length / 3, [ox, oy] = slipOf(li, slip, t, hue); let open = false;
      for (let q = 0; q <= n; q++) { const k = (q % n) * 3, w = Math.pow(Math.max(0, Math.cos(2 * (f[k + 2] - spin))), 6);
        if (w > cut) { const x = f[k] * R + ox, y = f[k + 1] * R + oy; if (!open) { ctx.moveTo(x, y); open = true; any = true; } else ctx.lineTo(x, y); }
        else open = false; } });
    return any;
  }
  // DOTS MODE. The lattice nearest the extent, scaled by E / level (device px at dpr 2 -> CSS px x0.5 x scale).
  // mode edge: 0 = interior dots, 1 = edge dots, 2 = all; spin/cut: only dots inside the CPU wedge when cut > 0.
  function dotsPass(ctx, s, E, spin, edge, cut, slip, t, h, sa, li) {
    const lvl = E < 40 ? 23 : E < 130 ? 64 : 256, L = s.gl.dl[lvl], k = E / lvl * 0.5, sz = L.d * k, a = L.a;
    ctx.fillStyle = V.hsl(h, sa, li, 1); let on = false;
    const o = slipOf(0, slip, t, s.hue);
    ctx.beginPath();
    for (let j = 0; j < L.n; j++) { const q = j * 4;
      if (edge !== 2 && a[q + 3] !== edge) continue;
      if (cut > 0 && Math.pow(Math.max(0, Math.cos(2 * (a[q + 2] - spin))), 6) <= cut) continue;
      ctx.rect(a[q] * k - sz / 2 + o[0], a[q + 1] * k - sz / 2 + o[1], sz, sz); on = true; }
    if (on) ctx.fill();
  }
  // the dot body: interior at the body tone, edge dots a touch brighter (the samples' "hard dots, no halo")
  function dotsBody(ctx, s, E, sat, light, B, flowDim, heat, slip, t) {
    const g = (1 - 0.65 * heat) * (1 - 0.4 * clamp(s.cpu / 0.35, 0, 1)) * flowDim;
    ctx.globalAlpha = clamp((0.55 + 0.35 * B) * g, 0, 1); dotsPass(ctx, s, E, 0, 0, 0, slip, t, s.hue, sat, Math.min(80, light));
    ctx.globalAlpha = clamp((0.7 + 0.3 * B) * g, 0, 1); dotsPass(ctx, s, E, 0, 1, 0, slip, t, s.hue, sat * 0.9, Math.min(90, light + 22));
  }
  function knock(tn) { const p = tn % 2.6; const bump = (c) => Math.max(0, 1 - Math.abs(p - c) / 0.09); return bump(1.0) + bump(1.3); }

  function drawOne(V, S, ctx, s) {
    const P = V.P, t = V.t, vpn = G.vpnAmt, E = s.E, R = E * 0.5, heat = s.heatSm * (1 - vpn), sa = V.on("strainAgitation");
    const lv = E < LOD_E ? s.gl.lo : s.gl.hi;
    const kn = s.needAmt > 0.5 && V.on("needsApproach") ? knock(s.needT) * 7 * (s.knockDir || 0) : 0;
    const ox = s.x + kn, oy = s.y;
    const sat = lerp(lerp(92, 80, heat), 40, vpn), light = lerp(lerp(60, 70, heat), 62, vpn);
    const breathe = s.state === "idle" ? 0.88 + 0.12 * Math.sin(t * TAU / 7 + s.hue) : 1;
    const B = clamp(s.bright + s.flare * 0.6, 0, 1.4) * (1 - 0.25 * vpn) * breathe;
    // body halo: soft, and low (0.35 of the sigils halo) so it never washes over the outline
    const hr = E * 0.95 * Math.sqrt(P.glow);
    ctx.globalAlpha = clamp((0.30 * B * P.glow * (0.6 + 0.4 * s.needAmt) + s.flare * 0.3) * 0.35, 0, 1);
    ctx.drawImage(sprite(V.hsl(q5(s.hue), q5(sat), 50, 1)), ox - hr, oy - hr, hr * 2, hr * 2);
    if (heat > 0.05) { ctx.globalAlpha = clamp(0.5 * heat * P.glow, 0, 1); const h2 = hr * 1.3;
      ctx.drawImage(sprite(V.hsl(4, 95, 50, 1)), ox - h2, oy - h2, h2 * 2, h2 * 2); }
    if (vpn > 0.05) { ctx.globalAlpha = 0.12 * vpn * P.glow; ctx.drawImage(sprite(V.hsl(210, 15, 70, 1)), ox - hr, oy - hr, hr * 2, hr * 2); }

    ctx.save(); ctx.translate(ox, oy);
    const strained = heat > 0.05 && sa;
    if (strained) ctx.transform(1, 0, (V.vnoise(s.hue, t * 2.2) - 0.5) * 0.5 * heat * heat, 1, 0, 0);   // the figure shears
    const slip = strained ? E * 0.06 * heat * heat * (1 + 0.25 * (S.m.thermal || 0)) : 0;               // and its loops slip apart
    // 1. the outline: a hairline, ~1/90 of the extent, 1..2 CSS px (Choir's rings are 1-1.4)
    const lw = clamp(E / 90, 1, 2);
    ctx.lineJoin = "round"; ctx.lineCap = "round";
    const flowDim = 1 - 0.25 * clamp(s.pulses.length / 6, 0, 1);
    const cpuOn = clamp(s.cpu / 0.35, 0, 1);
    // the base outline steps down while the CPU sweep runs, so the lit wedge reads as light moving round the figure;
    // strain: the hue gives way to ember
    ctx.globalAlpha = clamp((0.62 + 0.38 * B) * flowDim * (1 - 0.65 * heat) * (1 - 0.4 * cpuOn), 0, 1);
    ctx.strokeStyle = V.hsl(s.hue, sat * 0.9, Math.min(90, light + 18), 1); ctx.lineWidth = lw;
    if (DOTS) dotsBody(ctx, s, E, sat, light, B, flowDim, heat, slip, t);
    else { outlinePath(ctx, lv, R, slip, t, s.hue); ctx.stroke(); }
    // 2. machine strain: the outline runs ember (additive, so the hue stroke above is dimmed rather than overpainted)
    if (heat > 0.05) { ctx.globalAlpha = clamp(0.8 * heat * B + 0.15 * heat, 0, 1); ctx.strokeStyle = V.hsl(6, 95, 56, 1);
      if (DOTS) dotsPass(ctx, s, E, 0, 2, 0, slip, t, 6, 95, 56); else ctx.stroke(); }
    // 3. CPU: the twin wedge lights the outline it passes over; two bands so the light has a bright core
    if (cpuOn > 0.01) {                                  // follows the slipped loops under strain, like the outline
      // a soft wide band round a bright core; below ~40 px the band would fill the gaps between strokes (measured:
      // TARDIS and Fuji smeared at 23 px), so it fades out and the core narrows to the outline's own width
      const big = clamp((E - 30) / 40, 0, 1);
      if (DOTS) { ctx.globalAlpha = clamp(lerp(0.75, 1.0, big) * cpuOn * B, 0, 1);
        dotsPass(ctx, s, E, s.spin, 2, lerp(0.5, 0.35, big), slip, t, s.hue, sat * 0.3, 96); }
      else {
      if (big > 0.02) { ctx.strokeStyle = V.hsl(s.hue, sat * 0.7, 72, 1); ctx.lineWidth = lw * 2.4;
        if (sweepPath(ctx, lv, R, s.spin, 0.08, slip, t, s.hue)) { ctx.globalAlpha = clamp(0.35 * cpuOn * B * P.glow * big, 0, 1); ctx.stroke(); } }
      ctx.strokeStyle = V.hsl(s.hue, sat * 0.3, 96, 1); ctx.lineWidth = lw * lerp(1, 1.25, big);
      if (sweepPath(ctx, lv, R, s.spin, lerp(0.5, 0.35, big), slip, t, s.hue)) { ctx.globalAlpha = clamp(lerp(0.75, 1.0, big) * cpuOn * B, 0, 1); ctx.stroke(); } }
    }
    // 4. network strain: the outermost loop flickers as a jammed band
    if (s.bwS > 0.02) { const fl = V.vnoise(s.hue * 1.3, t * 11) > 0.5 ? 0.75 : 0.15;
      ctx.globalAlpha = clamp(s.bwS * fl * P.glow, 0, 1); ctx.strokeStyle = V.hsl(215, 40, 95, 1); ctx.lineWidth = lw * 1.6;
      ctx.beginPath(); const l = lv.loops[0]; ctx.moveTo(l[0][0] * R, l[0][1] * R); for (let q = 1; q < l.length; q++) ctx.lineTo(l[q][0] * R, l[q][1] * R); ctx.closePath(); ctx.stroke(); }
    // 5. bandwidth beads, inside the glyph: radius = u x the glyph's own rim at that angle
    for (const p of s.pulses) {
      const u = clamp(p.u, 0, 1), rad = u * rimAt(lv, p.a) * R * 0.94, px = Math.cos(p.a) * rad, py = Math.sin(p.a) * rad, rr = Math.max(0.9, E * 0.022);
      const jam = s.bwS > 0.02 && u > 0.62 ? s.bwS * (0.5 + 0.5 * V.vnoise(p.sd, t * 12)) : 0;
      ctx.globalAlpha = clamp((0.85 * p.br * (1 - 0.4 * jam) + 0.2 * jam) * (1 - vpn), 0, 1);
      ctx.fillStyle = p.dir < 0 ? V.hsl(212, 45, 95, 1) : V.hsl(42, 95, 72, 1);
      ctx.beginPath(); ctx.arc(px, py, rr, 0, TAU); ctx.fill();
      ctx.globalAlpha = clamp(0.25 * p.br * P.glow * (1 - vpn), 0, 1);
      ctx.drawImage(sprite(p.dir < 0 ? V.hsl(210, 55, 90, 1) : V.hsl(40, 100, 62, 1)), px - rr * 3, py - rr * 3, rr * 6, rr * 6);
    }
    ctx.restore();

    // 6. satellites = background tasks, one disc each, on an ellipse outside the glyph
    const n = Math.floor(s.procs + 1e-3), fr = s.procs - n, Ro = E * 0.62 + 9 * G.SZ * (1 - 0.2 * (S.m.mempress || 0)), tot = n + (fr > 0.02 ? 1 : 0);
    const dot = Math.max(1.3, 1.7 * Math.sqrt(G.SZ)), ledHalo = sprite(V.hsl(q5(s.hue), q5(sat), q5(light), 1));
    for (let k = 0; k < tot; k++) { const a = s.orb + k / Math.max(1, tot) * TAU;
      const x = ox + Math.cos(a) * Ro, y = oy + Math.sin(a) * Ro * 0.92;
      ctx.globalAlpha = (k < n ? 0.9 : fr) * clamp(B + 0.15, 0, 1);
      ctx.fillStyle = V.hsl(s.hue, sat * 0.85, 78, 1); ctx.beginPath(); ctx.arc(x, y, dot, 0, TAU); ctx.fill();
      ctx.globalAlpha *= 0.45; ctx.drawImage(ledHalo, x - dot * 3, y - dot * 3, dot * 6, dot * 6); }
    // 7. needs you: smooth stroked ripple rings out of the glyph (Choir's idiom), with the knock above
    if (s.needAmt > 0.01) {
      for (let k = 0; k < 3; k++) { const u = ((Math.max(0, s.needT) / 2.4) + k / 3) % 1, rad = E * 0.62 + 10 + u * (0.6 * E + 40 * Math.sqrt(G.SZ));
        const al = Math.sin(Math.PI * u) * 0.7 * s.needAmt;
        ctx.globalAlpha = clamp(al * 0.4 * P.glow, 0, 1); ctx.strokeStyle = V.hsl(s.hue, 85, 68, 1); ctx.lineWidth = 3;
        ctx.beginPath(); ctx.arc(ox, oy, rad, 0, TAU); ctx.stroke();
        ctx.globalAlpha = clamp(al, 0, 1); ctx.strokeStyle = V.hsl(s.hue, 70, 86, 1); ctx.lineWidth = 1.2;
        ctx.beginPath(); ctx.arc(ox, oy, rad, 0, TAU); ctx.stroke(); }
    }
  }
};
})(this);   // `this` at top level = window in a page, the bare global in the native/vm host
