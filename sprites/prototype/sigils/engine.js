/* Living Sigils renderer, shared by every glyph species (the 9x9 LED-bitmap idiom).
 * ONE call per species, from that species' piece file:
 *     SpritesSigilsEngine(V, GLYPHS)      GLYPHS = [[name, [9 rows of "#."]], ... x8]
 * It calls V.piece() itself, so the piece's inline script is one line. Each call closes over its own
 * simulation state (G) and glow-sprite cache, so two species on one stage never share either.
 *
 * The glyph tables live one file per species (prototype/sigils/glyphs_*.js), deliberately: a species whose
 * symbols are other people's trademarks is then one file deletion plus its two registration lines
 * (docs/SYMBOL_SPECIES.md, "Trademark note").
 *
 * Extracted verbatim from prototype/c3_sigils.html (2026-11-06) when the second species was added; the
 * renderer itself is unchanged, and the extraction was checked by rendering all 8 shipped variants to PNG
 * before and after (identical bytes). It force-mirrors every glyph left-to-right and lights the centre
 * pixel ("pilot light"), so a table's rows MUST already be symmetric about the vertical axis.
 * tests/test_sigil_glyphs.py asserts both are no-ops for every table, so a glyph reads as it was typed.
 *
 * `window.VARIANT_NAMES` stays a single global, as every other piece writes it, and two glyph species on
 * ONE stage therefore overwrite each other's. That is safe only because nothing on the stage reads it:
 * the two consumers are a standalone page each (app/settings.js reads it per preview iframe, which holds
 * exactly one piece, and the gallery's own variant labels are drawn only when TL.labels is set, which
 * never happens in live/shared mode). Anything added to the stage that needs variant names must take
 * them from its own GLYPHS table, not this global. */
(function (root) {
"use strict";
root.SpritesSigilsEngine = function (V, GLYPHS) {
  const TAU = Math.PI * 2;
  // ---- arm-B experiment hook (docs/SYMBOL_RESOLUTION.md) ----------------------------------------
  // The SHIPPED look is the four defaults below, so with no global set this renders exactly as before
  // (checked: arm-A stills are byte-identical with and without this block). ONLY the pages under
  // prototype/experiments/resolution/ set root.SPRITES_SIGIL_TUNE; app/stage.html never does, and
  // nothing in app/ or tests/ reads or writes it. Knobs, all optional:
  //   N     force the grid instead of deriving it from V.P.density (5..15; the glyph table must match)
  //   blob  the glow blob's width in cell pitches (3 = shipped, i.e. a cell's light spills over 3 cells)
  //   core  the hard centre square as a fraction of pitch (0.55 = shipped)
  //   floor the core's minimum size in CSS px (2 = shipped; too high a floor re-blurs a fine grid)
  //   halo  multiplier on the body halo's alpha (1 = shipped; 0 = no soft wash behind the symbol)
  //   led   multiplier on each cell's own glow blob alpha (1 = shipped; 0 = hard cores only)
  //   Round 2 (2026-11-07) raised a FORCED N's cap from 15 to 97 for the high-density edge-only grids;
  //   the derived N (no global) keeps its shipped 5..15 clamp.
  const TUNE = (typeof root.SPRITES_SIGIL_TUNE === "object" && root.SPRITES_SIGIL_TUNE) || {};
  const T_N = TUNE.N > 0 ? TUNE.N | 0 : 0, T_BLOB = TUNE.blob > 0 ? TUNE.blob : 3;
  const T_CORE = TUNE.core > 0 ? TUNE.core : 0.55, T_FLOOR = TUNE.floor > 0 ? TUNE.floor : 2;
  const T_HALO = TUNE.halo >= 0 ? TUNE.halo : 1, T_LED = TUNE.led >= 0 ? TUNE.led : 1;
  const clamp = (x, a, b) => x < a ? a : x > b ? b : x;
  const lerp = (a, b, f) => a + (b - a) * f;
  let G = null; // all simulation state (reset in init)
  const VARIANT_NAMES = GLYPHS.map(g => g[0]);
  window.VARIANT_NAMES = VARIANT_NAMES;
  function makeGlyph(iv, N) {
    const rows = GLYPHS[((iv % 8) + 8) % 8][1], M = rows.length, c = (N - 1) >> 1;
    const vsym = rows.every((r, j) => r === rows[M - 1 - j]);   // also mirrored top/bottom -> 4-fold mutation orbits
    const base = new Uint8Array(N * N);
    for (let j = 0; j < N; j++) for (let i = 0; i < N; i++) {
      const si = Math.round(i * (M - 1) / (N - 1)), sj = Math.round(j * (M - 1) / (N - 1));
      if (rows[sj][si] === "#") base[j * N + i] = 1; }
    for (let j = 0; j < N; j++) for (let i = 0; i < N; i++) if (base[j * N + i]) {   // keep exact symmetry after resampling
      base[j * N + (N - 1 - i)] = 1; if (vsym) { base[(N - 1 - j) * N + i] = 1; base[(N - 1 - j) * N + (N - 1 - i)] = 1; } }
    base[c * N + c] = 1;                                                                 // pilot light
    let rmax = 1; for (let m = 0; m < N * N; m++) if (base[m]) rmax = Math.max(rmax, Math.hypot(m % N - c, ((m / N) | 0) - c));
    return { N, c, vsym, base, rmax, on: Uint8Array.from(base), b: Float32Array.from(base, v => v * 0.6) };
  }
  function orbit(g, i, j) { const N = g.N, o = [[i, j], [N - 1 - i, j]];
    if (g.vsym) o.push([i, N - 1 - j], [N - 1 - i, N - 1 - j]); return o.map(([x, y]) => y * N + x); }

  // ---------- glow sprites (cached per colour string, so V.hsl / sat holds) ----------
  const SPR = new Map();
  function sprite(col) {
    let c = SPR.get(col); if (c) return c;
    c = document.createElement("canvas"); c.width = c.height = 64; const x = c.getContext("2d");
    const g = x.createRadialGradient(32, 32, 0, 32, 32, 32);
    g.addColorStop(0, col); g.addColorStop(0.25, col.replace(/,[\d.]+\)$/, ",0.35)")); g.addColorStop(1, col.replace(/,[\d.]+\)$/, ",0)"));
    x.fillStyle = g; x.fillRect(0, 0, 64, 64); SPR.set(col, c); return c;
  }
  const q5 = v => Math.round(v / 5) * 5;

  // ---------- layout: homes in free space, away from focus, menu bar and dock ----------
  function rectDist(x, y, f) { if (!f) return 1e4; const [rx, ry, rw, rh] = f;
    const dx = Math.max(rx - x, 0, x - (rx + rw)), dy = Math.max(ry - y, 0, y - (ry + rh)); return Math.hypot(dx, dy) * ((dx || dy) ? 1 : -1); }
  // live: ghosts take no part in the layout (their position comes from V.steer); they keep their own spot as "home"
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
    if (!f && gal) { // gallery, no window: a centred grid whose shape suits the stage (1 = centre, 8 = 4x2)
      let bc = 1, bs = -1;
      for (let c = 1; c <= n; c++) { const r = Math.ceil(n / c), sc = Math.min(V.W / c, (V.H - V.TOP - V.BOT) / r); if (sc > bs + 0.5) { bs = sc; bc = c; } }
      const cols = bc, rows = Math.ceil(n / cols), cw = V.W / cols, ch = (V.H - V.TOP - V.BOT) / rows, out = [];
      for (let k = 0; k < n; k++) { const r = Math.floor(k / cols), inRow = Math.min(cols, n - r * cols), c = k % cols;
        out.push([V.W / 2 + (c - (inRow - 1) / 2) * cw, V.TOP + (r + 0.5) * ch]); }
      return out; }
    const R = (gal ? 50 : 80) * G.SZ, mx = gal ? R : 70, slots = [];
    const edge = (x, y) => Math.min(x, V.W - x, y - V.TOP, V.H - V.BOT - y);
    for (let y = V.TOP + R + 6; y <= V.H - V.BOT - R; y += 12) for (let x = mx; x <= V.W - mx; x += 12) {
      const d = rectDist(x, y, f); if (d > R) slots.push([x, y, gal ? Math.min(d, 2 * edge(x, y)) : d]); }
    if (!slots.length) for (let x = mx; x <= V.W - mx; x += 60) slots.push([x, V.H - V.BOT - R, 0]);
    const chosen = [];
    // farthest-point sampling, first = farthest from the window
    let best = slots[0]; for (const s of slots) if (s[2] > best[2]) best = s; chosen.push(best);
    while (chosen.length < sigs.length) {
      let bs = null, bd = -1;
      for (const s of slots) { let m = 1e9; for (const c of chosen) m = Math.min(m, Math.hypot(s[0] - c[0], s[1] - c[1]));
        m = Math.min(m, s[2] * 1.4 + 40 * G.SZ); if (m > bd) { bd = m; bs = s; } }
      chosen.push(bs);
    }
    // assign greedily to the nearest current position (least travel)
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

  V.piece({
    init(V, S) {
      const N = T_N ? clamp(T_N, 5, 97) : clamp(2 * Math.round((9 * Math.sqrt(V.P.density) - 1) / 2) + 1, 5, 15);
      // stage scale: the 1280x800 trials keep scale 1; a gallery cell (e.g. 640x400) gets bigger sigils, shrunk to fit a crowd
      const n = V.sessions.length, gal = !V.LIVE && (V.H < 700 || V.W < 1000);
      const old = G, oldSigs = new Map(old ? old.sigs.map(o => [o.id, o]) : []);   // live: survivors keep their whole state by id
      const crowd = gal ? (n <= 2 ? 1 : n <= 3 ? 0.9 : clamp(Math.sqrt(3 / n) * 1.3, 0.78, 0.9)) : 1;
      G = { gal, crowd, SZ: szOf(V, gal, crowd) };
      // identity: s.iv picks the sigil. Old trial timelines carry no iv (runtime sets 0 for all): fall back to order.
      const allZero = !V.LIVE && !new URLSearchParams(location.search).get("iv") && n > 1 && V.sessions.every(z => !z.iv);
      const sigs = V.sessions.map((ss, i) => {
        const a = (i + 0.5) / V.sessions.length;
        const o = V.LIVE ? oldSigs.get(ss.id) : null;
        if (o && o.iv === ss.iv && o.g.N === N) { o.hue = ss.hue; o.ghost = !!ss.ghost; o.kept = true; return o; }
        return { id: ss.id, ghost: !!ss.ghost, hue: ss.hue, iv: allZero ? i : ss.iv, g: makeGlyph(allZero ? i : ss.iv, N), x: 760 + 420 * Math.cos(a * TAU) * 0.5, y: 400 + 260 * Math.sin(a * TAU) * 0.6,
          vx: 0, vy: 0, wx: 0, wy: 0, hx: 0, hy: 0, E: 54, spin: 0, tickAcc: 0, orb: V.rand() * TAU,
          bright: 0.5, needT: -1, needAmt: 0, flare: 0, heatSm: 0, playAmt: 0, state: "idle", mem: 0.5, procs: 2, cpu: 0,
          pulses: [], inAcc: 0, outAcc: 0, bwS: 0, rx: 0, tx: 0 };
      });
      Object.assign(G, { sigs, N, embers: [], sparks: [], focusKey: "", homes: [], vpnAmt: S.net.vpn === "down" ? 1 : 0,
            prevVpn: S.net.vpn, playPhase: 0, beat: 0, beam: 0 });
      if (V.LIVE && old) for (const k of ["embers", "sparks", "vpnAmt", "prevVpn", "playPhase", "beat", "beam", "playT"]) if (old[k] !== undefined) G[k] = old[k];
      for (const s of sigs) if (!s.kept) { s.mem = S.s[s.id].mem; s.E = 9 * 6 * Math.sqrt(clamp(s.mem, 0.2, 2.6) / 0.8) * G.SZ; }
      G.homes = computeHomes(V, S.focus, sigs);
      sigs.forEach((s, i) => { if (!s.kept) { s.x = G.homes[i][0]; s.y = G.homes[i][1]; s.hx = s.x; s.hy = s.y; } delete s.kept; V.report(s.id, s.x, s.y, sigRadius(V, s)); });
      G.focusKey = (S.focus || []).map(Math.round).join();
    },

    // live: survivors continue from their last reported spot (velocity kept); new ids start at their home
    carry(V, S, prev) {
      for (const s of G.sigs) { const p = prev[s.id]; if (!p) continue; s.x = p.x; s.y = p.y; V.report(s.id, s.x, s.y, sigRadius(V, s)); }
    },
    // live: the Size slider eases V.P.size; scale and re-lay the homes
    resize(V, S) {
      if (!G) return;
      G.SZ = szOf(V, G.gal, G.crowd);
      G.homes = computeHomes(V, S.focus, G.sigs);
    },
    // running lights: a row under the glyph's bottom row
    place(V, id, x, y) { const s = G && G.sigs.find(z => z.id === id); if (s) { s.x = x; s.y = y; s.vx = s.vy = 0; } },
    lightSpots(V, id, n) {
      const s = G && G.sigs.find(z => z.id === id); if (!s) return null;
      const pitch = s.E / s.g.N, gap = Math.max(5, Math.min(pitch * 0.9, 8)) * Math.sqrt(V.P.size), w = (n - 1) * gap, y = s.y + (s.g.N - 1) / 2 * pitch + pitch * 1.5 + 4;
      const out = []; for (let i = 0; i < n; i++) out.push([s.x - w / 2 + i * gap, y]); return out;
    },

    step(V, S, dt) {
      const t = V.t, sigs = G.sigs, f = S.focus;
      const fk = (f || []).map(Math.round).join();
      if (fk !== G.focusKey) { G.focusKey = fk; G.homes = computeHomes(V, f, sigs); }
      // VPN
      const down = S.net.vpn === "down";
      if (G.prevVpn === "down" && !down && V.reconnected(S.net)) { // reconnect: one joyful bloom
        for (const s of sigs) { if (s.ghost) continue; s.flare = 1; const n = Math.round(30 * V.P.density);
          for (let k = 0; k < n; k++) { const a = k / n * TAU + V.rand() * 0.2, sp = 120 + 120 * V.rand();
            G.sparks.push({ x: s.x, y: s.y, vx: Math.cos(a) * sp, vy: Math.sin(a) * sp, life: 1.4, max: 1.4, hue: s.hue, kind: 0 }); } } }
      G.prevVpn = S.net.vpn;
      G.vpnAmt = clamp(G.vpnAmt + (down ? dt / 0.8 : -dt / 0.5), 0, 1);
      if (down) { G.beat += dt; G.beam += dt * 0.55; }
      const heat = clamp(S.m.level / 3, 0, 1), thermal = S.m.thermal || 0, mp = S.m.mempress || 0;
      // play
      const pair = (S.play && S.play.pair) || [], pamt = V.on("play") ? (S.play && S.play.amt) || 0 : 0;
      const onNeeds = V.on("needsApproach"), onHuddle = V.on("vpnHuddle"), onStrain = V.on("strainAgitation");
      // play: one brief twirl (half a turn, eased) once they have drifted together; then hold and part
      G.playT = pamt > 0.6 ? (G.playT || 0) + dt : 0;
      { const u = clamp((G.playT - 1.2) / 2.6, 0, 1); G.playPhase = Math.PI * u * u * (3 - 2 * u) - Math.PI / 2; }
      const pi = pair.map(id => sigs.findIndex(s => s.id === id && !s.ghost));
      // huddle centre for VPN loss = mean of homes
      let cx = 0, cy = 0, nh = 0; G.homes.forEach((h, k) => { if (sigs[k].ghost) return; cx += h[0]; cy += h[1]; nh++; }); nh = Math.max(1, nh); cx /= nh; cy /= nh;
      if (V.LIVE && V.huddlePt) { cx = V.huddlePt[0]; cy = V.huddlePt[1]; }   // live: the ONE shared point chosen by the stage
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
        // memory -> glyph extent (area proportional to footprint)
        const tE = 9 * 6 * Math.sqrt(clamp(s.mem, 0.2, 2.6) / 0.8) * G.SZ;
        s.E += (tE - s.E) * Math.min(1, dt * 2.5);
        // CPU -> spin speed of the inner light, and glyph evolution (mutation ticks)
        s.spin += dt * TAU * 0.85 * s.cpu;
        s.tickAcc += dt * 2.2 * s.cpu * (G.vpnAmt > 0.5 ? 0.3 : 1) * (s.state === "idle" ? 0.25 : 1);
        const g = s.g, N = g.N, hc = g.c;
        while (s.tickAcc >= 1) { s.tickAcc -= 1;
          for (let r = 0; r < 2; r++) {   // toggle one symmetry orbit (mirror pair, or 4 cells for 4-fold sigils)
            const qx = Math.floor(V.rand() * (hc + 1)), qy = Math.floor(V.rand() * (g.vsym ? hc + 1 : N));
            if (qx === hc && qy === hc) continue;
            const orb = orbit(g, qx, qy), j = orb[0];
            let div = 0; for (let m = 0; m < g.on.length; m++) div += g.on[m] !== g.base[m];
            if (g.on[j] !== g.base[j]) { for (const o of orb) g.on[o] = g.base[o]; continue; }
            if (div > (g.vsym ? 4 : 2) * (N > 9 ? 2 : 1)) {   // at most one or two orbits off: identity holds
              // pull back toward identity
              for (let m = 0; m < g.on.length; m++) if (g.on[m] !== g.base[m]) { for (const o of orbit(g, m % N, (m / N) | 0)) g.on[o] = g.base[o]; break; } continue; }
            let nb = 0; for (const [dx, dy] of [[1,0],[-1,0],[0,1],[0,-1]]) { const X = qx + dx, Y = qy + dy;
              if (X >= 0 && Y >= 0 && X < N && Y < N && g.on[Y * N + X]) nb++; }
            if (nb > 0) { const v = g.on[j] ^ 1; for (const o of orb) g.on[o] = v; }
          } }
        for (let m = 0; m < g.on.length; m++) g.b[m] += ((g.on[m] ? 1 : 0) - g.b[m]) * Math.min(1, dt * 10);
        // ---- bandwidth: runs of light along the glyph's own pixels. rx = rim -> core (cool), tx = core -> rim (gold) ----
        s.rx = d.rx || 0; s.tx = d.tx || 0;
        const moving = clamp(Math.log10(1 + s.rx + s.tx) / 0.8, 0, 1), bwT = (S.net.strain || 0) * moving * (1 - G.vpnAmt);
        s.bwS += (bwT - s.bwS) * Math.min(1, dt * 3);
        const thr = 1 - 0.5 * s.bwS, live = 1 - G.vpnAmt;
        s.inAcc += dt * 5.5 * Math.log10(1 + s.rx) * thr * live; s.outAcc += dt * 5.5 * Math.log10(1 + s.tx) * thr * live;
        const brIn = 0.55 + 0.45 * clamp(Math.log10(1 + s.rx) / 1.4, 0, 1), brOut = 0.55 + 0.45 * clamp(Math.log10(1 + s.tx) / 1.4, 0, 1);
        while (s.inAcc >= 1) { s.inAcc -= 1; s.pulses.push({ dir: -1, a: V.rand() * TAU, u: 1.15, br: brIn, sd: V.rand() * 50, age: 0 }); }
        while (s.outAcc >= 1) { s.outAcc -= 1; s.pulses.push({ dir: 1, a: V.rand() * TAU, u: -0.1, br: brOut, sd: V.rand() * 50, age: 0 }); }
        for (const p of s.pulses) { p.age += dt; let sp = 1.15;
          if (s.bwS > 0.02) { // jam: stall and bunch at the rim, stutter, a trickle gets through
            const go = V.vnoise(p.sd, t * 4) > 0.55 ? 1 : 0.08, rim = p.u > 0.66;
            sp *= lerp(1, (rim ? 0.10 : 0.55) * go, s.bwS); }
          p.u += p.dir * sp * dt; }
        s.pulses = s.pulses.filter(p => p.dir < 0 ? p.u > -0.15 : p.u < 1.2);
        if (s.pulses.length > 36) s.pulses.splice(0, s.pulses.length - 36);
        if (G.vpnAmt > 0.5) s.pulses.length = 0;
        // satellites orbit only while the session works (state-bound)
        s.orb += dt * (s.state === "working" ? 0.6 : 0) * (1 + mp * 0.5);
        // ---- home for this frame ----
        let hx = G.homes[i][0], hy = G.homes[i][1];
        const k = pi.indexOf(i);
        if (k >= 0 && pi[1 - k] >= 0 && pamt > 0) { // play: orbit a shared midpoint
          const o = G.homes[pi[1 - k]], mx = (hx + o[0]) / 2, my = (hy + o[1]) / 2;
          const sep = (sigRadius(V, s) + sigRadius(V, sigs[pi[1 - k]])) * (G.gal ? 0.5 : 0.75) + 18, a = G.playPhase + (k ? Math.PI : 0);
          hx = lerp(hx, mx + Math.cos(a) * sep, pamt); hy = lerp(hy, my + Math.sin(a) * sep * 0.8, pamt);
          // clamp the dance out of the window
          if (rectDist(hx, hy, f) < sigRadius(V, s) + 20) { hx = G.homes[i][0]; hy = G.homes[i][1]; }
        }
        s.playAmt = k >= 0 ? pamt : 0;
        if (s.needAmt > 0 && f && onNeeds) { // needs you: come to the window's edge and knock
          const [rx, ry, rw, rh] = f, r = sigRadius(V, s) + 30;
          let nx, ny = clamp(G.homes[i][1], Math.max(ry + 50, V.TOP + r), Math.min(ry + rh - 50, V.H - V.BOT - r)), dir;
          if (G.homes[i][0] > rx + rw / 2 && rx + rw + r < V.W - 20) { nx = rx + rw + r; dir = -1; }
          else if (rx - r > 20) { nx = rx - r; dir = 1; }
          else { nx = rx + rw + r; dir = -1; }
          s.knockDir = dir;
          const e = s.needAmt; hx = lerp(hx, nx, e); hy = lerp(hy, ny, e);
        }
        if (G.vpnAmt > 0 && onHuddle && !s.ghost) { // huddle
          const a = hudIdx.indexOf(s) / hudIdx.length * TAU + 0.6, rr = (G.gal ? 0.85 : 1) * (34 + 14 * hudIdx.length) * G.SZ;
          hx = lerp(hx, cx + Math.cos(a) * rr, G.vpnAmt * (1 - s.needAmt)); hy = lerp(hy, cy + Math.sin(a) * rr * 0.8, G.vpnAmt * (1 - s.needAmt));
        }
        s.hx = hx; s.hy = hy;
        // route round the focused window, never through it: detour via its nearer horizontal edge
        if (f && !V.LIVE) { const [rx, ry, rw, rh] = f, m = sigRadius(V, s) + 16;   // live: V.nav routes round the focus
          const crosses = segHitsRect(s.x, s.y, hx, hy, rx - m, ry - m, rw + 2 * m, rh + 2 * m);
          if (crosses) {
            if (s.y > ry - m && s.y < ry + rh + m) {   // beside it: climb or drop to the clear edge first
              const up = ry - m, dn = ry + rh + m, okU = up > V.TOP + m * 0.6, okD = dn < V.H - V.BOT - m * 0.6;
              hy = (okU && (!okD || Math.abs(s.y - up) < Math.abs(s.y - dn))) ? up : dn; hx = s.x + Math.sign(hx - s.x) * 30;
            } else { hy = s.y; } } }   // above/below it: travel along, then descend
        // ---- idle wander: curl-noise, the only data-free motion; restless under strain ----
        const agit = onStrain ? 1 + 2.2 * s.heatSm * s.heatSm : 1, still = 1 - 0.8 * G.vpnAmt;
        const [ux, uy] = V.curl(s.x + i * 300, s.y, t * (0.4 + (onStrain ? 1.2 : 0) * s.heatSm));
        s.wx += (ux * 7 * V.P.drift * agit * still - s.wx * 0.08) * dt;
        s.wy += (uy * 7 * V.P.drift * agit * still - s.wy * 0.08) * dt;
        const wr = Math.hypot(s.wx, s.wy), wmax = 45 * V.P.drift * (1 - s.needAmt) * still * (s.state === "idle" && (!onStrain || s.heatSm < 0.2) ? 0.55 : 1) + 2;
        if (wr > wmax) { s.wx *= wmax / wr; s.wy *= wmax / wr; }
        // spring to home + wander, avoidance, separation
        const rr0 = sigRadius(V, s);
        let tx = clamp(hx + s.wx, 6 + rr0, V.W - 6 - rr0), ty = clamp(hy + s.wy, V.TOP + 4 + rr0, V.H - V.BOT - 4 - rr0);
        if (V.LIVE && (s.ghost || (s.needAmt < 0.01 && !(G.vpnAmt > 0.01 && onHuddle) && s.playAmt < 0.01))) [tx, ty] = V.steer(s.id, tx, ty, rr0);
        if (V.LIVE) [tx, ty] = (s.needAmt < 0.5 ? V.nav : V.navNeed)(s.id, s.x, s.y, tx, ty, rr0);   // fit + reachable + around the focus (needs-you: round it to the knock spot)
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
        // thermal -> embers rising
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
      const t = V.t, sigs = G.sigs, P = V.P, vpn = G.vpnAmt;
      ctx.save(); ctx.globalCompositeOperation = "lighter";
      // VPN lost: slow searching beam + red heartbeat at the huddle
      if (vpn > 0.01 && V.on("vpnHuddle") && !V.LIVE) {   // live: the runtime draws the one searchlight + beacon
        const [cx, cy] = G.hud, a = G.beam, L = 0.4 * Math.hypot(V.W, V.H);
        ctx.globalAlpha = 0.10 * vpn * P.glow;
        const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, L);
        g.addColorStop(0, V.hsl(205, 25, 75, 0.9)); g.addColorStop(1, V.hsl(205, 25, 60, 0));
        ctx.fillStyle = g; ctx.beginPath(); ctx.moveTo(cx, cy); ctx.arc(cx, cy, L, a - 0.12, a + 0.12); ctx.closePath(); ctx.fill();
        const ph = G.beat % 1.5, on = ph < 0.22 ? 1 : 0;   // small red beacon: a plain blink, not a heartbeat
        const rs = sprite(V.hsl(0, 95, 55, 1)), rr = 13 * Math.sqrt(P.glow * G.SZ);
        ctx.globalAlpha = vpn * (0.12 + 0.75 * on); ctx.drawImage(rs, cx - rr, cy - rr, rr * 2, rr * 2);
        ctx.globalAlpha = vpn * (0.3 + 0.7 * on); ctx.fillStyle = V.hsl(0, 95, 62, 1); ctx.fillRect(cx - 2, cy - 2, 4, 4);
      }
      for (const s of sigs) V.creature(s.id, () => drawSigil(V, S, ctx, s, sigs));
      // embers
      for (const e of G.embers) { const u = e.life / e.max; ctx.globalAlpha = 0.7 * u; ctx.fillStyle = V.hsl(8 + 18 * (1 - u), 95, 60, 1);
        ctx.fillRect(e.x - 1.2, e.y - 1.2, 2.4, 2.4); }
      // reconnect bloom sparks
      for (const p of G.sparks) { const u = p.life / p.max; ctx.globalAlpha = u * 0.9; ctx.fillStyle = V.hsl(p.hue, 90, 70, 1);
        ctx.fillRect(p.x - 1.6, p.y - 1.6, 3.2, 3.2); }
      ctx.restore();
    },
  });

  function drawSigil(V, S, ctx, s, sigs) {
    const P = V.P, t = V.t, g = s.g, N = g.N, vpn = G.vpnAmt;
    const E = s.E, pitch = E / N, heat = s.heatSm * (1 - vpn), sa = V.on("strainAgitation");
    const kn = s.needAmt > 0.5 && V.on("needsApproach") ? knock(s.needT) * 7 * (s.knockDir || 0) : 0;
    const ox = s.x + kn, oy = s.y;
    const sat = lerp(lerp(92, 80, heat), 40, vpn);                 // VPN: drain colour (hue kept)
    const light = lerp(lerp(60, 70, heat), 62, vpn);
    const breathe = s.state === "idle" ? 0.88 + 0.12 * Math.sin(t * TAU / 7 + s.hue) : 1;
    const B = clamp(s.bright + s.flare * 0.6, 0, 1.4) * (1 - 0.25 * vpn) * breathe;
    // body halo (declared decoration scaled by glow; heat adds a warm rim)
    const hr = E * 0.95 * Math.sqrt(P.glow);
    ctx.globalAlpha = clamp((0.30 * B * P.glow * (0.6 + 0.4 * s.needAmt) + s.flare * 0.3) * T_HALO, 0, 1);
    ctx.drawImage(sprite(V.hsl(q5(s.hue), q5(sat), 50, 1)), ox - hr, oy - hr, hr * 2, hr * 2);
    if (heat > 0.05) { ctx.globalAlpha = clamp(0.5 * heat * P.glow, 0, 1); const h2 = hr * 1.3;   // ember glow behind the glyph
      ctx.drawImage(sprite(V.hsl(4, 95, 50, 1)), ox - h2, oy - h2, h2 * 2, h2 * 2); }
    const emb = sprite(V.hsl(6, 95, 52, 1)), cool = sprite(V.hsl(210, 55, 90, 1)), gold = sprite(V.hsl(40, 100, 62, 1));
    if (vpn > 0.05) { ctx.globalAlpha = 0.12 * vpn * P.glow; ctx.drawImage(sprite(V.hsl(210, 15, 70, 1)), ox - hr, oy - hr, hr * 2, hr * 2); }
    const cpuOn = clamp(s.cpu / 0.35, 0, 1), jit = pitch * 0.22 * heat * heat * (1 + 0.25 * (S.m.thermal || 0));
    const ledHalo = sprite(V.hsl(q5(s.hue), q5(sat), q5(light), 1)), hotHalo = sprite(V.hsl(q5(s.hue), q5(sat * 0.6), 85, 1));
    const ls = pitch * T_BLOB * Math.sqrt(P.glow), core = Math.max(T_FLOOR, pitch * T_CORE);
    const c0 = (N - 1) / 2, ps = s.pulses, np = ps.length, bwS = s.bwS, flowDim = 1 - 0.35 * clamp(np / 6, 0, 1);
    for (let j = 0; j < N; j++) for (let i = 0; i < N; i++) {
      const b = g.b[j * N + i]; if (b < 0.03) continue;
      const dx = i - c0, dy = j - c0, cell = j * N + i;
      // CPU: a twin light sweeping round the glyph, speed = cores
      const ang = Math.atan2(dy, dx), dd = Math.cos(2 * (ang - s.spin)), rr = Math.hypot(dx, dy) / g.rmax;
      const boost = cpuOn * Math.pow(Math.max(0, dd), 6) * (Math.hypot(dx, dy) > 0.5 ? 1 : 0.3);
      // strain: desynchronised twinkle + jitter
      const tw = heat > 0.05 && sa ? 1 - 0.4 * heat * V.vnoise(cell * 1.7, t * 7 + s.hue) : 1;
      const shear = heat > 0.05 && sa ? (V.vnoise(j * 1.7 + s.hue, t * 2.2) - 0.5) * 2 * pitch * 0.55 * heat * heat : 0;   // rows slip out of line
      const x = ox + dx * pitch + shear + (heat > 0.05 && sa ? (V.vnoise(cell * 2.3, t * 9) - 0.5) * 2 * jit : 0);
      const y = oy + dy * pitch + (heat > 0.05 && sa ? (V.vnoise(cell * 3.1 + 50, t * 9) - 0.5) * 2 * jit : 0);
      const a = clamp(b * B * tw * (0.75 + 0.6 * boost) * flowDim, 0, 1);
      // bandwidth runs passing this pixel
      let pin = 0, pout = 0;
      for (let q = 0; q < np; q++) { const p = ps[q], wr = 1 - Math.abs(rr - p.u) / 0.2; if (wr <= 0) continue;
        let da = Math.abs(ang - p.a) % TAU; if (da > Math.PI) da = TAU - da;
        const wa = rr < 0.15 ? 1 : 1 - da / 1.25; if (wa <= 0) continue;
        const w = wr * wa * p.br; if (p.dir < 0) pin += w; else pout += w; }
      pin = Math.min(1.2, pin) * (1 - 0.4 * bwS); pout = Math.min(1.2, pout) * (1 - 0.4 * bwS);
      let clog = 0; if (bwS > 0.02 && rr > 0.62) clog = bwS * (V.vnoise(cell * 1.3, t * 11) > 0.5 ? 0.75 : 0.12);   // the jammed band at the rim
      if (heat > 0.05) { ctx.globalAlpha = clamp(0.32 * heat * P.glow, 0, 1); const le = ls * 1.6; ctx.drawImage(emb, x - le / 2, y - le / 2, le, le); }
      if (pin > 0.02 || clog > 0.02) { ctx.globalAlpha = clamp((pin + clog * 0.6) * 0.9 * P.glow, 0, 1); const lp = ls * 1.35; ctx.drawImage(cool, x - lp / 2, y - lp / 2, lp, lp); }
      if (pout > 0.02 || clog > 0.02) { ctx.globalAlpha = clamp((pout + clog * 0.6) * 0.9 * P.glow, 0, 1); const lp = ls * 1.35; ctx.drawImage(gold, x - lp / 2, y - lp / 2, lp, lp); }
      ctx.globalAlpha = clamp(a * 0.8 * P.glow * T_LED, 0, 1);
      if (T_LED > 0) ctx.drawImage(boost > 0.3 ? hotHalo : ledHalo, x - ls / 2, y - ls / 2, ls, ls);
      let col;
      if (dx === 0 && dy === 0) col = V.hsl(s.hue, 95, 66, 1);       // pilot light keeps full hue, always
      else if (pin + clog > 0.25 && pin + clog >= pout) col = V.hsl(215, 40, lerp(92, 99, Math.min(1, pin)), 1);
      else if (pout + clog > 0.25) col = V.hsl(42, 95, lerp(66, 82, Math.min(1, pout)), 1);
      else col = V.hsl(s.hue, sat, lerp(light + 6, 88, boost * 0.8), 1);
      ctx.globalAlpha = clamp(a + 0.8 * Math.max(pin, pout, clog), 0, 1); ctx.fillStyle = col; ctx.fillRect(x - core / 2, y - core / 2, core, core);
    }
    // each bandwidth run carries a soft light along its ray, never beyond the glyph's own rim
    for (const p of ps) { const u = clamp(p.u, 0, 1); if (p.u < -0.05 || p.u > 1.05) continue;
      const rad = u * g.rmax * pitch, px = ox + Math.cos(p.a) * rad, py = oy + Math.sin(p.a) * rad;
      const jam = bwS > 0.02 && u > 0.62 ? bwS * (0.5 + 0.5 * V.vnoise(p.sd, t * 12)) : 0;
      ctx.globalAlpha = clamp((0.42 * p.br * (1 - 0.5 * jam) + 0.12 * jam) * P.glow * (1 - vpn), 0, 1); const L = pitch * 2.6;
      ctx.drawImage(p.dir < 0 ? cool : gold, px - L / 2, py - L / 2, L, L); }
    // satellites = background tasks (one pixel per process; fractional count fades in)
    const n = Math.floor(s.procs + 1e-3), fr = s.procs - n, R = E * 0.62 + 9 * G.SZ * (1 - 0.2 * (S.m.mempress || 0)), tot = n + (fr > 0.02 ? 1 : 0);
    const sz = Math.max(2.5, 3.4 * Math.sqrt(G.SZ));
    for (let k = 0; k < tot; k++) { const a = s.orb + k / Math.max(1, tot) * TAU;
      const x = ox + Math.cos(a) * R, y = oy + Math.sin(a) * R * 0.92;
      ctx.globalAlpha = (k < n ? 0.9 : fr) * clamp(B + 0.15, 0, 1);
      ctx.fillStyle = V.hsl(s.hue, sat * 0.85, 76, 1); ctx.fillRect(x - sz / 2, y - sz / 2, sz, sz);
      ctx.globalAlpha *= 0.6; ctx.drawImage(ledHalo, x - sz * 2.5, y - sz * 2.5, sz * 5, sz * 5); }
    // needs you: dotted ripples outward + soft reticle corners
    if (s.needAmt > 0.01) {
      const per = 1.5;
      for (let k = 0; k < 3; k++) { const age = s.needT - k * per - Math.floor(Math.max(0, s.needT - k * per) / (per * 3)) * per * 3;
        if (age < 0 || age > 2.4) continue;
        const rr = E * 0.65 + 14 + age * 55 * Math.sqrt(G.SZ), al = s.needAmt * 0.85 * (1 - age / 2.4);
        const m = 28; ctx.fillStyle = V.hsl(s.hue, 90, 72, 1);
        for (let q = 0; q < m; q++) { const a = q / m * TAU; ctx.globalAlpha = al; ctx.fillRect(ox + Math.cos(a) * rr - 1.5, oy + Math.sin(a) * rr - 1.5, 3, 3); } }
      const rb = E * 0.6 + 6, L = E * 0.22, pul = 0.55 + 0.35 * Math.sin(s.needT * TAU * 0.7);
      ctx.globalAlpha = s.needAmt * pul; ctx.fillStyle = V.hsl(s.hue, 90, 78, 1);
      for (const [sx, sy] of [[-1,-1],[1,-1],[-1,1],[1,1]]) { const cx = ox + sx * rb, cy = oy + sy * rb, w = 2.2;
        ctx.fillRect(sx < 0 ? cx : cx - L, cy - w / 2, L, w); ctx.fillRect(cx - w / 2, sy < 0 ? cy : cy - L, w, L); }
    }
  }
  function knock(tn) { const p = tn % 2.6; const bump = (c) => Math.max(0, 1 - Math.abs(p - c) / 0.09); return bump(1.0) + bump(1.3); }
};
})(this);   // `this` at top level = window in a page, the bare global in the native/vm host (as labels.js does)
