/* ARM C EXPERIMENT ONLY -- a resolution comparison arm, not a shipped species, not registered in
 * app/stage.html. See docs/SYMBOL_RESOLUTION.md.
 *
 * What this arm IS: the same three Night Signals drawn as TRUE GEOMETRY -- arc, lineTo,
 * bezierCurveTo, stroke and fill -- in the idiom prototype/c4_kaleido.html and prototype/c1_choir.html
 * already use, so every edge resolves at device resolution instead of at a 9x9 or 15x15 cell grid.
 * It deliberately keeps the SAME data mapping as c6_night (colour+glyph = identity, area = memory,
 * inner sweep + spin = CPU, orbiting dots = background tasks, cool beads inward = download, gold beads
 * outward = upload, red ember wash = strain, grey drain = VPN lost) so the only thing a viewer is
 * comparing is how the symbol is drawn.
 *
 * What this arm IS NOT: the LED panel. There are no cells here, so the "lit bitmap" character --
 * mutation ticks toggling symmetry orbits as CPU rises, the pixel-by-pixel bandwidth runs, the rows
 * slipping out of alignment under thermal strain -- has no literal equivalent. The vector stand-ins
 * below (a rotating sweep, beads on a path, a shear transform) carry the same READING but they are a
 * different look, and that is the honest cost of the arm, not an oversight.
 *
 * Layout and physics are deliberately minimal (spring to a home + curl-noise wander): this arm exists
 * to be photographed beside arms A and B, and the stills are static, so reproducing the shipped
 * engine's full navigation, huddle, knock and play behaviour would add no information to the
 * comparison. If arm C were ever adopted that work is part of its cost, and the doc says so.
 *
 * All three glyphs are drawn in a UNIT BOX: x and y run -1..1, +y down, with the drawing centred on
 * the origin and left/right mirror symmetry built into each path (so the species' symmetry rule still
 * holds, by construction rather than by a table check). The caller scales by the glyph's extent, so
 * one path serves every size.
 */
(function (root) {
"use strict";
const TAU = Math.PI * 2;

// ---------------------------------------------------------------------------------------------
// The three symbols as paths in the unit box. Each takes (ctx) and leaves a path ready to fill or
// stroke; `half` paths are drawn once and then mirrored by the caller, so symmetry is structural.
// ---------------------------------------------------------------------------------------------

// Batman: the chest emblem. One closed path -- head bump, shoulder, the long swept wing out to the
// tip, then back along the scalloped lower edge to the tail point. Drawn as the right half and
// mirrored, so the two wings cannot drift apart.
function batHalf(ctx) {
  // Tuned by rendering candidates and looking at them, not by arithmetic: a deeper head dome or a
  // second scallop both turn the wings into spindly claws at sprite size, which is exactly the
  // "collapses into one shape" failure the 9x9 bat already had. One shallow scallop per wing survives.
  ctx.moveTo(0, -0.44);                                       // crown of the head, deliberately low
  ctx.bezierCurveTo(0.11, -0.44, 0.19, -0.38, 0.22, -0.29);   // head down to the shoulder
  ctx.bezierCurveTo(0.44, -0.42, 0.74, -0.50, 0.94, -0.46);   // shoulder out along the wing's top edge
  ctx.bezierCurveTo(0.99, -0.45, 1.00, -0.40, 1.00, -0.33);   // to the wing tip, swept up
  ctx.bezierCurveTo(0.99, -0.17, 0.94, -0.04, 0.86, 0.06);    // tip's trailing edge, swept back
  ctx.bezierCurveTo(0.86, -0.05, 0.82, -0.13, 0.73, -0.16);   // the one scallop: up into the notch
  ctx.bezierCurveTo(0.60, -0.04, 0.45, 0.10, 0.32, 0.25);     // inner wing, into the body's flank
  ctx.bezierCurveTo(0.28, 0.41, 0.16, 0.53, 0, 0.60);         // body's side, to the tail point
}
// TARDIS: the police box. Rectilinear by nature, so this is the glyph where vector buys least in
// outline and most in STROKE WEIGHT -- the panel lines are hairlines at any size.
function tardisPath(ctx, lw) {
  const x = 0.60, top = -0.52, bot = 0.86;
  ctx.moveTo(-x, bot); ctx.lineTo(-x, top); ctx.lineTo(x, top); ctx.lineTo(x, bot); ctx.closePath();
}
function tardisRoof(ctx) {
  ctx.moveTo(-0.60, -0.52); ctx.lineTo(-0.46, -0.68); ctx.lineTo(0.46, -0.68); ctx.lineTo(0.60, -0.52); ctx.closePath();
}
// Cog: toothed ring. The teeth are trapezoids on a circle, so the whole glyph is one analytic form:
// 8 teeth at exact TAU/8 spacing keeps the 4-fold symmetry the 9x9 Cog has (and so the same mutation
// orbits, if this arm ever needed them).
function cogTeeth(ctx, n, rIn, rOut, halfA) {
  for (let k = 0; k < n; k++) {
    const a = k * TAU / n;
    const a0 = a - halfA, a1 = a + halfA, a0o = a - halfA * 0.62, a1o = a + halfA * 0.62;
    ctx.moveTo(Math.cos(a0) * rIn, Math.sin(a0) * rIn);
    ctx.lineTo(Math.cos(a0o) * rOut, Math.sin(a0o) * rOut);
    ctx.lineTo(Math.cos(a1o) * rOut, Math.sin(a1o) * rOut);
    ctx.lineTo(Math.cos(a1) * rIn, Math.sin(a1) * rIn);
    ctx.closePath();
  }
}

// ---------------------------------------------------------------------------------------------
// drawGlyph(ctx, which, R, opt) -- the symbol, filled and rimmed, scaled to radius R (CSS px).
// opt.fill / opt.rim are colour strings; opt.lw is the rim width in CSS px.
// Everything is in path space, so it is resolution-independent: at dpr 2 the edges land on device
// pixels, which is the entire point of this arm.
// ---------------------------------------------------------------------------------------------
// ROUND 2 (owner, 2026-11-07: "make them just the edges similar to how you made the circles in the
// 'choir' species"). When armC_edge.html sets window.SPRITES_ARMC_EDGE, every symbol is drawn as its
// OUTLINE ONLY: the polylines in symbols_edge.js (Batman traced from the owner's reference image by
// tools/trace_symbols.py), stroked as crisp hairlines the way Choir strokes its rings, no fill.
const EDGE = () => root.SPRITES_ARMC_EDGE && root.SPRITES_SYMBOLS_EDGE;
function edgePath(ctx, which) {
  const sym = root.SPRITES_SYMBOLS_EDGE[which] || root.SPRITES_SYMBOLS_EDGE.Batman;
  for (const p of sym.loops) { ctx.moveTo(p[0][0], p[0][1]); for (let k = 1; k < p.length; k++) ctx.lineTo(p[k][0], p[k][1]); ctx.closePath(); }
  for (const p of sym.open || []) { ctx.moveTo(p[0][0], p[0][1]); for (let k = 1; k < p.length; k++) ctx.lineTo(p[k][0], p[k][1]); }
}
function drawGlyph(ctx, which, R, opt) {
  const fill = opt.fill, rim = opt.rim, lw = opt.lw;
  if (EDGE()) {
    ctx.save(); ctx.scale(R, R); ctx.lineJoin = "round"; ctx.lineCap = "round";
    ctx.beginPath(); edgePath(ctx, which); ctx.strokeStyle = rim; ctx.lineWidth = lw / R; ctx.stroke();
    ctx.restore(); return;
  }
  ctx.save(); ctx.scale(R, R);
  const S = 1 / R;                                  // so a stroke width given in CSS px stays in CSS px
  ctx.lineJoin = "round"; ctx.lineCap = "round";
  if (which === "Batman") {
    ctx.beginPath(); batHalf(ctx);
    ctx.save(); ctx.scale(-1, 1); batHalf(ctx); ctx.restore();   // the mirror half, same control points
    ctx.fillStyle = fill; ctx.fill();
    if (rim) { ctx.strokeStyle = rim; ctx.lineWidth = lw * S; ctx.stroke(); }
  } else if (which === "TARDIS") {
    ctx.beginPath(); tardisRoof(ctx); ctx.fillStyle = fill; ctx.fill();
    ctx.beginPath(); tardisPath(ctx); ctx.fillStyle = fill; ctx.fill();
    if (rim) { ctx.strokeStyle = rim; ctx.lineWidth = lw * S; ctx.stroke(); }
    // the lamp on the roof
    ctx.beginPath(); ctx.arc(0, -0.78, 0.085, 0, TAU); ctx.fillStyle = fill; ctx.fill();
    if (rim) { ctx.strokeStyle = rim; ctx.lineWidth = lw * S; ctx.stroke(); }
    // Door panels: four per door, as BRIGHT hairlines. They have to be additive, not dark: the whole
    // stage composites with globalCompositeOperation "lighter", under which a dark stroke adds nothing
    // and simply does not appear. (First draft drew them dark and they were invisible -- the kind of
    // fault that would have made this arm look featureless for a reason unrelated to vectors.)
    // These lines are the detail the 9x9 bitmap cannot hold at all and the 15x15 one holds only just.
    ctx.strokeStyle = opt.detail; ctx.lineWidth = Math.max(0.8, lw * 0.75) * S;
    for (let c = 0; c < 2; c++) for (let r = 0; r < 4; r++) {
      const x0 = c ? 0.07 : -0.51, w = 0.44, y0 = -0.40 + r * 0.30, hh = 0.21;
      ctx.beginPath(); ctx.rect(x0, y0, w, hh); ctx.stroke();
    }
    ctx.beginPath(); ctx.moveTo(0, -0.46); ctx.lineTo(0, 0.82); ctx.stroke();   // the door split
  } else {
    // Ring from rIn to rOut, with the teeth standing on rOut. The teeth must START inside the ring's
    // outer edge, or each one reads as a separate spoke floating off the rim; and the ring is filled as
    // an annulus (two arcs, "evenodd") rather than stroked, so the rim and the teeth are ONE silhouette
    // with one continuous outline instead of three stacked shapes.
    const rIn = 0.46, rOut = 0.72, teeth = 0.97, hub = 0.17;
    ctx.beginPath();
    ctx.arc(0, 0, rOut, 0, TAU);
    ctx.arc(0, 0, rIn, 0, TAU);
    cogTeeth(ctx, 8, rOut - 0.06, teeth, 0.19);
    ctx.fillStyle = fill; ctx.fill("evenodd");
    if (rim) {                                       // outline: outer edge, tooth flanks, inner bore
      ctx.strokeStyle = rim; ctx.lineWidth = lw * S;
      ctx.beginPath(); cogTeeth(ctx, 8, rOut - 0.06, teeth, 0.19); ctx.stroke();
      ctx.beginPath(); ctx.arc(0, 0, rOut, 0, TAU); ctx.stroke();
      ctx.beginPath(); ctx.arc(0, 0, rIn, 0, TAU); ctx.stroke();
    }
    ctx.beginPath(); ctx.arc(0, 0, hub, 0, TAU); ctx.fillStyle = fill; ctx.fill();
    if (rim) { ctx.strokeStyle = rim; ctx.lineWidth = lw * S; ctx.stroke(); }
  }
  ctx.restore();
}
// The glyph's outline as a path only (no paint), for clipping a wash or running beads along it.
function glyphPath(ctx, which, R) {
  ctx.save(); ctx.scale(R, R); ctx.beginPath();
  if (EDGE()) edgePath(ctx, which);
  else if (which === "Batman") { batHalf(ctx); ctx.save(); ctx.scale(-1, 1); batHalf(ctx); ctx.restore(); }
  else if (which === "TARDIS") { tardisRoof(ctx); tardisPath(ctx); }
  else { cogTeeth(ctx, 8, 0.66, 0.97, 0.19); ctx.arc(0, 0, 0.72, 0, TAU); }
  ctx.restore();
}
root.SPRITES_ARMC = { drawGlyph, glyphPath };

// ---------------------------------------------------------------------------------------------
// The piece. Same five multipliers, same reported geometry, same mapping as c6_night.
// ---------------------------------------------------------------------------------------------
root.SpritesArmCVector = function (V, NAMES) {
  const clamp = (x, a, b) => x < a ? a : x > b ? b : x;
  const lerp = (a, b, f) => a + (b - a) * f;
  let G = null;
  window.VARIANT_NAMES = NAMES;
  const SPR = new Map();
  function sprite(col) {                              // the one raster in this arm: the soft body halo,
    let c = SPR.get(col); if (c) return c;            // which is a gradient in every species and has no
    c = document.createElement("canvas"); c.width = c.height = 64;   // edges to resolve
    const x = c.getContext("2d"), g = x.createRadialGradient(32, 32, 0, 32, 32, 32);
    g.addColorStop(0, col); g.addColorStop(0.25, col.replace(/,[\d.]+\)$/, ",0.35)")); g.addColorStop(1, col.replace(/,[\d.]+\)$/, ",0)"));
    x.fillStyle = g; x.fillRect(0, 0, 64, 64); SPR.set(col, c); return c;
  }
  const szOf = () => V.P.size * (V.LIVE ? Math.min(V.W / 1280, V.H / 800) : 1);
  const radOf = s => s.E * 0.72 + 10 * G.SZ;

  V.piece({
    init(V, S) {
      const n = V.sessions.length;
      G = { SZ: szOf(), embers: [], vpnAmt: S.net.vpn === "down" ? 1 : 0, prevVpn: S.net.vpn };
      G.sigs = V.sessions.map((ss, i) => ({
        id: ss.id, ghost: !!ss.ghost, hue: ss.hue, iv: ((ss.iv % 8) + 8) % 8,
        x: V.W * (i + 0.5) / n, y: (V.TOP + V.H - V.BOT) / 2, vx: 0, vy: 0, wx: 0, wy: 0,
        E: 54, spin: 0, orb: V.rand() * Math.PI * 2, bright: 0.5, needT: -1, needAmt: 0,
        heatSm: 0, state: "idle", mem: 0.5, procs: 2, cpu: 0, pulses: [], inAcc: 0, outAcc: 0,
        bwS: 0, rx: 0, tx: 0, flare: 0 }));
      for (const s of G.sigs) { s.mem = S.s[s.id].mem; s.E = 9 * 6 * Math.sqrt(clamp(s.mem, 0.2, 2.6) / 0.8) * G.SZ;
        s.hx = s.x; s.hy = s.y; V.report(s.id, s.x, s.y, radOf(s)); }
    },
    carry(V, S, prev) { for (const s of G.sigs) { const p = prev[s.id]; if (!p) continue; s.x = p.x; s.y = p.y; V.report(s.id, s.x, s.y, radOf(s)); } },
    resize() { if (G) G.SZ = szOf(); },
    place(V, id, x, y) { const s = G && G.sigs.find(z => z.id === id); if (s) { s.x = x; s.y = y; s.vx = s.vy = 0; } },

    step(V, S, dt) {
      const t = V.t;
      const down = S.net.vpn === "down";
      G.prevVpn = S.net.vpn;
      G.vpnAmt = clamp(G.vpnAmt + (down ? dt / 0.8 : -dt / 0.5), 0, 1);
      const heat = clamp(S.m.level / 3, 0, 1), thermal = S.m.thermal || 0;
      G.sigs.forEach((s, i) => {
        const d = S.s[s.id]; if (!d) return;
        s.cpu = d.cpu || 0; s.mem = d.mem != null ? d.mem : s.mem; s.procs = d.procs || 0;
        if (d.state === "needs" && s.state !== "needs") s.needT = 0;
        s.state = d.state || "idle";
        if (s.state === "needs") s.needT += dt;
        s.needAmt = clamp(s.needAmt + (s.state === "needs" ? dt / 0.4 : -dt / 0.8), 0, 1);
        const tgtB = s.state === "idle" ? 0.5 : s.state === "needs" ? 1 : 0.85;
        s.bright += (tgtB - s.bright) * Math.min(1, dt * 3);
        s.heatSm += (heat - s.heatSm) * Math.min(1, dt * 2);
        const tE = 9 * 6 * Math.sqrt(clamp(s.mem, 0.2, 2.6) / 0.8) * G.SZ;
        s.E += (tE - s.E) * Math.min(1, dt * 2.5);
        s.spin += dt * Math.PI * 2 * 0.85 * s.cpu;
        s.orb += dt * (s.state === "working" ? 0.6 : 0);
        // bandwidth: beads born at a rate set by rx/tx, running along the glyph's own radius
        s.rx = d.rx || 0; s.tx = d.tx || 0;
        const moving = clamp(Math.log10(1 + s.rx + s.tx) / 0.8, 0, 1);
        s.bwS += ((S.net.strain || 0) * moving * (1 - G.vpnAmt) - s.bwS) * Math.min(1, dt * 3);
        const live = 1 - G.vpnAmt, thr = 1 - 0.5 * s.bwS;
        s.inAcc += dt * 5.5 * Math.log10(1 + s.rx) * thr * live;
        s.outAcc += dt * 5.5 * Math.log10(1 + s.tx) * thr * live;
        while (s.inAcc >= 1) { s.inAcc -= 1; s.pulses.push({ dir: -1, a: V.rand() * Math.PI * 2, u: 1.1, br: 0.8 }); }
        while (s.outAcc >= 1) { s.outAcc -= 1; s.pulses.push({ dir: 1, a: V.rand() * Math.PI * 2, u: -0.05, br: 0.8 }); }
        for (const p of s.pulses) p.u += p.dir * 1.15 * dt;
        s.pulses = s.pulses.filter(p => p.dir < 0 ? p.u > -0.1 : p.u < 1.15);
        if (s.pulses.length > 36) s.pulses.splice(0, s.pulses.length - 36);
        if (G.vpnAmt > 0.5) s.pulses.length = 0;
        // motion: spring to home + curl-noise wander (see the header: deliberately minimal)
        const [ux, uy] = V.curl(s.x + i * 300, s.y, t * 0.4);
        s.wx += (ux * 7 * V.P.drift - s.wx * 0.08) * dt; s.wy += (uy * 7 * V.P.drift - s.wy * 0.08) * dt;
        const r = radOf(s);
        const tx = clamp(s.hx + s.wx, 6 + r, V.W - 6 - r), ty = clamp(s.hy + s.wy, V.TOP + 4 + r, V.H - V.BOT - 4 - r);
        let ax = 5 * (tx - s.x) - 2 * Math.sqrt(5) * s.vx, ay = 5 * (ty - s.y) - 2 * Math.sqrt(5) * s.vy;
        s.vx += ax * dt; s.vy += ay * dt; s.x += s.vx * dt; s.y += s.vy * dt;
        V.report(s.id, s.x, s.y, r);
        if (thermal > 0.05 && G.vpnAmt < 0.5) { s.emAcc = (s.emAcc || 0) + dt * thermal * 1.6 * V.P.density;
          while (s.emAcc >= 1) { s.emAcc -= 1; G.embers.push({ x: s.x + (V.rand() - 0.5) * s.E, y: s.y - s.E * 0.3,
            vx: (V.rand() - 0.5) * 14, vy: -30 - 40 * V.rand(), life: 1.6, max: 1.6 }); } }
      });
      for (const e of G.embers) { e.x += e.vx * dt; e.y += e.vy * dt; e.life -= dt; }
      G.embers = G.embers.filter(e => e.life > 0);
    },

    draw(V, S, ctx) {
      ctx.save(); ctx.globalCompositeOperation = "lighter";
      for (const s of G.sigs) V.creature(s.id, () => drawOne(V, S, ctx, s));
      for (const e of G.embers) { const u = e.life / e.max; ctx.globalAlpha = 0.7 * u;
        ctx.fillStyle = V.hsl(8 + 18 * (1 - u), 95, 60, 1); ctx.beginPath(); ctx.arc(e.x, e.y, 1.3, 0, TAU); ctx.fill(); }
      ctx.restore();
    },
  });

  function drawOne(V, S, ctx, s) {
    const P = V.P, t = V.t, vpn = G.vpnAmt, E = s.E, heat = s.heatSm * (1 - vpn);
    const which = NAMES[s.iv] || NAMES[0];
    const R = E * 0.5;                                     // the glyph's unit box maps to this radius
    const sat = lerp(lerp(92, 80, heat), 40, vpn), light = lerp(lerp(60, 70, heat), 62, vpn);
    const breathe = s.state === "idle" ? 0.88 + 0.12 * Math.sin(t * TAU / 7 + s.hue) : 1;
    const B = clamp(s.bright + s.flare * 0.6, 0, 1.4) * (1 - 0.25 * vpn) * breathe;
    const ox = s.x, oy = s.y;
    // body halo: the one gradient, exactly as every other species draws its halo
    const hr = E * 0.95 * Math.sqrt(P.glow);
    ctx.globalAlpha = clamp(0.30 * B * P.glow * (0.6 + 0.4 * s.needAmt) * (EDGE() ? 0.35 : 1), 0, 1);
    ctx.drawImage(sprite(V.hsl(s.hue, sat, 50, 1)), ox - hr, oy - hr, hr * 2, hr * 2);
    if (heat > 0.05) { ctx.globalAlpha = clamp(0.5 * heat * P.glow, 0, 1); const h2 = hr * 1.3;
      ctx.drawImage(sprite(V.hsl(4, 95, 50, 1)), ox - h2, oy - h2, h2 * 2, h2 * 2); }

    ctx.save(); ctx.translate(ox, oy);
    // thermal strain: the whole figure shears, the vector analogue of the LED rows slipping
    if (heat > 0.05 && V.on("strainAgitation")) ctx.transform(1, 0, (V.vnoise(s.hue, t * 2.2) - 0.5) * 0.5 * heat * heat, 1, 0, 0);

    // the rim: a true hairline at any size. Edge mode: ~1/40 of the glyph, floor 1 CSS px (2 device px),
    // so a 256 px symbol gets a ~3 px line and a 23 px one a 1 px line, both crisp
    const lw = EDGE() ? Math.max(1, E * 0.022) : Math.max(0.9, 1.1 * Math.sqrt(P.size));
    // 1. the body, filled at the session's own hue, with a brighter rim so the silhouette has an edge
    ctx.globalAlpha = clamp((EDGE() ? 1.0 : 0.62) * B + (EDGE() ? 0.2 : 0), 0, 1);
    SPRITES_ARMC.drawGlyph(ctx, which, R, { fill: V.hsl(s.hue, sat, light - 8, 1),
      rim: V.hsl(s.hue, sat * 0.9, Math.min(92, light + 26), 1), lw,
      detail: V.hsl(s.hue, sat * 0.8, Math.min(88, light + 18), 1) });

    // 2. CPU: a twin wedge of light sweeping round the figure, clipped to the figure itself. Takes the
    //    place of the LED sweep; being a clip, the lit area has the glyph's own edges, not a cell grid.
    const cpuOn = clamp(s.cpu / 0.35, 0, 1);
    if (cpuOn > 0.01 && EDGE()) {
      for (const dir of [0, Math.PI]) { const a = s.spin + dir;
        ctx.save(); ctx.beginPath(); ctx.moveTo(0, 0); ctx.arc(0, 0, R * 1.2, a - 0.42, a + 0.42); ctx.closePath(); ctx.clip();
        ctx.globalAlpha = clamp(0.8 * cpuOn * B, 0, 1);
        SPRITES_ARMC.drawGlyph(ctx, which, R, { rim: V.hsl(s.hue, sat * 0.4, 94, 1), lw: lw * 1.15 });
        ctx.restore(); }
    } else if (cpuOn > 0.01) {
      ctx.save(); SPRITES_ARMC.glyphPath(ctx, which, R); ctx.clip();
      for (const dir of [0, Math.PI]) {
        const a = s.spin + dir, g = ctx.createRadialGradient(0, 0, 0, 0, 0, R * 1.05);
        g.addColorStop(0, V.hsl(s.hue, sat * 0.5, 94, 1)); g.addColorStop(1, V.hsl(s.hue, sat * 0.6, 80, 0));
        ctx.globalAlpha = clamp(0.55 * cpuOn * B, 0, 1); ctx.fillStyle = g;
        ctx.beginPath(); ctx.moveTo(0, 0); ctx.arc(0, 0, R * 1.05, a - 0.42, a + 0.42); ctx.closePath(); ctx.fill();
      }
      ctx.restore();
    }
    // 3. strain: a red ember wash inside the figure (clipped, so it stays in the symbol)
    if (heat > 0.05 && EDGE()) { ctx.globalAlpha = clamp(0.5 * heat, 0, 1);
      SPRITES_ARMC.drawGlyph(ctx, which, R, { rim: V.hsl(6, 95, 55, 1), lw }); }
    else if (heat > 0.05) { ctx.save(); SPRITES_ARMC.glyphPath(ctx, which, R); ctx.clip();
      ctx.globalAlpha = clamp(0.45 * heat * P.glow, 0, 1); ctx.fillStyle = V.hsl(6, 95, 48, 1);
      ctx.fillRect(-R, -R, 2 * R, 2 * R); ctx.restore(); }
    // 4. bandwidth: beads on the glyph's radius -- cool inward (download), gold outward (upload),
    //    each a small filled circle, so it is round at any size instead of a square cell
    for (const p of s.pulses) {
      const u = clamp(p.u, 0, 1), rad = u * R * 0.96;
      const px = Math.cos(p.a) * rad, py = Math.sin(p.a) * rad, rr = Math.max(1.1, R * 0.055);
      ctx.globalAlpha = clamp(0.85 * p.br * (1 - vpn), 0, 1);
      ctx.fillStyle = p.dir < 0 ? V.hsl(212, 45, 95, 1) : V.hsl(42, 95, 72, 1);
      ctx.beginPath(); ctx.arc(px, py, rr, 0, TAU); ctx.fill();
      ctx.globalAlpha = clamp(0.3 * p.br * P.glow * (1 - vpn), 0, 1);
      ctx.drawImage(sprite(p.dir < 0 ? V.hsl(210, 55, 90, 1) : V.hsl(40, 100, 62, 1)), px - rr * 3, py - rr * 3, rr * 6, rr * 6);
    }
    // 5. the pilot light: always on, the session's own hue, a crisp disc at the centre
    ctx.globalAlpha = clamp(0.5 + 0.5 * B, 0, 1);
    ctx.fillStyle = V.hsl(s.hue, 95, 72, 1);
    ctx.beginPath(); ctx.arc(0, 0, Math.max(1.4, R * 0.085), 0, TAU); ctx.fill();
    ctx.restore();

    // 6. satellites = background tasks, one small disc each, on an ellipse outside the figure
    const n = Math.floor(s.procs + 1e-3), fr = s.procs - n, tot = n + (fr > 0.02 ? 1 : 0);
    const orbR = E * 0.62 + 9 * G.SZ, dot = Math.max(1.6, 2.1 * Math.sqrt(G.SZ));
    for (let k = 0; k < tot; k++) { const a = s.orb + k / Math.max(1, tot) * TAU;
      const x = ox + Math.cos(a) * orbR, y = oy + Math.sin(a) * orbR * 0.92;
      ctx.globalAlpha = (k < n ? 0.9 : fr) * clamp(B + 0.15, 0, 1);
      ctx.fillStyle = V.hsl(s.hue, sat * 0.85, 78, 1); ctx.beginPath(); ctx.arc(x, y, dot, 0, TAU); ctx.fill();
      ctx.globalAlpha *= 0.5; ctx.drawImage(sprite(V.hsl(s.hue, sat, light, 1)), x - dot * 3, y - dot * 3, dot * 6, dot * 6); }
    // 7. needs you: smooth stroked rings out of the figure (an arc, not a ring of dots)
    if (s.needAmt > 0.01) {
      for (let k = 0; k < 2; k++) { const u = ((t / 2.2) + k * 0.5) % 1, rad = E * 0.62 + u * (0.6 * E + 18);
        const al = Math.sin(Math.PI * u) * 0.5 * s.needAmt;
        ctx.globalAlpha = clamp(al * P.glow, 0, 1); ctx.strokeStyle = V.hsl(s.hue, 85, 68, 1); ctx.lineWidth = 3.2;
        ctx.beginPath(); ctx.arc(ox, oy, rad, 0, TAU); ctx.stroke();
        ctx.globalAlpha = clamp(al, 0, 1); ctx.strokeStyle = V.hsl(s.hue, 70, 86, 1); ctx.lineWidth = 1;
        ctx.beginPath(); ctx.arc(ox, oy, rad, 0, TAU); ctx.stroke(); }
    }
  }
};
})(this);
