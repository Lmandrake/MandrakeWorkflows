/* Visitors prototype runtime: the shared contract every trial piece is built on.
 *
 * A piece is one HTML file that loads, in order:
 *   <script src="timelines.js"></script>
 *   <script src="visitors_runtime.js"></script>
 *   <script> V.piece({ init(V), step(V, S, dt), draw(V, S, ctx) }) </script>
 * plus <script id="COLOPHON" type="application/json">["pulse rate = CPU", ...]</script>
 * (the disclosed mapping, 2-5 short lines; the judging sheet shows it before the clip plays).
 *
 * Determinism: the simulation runs at a fixed 60 Hz step. All randomness MUST come from V.rand()
 * (seeded). step() may integrate state; draw() must only read it. That lets QA call
 * window.__renderAt(t) and get the same frame every time.
 *
 * URL params: brief=a|b|c|d|e|p  variant=1|2  autostart=0|1  legend=0|1
 *             glow, density, drift, sat, size  (multipliers, default 1; the A/B pole pairs use them)
 * Every piece MUST honour all five multipliers:
 *   glow    = halo/bloom intensity        density = lit elements / particles per creature
 *   drift   = idle drift speed            sat     = colour saturation (pass hues through V.hsl)
 *   size    = overall creature scale      (V.P holds them)
 *
 * Messages: parent posts {cmd:'start'}; the piece posts {ev:'ready'}, {ev:'started'}, {ev:'ended'}.
 * QA hooks: window.__renderAt(t) (sync, re-simulates 0..t), window.__report() (positions),
 *           window.__errors (array), window.__fps().
 */
(function () {
"use strict";
// One runtime INSTANCE per piece. Standalone page (gallery, Settings stills): created from the page URL; it owns its
// canvases, loop and window.* QA hooks, exactly as before. Shared mode (app/stage.html, ONE canvas for every species):
// the stage calls VisitorsRuntime.create(params, env) per species, env = {ctx, canvas, post(msg), wake()}, then runs the
// piece factory window.VISITORS_PIECES[name](V). The instance draws into the shared ctx, never clears or schedules it,
// and exposes the QA hooks on V (V.__report, V.__live, ...); the stage's one loop calls V._frame(now).
function createRuntime(q, env) {
  const SHARED = !!env;
  const num = (k, d) => { const v = parseFloat(q.get(k)); return isFinite(v) ? v : d; };
  // Gallery cells: w/h set the stage size, chrome=0 drops menu bar and dock (TOP/BOT margins become 0).
  const W = Math.round(num("w", 1280)), H = Math.round(num("h", 800)), DT = 1 / 60;
  // Live mode (app/stage.html): live=1, no timeline, no backdrop, no HUD; top/bot = menu-bar and Dock margins.
  const LIVE = q.get("live") === "1";
  const CHROME = q.get("chrome") !== "0", TOP = LIVE ? num("top", 0) : CHROME ? 22 : 0, BOT = LIVE ? num("bot", 0) : CHROME ? 70 : 0;
  const P = { glow: num("glow", 1), density: num("density", 1), drift: num("drift", 1),
              sat: num("sat", 1), size: num("size", 1) };
  // Live size (owner, 2026-11-01 04:45): "The sprites you're playing with now are at the largest end of what should be
  // permitted." The slider (0.5..2, default 1) maps to P.size = slider x LIVE_BASE, so 200% = the old live size,
  // 100% = half of it, 50% = a quarter.
  const LIVE_BASE = 0.5;
  if (q.get("live") === "1") P.size *= LIVE_BASE;
  // Size normalisation (owner, 2026-11-07: "for the same memory configuration the stdev of the distribution of pixel
  // distance from its center is roughly equal"). ONE zoom per creature, k = SPRITES_SIZE_NORM[context][species][iv]
  // (prototype/size_norm.js, generated and measured by tools/size_calibrate.py), applied about the creature's reported
  // centre in creature() below, to its reported radius (hits, hover, labels, satellites) and to the radius the runtime's
  // nav/steer keep clear. k never depends on the data, so memory -> area holds within a species exactly as each piece
  // draws it. Context: live=1 -> "live"; Settings passes norm=hero|tile|form; anything else (gallery, trials) -> none.
  const NORM_CTX = q.get("norm") || (LIVE ? "live" : "");
  const SPECIES_ID = q.get("species") || (((typeof location !== "undefined" && location.pathname) || "").match(/(c\d+_\w+)\.html$/) || [])[1] || "";
  const NORM_ROW = (NORM_CTX && window.SPRITES_SIZE_NORM && window.SPRITES_SIZE_NORM[NORM_CTX] && window.SPRITES_SIZE_NORM[NORM_CTX][SPECIES_ID]) || null;
  const sizeK = id => { if (!NORM_ROW) return 1; const s = V.sessions.find(x => x.id === id); const iv = s ? ((Math.round(s.iv || 0) % 8) + 8) % 8 : 0;
    const k = NORM_ROW[iv]; return k > 0 ? k : 1; };
  const brief = q.get("brief") || "a", variant = q.get("variant") || "1";
  const ALL = Object.assign({}, window.VISITORS_TIMELINES || {}, window.VISITORS_SCENARIOS || {});
  const TL = LIVE ? { id: "live", seed: num("seed", 20261031), duration: Infinity, sessions: [], keys: [] }
    : q.get("tl") ? ALL[q.get("tl")] : (ALL[brief + variant] || ALL[brief + "1"]);
  if (!TL) throw new Error("no timeline " + (q.get("tl") || brief + variant));
  // Individualizer: each session carries `iv` (0..7), the variant of its concept's form. Default comes from
  // the timeline; URL iv=3 (all sessions) or iv=0,4,2 (per session index) overrides. Pieces read s.iv.
  { const ivq = q.get("iv"), list = ivq ? ivq.split(",").map(Number) : null;
    TL.sessions.forEach((s, i) => { if (list) s.iv = list.length === 1 ? list[0] : (list[i] ?? s.iv ?? 0);
      if (!Number.isFinite(s.iv)) s.iv = 0;
      if (q.get("hue")) s.hue = parseFloat(q.get("hue")); }); }
  window.__errors = window.__errors || [];
  if (!SHARED) window.addEventListener("error", e => window.__errors.push(String(e.message)));

  // ---------- seeded RNG + noise ----------
  let seed = 0;
  function srand(s) { seed = (s >>> 0) || 1; }
  function rand() { seed = (seed + 0x6D2B79F5) >>> 0; let t = seed;
    t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }
  // smooth value noise, deterministic, no RNG state consumed
  function hash(x, y) { let h = (x * 374761393 + y * 668265263) | 0; h = Math.imul(h ^ (h >>> 13), 1274126177);
    return ((h ^ (h >>> 16)) >>> 0) / 4294967296; }
  function vnoise(x, y) { const xi = Math.floor(x), yi = Math.floor(y), xf = x - xi, yf = y - yi;
    const u = xf * xf * (3 - 2 * xf), v = yf * yf * (3 - 2 * yf);
    const a = hash(xi, yi), b = hash(xi + 1, yi), c = hash(xi, yi + 1), d = hash(xi + 1, yi + 1);
    return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v; }
  // curl of a noise potential: divergence-free drift field (unit-ish magnitude)
  function curl(x, y, t) { const e = 0.01, s = 0.004;
    const f = (X, Y) => vnoise(X * s + t * 0.05, Y * s - t * 0.03);
    const dx = (f(x, y + 1 / s * e) - f(x, y - 1 / s * e)), dy = (f(x + 1 / s * e, y) - f(x - 1 / s * e, y));
    const m = 1 / (2 * e); return [dx * m, -dy * m]; }

  // ---------- timeline sampling ----------
  const DISCRETE = new Set(["state", "vpn"]);
  function lerpObj(a, b, f) { const o = {};
    for (const k in a) { const va = a[k], vb = b && k in b ? b[k] : va;
      if (Array.isArray(va)) o[k] = va.map((x, i) => typeof x === "number" ? x + ((vb[i] ?? x) - x) * f : x);
      else if (typeof va === "object" && va) o[k] = lerpObj(va, vb, f);
      else if (typeof va === "number" && !DISCRETE.has(k)) o[k] = va + (vb - va) * f;
      else o[k] = va; }
    return o; }
  function sample(t) {
    const K = TL.keys; let i = 0;
    while (i < K.length - 1 && K[i + 1].t <= t) i++;
    const a = K[i], b = K[Math.min(i + 1, K.length - 1)];
    const span = b.t - a.t, f = span > 0 ? Math.min(1, Math.max(0, (t - a.t) / span)) : 0;
    const ff = f * f * (3 - 2 * f);
    const st = lerpObj(a, b, ff);
    // discrete fields switch at the NEXT key's time, not before
    for (const id in a.s) { st.s[id].state = (t >= b.t && b.s[id]) ? b.s[id].state : a.s[id].state; }
    st.net.vpn = (t >= b.t ? b.net.vpn : a.net.vpn);
    st.net.strain = st.net.strain || 0;
    { const ids = Object.keys(st.s), share = (st.net.mbps || 0) / Math.max(1, ids.length);
      for (const id of ids) { const x = st.s[id]; if (x.rx == null) { x.rx = share * 0.8; x.tx = share * 0.2; } } }
    return st; }

  // ---------- canvases ----------
  let stage = null;
  if (!SHARED) {
    document.documentElement.style.cssText = "margin:0;height:100%;background:" + (LIVE ? "transparent" : "#000");
    document.body.style.cssText = "margin:0;height:100%;overflow:hidden;background:" + (LIVE ? "transparent" : "#05070a");
    stage = document.createElement("div");
    stage.style.cssText = `position:absolute;left:0;top:0;width:${W}px;height:${H}px;transform-origin:0 0`;
    document.body.appendChild(stage); }
  const dpr = num("dpr", Math.min(2, window.devicePixelRatio || 1));
  function mk(z) { const c = document.createElement("canvas"); const tiny = LIVE && z === 0;   // live: no backdrop canvas
    c.width = tiny ? 1 : W * dpr; c.height = tiny ? 1 : H * dpr;
    c.style.cssText = `position:absolute;left:0;top:0;width:${W}px;height:${H}px;z-index:${z}`; stage.appendChild(c);
    const x = c.getContext("2d"); x.setTransform(dpr, 0, 0, dpr, 0, 0); return [c, x]; }
  const [bgC, bg] = SHARED ? [null, null] : mk(0);
  const [fgC, ctx] = SHARED ? [env.canvas, env.ctx] : mk(1);
  // Per-creature opacity (arrivals, departures, ghosts): while V.creature(id, fn) runs, every globalAlpha the piece sets
  // is multiplied by that creature's alpha. Reading globalAlpha returns the piece's own value. The accessor reads the
  // state of whichever instance is drawing (ctx.__aS, swapped by the stage), so instances sharing one ctx stay separate.
  const AS = { mul: 1, raw: 1 };
  if (!Object.prototype.hasOwnProperty.call(ctx, "__aS")) {
    const d = Object.getOwnPropertyDescriptor(CanvasRenderingContext2D.prototype, "globalAlpha");
    Object.defineProperty(ctx, "globalAlpha", { configurable: true, get() { return this.__aS.raw; },
      set(v) { const a = this.__aS; a.raw = v; if (this.__flush) this.__flush(); d.set.call(this, Math.max(0, Math.min(1, v)) * a.mul); } }); }
  ctx.__aS = AS;
  let skipDraw = false;   // shared mode: the stage steps without drawing while nothing is visible
  function creature(id, fn) { const m = LIVE ? alphaOf(id) : 1, s = V.sessions.find(x => x.id === id);
    V.cur = s || null; if (m <= 0.004) { V.cur = null; return; }
    const pm = AS.mul, o = pull[id]; AS.mul = m; ctx.globalAlpha = AS.raw; if (o) ctx.translate(o[0], o[1]);
    // size normalisation: zoom by k about the creature's own centre (its last report, before any hover pull)
    const k = sizeK(id), rc = k !== 1 ? reports[id] : null;
    if (rc) { ctx.translate(rc.bx, rc.by); ctx.scale(k, k); ctx.translate(-rc.bx, -rc.by); }
    try { fn(); } finally { if (rc) { ctx.translate(rc.bx, rc.by); ctx.scale(1 / k, 1 / k); ctx.translate(-rc.bx, -rc.by); }
      if (o) ctx.translate(-o[0], -o[1]); AS.mul = pm; ctx.globalAlpha = AS.raw; V.cur = null; } }
  // a piece's own point for creature id (running lights, hover motes), moved as creature() zooms it
  const zoomPt = (id, p) => { const k = sizeK(id), r = reports[id]; return k === 1 || !r ? p : [r.bx + (p[0] - r.bx) * k, r.by + (p[1] - r.by) * k]; };
  function fit() { if (SHARED) return; const s = Math.min(innerWidth / W, innerHeight / H);
    stage.style.transform = `translate(${(innerWidth - W * s) / 2}px,${(innerHeight - H * s) / 2}px) scale(${s})`; }
  if (!SHARED) { addEventListener("resize", fit); fit(); }

  const img = new Image(); let imgOk = false;
  img.onload = () => { imgOk = true; drawBg(lastFocus); }; if (!LIVE) img.src = "desktop_blur.png";
  let lastFocus = null;
  const noBg = q.get("bg") === "0";   // QA: creatures only, on black, to measure coverage/visibility
  function drawBg(f) {
    if (LIVE) return;
    bg.clearRect(0, 0, W, H);
    if (noBg) { bg.fillStyle = "#000"; bg.fillRect(0, 0, W, H); return; }
    if (imgOk) { const s = Math.max(W / img.width, H / img.height);
      bg.drawImage(img, (W - img.width * s) / 2, (H - img.height * s) / 2, img.width * s, img.height * s); }
    else { const g = bg.createLinearGradient(0, 0, W, H); g.addColorStop(0, "#1a2433"); g.addColorStop(1, "#2b1f2e");
      bg.fillStyle = g; bg.fillRect(0, 0, W, H); }
    bg.fillStyle = `rgba(0,0,0,${num("dim", 0.38)})`; bg.fillRect(0, 0, W, H);
    // menu bar
    if (CHROME) { bg.fillStyle = "rgba(20,20,24,0.55)"; bg.fillRect(0, 0, W, 22); }
    if (f) { const [x, y, w, h] = f;
      bg.save(); bg.shadowColor = "rgba(0,0,0,0.6)"; bg.shadowBlur = 30;
      bg.fillStyle = "rgba(28,30,36,0.92)"; roundRect(bg, x, y, w, h, 10); bg.fill(); bg.restore();
      bg.fillStyle = "rgba(48,50,58,0.95)"; roundRect(bg, x, y, w, 28, 10); bg.fill(); bg.fillRect(x, y + 18, w, 10);
      ["#ff5f57", "#febc2e", "#28c840"].forEach((c, i) => { bg.fillStyle = c; bg.beginPath(); bg.arc(x + 16 + i * 20, y + 14, 6, 0, 7); bg.fill(); });
      bg.fillStyle = "rgba(200,205,215,0.18)";
      for (let r = 0; r < Math.floor((h - 60) / 22); r++) bg.fillRect(x + 24, y + 48 + r * 22, (w - 48) * (0.4 + 0.55 * hash(r, 7)), 8);
    }
    // dock
    if (CHROME) { bg.fillStyle = "rgba(255,255,255,0.10)"; roundRect(bg, W / 2 - 260, H - 58, 520, 50, 14); bg.fill(); }
  }
  function roundRect(c, x, y, w, h, r) { c.beginPath(); c.moveTo(x + r, y); c.arcTo(x + w, y, x + w, y + h, r);
    c.arcTo(x + w, y + h, x, y + h, r); c.arcTo(x, y + h, x, y, r); c.arcTo(x, y, x + w, y, r); c.closePath(); }

  // ---------- helpers exposed to pieces ----------
  function hsl(h, s, l, a = 1) { if (V.cur && V.cur.white) s *= 0.06;
    return `hsla(${h},${Math.max(0, Math.min(100, s * P.sat))}%,${l}%,${a})`; }
  function avoid(x, y, margin = 60) { // repulsion from focused window, menu bar, dock; returns [fx, fy]
    let fx = 0, fy = 0; const f = on("avoidFocus") ? lastFocus : null;
    if (f) { const [rx, ry, rw, rh] = f; const cx = Math.max(rx, Math.min(x, rx + rw)), cy = Math.max(ry, Math.min(y, ry + rh));
      let dx = x - cx, dy = y - cy, d = Math.hypot(dx, dy);
      if (d === 0) { dx = x - (rx + rw / 2); dy = y - (ry + rh / 2); d = 1e-3;
        const w = navLast && Math.abs(navLast.x - x) < 0.5 && Math.abs(navLast.y - y) < 0.5 && navLast.f === V.frame ? navLast : null;
        if (w) { fx += w.ux * 3; fy += w.uy * 3; }   // R1-SPEC S3: a travelling plan leads out; push along it, not at the nearest edge
        else { const ex = Math.min(x - rx, rx + rw - x), ey = Math.min(y - ry, ry + rh - y);   // inside: push to nearest edge
          if (ex < ey) { fx += Math.sign(dx) * 3; } else { fy += Math.sign(dy) * 3; } } }
      else if (d < margin) { const n = needLast && Math.abs(needLast.x - x) < 0.5 && Math.abs(needLast.y - y) < 0.5 && needLast.f === V.frame ? needLast.k : 0;
        const k = (1 - d / margin) * 2 * (1 - 2 * n); fx += dx / d * k; fy += dy / d * k; } }   // nudgeLongWait: the edge push fades as the nudge grows
    if (LIVE && cursor && on("avoidCursor") && !isHoveredAt(x, y)) { const dx = x - cursor[0], dy = y - cursor[1], d = Math.hypot(dx, dy) || 1e-3,
        R = margin + 90 * Math.sqrt(Math.max(0.25, P.size)), shy = performance.now() - cursorMovedAt < 800 ? 1.25 : 0.8;   // weaker than the focused window
      if (d < R) { const k = (1 - d / R) * shy; fx += dx / d * k; fy += dy / d * k; } }
    const edge = 40; if (x < edge) fx += (1 - x / edge); if (x > W - edge) fx -= (1 - (W - x) / edge);
    if (y < TOP + edge) fy += (1 - (y - TOP) / edge); if (y > H - BOT - edge) fy -= (1 - (H - BOT - y) / edge);
    return [fx, fy]; }
  function insideFocus(x, y, r = 0) { const f = on("avoidFocus") ? lastFocus : null; if (!f) return false; const [rx, ry, rw, rh] = f;
    return x + r > rx && x - r < rx + rw && y + r > ry && y - r < ry + rh; }

  let reports = {};
  const V = {
    W, H, TOP, BOT, DT, P, TL, brief, variant, rand, srand, vnoise, curl, hsl, avoid, insideFocus,
    sessions: TL.sessions, t: 0, frame: 0, LIVE,
    huddlePt: null,                       // live: ONE shared VPN-huddle point for every species (stage picks open space)
    on: k => on(k),                       // behaviour switch (live: Settings; default ON; gallery: always on)
    alpha: id => alphaOf(id), lightCount: d => lightCount(d), nav: (id, x, y, tx, ty, r) => nav(id, x, y, tx, ty, (r || 30) * sizeK(id)), navNeed: (id, x, y, tx, ty, r) => navNeed(id, x, y, tx, ty, (r || 30) * sizeK(id)), creature: (id, fn) => creature(id, fn), cur: null,
    sizeK: id => sizeK(id),               // the size-normalisation zoom of creature id (1 when no table/context applies)
    isWhite: id => { const s = V.sessions.find(x => x.id === id); return !!(s && s.white); },
    isGhost: id => { const s = V.sessions.find(x => x.id === id); return !!(s && s.ghost); },             // arrival/departure/ghost opacity for a creature, multiply into its draw
    steer: (id, tx, ty, r) => steer(id, tx, ty, (r || 30) * sizeK(id)),   // live: blend the behaviour targets into a home target
    // the reconnect bloom fires on LOST -> OK only (SHIP_PLAN; R1 #7): a lost -> at risk or lost -> none edge also turns
    // vpn "down" to "up" but is no reconnect. No link field (gallery timelines) = the old vpn edge alone.
    reconnected: net => !net || net.link == null || net.link === "ok",
    LEVELS: ["light", "medium", "high", "danger"],
    // Constellation labels: a piece may hand over up to ~40 screen points it draws for a creature (V.motes(id, pts));
    // kept only for the hovered one, shifted by its hover pull
    motes(id, pts) { if (id !== hoverId || !Array.isArray(pts)) return; motePts[id] = pts.slice(0, 40); },
    report(id, x, y, r) { const o = pull[id]; r *= sizeK(id); reports[id] = o ? { x: x + o[0], y: y + o[1], r, bx: x, by: y } : { x, y, r, bx: x, by: y }; },  // once per frame per session
    piece(def) { V._def = def; boot(); },
    _alpha: AS,                           // shared mode: this instance's globalAlpha state (the stage sets ctx.__aS to it)
  };
  if (!SHARED) window.V = V;
  const post = m => SHARED ? env.post(m) : parent.postMessage(m, "*");

  // ---------- live mode (app/stage.html drives it with postMessage {cmd:"live", ...}) ----------
  // Sessions arrive as [{id, hue, iv, name, label, pid, white, ghost}] and state as S {s:{id:{...}}, m, net, focus, play}.
  // Absent fields are filled with CALM values here (never a measured zero), flagged in S.s[id]._absent.
  const B = {};
  function on(k) { return !LIVE || B[k] !== false; }
  let cursor = null, cursorMovedAt = 0, cursorRestAt = 0, activity = { typing: false, idleSec: 0 }, windows = [];
  let demoMode = false, beaconOwner = false, vpnA = 0, riskA = 0;
  let liveS = null, liveFirst = true, paused = false, sizeTarget = P.size, lastHits = 0, wake = 1;
  const born = {}, leaving = {}, lastData = {}, prevState = {}, flares = [], steerSt = {}, greets = [];
  let lastFlare = -99;
  const CALM = { cpu: 0.05, mem: 0.6, procs: 1, state: "idle", rx: 0, tx: 0 };
  function normS(raw, sessions) {
    raw = raw || {}; const out = { s: {}, m: Object.assign({ level: 0, thermal: 0, mempress: 0 }, raw.m || {}),
      net: Object.assign({ mbps: 0, vpn: "up", loss: 0, strain: 0 }, raw.net || {}),
      focus: raw.focus || null, play: raw.play || { pair: ["", ""], amt: 0 } };
    // avoidFocus off: no focused window for layout either, unless someone needs you and needsApproach is on
    if (!on("avoidFocus") && !(on("needsApproach") && Object.values(raw.s || {}).some(d => d && d.state === "needs"))) out.focus = null;
    for (const k in out.m) if (!Number.isFinite(out.m[k])) out.m[k] = 0;
    for (const k of ["mbps", "loss", "strain"]) if (!Number.isFinite(out.net[k])) out.net[k] = 0;
    for (const ss of sessions) { const d = (raw.s || {})[ss.id] || lastData[ss.id] || {}, o = {}, ab = [];
      for (const k in CALM) { const v = d[k]; if (k === "state" ? typeof v === "string" : Number.isFinite(v)) o[k] = v; else { o[k] = CALM[k]; ab.push(k); } }
      if (ss.ghost || leaving[ss.id]) { o.cpu = 0.02; o.state = "idle"; o.rx = 0; o.tx = 0; o.procs = 0; }
      if (o.state !== "working" && o.state !== "needs") o.state = "idle";
      for (const k in d) if (!(k in CALM)) o[k] = d[k];   // burning, needSec, ... pass through
      o._absent = ab; out.s[ss.id] = o; }
    return out; }
  const sig = list => list.map(s => [s.id, s.hue, s.iv, s.white ? 1 : 0, s.ghost ? 1 : 0, s.slot, s.slots].join(":")).join("|");
  function membership(list) {   // re-init on any change of who is on stage; positions carried by id
    const now = V.t, ids = new Set(list.map(s => s.id));
    for (const s of V.sessions) if (!ids.has(s.id) && !leaving[s.id] && on("arrivals") && !liveFirst) leaving[s.id] = { t: now, s };
    for (const id in leaving) if (ids.has(id) || now - leaving[id].t > 1.6) delete leaving[id];
    const full = list.concat(Object.values(leaving).map(l => l.s));
    for (const s of list) if (!(s.id in born)) born[s.id] = liveFirst || !on("arrivals") ? -99 : now;
    for (const id in born) if (!full.some(s => s.id === id)) delete born[id];
    const keep = new Set(full.map(s => s.id));   // review R1 #18: per-id state of departed sessions is dropped
    for (const M of [lastData, prevState, steerSt, navA, navVis, pull, motePts]) for (const id in M) if (!keep.has(id)) delete M[id];
    for (const id of [...navPlan.keys()]) if (!keep.has(id)) navPlan.delete(id);
    if (sig(full) === sig(V.sessions)) return false;
    const prev = {}; for (const id in reports) prev[id] = Object.assign({}, reports[id]);
    V.sessions = full; TL.sessions = full; reports = {};
    S = normS(liveS, full); S.T = simT; S.tData = simT; lastFocus = S.focus;
    if (full.length) { V._def.init && V._def.init(V, S); if (V._def.carry) V._def.carry(V, S, prev); }
    return true; }
  const navA = {};
  function alphaOf(id) { if (!LIVE) return 1; const s = V.sessions.find(x => x.id === id); let a = 1;
    if (navA[id] != null) a *= navA[id];
    if (born[id] > -99) a *= Math.min(1, Math.max(0, (V.t - born[id]) / 1.5));
    if (leaving[id]) a *= Math.max(0, 1 - (V.t - leaving[id].t) / 1.5);
    if (s && s.ghost) a *= 0.3;
    return a * a * (3 - 2 * a) || 0; }
  // A home target, blended toward whatever the switched-on behaviours want. Never toward the inside of the focused window.
  function steer(id, tx, ty, r) {
    if (!LIVE) return [tx, ty];
    const s = V.sessions.find(x => x.id === id), d = S && S.s[id]; if (!s || !d) return [tx, ty];
    if (S.net.vpn === "down" && on("vpnHuddle") && !s.ghost) return [tx, ty];   // the huddle wins over every steer
    const rk = s.ghost || !V.huddlePt ? 0 : 0.22 * riskA;   // at risk: the flock is drawn in slightly toward the beacon
    if (rk > 0.001) { tx += (V.huddlePt[0] - tx) * rk; ty += (V.huddlePt[1] - ty) * rk; }
    const st = steerSt[id] || (steerSt[id] = { x: tx, y: ty, b: 0, perchT: -1, perchAt: 30 + 90 * hash(id.length, id.charCodeAt(0) | 0), perch: null, greet: null });
    let gx = tx, gy = ty, want = 0; const now = V.t;
    if (s.ghost) {   // ghost visitor: faint, almost still, in a spot NO window covers (ghostSpots), one slot each
      const k = Number.isFinite(s.slot) ? s.slot : V.sessions.filter(x => x.ghost).indexOf(s), nk = s.slots || 1;
      const sp = ghostSpots(nk, r)[k] || [W - r - 18, TOP + (H - TOP - BOT) * (k + 1) / (nk + 1)];
      gx = sp[0]; gy = sp[1]; want = 1; }
    else if (d.state === "needs") { }   // nudgeLongWait lives in navNeed (every piece routes its knock spot through it)
    else {
      const g = greets.find(q => q.who === id && now < q.until);
      if (g && on("greetNewcomers")) { const dx = g.x - tx, dy = g.y - ty, dd = Math.hypot(dx, dy) || 1, go = Math.max(0, dd - r - 120);
        gx = tx + dx / dd * go; gy = ty + dy / dd * go; want = 0.7; }
      else if (activity.typing && on("edgeWhileTyping")) { gx = tx < W / 2 ? Math.max(r + 12, W * 0.06) : Math.min(W - r - 12, W * 0.94); gy = ty; want = 0.7; }
      else if (cursor && on("curiosity") && d.state === "idle" && cursorRestAt && now - cursorRestAt > 2 && now - cursorRestAt < 9 && curious() === id) {
        const dx = cursor[0] - tx, dy = cursor[1] - ty, dd = Math.hypot(dx, dy) || 1, go = Math.max(0, dd - r - 110);
        gx = tx + dx / dd * go * 0.6; gy = ty + dy / dd * go * 0.6; want = 0.8; }
      else {
        const own = on("followOwnWindow") && s.pid ? windows.find(w => w.sessionPid === s.pid) : null;
        if (on("perch") && d.state === "idle") {
          if (!st.perch && now > st.perchAt) { st.perchAt = now + 70 + 80 * V.rand();
            const f = lastFocus, cands = windows.filter(w => w.w > 3 * r && w.y > TOP + 2 * r && !(f && w.x === f[0] && w.y === f[1]));
            const w = cands.length ? cands[Math.floor(V.rand() * cands.length)] : null;
            if (w) { const px = w.x + w.w * (0.2 + 0.6 * V.rand()), py = w.y - r * 0.9;
              if (!(f && px + r > f[0] && px - r < f[0] + f[2] && py + r > f[1] && py - r < f[1] + f[3])) st.perch = [px, py, now + 18 + 10 * V.rand()]; } }
          if (st.perch && now > st.perch[2]) st.perch = null; }
        else st.perch = null;
        if (st.perch) { gx = st.perch[0]; gy = st.perch[1]; want = 0.85; }
        else if (own) { const room = W - (own.x + own.w), sx = room > 2 * r + 30 ? own.x + own.w + r + 20 : own.x - r - 20;
          gx = Math.max(r, Math.min(W - r, sx)); gy = Math.max(TOP + r, Math.min(H - BOT - r, own.y + r + 30)); want = 0.45; } } }
    st.b += (want - st.b) * Math.min(1, lastDt / 1.2);   // ease in and out, never a jump
    if (want > 0) { st.x = gx; st.y = gy; }
    return [tx + (st.x - tx) * st.b, ty + (st.y - ty) * st.b]; }
  // Spots for n ghosts: candidates along all four screen edges (inset by the creature), scored by how far they are
  // from every on-screen window (setWindows) and the focused window; uncovered spots win, then they spread out. All
  // layers compute the same list from the same windows, so slot k means the same spot in every layer.
  let gsKey = "", gsOut = [];
  function ghostSpots(n, r) {
    const key = n + "|" + Math.round(r / 8) + "|" + windows.map(w => [w.x, w.y, w.w, w.h].join()).join(";") + "|" + (lastFocus || []).join();
    if (key === gsKey) return gsOut; gsKey = key;
    const rr = Math.max(r, 24), dockR = on("avoidDockMenu") ? 90 : 18, x0 = rr + 18, x1 = W - rr - dockR, y0 = TOP + rr + 8, y1 = H - BOT - rr - 8;
    const rects = windows.map(w => [w.x, w.y, w.w, w.h]); if (lastFocus) rects.push(lastFocus);
    const clear = (x, y) => { let m = 1e9; for (const [rx, ry, rw, rh] of rects) {
        const dx = Math.max(rx - x, 0, x - (rx + rw)), dy = Math.max(ry - y, 0, y - (ry + rh));
        m = Math.min(m, (dx || dy) ? Math.hypot(dx, dy) : -Math.min(x - rx, rx + rw - x, y - ry, ry + rh - y)); } return m; };
    const c = [], st = 24;
    for (let y = y0; y <= y1; y += st) { c.push([x1, y]); c.push([x0, y]); }
    for (let x = x0; x <= x1; x += st) { c.push([x, y0]); c.push([x, y1]); }
    c.forEach(p => { p[2] = clear(p[0], p[1]); });
    const out = [];
    for (let i = 0; i < n; i++) { let best = null, bs = -1e18;
      for (const p of c) { let sep = 1e9; for (const o of out) sep = Math.min(sep, Math.hypot(p[0] - o[0], p[1] - o[1]));
        const sc = Math.min(p[2], rr + 40) * 4 + Math.min(sep, 6 * rr) + (p[0] === x1 ? 20 : 0);   // uncovered first, then spread; prefer right
        if (sc > bs) { bs = sc; best = p; } }
      out.push(best); }
    gsOut = out; return out; }
  // ---------- movement and terrain (owner rulings 2026-11-01, SHIP_PLAN "Movement and terrain") ----------
  // A coarse cost grid over the visible frame: desktop background cheapest, other windows medium, the focused window
  // expensive. Clearance maps (distance to the frame edge, to the focused window) give FIT: a creature may rest only
  // where its whole extent fits. V.nav(id, x, y, tx, ty, r) turns a piece's desired target into a reachable, fitting
  // goal and returns the next waypoint on the min-cost path (around the focused window, never across it while a way
  // round exists). An unchanged target that already fits and is reachable in a straight line is returned as is, so
  // ordinary motion looks exactly as the piece drew it. No spot fits anywhere = the creature fades out on this Space.
  const CELL = 24; let visRect = null, grid = null, gridKey = "";
  function buildGrid() {
    const vr = visRect || [0, TOP, W, H - TOP - BOT], f = on("avoidFocus") ? lastFocus : null;
    const key = vr.join() + "|" + (f || []).join() + "|" + windows.map(w => [w.x, w.y, w.w, w.h].join()).join(";") + "|" + W + "x" + H;
    if (grid && key === gridKey) return grid; gridKey = key;
    const nx = Math.ceil(W / CELL), ny = Math.ceil(H / CELL), N = nx * ny, cost = new Float32Array(N), wall = new Uint8Array(N), foc = new Uint8Array(N);
    const inR = (x, y, r) => r && x >= r[0] && x < r[0] + r[2] && y >= r[1] && y < r[1] + r[3];
    for (let j = 0; j < ny; j++) for (let i = 0; i < nx; i++) { const k = j * nx + i, x = (i + 0.5) * CELL, y = (j + 0.5) * CELL;
      if (!inR(x, y, vr)) { wall[k] = 1; cost[k] = 1e9; continue; }
      if (f && inR(x, y, f)) { foc[k] = 1; cost[k] = 60; continue; }
      cost[k] = windows.some(w => inR(x, y, [w.x, w.y, w.w, w.h])) ? 3 : 1; }
    const dt = src => { const d = new Float32Array(N); for (let k = 0; k < N; k++) d[k] = src[k] ? 0 : 1e9;   // chamfer distance (px)
      const a = CELL, b = CELL * 1.414;
      for (let j = 0; j < ny; j++) for (let i = 0; i < nx; i++) { const k = j * nx + i; let v = d[k];
        if (i > 0) v = Math.min(v, d[k - 1] + a); if (j > 0) { v = Math.min(v, d[k - nx] + a); if (i > 0) v = Math.min(v, d[k - nx - 1] + b); if (i < nx - 1) v = Math.min(v, d[k - nx + 1] + b); } d[k] = v; }
      for (let j = ny - 1; j >= 0; j--) for (let i = nx - 1; i >= 0; i--) { const k = j * nx + i; let v = d[k];
        if (i < nx - 1) v = Math.min(v, d[k + 1] + a); if (j < ny - 1) { v = Math.min(v, d[k + nx] + a); if (i < nx - 1) v = Math.min(v, d[k + nx + 1] + b); if (i > 0) v = Math.min(v, d[k + nx - 1] + b); } d[k] = v; }
      return d; };
    // edge clearance: the outside of the frame counts as wall (cells beyond the grid are wall too)
    const cw = dt(wall); for (let j = 0; j < ny; j++) for (let i = 0; i < nx; i++) { const k = j * nx + i, x = (i + 0.5) * CELL, y = (j + 0.5) * CELL;
      cw[k] = Math.min(cw[k], x - vr[0], vr[0] + vr[2] - x, y - vr[1], vr[1] + vr[3] - y); }
    grid = { nx, ny, cost, wall, foc, cw, cf: f ? dt(foc) : null, ver: (grid ? grid.ver : 0) + 1 }; navPlan.clear(); return grid; }
  function bestCost(g, r) {   // cheapest terrain anywhere that fits this radius (cached per radius bucket)
    const b = Math.round(r / 8); g.bc = g.bc || {}; if (b in g.bc) return g.bc[b]; let m = 1e9;
    for (let k = 0; k < g.cost.length; k++) if (fitsAt(g, k, r) && g.cost[k] < m) m = g.cost[k]; return (g.bc[b] = m); }
  const fitsAt = (g, k, r) => !g.wall[k] && !g.foc[k] && g.cw[k] >= r && (!g.cf || g.cf[k] >= r + 8);
  const cellOf = (g, x, y) => Math.max(0, Math.min(g.ny - 1, Math.floor(y / CELL))) * g.nx + Math.max(0, Math.min(g.nx - 1, Math.floor(x / CELL)));
  function dijkstra(g, start, clr) {   // clr: cells nearer the focus than this (px, chamfer) cost extra, so paths keep the disc off it
    const N = g.nx * g.ny, d = new Float32Array(N).fill(1e12), par = new Int32Array(N).fill(-1), done = new Uint8Array(N); d[start] = 0;
    // binary heap on typed arrays (no per-entry allocation)
    const HK = new Float64Array(N * 8 + 8), HV = new Int32Array(N * 8 + 8); let hn = 0;
    const push = (key, v) => { let i = hn++; HK[i] = key; HV[i] = v; while (i) { const p = (i - 1) >> 1; if (HK[p] <= HK[i]) break;
        const tk = HK[p]; HK[p] = HK[i]; HK[i] = tk; const tv = HV[p]; HV[p] = HV[i]; HV[i] = tv; i = p; } };
    const pop = () => { const v = HV[0]; hn--; HK[0] = HK[hn]; HV[0] = HV[hn]; let i = 0; for (;;) { const a = 2 * i + 1, b = a + 1; let m = i;
        if (a < hn && HK[a] < HK[m]) m = a; if (b < hn && HK[b] < HK[m]) m = b; if (m === i) break;
        const tk = HK[m]; HK[m] = HK[i]; HK[i] = tk; const tv = HV[m]; HV[m] = HV[i]; HV[i] = tv; i = m; } return v; };
    push(0, start);
    while (hn > 0 && hn < HK.length - 9) { const k = pop(); if (done[k]) continue; done[k] = 1; const dk = d[k], i = k % g.nx, j = (k / g.nx) | 0;
      for (let dj = -1; dj <= 1; dj++) for (let di = -1; di <= 1; di++) { if (!di && !dj) continue; const ii = i + di, jj = j + dj;
        if (ii < 0 || jj < 0 || ii >= g.nx || jj >= g.ny) continue; const q = jj * g.nx + ii; if (g.wall[q]) continue;
        if (g.foc[q] && !g.foc[k]) continue;   // the focused window is one-way: you may leave it, never enter or cross it
        const nd = dk + (di && dj ? 1.414 : 1) * CELL * ((g.cost[k] + g.cost[q]) / 2 + (clr && g.cf && !g.foc[q] && g.cf[q] < clr ? 30 : 0)); if (nd < d[q]) { d[q] = nd; par[q] = k; push(nd, q); } } }
    return { d, par }; }
  // Straight segment avoids ENTERING the focused window (cell test, every half cell). One-way, as in dijkstra: a segment
  // that starts inside the focus may run out of it (leaving is the point), but never back in (R1-SPEC S3: testing every
  // cell made each waypoint of a creature inside the focus the very next cell, so it crawled out at ~12 px/s).
  function segClear(g, x0, y0, x1, y1) {
    const n = Math.ceil(Math.hypot(x1 - x0, y1 - y0) / (CELL / 2)); let out = false;
    for (let s = 0; s <= n; s++) { const u = n ? s / n : 0, f = g.foc[cellOf(g, x0 + (x1 - x0) * u, y0 + (y1 - y0) * u)];
      if (!f) { if (!g.wall[cellOf(g, x0 + (x1 - x0) * u, y0 + (y1 - y0) * u)]) out = true; } else if (out) return false; } return true; }
  function nearestOpen(g, x, y) { let b = -1, bd = 1e18;   // nearest cell inside the visible frame (wall-band starts)
    for (let k = 0; k < g.wall.length; k++) { if (g.wall[k]) continue; const cx = (k % g.nx + 0.5) * CELL, cy = ((k / g.nx | 0) + 0.5) * CELL,
      dd = (cx - x) * (cx - x) + (cy - y) * (cy - y); if (dd < bd) { bd = dd; b = k; } } return b; }
  const navPlan = new Map(), navVis = {}; let navLast = null, needLast = null;   // needLast: the nudgeLongWait level of the last navNeed call; navLast: the travelling waypoint direction of the last nav call (for avoid)
  function nav(id, x, y, tx, ty, r, strict) {
    if (!LIVE) return [tx, ty];
    const g = buildGrid(), rr = r + 10, ks = cellOf(g, x, y), kt = cellOf(g, tx, ty);
    // straight line clear: no focus cell on it; strict (needs-you): the whole hit disc stays off the focus along it
    const line = (ax, ay, bx, by) => segClear(g, ax, ay, bx, by) && (!strict || g.foc[ks] || discClear(lastFocus, ax, ay, bx, by, hitR(id, r) + 2));
    // 1. the common case: target fits, terrain is not worse than where we are, straight line clear -> untouched
    const okT = fitsAt(g, kt, rr) && g.cost[kt] <= bestCost(g, rr) && line(x, y, tx, ty);
    let pl = navPlan.get(id);
    if (okT && !(pl && pl.travel)) { navVis[id] = 1; return [tx, ty]; }
    // 2. (re)plan: Dijkstra from here; goal = fitting cell minimising terrain + distance to the wanted target + path cost
    if (!pl || pl.ver !== g.ver || Math.hypot(pl.tx - tx, pl.ty - ty) > 4 * CELL || Math.abs(pl.r - rr) > 12 || V.t - pl.at > 2) {
      // R1-SPEC S2: a creature whose centre lies in the wall band (menu bar, Dock, off the frame) has only wall or focus
      // neighbours, so a search seeded at its own cell reached nothing and "unreachable" read as "no room". Seed from the
      // nearest non-wall cell instead; and only when NO cell fits anywhere is it "no room". Fitting cells that are all
      // unreachable (a sealed pocket) fall back to the nearest fitting cell, straight.
      const k0 = g.wall[ks] ? nearestOpen(g, x, y) : ks, { d, par } = dijkstra(g, k0 < 0 ? ks : k0, hitR(id, r) + CELL); let best = -1, bs = 1e18, any = -1, ad = 1e18;
      for (let k = 0; k < d.length; k++) { if (!fitsAt(g, k, rr)) continue;
        if (d[k] > 1e11) { const cx = (k % g.nx + 0.5) * CELL, cy = ((k / g.nx | 0) + 0.5) * CELL, dd = Math.hypot(cx - tx, cy - ty) + Math.hypot(cx - x, cy - y);
          if (dd < ad) { ad = dd; any = k; } continue; }
        const cx = (k % g.nx + 0.5) * CELL, cy = ((k / g.nx | 0) + 0.5) * CELL;
        // closeness to the wanted target dominates; path cost breaks ties (so a reachable target is reached, the long
        // way round the focus if need be); window terrain is avoided when background is available
        const sc = (g.cost[k] - 1) * 1500 + 1.5 * Math.hypot(cx - tx, cy - ty) + 0.25 * d[k] + (g.cf ? Math.max(0, 100 - g.cf[k]) : 0);
        if (sc < bs) { bs = sc; best = k; } }
      if (best < 0) best = any;
      const path = []; for (let k = best; k >= 0 && k !== ks; k = par[k]) path.push(k); path.reverse();
      pl = { ver: g.ver, kt, tx, ty, r: rr, at: V.t, goal: best, path, travel: best >= 0 && (best !== kt || !okT) }; navPlan.set(id, pl); }
    if (pl.goal < 0) { navVis[id] = 0; return [x, y]; }            // nothing fits anywhere: fade out in place
    navVis[id] = 1;
    const gx = (pl.goal % g.nx + 0.5) * CELL, gy = ((pl.goal / g.nx | 0) + 0.5) * CELL;
    if (Math.hypot(gx - x, gy - y) < CELL * 1.5) { pl.travel = false;
      return fitsAt(g, kt, rr) && g.cost[kt] <= bestCost(g, rr) && line(x, y, tx, ty) ? [tx, ty] : [gx, gy]; }
    // next waypoint: the farthest path cell (up to ~6 cells on) reachable in a straight line that avoids the focus
    let wx = gx, wy = gy;
    for (let i = Math.min(pl.path.length - 1, 6); i >= 0; i--) { const k = pl.path[i], cx = (k % g.nx + 0.5) * CELL, cy = ((k / g.nx | 0) + 0.5) * CELL;
      if (i === 0 || (segClear(g, x, y, cx, cy) && (g.foc[ks] || discClear(lastFocus, x, y, cx, cy, hitR(id, r) + 12)))) { wx = cx; wy = cy; break; } }
    { const ux = wx - x, uy = wy - y, m = Math.hypot(ux, uy) || 1; navLast = { x, y, ux: ux / m, uy: uy / m, f: V.frame }; }
    // drop path cells already passed
    while (pl.path.length > 1) { const k = pl.path[0], cx = (k % g.nx + 0.5) * CELL, cy = ((k / g.nx | 0) + 0.5) * CELL; if (Math.hypot(cx - x, cy - y) < CELL) pl.path.shift(); else break; }
    return [wx, wy]; }
  // Needs-you approach (R1-SPEC S1, S8). The piece's knock spot sits just outside the focused window, closer than FIT
  // allows, so it is not snapped to a cell: when the straight run to it keeps the creature's disc off the focus, it is
  // returned as is (the knock wobble passes through); otherwise the min-cost path round the focus leads to the fitting
  // cell nearest the spot, until the straight run clears. nudgeLongWait (> 10 min) moves the spot closer each minute:
  // the edge gap shrinks by k = 8 % per minute up to 50 %, never below 6 px (hard cap, never touching).
  const hitR = (id, r) => Math.max(18, r, reports[id] ? reports[id].r : 0);   // the disc postHits reports, max(18, r)
  function discClear(f, x0, y0, x1, y1, r) { if (!f) return true; const [rx, ry, rw, rh] = f, n = Math.ceil(Math.hypot(x1 - x0, y1 - y0) / 6);
    for (let s = 0; s <= n; s++) { const u = n ? s / n : 0, x = x0 + (x1 - x0) * u, y = y0 + (y1 - y0) * u;
      if (x + r > rx && x - r < rx + rw && y + r > ry && y - r < ry + rh) return false; } return true; }
  function navNeed(id, x, y, tx, ty, r) {
    if (!LIVE) return [tx, ty];
    const f = on("avoidFocus") ? lastFocus : null, d = S && S.s[id], rep = reports[id];
    const hr = hitR(id, r);   // the hit disc (postHits reports max(18, r)) must stay off the focus too
    if (f) { const [rx, ry, rw, rh] = f, keep = hr + 10;   // a knock spot ON the focus (or touching it) is moved just outside
      const cx = Math.max(rx, Math.min(tx, rx + rw)), cy = Math.max(ry, Math.min(ty, ry + rh)), dd = Math.hypot(tx - cx, ty - cy);
      if (dd === 0) { const e = [tx - rx, rx + rw - tx, ty - ry, ry + rh - ty], m = Math.min(...e), i = e.indexOf(m);
        if (i === 0) tx = rx - keep; else if (i === 1) tx = rx + rw + keep; else if (i === 2) ty = ry - keep; else ty = ry + rh + keep; }
      else if (dd < keep) { tx = cx + (tx - cx) / dd * keep; ty = cy + (ty - cy) / dd * keep; } }
    if (f && d && on("nudgeLongWait") && (d.needSec || 0) > 600) { const [rx, ry, rw, rh] = f;
      const cx = Math.max(rx, Math.min(tx, rx + rw)), cy = Math.max(ry, Math.min(ty, ry + rh)), dd = Math.hypot(tx - cx, ty - cy);
      const gap = dd - hr - 6, k = Math.min(0.5, 0.08 * Math.floor((d.needSec - 600) / 60 + 1));
      if (dd > 0 && gap > 0) { const go = gap * k; tx += (cx - tx) / dd * go; ty += (cy - ty) / dd * go; }
      needLast = { x, y, k, f: V.frame }; } else needLast = null;
    if (discClear(f, x, y, tx, ty, hr + 2)) { const pl = navPlan.get(id); if (pl) pl.travel = false; navVis[id] = 1; return [tx, ty]; }
    return nav(id, x, y, tx, ty, r, true); }
  let curiousId = null, curiousAt = -1;
  function curious() {   // the one idle creature nearest a resting cursor, chosen once per rest
    if (curiousAt === cursorRestAt) return curiousId; curiousAt = cursorRestAt; curiousId = null; let bd = 420;
    for (const id in reports) { const s = V.sessions.find(x => x.id === id), r = reports[id];
      if (!s || s.ghost || (S.s[id] || {}).state !== "idle") continue;
      const d = Math.hypot(r.x - cursor[0], r.y - cursor[1]); if (d < bd) { bd = d; curiousId = id; } }
    return curiousId; }
  function liveCalm() { if (!S) return true; if (hoverId || flares.length || S.net.vpn === "down" || S.net.link === "risk" || (S.play && S.play.amt > 0)) return false;
    if (S.m.level > 0.6 || (S.net.strain || 0) > 0.05) return false;
    for (const id in S.s) if (S.s[id].state !== "idle") return false;
    for (const id in born) if (V.t - born[id] < 2) return false;
    if (Object.keys(leaving).length || (cursor && performance.now() - cursorMovedAt < 1500)) return false;
    return true; }
  // ONE constant frame rate whenever anything is visible (owner, 2026-11-01 05:10: "Their fps shouldn't change, just
  // their velocity"). Slow-downs (hover, sleep) scale the simulated time per frame, never the frame rate. ?fps=N for tests.
  const LIVE_FPS = num("fps", 24);
  function liveFps() { return anyVisible() ? LIVE_FPS : 2; }
  function anyVisible() { if (!V.sessions.length) return false; for (const s of V.sessions) if (alphaOf(s.id) > 0.004) return true; return false; }
  // the beacon: lost = searchlight + red beacon at full strength; at risk (VPN down off site, API still fine) = a faint
  // beacon only, no searchlight (owner, 2026-11-01 ~08:15)
  const beaconK = () => Math.sqrt(Math.max(0.25, P.size * 2));
  function beaconAt() { if (!beaconOwner || !V.huddlePt || Math.max(vpnA, riskA) < 0.02) return null; const k = beaconK();
    return [V.huddlePt[0], V.huddlePt[1] - 46 * k, Math.max(22, 16 * k)]; }
  function drawBeacon() {   // the ONE searchlight + red beacon over the shared huddle point (owner layer only)
    if (!beaconOwner || !V.huddlePt) return;
    if (vpnA < 0.02) { if (riskA >= 0.02) drawBeaconLight(0.35 * riskA); return; }
    const [hx, hy] = V.huddlePt, t = V.t, k = beaconK();
    ctx.save(); ctx.globalCompositeOperation = "lighter";
    const ang = -Math.PI / 2 + 0.75 * Math.sin(t * 0.8), L = 380 * k, wd = 0.09, g = ctx.createRadialGradient(hx, hy, 0, hx, hy, L);
    g.addColorStop(0, `rgba(170,195,230,${0.16 * vpnA * P.glow})`); g.addColorStop(1, "rgba(170,195,230,0)");
    ctx.fillStyle = g; ctx.beginPath(); ctx.moveTo(hx, hy); ctx.arc(hx, hy, L, ang - wd, ang + wd); ctx.closePath(); ctx.fill();
    const ph = (t % 1.5) / 1.5, pulse = Math.exp(-Math.pow(ph / 0.09, 2)) + 0.25, by = hy - 46 * k;
    const gr = ctx.createRadialGradient(hx, by, 0, hx, by, 14 * k); gr.addColorStop(0, `rgba(255,70,60,${0.8 * vpnA * pulse})`); gr.addColorStop(1, "rgba(255,70,60,0)");
    ctx.fillStyle = gr; ctx.fillRect(hx - 14 * k, by - 14 * k, 28 * k, 28 * k);
    ctx.globalAlpha = vpnA * Math.min(1, pulse + 0.2); ctx.fillStyle = "hsl(0,100%,70%)"; ctx.beginPath();
    ctx.moveTo(hx, by - 2.6 * k); ctx.lineTo(hx + 2.6 * k, by); ctx.lineTo(hx, by + 2.6 * k); ctx.lineTo(hx - 2.6 * k, by); ctx.closePath(); ctx.fill();
    ctx.restore(); if (riskA > vpnA) drawBeaconLight(0.35 * (riskA - vpnA)); }
  function drawBeaconLight(a) { const [hx, hy] = V.huddlePt, t = V.t, k = beaconK(), by = hy - 46 * k;   // red beacon alone, slower blink
    const ph = (t % 2.4) / 2.4, pulse = Math.exp(-Math.pow(ph / 0.12, 2)) + 0.3;
    ctx.save(); ctx.globalCompositeOperation = "lighter";
    const gr = ctx.createRadialGradient(hx, by, 0, hx, by, 14 * k); gr.addColorStop(0, `rgba(255,70,60,${0.8 * a * pulse})`); gr.addColorStop(1, "rgba(255,70,60,0)");
    ctx.fillStyle = gr; ctx.fillRect(hx - 14 * k, by - 14 * k, 28 * k, 28 * k);
    ctx.globalAlpha = a * Math.min(1, pulse + 0.2); ctx.fillStyle = "hsl(0,100%,70%)"; ctx.beginPath();
    ctx.moveTo(hx, by - 2.6 * k); ctx.lineTo(hx + 2.6 * k, by); ctx.lineTo(hx, by + 2.6 * k); ctx.lineTo(hx - 2.6 * k, by); ctx.closePath(); ctx.fill();
    ctx.restore(); }
  let lastDt = DT;
  function liveStep(dt) {   // per tick, live-only bookkeeping
    lastDt = dt;
    for (const s of V.sessions) { const id = s.id, v = navVis[id] == null ? 1 : navVis[id], a = navA[id] == null ? 1 : navA[id];
      if (a < 0.02 && v === 1 && navA[id] != null) { const pl = navPlan.get(id), g = grid;   // reappear AT a fitting spot
        if (pl && pl.goal >= 0 && g && V._def.place) V._def.place(V, id, (pl.goal % g.nx + 0.5) * CELL, ((pl.goal / g.nx | 0) + 0.5) * CELL); }
      navA[id] = a + (v - a) * Math.min(1, dt / 0.6); }
    { const dn = S.net.vpn === "down" && on("vpnHuddle"); vpnA += ((dn ? 1 : 0) - vpnA) * Math.min(1, dt * (dn ? 1.4 : 2.2));
      const rk = S.net.link === "risk" && on("vpnHuddle"); riskA += ((rk ? 1 : 0) - riskA) * Math.min(1, dt * (rk ? 0.8 : 2.2)); }
    P.size += (sizeTarget - P.size) * Math.min(1, dt * 2.5);
    if (Math.abs(P.size - sizeTarget) < 0.002) P.size = sizeTarget;
    if (V._def.resize && Math.abs(P.size - (V._sizeSeen || 0)) > 0.002) { V._sizeSeen = P.size; V._def.resize(V, S); }
    for (const id in S.s) { const st = S.s[id].state, was = prevState[id];
      if (was === "working" && st === "idle" && on("celebrateDone") && V.t - lastFlare > 4 && reports[id] && !(on("quietUnderStrain") && S.m.level >= 2)) {
        lastFlare = V.t; const s = V.sessions.find(x => x.id === id); flares.push({ id, t: V.t, hue: s ? s.hue : 200, white: s && s.white }); }
      prevState[id] = st; }
    for (let i = flares.length - 1; i >= 0; i--) if (V.t - flares[i].t > 1.4) flares.splice(i, 1);
    if (Object.keys(leaving).some(id => V.t - leaving[id].t > 1.6)) membership(V.sessions.filter(s => !leaving[s.id])); }
  function drawFlares() { for (const f of flares) { const r = reports[f.id]; if (!r) continue; const u = (V.t - f.t) / 1.4, R = r.r * (0.9 + 0.8 * u);
      ctx.save(); ctx.globalCompositeOperation = "lighter";
      for (let k = 0; k < 10; k++) { const a = k / 10 * Math.PI * 2 + u * 2.2, x = r.x + Math.cos(a) * R, y = r.y + Math.sin(a) * R * 0.8;
        ctx.globalAlpha = 0.7 * Math.sin(Math.PI * Math.min(1, u)) * alphaOf(f.id); ctx.fillStyle = hsl(f.hue, f.white ? 0 : 90, 75, 1);
        ctx.beginPath(); ctx.arc(x, y, 1.6 + 1.4 * (1 - u), 0, 7); ctx.fill(); }
      ctx.restore(); } }
  // Running lights (BURNING_CONCEPTS rulings): one lit pip per burning item (beyond 12 they group: the strip grows by
  // sqrt), white-gold candle flicker; red tier flickers faster, amber slower. Absent `burning` = no lights.
  // A piece may draw them in its own idiom (define draw positions via V.lightSpots(id) -> [[x,y],...]); else the runtime
  // draws a short strip under the creature's reported circle.
  function lightCount(d) { const b = d && Number.isFinite(d.burning) ? d.burning : 0; return b <= 0 ? 0 : b <= 12 ? b : Math.round(12 + Math.sqrt(b - 12)); }
  function drawLight(c, x, y, sz, i, d, a) { const red = Math.min(d.burning_red || 0, 99), fast = i < red;
    const f = fast ? 0.55 + 0.45 * vnoise(V.t * 5.2 + i * 7.1, i) : 0.65 + 0.35 * vnoise(V.t * 1.3 + i * 3.7, i + 9);
    c.save(); c.globalCompositeOperation = "lighter"; c.globalAlpha = Math.min(1, a * 0.35 * f);
    c.fillStyle = "rgba(255,214,150,1)"; c.beginPath(); c.arc(x, y, sz * 2.4, 0, 7); c.fill();
    c.globalAlpha = Math.min(1, a * (0.6 + 0.4 * f)); c.fillStyle = "rgba(255,244,220,1)"; c.beginPath(); c.arc(x, y, sz * 0.9, 0, 7); c.fill(); c.restore(); }
  // Headless satellites (Augur 1.2 sessions[].parent; stage adaptState puts them in S.s[id].heads): a `claude -p` run
  // started from this session. Same orbit idiom as the background-task satellites but told apart by shape and tint: a
  // small hollow diamond in the creature's own hue, on a slightly wider, slower, counter-rotating orbit. Weight (cpu) is
  // drawn as brightness only (owner, 2026-11-04): headBright, eased per satellite in headA.
  const headA = {};   // satellite id -> eased brightness
  // cpu_cores -> brightness, fixed absolute scale: 0 cores = 0.35 floor, >= 1 core = 1, sqrt between; missing = floor.
  function headBright(cpu) { const c = typeof cpu === "number" && isFinite(cpu) ? Math.max(0, Math.min(1, cpu)) : 0; return 0.35 + 0.65 * Math.sqrt(c); }
  V.headBright = headBright;
  function drawHeads() { for (const s of V.sessions) { const d = S.s[s.id], hs = d && Array.isArray(d.heads) ? d.heads : null, r = reports[s.id];
      if (!hs || !hs.length || !r || s.ghost) continue;
      const a0 = alphaOf(s.id), R = r.r * 1.35 + 8 * Math.sqrt(P.size), sz = Math.max(2.2, 2.8 * Math.sqrt(P.size)), n = hs.length;
      ctx.save(); ctx.lineWidth = Math.max(1, 0.9 * Math.sqrt(P.size)); ctx.strokeStyle = hsl(s.hue, s.white ? 0 : 70, 78, 1);
      for (let k = 0; k < n; k++) { const a = -V.t * 0.35 + k / n * Math.PI * 2 + (s.iv || 0), x = r.x + Math.cos(a) * R, y = r.y + Math.sin(a) * R * 0.85;
        const hd = hs[k], tg = headBright(hd && hd.cpu), key = hd && hd.id != null ? hd.id : s.id + "#" + k, cur = headA[key] == null ? tg : headA[key];
        headA[key] = cur + (tg - cur) * Math.min(1, (lastDt || 0.016) / 0.8);   // ease so a satellite does not flicker tick to tick
        ctx.globalAlpha = headA[key] * a0; ctx.beginPath(); ctx.moveTo(x, y - sz); ctx.lineTo(x + sz, y); ctx.lineTo(x, y + sz); ctx.lineTo(x - sz, y); ctx.closePath(); ctx.stroke(); }
      ctx.restore(); } }
  function drawAllLights() { for (const s of V.sessions) { const d = S.s[s.id], n = lightCount(d), r = reports[s.id]; if (!n || !r || s.white) continue;
      const a = alphaOf(s.id) * (s.ghost ? 2.6 : 1);   // a ghost is faint but its lights are lit
      const spots = V._def.lightSpots ? V._def.lightSpots(V, s.id, n) : null, sz = Math.max(1.0, 1.3 * Math.sqrt(P.size));   // pip core (r = 0.9 sz) >= 1.8 px across
      if (spots) { const o = pull[s.id] || [0, 0]; spots.forEach((p0, i) => { const p = zoomPt(s.id, p0); drawLight(ctx, p[0] + o[0], p[1] + o[1], sz, i, d, a); }); continue; }
      const gap = Math.max(4, 6 * Math.sqrt(P.size)), w = (n - 1) * gap, y = r.y + r.r * 0.92 + 6;
      for (let i = 0; i < n; i++) drawLight(ctx, r.x - w / 2 + i * gap, y, sz, i, d, a); } }

  function postHits() { const now = performance.now(); if (now - lastHits < 100) return; lastHits = now;
    const hits = []; for (const id in reports) { const s = V.sessions.find(x => x.id === id); if (!s || leaving[id]) continue;   // ghosts too: a ghost click opens its project
      if (alphaOf(id) < 0.1) continue;   // faded out (nothing fits, arriving): no disc, it must not block a click (R1 #5); a ghost is 0.22
      const r = reports[id]; hits.push({ id, x: Math.round(r.x), y: Math.round(r.y), r: Math.round(Math.max(18, r.r)) }); }
    const m = JSON.stringify(hits); if (m === lastHitsMsg) return; lastHitsMsg = m;   // only on change
    post({ ev: "hits", hits }); }
  let lastHitsMsg = "";
  function onLive(m) {
    if (m.behaviors) { for (const k in B) delete B[k]; Object.assign(B, m.behaviors); }
    if ("cursor" in m) { const c = m.cursor ? [m.cursor.x, m.cursor.y] : null;
      if (c && (!cursor || Math.hypot(c[0] - cursor[0], c[1] - cursor[1]) > 2)) { cursorMovedAt = performance.now(); cursorRestAt = 0; }
      cursor = c; if (!c) cursorRestAt = 0; }
    if ("demo" in m) demoMode = !!m.demo;
    if ("huddle" in m) { V.huddlePt = m.huddle ? [m.huddle.x, m.huddle.y] : null; beaconOwner = !!(m.huddle && m.huddle.owner); }
    if (m.activity) activity = m.activity;
    if (m.windows) windows = m.windows;
    if (m.visible) visRect = [m.visible.x, m.visible.y, m.visible.w, m.visible.h];
    if (Number.isFinite(m.scale)) sizeTarget = Math.max(0.5, Math.min(2, m.scale)) * LIVE_BASE;
    if (m.greet) { let bd = 600, who = null; for (const id in reports) { if (id === m.greet.id) continue; const s = V.sessions.find(x => x.id === id), r = reports[id];
        if (!s || s.ghost || (S.s[id] || {}).state === "needs") continue; const d = Math.hypot(r.x - m.greet.x, r.y - m.greet.y); if (d < bd) { bd = d; who = id; } }
      if (who) greets.push({ who, x: m.greet.x, y: m.greet.y, until: V.t + 5 }); while (greets.length > 8) greets.shift(); }
    if ("paused" in m && m.paused !== paused) { paused = m.paused; if (!paused) { last = performance.now(); schedule(); } }
    if (m.S && m.sessions) { liveS = m.S; for (const id in (m.S.s || {})) lastData[id] = m.S.s[id];
      if (!membership(m.sessions)) { S = normS(liveS, V.sessions); S.T = simT; S.tData = simT; }
      liveFirst = false; } }
  let timer = 0;
  // Frames land on a wall-clock grid shared by every layer (timeOrigin + now), so the stage's iframes paint in ONE
  // rendering update per frame instead of one each (CPU, 2026-11-01: the cost is per update, not per pixel).
  function schedule() { if (SHARED) { if (!paused) env.wake(); return; }
    clearTimeout(timer); if (paused) return;
    const p = 1000 / liveFps(), t = performance.timeOrigin + performance.now(); let w = p - (t % p) - 4; if (w < 2) w += p;
    timer = setTimeout(() => requestAnimationFrame(loop), w); }

  // ---------- loop ----------
  let running = false, started = false, ended = false, simT = 0, acc = 0, last = 0, S = null, frames = [];
  function reset() { srand(TL.seed || 20261031); reports = {}; simT = 0; V.t = 0; V.frame = 0; S = LIVE ? normS(liveS, V.sessions) : sample(0);
    lastFocus = S.focus || null; drawBg(lastFocus); if (!LIVE || V.sessions.length) V._def.init && V._def.init(V, S); }
  function tick(dt) { dt = dt || DT; const tt = Math.min(simT, TL.duration); if (LIVE) { S.T = simT; S.tData = simT; liveStep(dt); } else S = sample(tt); S.T = simT; S.tData = tt;
    const nf = S.focus ? S.focus.map(Math.round).join() : ""; if (nf !== (lastFocus ? lastFocus.map(Math.round).join() : "")) { lastFocus = S.focus; drawBg(lastFocus); }
    V.t = simT; if (!LIVE || V.sessions.length) V._def.step && V._def.step(V, S, dt); simT += dt; V.frame++; }
  function render() { if (skipDraw) return; if (SHARED) ctx.__aS = AS; else ctx.clearRect(0, 0, W, H); if (LIVE && !V.sessions.length) return; V._def.draw(V, S, ctx);
    if (LIVE) { drawAllLights(); drawHeads(); }
    if (q.get("legend") === "1") drawLegend();
    if (q.get("hud") === "1") { drawHud(); drawLabels(); }
    if (LIVE) { drawFlares(); drawBeacon(); }
    if (on("hoverName") && !SHARED) drawHover(); }   // shared: the stage draws the hover label after every species
  // Gallery labels under each creature (TL.labels: "variant" = window.VARIANT_NAMES[iv], "name" = session name).
  function drawLabels() { if (!TL.labels) return; const names = window.VARIANT_NAMES || [];
    ctx.save(); ctx.font = Math.max(9, Math.round(H / 44)) + "px -apple-system,system-ui,sans-serif"; ctx.textAlign = "center";
    for (const s of TL.sessions) { const r = reports[s.id]; if (!r) continue;
      const lab = TL.labels === "variant" ? (s.iv + " " + (names[s.iv] || "")) : s.name;
      const y = Math.max(12, r.y - Math.max(14, r.r) - 6);
      ctx.fillStyle = "rgba(225,232,245,0.55)"; ctx.fillText(lab, r.x, y); }
    ctx.restore(); }
  // Gallery HUD: the driving values of a scenario (TL.hud lists which), so a viewer sees the data under the motion.
  function drawHud() { if (!S || !TL.hud) return; const s0 = S.s[TL.sessions[0].id], out = [];
    for (const k of TL.hud) {
      if (k === "cpu") out.push(["CPU", s0.cpu / 4, s0.cpu.toFixed(1) + " cores"]);
      else if (k === "mem") out.push(["memory", s0.mem / 2.5, s0.mem.toFixed(1) + " GB"]);
      else if (k === "procs") out.push(["tasks", s0.procs / 12, String(Math.round(s0.procs))]);
      else if (k === "state") out.push(["session", s0.state === "needs" ? 1 : s0.state === "working" ? 0.5 : 0.05, s0.state === "needs" ? "NEEDS YOU" : s0.state]);
      else if (k === "level") out.push(["machine", S.m.level / 3, ["light", "medium", "high", "danger"][Math.min(3, Math.round(S.m.level))] + (S.m.thermal >= 1.5 ? " · hot" : S.m.thermal >= 0.5 ? " · warm" : "")]);
      else if (k === "rx") out.push(["download", Math.min(1, Math.log10(1 + (s0.rx || 0)) / 1.5), (s0.rx || 0).toFixed(1) + " Mbit/s"]);
      else if (k === "tx") out.push(["upload", Math.min(1, Math.log10(1 + (s0.tx || 0)) / 1.5), (s0.tx || 0).toFixed(1) + " Mbit/s"]);
      else if (k === "bw") out.push(["link", 1 - (S.net.strain || 0), (S.net.strain || 0) > 0.5 ? "TOO SLOW" : "keeping up"]);
      else if (k === "mbps") out.push(["network", Math.min(1, Math.log10(1 + S.net.mbps) / 1.7), S.net.mbps.toFixed(1) + " Mbit/s"]);
      else if (k === "vpn") out.push(["VPN", S.net.vpn === "down" ? 0 : 1, S.net.vpn === "down" ? "LOST" : "up"]);
      else if (k === "play") out.push(["play", S.play.amt, S.play.amt > 0.5 ? "playing" : "apart"]); }
    const fs = Math.max(10, Math.round(H / 30)); ctx.save(); ctx.font = fs + "px ui-monospace,Menlo,monospace";
    out.forEach(([lab, f, val], i) => { const y = H - 8 - (out.length - 1 - i) * (fs + 6);
      ctx.fillStyle = "rgba(0,0,0,0.5)"; ctx.fillRect(6, y - fs, W * 0.42, fs + 4);
      ctx.fillStyle = "rgba(255,255,255,0.18)"; ctx.fillRect(8 + fs * 5, y - fs * 0.62, W * 0.12, fs * 0.42);
      ctx.fillStyle = "rgba(255,255,255,0.75)"; ctx.fillRect(8 + fs * 5, y - fs * 0.62, W * 0.12 * Math.max(0, Math.min(1, f)), fs * 0.42);
      ctx.fillStyle = "rgba(230,235,245,0.9)"; ctx.fillText(lab, 10, y); ctx.fillText(val, 14 + fs * 5 + W * 0.12, y); });
    ctx.restore(); }
  function drawLegend() { const el = document.getElementById("COLOPHON"); if (!el) return;
    const lines = JSON.parse(el.textContent); ctx.save(); ctx.font = "13px system-ui"; ctx.fillStyle = "rgba(0,0,0,0.55)";
    ctx.fillRect(16, H - 30 - lines.length * 18, 360, lines.length * 18 + 14); ctx.fillStyle = "#dde";
    lines.forEach((l, i) => ctx.fillText(l, 26, H - 20 - (lines.length - 1 - i) * 18)); ctx.restore(); }
  // Hover (owner, 2026-10-31): near a creature, time slows to ~10% and its project name appears.
  let mouse = null, hoverId = null, slow = 1;
  if (q.get("hover") !== "0") {
    addEventListener("mousemove", e => { const r = stage.getBoundingClientRect(), k = r.width / W;
      mouse = [(e.clientX - r.left) / k, (e.clientY - r.top) / k]; });
    addEventListener("mouseleave", () => { mouse = null; }); }
  // Live (owner, 2026-11-01 ~07:10: "If I hover over them, they should go toward my cursor, not away from it"): the hit
  // area is generous (1.3x the reported extent) and a hover survives 300 ms off it, so jitter does not break it.
  let hoverLost = 0;
  function pickHover() { if (LIVE) mouse = cursor; const was = hoverId; hoverId = null; for (const k in motePts) if (k !== was) delete motePts[k];
    if (!mouse || !on("hoverName")) { hoverLost = 0; return; } let bd = 1e9;
    const k = LIVE ? 1.3 : 1.1;
    if (released) { const r = reports[released]; if (!r || Math.hypot(r.bx - mouse[0], r.by - mouse[1]) > pullCap(r) + Math.max(24, r.r * k)) released = null; }
    for (const id in reports) { const r = reports[id], d = Math.hypot(r.x - mouse[0], r.y - mouse[1]);
      if (LIVE && alphaOf(id) < 0.1) continue;   // R2-SPEC #4: faded out (no room, arriving) is not hoverable, as in postHits
      if (id !== released && d < Math.max(24, r.r * k) && d < bd) { bd = d; hoverId = id; } }
    if (LIVE && !hoverId && was && was !== released && reports[was] && alphaOf(was) >= 0.1) { const nowMs = performance.now(); if (!hoverLost) hoverLost = nowMs;
      if (nowMs - hoverLost < 300) hoverId = was; else hoverLost = 0; } else hoverLost = 0; }
  // The hovered creature eases toward the cursor and holds centred under it (a display offset on top of the piece's own
  // motion, so no piece code changes): exponential approach, no overshoot, no orbit. It never enters the focused window
  // (the step that would is refused, so it stops at the edge); other windows are fine. Unhovered, the offset eases back
  // to 0 and the piece's own wandering carries on.
  // Bounded (R1 #6): the offset never exceeds pullCap (1.5 r, at least 24 px) from the creature's own position; a cursor
  // that leads it farther releases the hover (the creature eases home and is not re-hovered until the cursor leaves its
  // reach), so a slow cursor cannot carry a click-blocking disc across the screen. At the focused window the whole hit
  // disc (max(18, r), as postHits reports it) plus 4 px stays outside.
  const pull = {}, motePts = {}; let released = null, hoverAt = null;
  const pullCap = r => Math.max(24, 1.5 * r.r);
  function isHoveredAt(x, y) { const r = hoverId && reports[hoverId]; return !!r && Math.hypot(x - r.bx, y - r.by) < Math.max(12, r.r * 0.6); }
  function stepPull(dt) { if (!LIVE) return;
    if (hoverId && cursor && !pull[hoverId]) pull[hoverId] = [0, 0];
    if (hoverId && reports[hoverId] && (!hoverAt || hoverAt.id !== hoverId)) hoverAt = { id: hoverId, x: reports[hoverId].bx, y: reports[hoverId].by };
    if (!hoverId) hoverAt = null;
    for (const id in pull) { const r = reports[id], o = pull[id]; if (!r) { delete pull[id]; continue; }
      let on_ = id === hoverId && cursor, tx = on_ ? cursor[0] - r.bx : 0, ty = on_ ? cursor[1] - r.by : 0;
      // R2-SPEC #1: the release is measured from where the creature was when the hover began, so the piece's own slow
      // drift under a parked cursor never releases it (c2 drifted 20 px in 10 s and was let go); the cursor leading it
      // more than the cap away still does (R1 #6). The offset itself stays within the cap of the live position.
      const cap = pullCap(r), an = on_ && hoverAt && hoverAt.id === id ? hoverAt : { x: r.bx, y: r.by };
      if (on_ && Math.hypot(cursor[0] - an.x, cursor[1] - an.y) > cap) { released = id; hoverId = null; hoverAt = null; hoverLost = 0; on_ = false; tx = 0; ty = 0; }
      { const m = Math.hypot(tx, ty); if (m > cap) { tx *= cap / m; ty *= cap / m; } }
      const k = 1 - Math.exp(-dt / (on_ ? 0.42 : 0.9)), nx = o[0] + (tx - o[0]) * k, ny = o[1] + (ty - o[1]) * k;
      const inF = (ox, oy) => insideFocus(r.bx + ox, r.by + oy, Math.max(18, r.r) + 4);
      if (!inF(nx, ny) || inF(o[0], o[1])) { o[0] = nx; o[1] = ny; }
      else if (!inF(nx, o[1])) o[0] = nx; else if (!inF(o[0], ny)) o[1] = ny;   // slide along the focus edge
      if (!on_ && Math.hypot(o[0], o[1]) < 0.05) { delete pull[id]; r.x = r.bx; r.y = r.by; continue; }
      r.x = r.bx + o[0]; r.y = r.by + o[1]; } }
  function drawHover() { if (!hoverId) return; const r = reports[hoverId], s = V.sessions.find(x => x.id === hoverId);
    if (!r || !s) return; ctx.save(); ctx.font = Math.max(11, Math.round(H / 36)) + "px -apple-system,system-ui,sans-serif";
    ctx.textAlign = "center"; ctx.fillStyle = "rgba(235,240,250,0.85)";
    ctx.fillText(s.label || s.name, r.x, Math.max(14, r.y - Math.max(14, r.r) - 8)); ctx.restore(); }
  function loop(now) {
    if (LIVE && paused) return;
    pickHover(); slow += ((hoverId ? 0.1 : 1) - slow) * 0.15;
    if (LIVE) { const away = on("sleepWhenAway") && activity.idleSec > 300; wake += ((away ? 0.25 : 1) - wake) * 0.03;
      if (cursor && !cursorRestAt && performance.now() - cursorMovedAt > 800) cursorRestAt = V.t; }
    if (running && LIVE) {   // live: one variable step per frame (sub-stepped to <= 1/30 s), so slow motion stays smooth
      let e = Math.min(0.15, (now - last) / 1000) * slow * wake; while (e > 1e-4) { const d = Math.min(e, 1 / 30); tick(d); e -= d; } }
    else if (running) { acc += Math.min(0.15, (now - last) / 1000) * slow; let n = 0;
      while (acc >= DT && n < 10) { tick(); acc -= DT; n++; }
      if (n === 10) acc = 0;
      if (!ended && simT >= TL.duration) { ended = true; post({ ev: "ended", id: TL.id });
        if (q.get("loop") === "1") { reset(); ended = false; } } }
    if (LIVE) stepPull(Math.min(0.15, (now - last) / 1000));
    last = now; render(); frames.push(now); if (frames.length > 120) frames.shift();
    if (SHARED) postHits(); else if (LIVE) { postHits(); schedule(); } else requestAnimationFrame(loop); }
  function start() { if (started) return; started = true; reset(); running = true; last = performance.now();
    post({ ev: "started", id: TL.id }); }
  function boot() { if (SHARED) { reset(); start(); post({ ev: "ready", id: TL.id }); return; }
    reset(); render();
    addEventListener("message", e => { if (!e.data) return; if (e.data.cmd === "start") start();
      if (LIVE && e.data.cmd === "live") onLive(e.data);
      if (e.data.cmd === "restart") { started = true; reset(); ended = false; running = true; last = performance.now(); } });
    if (q.get("autostart") === "1" || LIVE) start();
    parent.postMessage({ ev: "ready", id: TL.id }, "*"); if (LIVE) schedule(); else requestAnimationFrame(loop); }

  const QA = SHARED ? V : window;
  QA.__renderAt = function (t) { running = false; started = true; reset();
    const n = Math.round(t / DT); for (let i = 0; i < n; i++) tick(); render();
    return { t: simT, reports: JSON.parse(JSON.stringify(reports)), focus: lastFocus, state: S }; };
  // QA: continue the simulation (no reset) to time t and render; cheap incremental sampling.
  QA.__advanceTo = function (t) { if (!started || running) { running = false; started = true; reset(); }
    while (simT + DT / 2 < t) tick(); render(); return simT; };
  // QA: creature-layer statistics on a downsampled grid (fg canvas only; backdrop excluded).
  const qa = document.createElement("canvas"); qa.width = 320; qa.height = 200; const qx = qa.getContext("2d", { willReadFrequently: true });
  const qb = document.createElement("canvas"); qb.width = 320; qb.height = 200; const qbx = qb.getContext("2d", { willReadFrequently: true });
  const lin = v => { v /= 255; return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
  QA.__lumStats = function () {
    qx.clearRect(0, 0, 320, 200); qx.drawImage(fgC, 0, 0, 320, 200); const d = qx.getImageData(0, 0, 320, 200).data;
    qbx.clearRect(0, 0, 320, 200); qbx.drawImage(bgC, 0, 0, 320, 200); const b = qbx.getImageData(0, 0, 320, 200).data;
    let lit = 0, litF = 0, nF = 0; const blocks = new Array(12).fill(0), bn = new Array(12).fill(0);
    const f = lastFocus ? lastFocus.map(v => v / 4) : null;
    for (let y = 0; y < 200; y++) for (let x = 0; x < 320; x++) { const i = (y * 320 + x) * 4, a = d[i + 3] / 255;
      const L = (0.2126 * lin(d[i]) + 0.7152 * lin(d[i + 1]) + 0.0722 * lin(d[i + 2]));
      const LB = (0.2126 * lin(b[i]) + 0.7152 * lin(b[i + 1]) + 0.0722 * lin(b[i + 2]));
      const C = a * L + (1 - a) * LB;   // source-over approximation of the composite
      const on = a * L > 0.02; if (on) lit++;
      const k = Math.min(3, Math.floor(x / 80)) + 4 * Math.min(2, Math.floor(y / 67)); blocks[k] += C; bn[k]++;
      if (f && x >= f[0] && x < f[0] + f[2] && y >= f[1] && y < f[1] + f[3]) { nF++; if (on) litF++; } }
    return { litFrac: lit / 64000, litFocusFrac: nF ? litF / nF : 0, blocks: blocks.map((v, i) => v / bn[i]) }; };
  // QA: peak contrast of each creature against the backdrop at its reported position (full res).
  QA.__visibility = function () { const out = {};
    for (const id in reports) { const r = reports[id], R = Math.max(3, Math.min(60, r.r));
      const x0 = Math.max(0, Math.round((r.x - R) * dpr)), y0 = Math.max(0, Math.round((r.y - R) * dpr));
      const w = Math.max(1, Math.min(fgC.width - x0, Math.round(2 * R * dpr))), h = Math.max(1, Math.min(fgC.height - y0, Math.round(2 * R * dpr)));
      const d = ctx.getImageData(x0, y0, w, h).data, b = bg.getImageData(x0, y0, w, h).data;
      let peak = 0, bsum = 0, n = 0;
      for (let i = 0; i < d.length; i += 4) { const a = d[i + 3] / 255;
        const L = 0.2126 * lin(d[i]) + 0.7152 * lin(d[i + 1]) + 0.0722 * lin(d[i + 2]);
        const LB = 0.2126 * lin(b[i]) + 0.7152 * lin(b[i + 1]) + 0.0722 * lin(b[i + 2]);
        const C = a * L + (1 - a) * LB; if (C > peak) peak = C; bsum += LB; n++; }
      const LBm = bsum / n; out[id] = { contrast: (peak + 0.05) / (LBm + 0.05), peak, bg: LBm }; }
    return out; };
  QA.__report = () => ({ t: simT, reports, focus: lastFocus });
  QA.__nav = () => ({ plans: [...navPlan.entries()].map(([id, p]) => [id, p.goal, p.path.length, p.travel]), vis: navVis, a: navA, grid: grid && [grid.nx, grid.ny, grid.ver] });
  // QA (live): feed one live message synchronously, then advance n fixed steps and render; returns reports.
  QA.__live = function (msg, n) { if (msg) onLive(msg); paused = true; for (let i = 0; i < (n || 0); i++) tick(); render();
    return { t: simT, reports: JSON.parse(JSON.stringify(reports)), ids: V.sessions.map(s => s.id), errors: window.__errors }; };
  // QA (review R1 #18): the ids each per-id map holds, to check that departed sessions are pruned
  QA.__idMaps = () => ({ lastData: Object.keys(lastData), prevState: Object.keys(prevState), steerSt: Object.keys(steerSt), navPlan: [...navPlan.keys()],
    pull: Object.keys(pull), navA: Object.keys(navA), navVis: Object.keys(navVis), motePts: Object.keys(motePts), born: Object.keys(born), leaving: Object.keys(leaving) });
  QA.__fps = () => frames.length < 2 ? 0 : 1000 * (frames.length - 1) / (frames[frames.length - 1] - frames[0]);
  QA.__duration = TL.duration;
  // shared mode: the stage's one loop advances and draws this instance; live messages arrive as direct calls
  // hover-label hook: the hovered creature (id, x, y, r, session, optional motes from the piece's own motes(V, id))
  V._beacon = () => beaconAt();
  V._hover = () => { if (!hoverId || !reports[hoverId]) return null; const r = reports[hoverId], s = V.sessions.find(x => x.id === hoverId);
    if (!s) return null; return { id: hoverId, x: r.x, y: r.y, r: r.r, s, alpha: alphaOf(hoverId), motes: hoverMotes(hoverId) }; };
  // the piece's own points: V.motes() if it reported any, else its running-light spots (its rim/body points), else none
  function hoverMotes(id) { let pts = motePts[id];
    if (!pts && V._def.lightSpots) { try { pts = V._def.lightSpots(V, id, 32); } catch (e) { pts = null; } }
    if (!Array.isArray(pts) || !pts.length) return undefined; const o = pull[id] || [0, 0]; return pts.map(p0 => { const p = zoomPt(id, p0); return [p[0] + o[0], p[1] + o[1]]; }); }
  V._frame = (now, noDraw) => { skipDraw = !!noDraw; try { loop(now); } finally { skipDraw = false; } }; V._onLive = onLive; V._anyVisible = anyVisible; V._isPaused = () => paused;
  return V;
}
window.VisitorsRuntime = { create: createRuntime };
// Standalone page: one instance from the page URL. app/stage.html sets VISITORS_SHARED before loading this file.
if (!window.VISITORS_SHARED) createRuntime(new URLSearchParams(location.search), null);
})();
