/* Sprites hover labels (2026-11-01): five styles, owner ruling ~06:40 "all switchable in Settings, Constellation the default".
 * Public API at the bottom: SpritesLabels.draw(ctx, {...}), track(), groundAt(). Internals below take (ctx, L, env).
 *
 * SpritesLabels.draw(ctx, opt, L, env)
 *   L   = { name (the shortname), hue (deg), x, y, r (creature centre and extent radius, CSS px; rt/rb = extent
 *           above/below the centre when the form is lopsided, e.g. Siphonophore tentacles),
 *           e (appear progress 0..1), out (true while disappearing), t (seconds), seed }
 *   env = { k (type scale = sqrt(size slider): 50% -> 0.71, 100% -> 1, 200% -> 1.41), W, H (screen, CSS px), dpr }
 * Type: cap height 12 px x k for every option (measured on "H" per font, not assumed).
 * Every option draws a soft dark halo first so the hue reads over the red wallpaper AND a white window,
 * and keeps a clear gap of >= 6 px x k from the creature's extent radius (never covers it).
 * Labels are identity only (project shortname); nothing about them encodes data. */
(function (root) {
  "use strict";
  const TAU = Math.PI * 2, clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const ease = u => { u = clamp(u, 0, 1); return u * u * (3 - 2 * u); };
  const easeOut = u => { u = clamp(u, 0, 1); return 1 - Math.pow(1 - u, 3); };
  const seg = (e, a, b) => clamp((e - a) / (b - a), 0, 1);
  const hsl = (h, s, l, a = 1) => `hsla(${h},${s}%,${l}%,${a})`;
  function rng(s) { s = (s >>> 0) || 1; return () => { s = (s + 0x6D2B79F5) >>> 0; let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
  function hash(s) { let h = 2166136261; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return h >>> 0; }

  // font whose "H" is `cap` px tall (measured once per family)
  const ratio = {};
  function capFont(ctx, style, weight, fam, cap) { const key = style + weight + fam;
    if (!ratio[key]) { ctx.save(); ctx.font = `${style} ${weight} 100px ${fam}`; const m = ctx.measureText("H");
      ratio[key] = (m.actualBoundingBoxAscent || 70) / 100; ctx.restore(); }
    const px = cap / ratio[key]; return { font: `${style} ${weight} ${px.toFixed(2)}px ${fam}`, px }; }

  // the shared legibility device: a soft dark halo under the glyphs (not a box)
  // Owner ruling 2026-11-01: the halo appears only where the ground under the label is bright (L.ground === "bright");
  // over the wallpaper and the terminal the light stays pure. Orbit and the Tag keep their own grounds.
  function halo(ctx, k, a, fn, L) { if (L && L.ground !== "bright") return; ctx.save(); ctx.globalCompositeOperation = "source-over";
    ctx.fillStyle = ctx.strokeStyle = `rgba(4,6,10,${0.55 * a})`; ctx.shadowColor = `rgba(4,6,10,${0.75 * a})`;
    ctx.shadowBlur = 8 * k; ctx.lineWidth = 3 * k; ctx.lineJoin = "round"; fn(true); ctx.restore(); }

  // where the name goes: above the creature unless that would leave the screen
  const top = L => L.rt ?? L.r, bot = L => L.rb ?? L.r;
  function above(L, env, need) { return L.y - top(L) - need > 30; }

  // ---------------- 1. FILAMENT: a hairline script that writes itself in, a pen-light at the nib ----------------
  function filament(ctx, L, env) {
    const k = env.k, cap = 13 * k, f = capFont(ctx, "italic", 600, "'Snell Roundhand', 'Apple Chancery', cursive", cap);
    ctx.save(); ctx.font = f.font; const w = ctx.measureText(L.name).width; ctx.restore();
    const up = above(L, env, cap + 14 * k), x0 = L.x - w / 2, base = up ? L.y - top(L) - 8 * k : L.y + bot(L) + 8 * k + cap;
    const e = L.out ? 1 : easeOut(L.e), a = L.out ? ease(L.e) : 1, rise = L.out ? (1 - L.e) * -5 * k : 0;
    const reveal = x0 - 4 * k + (w + 14 * k) * e;               // the ink front
    ctx.save(); ctx.translate(0, rise); ctx.globalAlpha = a;
    // soft-edged wipe: clip to the left of the ink front, feather it with a gradient mask
    ctx.beginPath(); ctx.rect(x0 - 30 * k, base - cap * 2.2, Math.max(0, reveal - (x0 - 30 * k)), cap * 3.6); ctx.clip();
    ctx.font = f.font; ctx.textBaseline = "alphabetic"; ctx.textAlign = "left";
    halo(ctx, k, 1, () => { ctx.strokeText(L.name, x0, base); ctx.fillText(L.name, x0, base); }, L);
    // swash: a tapering hairline under the word, the pen's exit stroke
    ctx.save(); ctx.lineCap = "round"; const sy = base + 3.2 * k;
    for (let i = 0; i < 2; i++) { ctx.beginPath(); ctx.moveTo(x0 + w * 0.08, sy + 0.6 * k);
      ctx.bezierCurveTo(x0 + w * 0.4, sy + 2.4 * k, x0 + w * 0.75, sy - 0.4 * k, x0 + w + 9 * k, sy - 3.4 * k);
      ctx.strokeStyle = i ? hsl(L.hue, 100 * L.sk, 82, 0.75) : hsl(L.hue, 100 * L.sk, 60, 0.5); ctx.lineWidth = (i ? 0.55 : 1.6) * k;
      if (!i) { ctx.shadowColor = hsl(L.hue, 100 * L.sk, 55, 0.9); ctx.shadowBlur = 5 * k; } ctx.stroke(); }
    ctx.restore();
    // glow, then a crisp pale core
    ctx.shadowColor = hsl(L.hue, 100 * L.sk, 55, 0.95); ctx.shadowBlur = 6 * k; ctx.fillStyle = hsl(L.hue, 100 * L.sk, 66, 1); ctx.fillText(L.name, x0, base);
    ctx.shadowBlur = 0; ctx.fillStyle = hsl(L.hue, 100 * L.sk, 86, 0.9); ctx.fillText(L.name, x0, base);
    ctx.restore();
    // the nib: a bright mote riding the ink front while writing
    if (!L.out && L.e > 0.01 && L.e < 0.99) { const nx = reveal - 4 * k, ny = base - cap * 0.35 + Math.sin(L.e * 38) * cap * 0.28;
      ctx.save(); const g = ctx.createRadialGradient(nx, ny, 0, nx, ny, 7 * k); g.addColorStop(0, hsl(L.hue, 100 * L.sk, 92, 1));
      g.addColorStop(0.25, hsl(L.hue, 100 * L.sk, 70, 0.6)); g.addColorStop(1, hsl(L.hue, 100 * L.sk, 60, 0)); ctx.fillStyle = g;
      ctx.beginPath(); ctx.arc(nx, ny, 7 * k, 0, TAU); ctx.fill(); ctx.restore(); }
  }

  // ---------------- 2. ORBIT: letterspaced capitals riding a dial arc under the creature ----------------
  function orbit(ctx, L, env) {
    const k = env.k, cap = 11 * k, f = capFont(ctx, "normal", 600, "'Avenir Next', 'Avenir', sans-serif", cap);
    const txt = L.name.toUpperCase(), track = 0.24 * f.px;
    ctx.save(); ctx.font = f.font; const ws = [...txt].map(c => ctx.measureText(c).width); ctx.restore();
    const down = L.y + bot(L) + 30 * k < env.H - 8;                                   // smile under, else frown over
    const total = ws.reduce((s, w) => s + w, 0) + track * (ws.length - 1), SPAN = 1.83;   // v2: at most ~105 deg of arc
    const Rmin = (down ? bot(L) : top(L)) + 7 * k + (down ? cap : 0), Rspan = total / SPAN + (down ? cap / 2 : -cap / 2);
    const R = Math.max(Rmin, Rspan), Rm = R - (down ? cap / 2 : -cap / 2), th = total / Rm;
    const cy = L.y - (R - Rmin) * (down ? 1 : -1);          // a wider arc is centred higher (lower) so it still hugs the creature
    const mid = down ? Math.PI / 2 : -Math.PI / 2, dir = down ? -1 : 1;           // left-to-right reading order
    const n = ws.length, A = L.out ? ease(L.e) : 1;
    // dial hairlines beyond both ends, with tick dots
    const eA = L.out ? 1 : easeOut(seg(L.e, 0, 0.7));
    ctx.save(); ctx.globalAlpha = A; ctx.lineCap = "round";
    const ext = 0.16 * eA, hw = th / 2 + 0.05;
    for (const s of [-1, 1]) { const a0 = mid - dir * s * hw, a1 = mid - dir * s * (hw + ext);
      const gx0 = L.x + Math.cos(a0) * Rm, gy0 = cy + Math.sin(a0) * Rm, gx1 = L.x + Math.cos(a1) * Rm, gy1 = cy + Math.sin(a1) * Rm;
      const g = ctx.createLinearGradient(gx0, gy0, gx1, gy1); g.addColorStop(0, hsl(L.hue, 100 * L.sk, 72, 0.75)); g.addColorStop(1, hsl(L.hue, 100 * L.sk, 72, 0));
      ctx.strokeStyle = g; ctx.lineWidth = 0.7 * k; ctx.beginPath(); ctx.arc(L.x, cy, Rm, Math.min(a0, a1), Math.max(a0, a1)); ctx.stroke();
      ctx.fillStyle = hsl(L.hue, 100 * L.sk, 80, 0.85 * eA); ctx.beginPath(); ctx.arc(gx0 + (gx1 - gx0) * 0.38, gy0 + (gy1 - gy0) * 0.38, 0.9 * k, 0, TAU); ctx.fill(); }
    ctx.restore();
    // letters: each slides out along the arc from the centre, staggered centre-outward
    let s = -total / 2;
    for (let i = 0; i < n; i++) { const c = (s + ws[i] / 2) / Rm; s += ws[i] + track;
      const d = Math.abs(i - (n - 1) / 2) / Math.max(1, (n - 1) / 2), u = L.out ? 1 : easeOut(seg(L.e, d * 0.35, d * 0.35 + 0.6));
      const ang = mid + dir * c * u, la = A * (L.out ? 1 : seg(L.e, d * 0.35, d * 0.35 + 0.35));
      if (la <= 0) continue;
      ctx.save(); ctx.translate(L.x + Math.cos(ang) * R, cy + Math.sin(ang) * R); ctx.rotate(ang + (down ? -Math.PI / 2 : Math.PI / 2));
      ctx.font = f.font; ctx.textAlign = "center"; ctx.textBaseline = down ? "alphabetic" : "top"; ctx.globalAlpha = la;
      const yy = down ? 0 : 0;
      halo(ctx, k, 1, () => { ctx.strokeText(txt[i], 0, yy); ctx.fillText(txt[i], 0, yy); });
      ctx.shadowColor = hsl(L.hue, 100 * L.sk, 55, 0.9); ctx.shadowBlur = 5 * k; ctx.fillStyle = hsl(L.hue, 100 * L.sk, 70, 1); ctx.fillText(txt[i], 0, yy);
      ctx.shadowBlur = 0; ctx.fillStyle = hsl(L.hue, 100 * L.sk, 88, 0.85); ctx.fillText(txt[i], 0, yy);
      ctx.restore(); }
  }

  // ---------------- 3. CONSTELLATION: the creature's motes fly out and settle into the letters ----------------
  const starCache = new Map();
  function stars(name, k) { const key = name + "|" + k.toFixed(3); if (starCache.has(key)) return starCache.get(key);
    const cap = 14 * k, S = 4, c = document.createElement("canvas"), x = c.getContext("2d");
    const f = capFont(x, "normal", 600, "'SF Pro Rounded', ui-rounded, 'Avenir Next', sans-serif", cap * S);
    x.font = f.font; const w = Math.ceil(x.measureText(name).width) + 8 * S, h = Math.ceil(cap * S * 1.9);
    c.width = w; c.height = h; x.font = f.font; x.textBaseline = "alphabetic"; x.fillStyle = "#fff"; x.fillText(name, 4 * S, cap * S * 1.35);
    const d = x.getImageData(0, 0, w, h).data, pts = [], step = 1.9 * k * S, R = rng(hash(name));
    for (let yy = 0; yy < h; yy += step) for (let xx = (yy / step) % 2 ? step / 2 : 0; xx < w; xx += step) {
      const jx = xx + (R() - 0.5) * step * 0.3, jy = yy + (R() - 0.5) * step * 0.3, ix = jx | 0, iy = jy | 0;
      if (ix < 0 || iy < 0 || ix >= w || iy >= h) continue;
      if (d[(iy * w + ix) * 4 + 3] > 140) pts.push({ x: jx / S, y: jy / S, d: R(), ph: R() * TAU, ox: R(), oy: R(), big: R() < 0.12 }); }
    const out = { pts, w: w / S, h: h / S, base: cap * 1.35, glyph: c, S, f }; starCache.set(key, out); return out; }
  function constellation(ctx, L, env) {
    const k = env.k, st = stars(L.name, k), up = above(L, env, st.h + 10 * k);
    const ox = L.x - st.w / 2, oy = up ? L.y - top(L) - 7 * k - st.h * 0.86 : L.y + bot(L) + 6 * k - st.h * 0.2;
    const A = L.out ? 1 : 1;
    // halo under the word (fades in with the motes)
    if (L.ground === "bright") { const hA = L.out ? ease(L.e) : ease(seg(L.e, 0.15, 0.9));
      ctx.save(); ctx.globalAlpha = hA; ctx.filter = `blur(${(3.4 * k).toFixed(1)}px)`;
      ctx.drawImage(darkGlyph(st), ox, oy, st.w, st.h); ctx.drawImage(darkGlyph(st), ox, oy, st.w, st.h); ctx.filter = "none"; ctx.restore(); }
    ctx.save();
    for (const p of st.pts) {
      const del = p.d * 0.4, u = L.out ? 1 - easeOut(seg(1 - L.e, del * 0.6, del * 0.6 + 0.55)) : easeOut(seg(L.e, del, del + 0.6));
      if (u <= 0.001) continue;
      const m = L.motes && L.motes.length ? L.motes[(p.ox * 9973 | 0) % L.motes.length] : null;   // a real mote of the creature, else a point inside it
      const sx = m ? m[0] : L.x + (p.ox - 0.5) * L.r * 0.9, sy = m ? m[1] : L.y + (p.oy - 0.5) * L.r * 0.9, tx = ox + p.x, ty = oy + p.y;
      const bend = Math.sin(u * Math.PI) * (p.ox - 0.5) * 22 * k;            // a curved flight, not a straight beam
      const px = sx + (tx - sx) * u + bend, py = sy + (ty - sy) * u;
      const tw = 0.78 + 0.22 * Math.sin(L.t * 2.6 + p.ph);
      const r0 = (p.big ? 0.85 : 0.5) * k;
      if (u < 0.98) { const pu = Math.max(0, u - 0.08), qx = sx + (tx - sx) * pu + Math.sin(pu * Math.PI) * (p.ox - 0.5) * 22 * k, qy = sy + (ty - sy) * pu;
        ctx.strokeStyle = hsl(L.hue, 100 * L.sk, 75, 0.45 * u); ctx.lineWidth = r0; ctx.beginPath(); ctx.moveTo(qx, qy); ctx.lineTo(px, py); ctx.stroke(); }
      ctx.globalAlpha = Math.min(1, u * 1.4) * tw;
      ctx.fillStyle = hsl(L.hue, 100 * L.sk, 60, 0.35); ctx.beginPath(); ctx.arc(px, py, r0 * 2.6, 0, TAU); ctx.fill();
      ctx.fillStyle = hsl(L.hue, 100 * L.sk, p.big ? 92 : 80, 1); ctx.beginPath(); ctx.arc(px, py, r0, 0, TAU); ctx.fill(); }
    ctx.restore();
  }
  const darkCache = new WeakMap();
  function darkGlyph(st) { if (darkCache.has(st)) return darkCache.get(st);
    const c = document.createElement("canvas"); c.width = st.glyph.width; c.height = st.glyph.height; const x = c.getContext("2d");
    x.drawImage(st.glyph, 0, 0); x.globalCompositeOperation = "source-in"; x.fillStyle = "rgba(3,5,9,0.6)"; x.fillRect(0, 0, c.width, c.height);
    // thicken: re-draw offset copies
    const d = document.createElement("canvas"); d.width = c.width; d.height = c.height; const y = d.getContext("2d");
    for (let a = 0; a < 8; a++) y.drawImage(c, Math.cos(a / 8 * TAU) * 2 * st.S, Math.sin(a / 8 * TAU) * 2 * st.S);
    darkCache.set(st, d); return d; }

  // ---------------- 4. LANTERN TAG: a smoked-glass tag on a thread, its pip a running light ----------------
  function tag(ctx, L, env) {
    const k = env.k, cap = 10.5 * k, f = capFont(ctx, "normal", 600, "'SF Pro Rounded', ui-rounded, 'Avenir Next', sans-serif", cap);
    ctx.save(); ctx.font = f.font; ctx.letterSpacing = (0.03 * f.px).toFixed(2) + "px"; const tw = ctx.measureText(L.name).width; ctx.restore();
    const e = L.e, thr = L.out ? 1 : easeOut(seg(e, 0, 0.45)), unf = L.out ? 1 : seg(e, 0.3, 0.85), txtA = L.out ? 1 : ease(seg(e, 0.55, 1));
    const A = L.out ? ease(L.e) : 1;
    const len = 13 * k * thr, sway = Math.sin(L.t * 1.25 + L.seed) * 0.07, ax = L.x, ay = L.y + bot(L) * 0.92;
    const tx = ax + Math.sin(sway) * len, ty = ay + Math.cos(sway) * len;
    ctx.save(); ctx.globalAlpha = A;
    // thread: a hairline with a slight catenary, a bead at the knot
    ctx.lineCap = "round"; ctx.strokeStyle = hsl(L.hue, 90 * L.sk, 72, 0.7); ctx.lineWidth = 0.7 * k;
    ctx.beginPath(); ctx.moveTo(ax, ay); ctx.quadraticCurveTo(ax + Math.sin(sway) * len * 0.3 + 1.2 * k, ay + len * 0.55, tx, ty); ctx.stroke();
    ctx.fillStyle = hsl(L.hue, 100 * L.sk, 82, 0.95); ctx.beginPath(); ctx.arc(ax, ay, 1.1 * k, 0, TAU); ctx.fill();
    if (unf > 0) {
      const over = unf < 1 ? 1 + Math.sin(unf * Math.PI) * 0.08 : 1, hgt = (cap + 7.5 * k) * easeOut(unf) * over, wd = tw + 21 * k;
      const x0 = tx - wd / 2, y0 = ty, rr = Math.min(hgt / 2, 6 * k);
      ctx.save(); ctx.translate(tx, ty); ctx.rotate(-sway * 0.6); ctx.translate(-tx, -ty);
      ctx.shadowColor = "rgba(0,0,0,0.45)"; ctx.shadowBlur = 8 * k; ctx.shadowOffsetY = 1.5 * k;
      const g = ctx.createLinearGradient(0, y0, 0, y0 + hgt); g.addColorStop(0, "rgba(14,18,26,0.62)"); g.addColorStop(1, "rgba(5,7,12,0.74)");
      ctx.fillStyle = g; rrect(ctx, x0, y0, wd, hgt, rr); ctx.fill(); ctx.shadowColor = "transparent";
      ctx.strokeStyle = hsl(L.hue, 95 * L.sk, 66, 0.45); ctx.lineWidth = 0.6 * k; rrect(ctx, x0 + 0.4, y0 + 0.4, wd - 0.8, hgt - 0.8, rr); ctx.stroke();
      ctx.strokeStyle = "rgba(255,255,255,0.10)"; ctx.lineWidth = 0.6 * k; ctx.beginPath(); ctx.moveTo(x0 + rr, y0 + 1.2 * k); ctx.lineTo(x0 + wd - rr, y0 + 1.2 * k); ctx.stroke();
      // the pip: a running light, slow candle flicker
      const fl = 0.75 + 0.25 * Math.sin(L.t * 2.1 + L.seed) * Math.sin(L.t * 3.3), px = x0 + 7.5 * k, py = y0 + hgt / 2;
      const pg = ctx.createRadialGradient(px, py, 0, px, py, 5 * k); pg.addColorStop(0, hsl(L.hue, 100 * L.sk, 90, fl)); pg.addColorStop(0.3, hsl(L.hue, 100 * L.sk, 62, 0.75 * fl)); pg.addColorStop(1, hsl(L.hue, 100 * L.sk, 55, 0));
      ctx.fillStyle = pg; ctx.beginPath(); ctx.arc(px, py, 5 * k, 0, TAU); ctx.fill();
      if (txtA > 0) { ctx.globalAlpha = A * txtA; ctx.font = f.font; ctx.letterSpacing = (0.03 * f.px).toFixed(2) + "px"; ctx.textBaseline = "alphabetic";
        ctx.fillStyle = hsl(L.hue, 100 * L.sk, 80, 1); ctx.shadowColor = hsl(L.hue, 100 * L.sk, 55, 0.6); ctx.shadowBlur = 4 * k;
        ctx.fillText(L.name, x0 + 14 * k, y0 + hgt / 2 + cap / 2); }
      ctx.restore(); }
    ctx.restore();
  }
  function rrect(c, x, y, w, h, r) { c.beginPath(); c.moveTo(x + r, y); c.arcTo(x + w, y, x + w, y + h, r); c.arcTo(x + w, y + h, x, y + h, r);
    c.arcTo(x, y + h, x, y, r); c.arcTo(x, y, x + w, y, r); c.closePath(); }

  // ---------------- 5. WHISPER: a lowercase italic that comes into focus and breathes with the creature ----------------
  function whisper(ctx, L, env) {
    const k = env.k, cap = 12.5 * k, f = capFont(ctx, "italic", 400, "'Baskerville', 'Hoefler Text', Georgia, serif", cap);
    const txt = L.name, sp = 0.05 * f.px;   // v2: case kept (lowercase broke CamelCase shortnames)
    ctx.save(); ctx.font = f.font; const ws = [...txt].map(c => ctx.measureText(c).width); ctx.restore();
    const total = ws.reduce((a, b) => a + b, 0) + sp * (ws.length - 1), up = above(L, env, cap + 14 * k);
    const base = up ? L.y - top(L) - 8 * k : L.y + bot(L) + 8 * k + cap;
    const breathe = 0.5 + 0.5 * Math.sin(L.t * TAU / (L.pulse || 3.2) + L.seed);          // the creature's breath
    let x = L.x - total / 2;
    for (let i = 0; i < ws.length; i++) {
      const d = i / Math.max(1, ws.length - 1);
      const u = L.out ? 1 - ease(seg(1 - L.e, d * 0.3, d * 0.3 + 0.7)) : ease(seg(L.e, d * 0.35, d * 0.35 + 0.65));
      if (u > 0.002) {
        const bl = (1 - u) * 5 * k, dy = L.out ? -(1 - u) * 6 * k : (1 - u) * 4 * k;
        ctx.save(); ctx.font = f.font; ctx.textBaseline = "alphabetic"; ctx.globalAlpha = u;
        if (bl > 0.15) ctx.filter = `blur(${bl.toFixed(2)}px)`;
        halo(ctx, k, 0.9, () => { ctx.strokeText(txt[i], x, base + dy); ctx.fillText(txt[i], x, base + dy); }, L);
        ctx.shadowColor = hsl(L.hue, 100 * L.sk, 60, 0.45 + 0.45 * breathe); ctx.shadowBlur = (5 + 6 * breathe) * k;
        ctx.fillStyle = hsl(L.hue, 95 * L.sk, 72 + 6 * breathe, 1); ctx.fillText(txt[i], x, base + dy);
        ctx.shadowBlur = 0; ctx.fillStyle = hsl(L.hue, 100 * L.sk, 88, 0.55 + 0.3 * breathe); ctx.fillText(txt[i], x, base + dy);
        ctx.restore(); }
      x += ws[i] + sp; }
  }

  const OPTIONS = {
    1: { key: "filament", title: "Filament", fn: filament, inS: 0.9, outS: 0.35 },
    2: { key: "orbit", title: "Orbit", fn: orbit, inS: 0.8, outS: 0.3 },
    3: { key: "constellation", title: "Constellation", fn: constellation, inS: 1.2, outS: 0.7 },
    4: { key: "tag", title: "Lantern tag", fn: tag, inS: 0.7, outS: 0.3 },
    5: { key: "whisper", title: "Whisper", fn: whisper, inS: 0.9, outS: 0.6 },
  };
  function drawRaw(ctx, opt, L, env) { const o = OPTIONS[opt]; if (!o || L.e <= 0) return; if (L.sk == null) L.sk = 1; o.fn(ctx, L, env); }

  // ---------------- public API (for the stage) ----------------
  const STYLES = ["filament", "orbit", "constellation", "tag", "whisper"], DEFAULT = "constellation";
  const BYKEY = {}; for (const n in OPTIONS) BYKEY[OPTIONS[n].key] = +n;
  function hexHue(hex) { const m = /^#?([0-9a-f]{6})$/i.exec(hex || ""); if (!m) return null; const n = parseInt(m[1], 16);
    const r = (n >> 16) / 255, g = (n >> 8 & 255) / 255, b = (n & 255) / 255, mx = Math.max(r, g, b), mn = Math.min(r, g, b), d = mx - mn;
    if (!d) return 0; const x = mx === r ? ((g - b) / d) % 6 : mx === g ? (b - r) / d + 2 : (r - g) / d + 4; return Math.round((x * 60 + 360) % 360); }
  /* draw(ctx, o): one label into the GIVEN 2D context (CSS-px transform already set).
   *   style  "filament"|"orbit"|"constellation"|"tag"|"whisper" (unknown -> constellation)
   *   name   full project name (seeds per-label variation) · short  text to show (else name)
   *   hex    "#RRGGBB" project colour; absent = an unmanaged (white) sprite: neutral, desaturated
   *   hue    optional degrees, used when hex is absent and the sprite is coloured
   *   x, y, r  creature centre and extent radius (CSS px, as V.report gives them); rt, rb optional top/bottom extents
   *   scale  the Size slider (0.5..2) · t  seconds (any clock) · phase "in"|"hold"|"out" · p  0..1 progress in that phase
   *   ground "bright"|"dark" under the label (SpritesLabels.groundAt) · motes  optional [[x,y],...] creature points
   *   W, H   screen size (for the above/below choice; default 1e4) */
  function draw(ctx, o) { const n = BYKEY[o.style] || BYKEY[DEFAULT], k = Math.sqrt(clamp(+o.scale || 1, 0.5, 2));
    const p = clamp(o.p == null ? 1 : +o.p, 0, 1), ph = o.phase || "hold";
    const e = ph === "in" ? p : ph === "out" ? 1 - p : 1; if (e <= 0) return;
    const hh = hexHue(o.hex), hue = hh != null ? hh : (+o.hue || 0), sk = hh != null || Number.isFinite(o.hue) ? 1 : 0.05;
    const seed = (hash(String(o.name || o.short || "")) % 1000) / 159;
    drawRaw(ctx, n, { name: String(o.short || o.name || ""), hue, sk, x: o.x, y: o.y, r: Math.max(6, o.r || 0), rt: o.rt, rb: o.rb,
      e, out: ph === "out", t: +o.t || 0, seed, pulse: o.pulse || 3.2, ground: o.ground || "dark", motes: o.motes },
      { k, W: o.W || 1e4, H: o.H || 1e4 }); }
  /* Hover state machine (one per creature): track(st, hovered, dt, style) -> st with {phase, p}; st.phase null = nothing to draw. */
  function track(st, hovered, dt, style) { st = st || { phase: null, p: 0 }; const o = OPTIONS[BYKEY[style] || BYKEY[DEFAULT]];
    if (hovered) { if (st.phase === "out") { st.phase = "in"; st.p = 1 - st.p; } else if (!st.phase) { st.phase = "in"; st.p = 0; }
      if (st.phase === "in") { st.p += dt / o.inS; if (st.p >= 1) { st.phase = "hold"; st.p = 1; } } }
    else if (st.phase) { if (st.phase !== "out") { st.p = st.phase === "in" ? 1 - st.p : 0; st.phase = "out"; }
      st.p += dt / o.outS; if (st.p >= 1) { st.phase = null; st.p = 0; } }
    return st; }
  /* Ground under a label (owner ruling 2026-11-01): the stage canvas is transparent and cannot read the pixels behind it, so the
   * window rects are the proxy. Windows arrive FRONT TO BACK (App.swift), so the ground is the first window containing the
   * label box's centre (R1-SPEC S5: a terminal in front of a maximised browser is the terminal's ground): "bright" unless the
   * host flagged it dark (terminal apps, `dark: true`); no window there = the wallpaper = "dark". box = [x, y, w, h]. */
  function groundAt(windows, box) { const cx = box[0] + box[2] / 2, cy = box[1] + box[3] / 2;
    for (const w of windows || []) { if (!w) continue;
      if (cx >= w.x && cx < w.x + w.w && cy >= w.y && cy < w.y + w.h) return w.dark ? "dark" : "bright"; }
    return "dark"; }
  /* The label's box for groundAt: the full extent any style may use (above or below the creature). */
  function labelBox(x, y, r, scale, text) { const k = Math.sqrt(clamp(+scale || 1, 0.5, 2)), w = Math.max(60, String(text || "").length * 9) * k;
    return [x - w / 2 - 8 * k, y - r - 30 * k, w + 16 * k, 2 * r + 60 * k]; }
  root.SpritesLabels = { draw, track, groundAt, labelBox, STYLES, DEFAULT, OPTIONS, drawRaw,
    TITLES: { filament: "Filament", orbit: "Orbit", constellation: "Constellation", tag: "Lantern tag", whisper: "Whisper" } };
})(this);
