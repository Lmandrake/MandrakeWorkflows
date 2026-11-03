/* Sprites native renderer, JS half (docs/NATIVE_PORT.md). A CanvasRenderingContext2D that records instead of drawing:
 * every fill, stroke and drawImage becomes GPU instances in one Float32Array that app/macos/Render.swift draws with Metal
 * in a single instanced draw. Offscreen canvases (the pieces' glow-sprite caches) record into their own small list;
 * drawing one that holds a single gradient fill replays that fill analytically at the destination (no texture).
 *
 * Instance (ST floats): 0 code = kind | op<<3 | blend<<5 | paint<<7 | target<<9
 *   kind 0 rect(x0,y0,x1,y1) 1 ellipse(cx,cy,rx,ry,angle,lineWidth|0) 2 segment(x0,y0,x1,y1,lineWidth)
 *        3 triangle(x0,y0,x1,y1,x2,y2,exteriorEdgeBits) 4 path resolve 5 layer resolve
 *   op 0 paint, 1 coverage (union of one path's pieces; resolved by the path's kind-4 instance)
 *   blend 0 source-over 1 lighter · paint 0 solid 1 radial 2 linear 3 label texture · target 0 frame 1 species layer
 *   1..7 geometry (device px) · 8 globalAlpha · 9..12 rgba (solid, unpremultiplied) or gradient geometry
 *   13 palette index · 14..17 bounding box (device px, AA margin included)
 *   drawImage of a sprite canvas (kind 0 over the destination rect): 5 source shape (0 rect, 1 disc), 6,7,19 disc centre
 *   and radius in sprite px; 20..23 sprite->device map ox, oy, kx, ky. The shader then samples the sprite as Chromium
 *   does: 8-bit premultiplied texels at texel centres, bilinear (the approved look's glow tails).
 * Palette (PS floats): count, then up to 7 stops of (offset, r, g, b, a). */
(function (G) {
"use strict";
const ST = 24, PS = 36, MAXSTOPS = 7, MAXLABELS = 4, TAU = Math.PI * 2;
const RECT = 0, ELL = 1, SEG = 2, TRI = 3, RES = 4, LAYER = 5;
const BLEND = { "source-over": 0, "lighter": 1 };
const stats = G.__nativeStats = { unsupported: {} };
function unsup(k) { stats.unsupported[k] = (stats.unsupported[k] || 0) + 1; }

// ---------- colours: CSS strings -> [r,g,b,a] (rgb rounded to 8 bits as the browser's parser does), cached ----------
const NAMED = { transparent: [0, 0, 0, 0], black: [0, 0, 0, 1], white: [1, 1, 1, 1], red: [1, 0, 0, 1], green: [0, 128 / 255, 0, 1],
  blue: [0, 0, 1, 1], yellow: [1, 1, 0, 1], gray: [128 / 255, 128 / 255, 128 / 255, 1], grey: [128 / 255, 128 / 255, 128 / 255, 1] };
const cache = new Map();
const b8 = v => Math.round(Math.max(0, Math.min(1, v)) * 255) / 255;
function num(s, pct) { return s.endsWith("%") ? parseFloat(s) / 100 * pct : parseFloat(s); }
function parse(s) {
  if (s[0] === "#") { let h = s.slice(1); if (h.length === 3 || h.length === 4) h = h.split("").map(c => c + c).join("");
    if (!/^[0-9a-f]{6}([0-9a-f]{2})?$/.test(h)) return null; const n = parseInt(h.slice(0, 6), 16);
    return [(n >> 16) / 255, (n >> 8 & 255) / 255, (n & 255) / 255, h.length === 8 ? parseInt(h.slice(6), 16) / 255 : 1]; }
  const m = /^(rgba?|hsla?)\((.*)\)$/.exec(s); if (!m) return NAMED[s] ? NAMED[s].slice() : null;
  const p = m[2].split(/[\s,\/]+/).filter(Boolean); if (p.length < 3) return null;
  const a = p.length > 3 ? Math.max(0, Math.min(1, num(p[3], 1))) : 1; if (!isFinite(a)) return null;
  if (m[1][0] === "r") { const c = [0, 1, 2].map(i => b8(num(p[i], 255) / 255)); if (!c.every(isFinite)) return null; c.push(a); return c; }
  let H = parseFloat(p[0]); if (p[0].endsWith("turn")) H *= 360; else if (p[0].endsWith("rad")) H *= 180 / Math.PI;
  const S = Math.max(0, Math.min(1, parseFloat(p[1]) / 100)), L = Math.max(0, Math.min(1, parseFloat(p[2]) / 100));
  if (!(isFinite(H) && isFinite(S) && isFinite(L))) return null;
  const hh = ((H % 360) + 360) % 360, A = S * Math.min(L, 1 - L);
  const f = n => { const k = (n + hh / 30) % 12; return L - A * Math.max(-1, Math.min(k - 3, 9 - k, 1)); };
  return [b8(f(0)), b8(f(8)), b8(f(4)), a];
}
// Fast path for the pieces' own strings, "hsla(H,S%,L%,A)" / "rgba(R,G,B,A)" with a varying alpha: the colour part is
// cached by its prefix and only the alpha is parsed (each frame makes hundreds of distinct alpha strings).
const pre = new Map();
function color(s) {
  if (typeof s !== "string") return null;
  const k = s.lastIndexOf(",");
  if (k > 5 && s.charCodeAt(s.length - 1) === 41 && (s.charCodeAt(0) === 104 || s.charCodeAt(0) === 114) && s.charCodeAt(3) === 97) {   // hsla( / rgba(
    const head = s.slice(0, k); let rgb = pre.get(head);
    if (rgb === undefined) { const c = parse((head + ",1)").trim().toLowerCase()); rgb = c ? [c[0], c[1], c[2]] : null; if (pre.size > 4000) pre.clear(); pre.set(head, rgb); }
    if (rgb) { const a = +s.slice(k + 1, -1); if (a === a) { const c = [rgb[0], rgb[1], rgb[2], a < 0 ? 0 : a > 1 ? 1 : a]; return c; } }
  }
  let c = cache.get(s); if (c !== undefined) return c; if (cache.size > 20000) cache.clear();
  c = parse(s.trim().toLowerCase()); cache.set(s, c); return c; }

class CanvasGradient {
  constructor(type, g) { this.type = type; this.g = g; this.stops = []; this._gen = -1; this._pal = 0; }
  addColorStop(o, c) { o = +o; if (!(o >= 0 && o <= 1)) throw new RangeError("addColorStop: offset out of range");
    const col = color(String(c)); if (!col) throw new SyntaxError("addColorStop: bad colour " + c);
    let i = this.stops.length; while (i > 0 && this.stops[i - 1][0] > o) i--;
    this.stops.splice(i, 0, [o, col[0], col[1], col[2], col[3]]); this._gen = -1; }
}

// ---------- sinks: where instances go ----------
class Sink {
  constructor(main) { this.main = main; this.f = new Float32Array(ST * (main ? 8192 : 4)); this.n = 0; this.ver = 0;
    this.pal = new Float32Array(PS * (main ? 64 : 1)); this.paln = 0; this.gen = 1; this.grads = []; this.tgt = 0;
    this.lb = [Infinity, Infinity, -Infinity, -Infinity]; this.layers = 0; this.labn = 0; }
  reset() { this.n = 0; this.paln = 0; this.gen++; this.grads.length = 0; this.ver++; this.tgt = 0; this.layers = 0; this.labn = 0; }
  palOf(gr) { if (!this.main) { this.grads.push(gr); return this.grads.length - 1; }
    if (gr._gen === this.gen && gr._sink === this) return gr._pal;
    if ((this.paln + 1) * PS > this.pal.length) { const p = new Float32Array(this.pal.length * 2); p.set(this.pal); this.pal = p; }
    const o = this.paln * PS, st = gr.stops, n = Math.min(MAXSTOPS, st.length); if (st.length > MAXSTOPS) unsup("stops>7");
    this.pal[o] = n; for (let i = 0; i < n; i++) for (let k = 0; k < 5; k++) this.pal[o + 1 + i * 5 + k] = st[i][k];
    gr._gen = this.gen; gr._sink = this; gr._pal = this.paln++; return gr._pal; }
  put(code, g0, g1, g2, g3, g4, g5, g6, alpha, p0, p1, p2, p3, pal, x0, y0, x1, y1) {
    if ((this.n + 1) * ST > this.f.length) { const f = new Float32Array(this.f.length * 2); f.set(this.f); this.f = f; }
    const f = this.f, o = this.n++ * ST;
    f[o] = code; f[o + 1] = g0; f[o + 2] = g1; f[o + 3] = g2; f[o + 4] = g3; f[o + 5] = g4; f[o + 6] = g5; f[o + 7] = g6;
    f[o + 8] = alpha; f[o + 9] = p0; f[o + 10] = p1; f[o + 11] = p2; f[o + 12] = p3; f[o + 13] = pal;
    f[o + 14] = x0; f[o + 15] = y0; f[o + 16] = x1; f[o + 17] = y1; f[o + 18] = 0; f[o + 19] = 0; f[o + 20] = 0; f[o + 21] = 0; f[o + 22] = 0; f[o + 23] = 0;
    if (this.tgt) { const b = this.lb; if (x0 < b[0]) b[0] = x0; if (y0 < b[1]) b[1] = y0; if (x1 > b[2]) b[2] = x1; if (y1 > b[3]) b[3] = y1; }
    this.ver++; }
}

// paint scratch (no allocation per draw): set by paintFrom()
let PT = 0, P0 = 0, P1 = 0, P2 = 0, P3 = 0, PAL = 0;
function paintFrom(S, style, m) {
  if (style instanceof CanvasGradient) { if (!style.stops.length) return false; const g = style.g, sc = Math.sqrt(Math.abs(m[0] * m[3] - m[1] * m[2]));
    if (style.type === 1) { if (g[0] !== g[3] || g[1] !== g[4]) unsup("radial:nonconcentric");
      P0 = m[0] * g[3] + m[2] * g[4] + m[4]; P1 = m[1] * g[3] + m[3] * g[4] + m[5]; P2 = g[2] * sc; P3 = g[5] * sc; }
    else { P0 = m[0] * g[0] + m[2] * g[1] + m[4]; P1 = m[1] * g[0] + m[3] * g[1] + m[5]; P2 = m[0] * g[2] + m[2] * g[3] + m[4]; P3 = m[1] * g[2] + m[3] * g[3] + m[5]; }
    PT = style.type; PAL = S.palOf(style); return true; }
  const c = style; if (!c || c[3] <= 0) return false; PT = 0; P0 = c[0]; P1 = c[1]; P2 = c[2]; P3 = c[3]; PAL = 0; return true; }

// ---------- the context ----------
function State(o) { if (o) { for (const k in o) this[k] = o[k]; this.m = o.m.slice(); return; }
  this.m = [1, 0, 0, 1, 0, 0]; this.alpha = 1; this.comp = "source-over"; this.fillV = "#000000"; this.fillP = [0, 0, 0, 1];
  this.strokeV = "#000000"; this.strokeP = [0, 0, 0, 1]; this.lw = 1; this.font = "10px sans-serif"; this.textAlign = "start";
  this.textBaseline = "alphabetic"; this.lineCap = "butt"; this.lineJoin = "miter"; this.miterLimit = 10; this.shadowBlur = 0;
  this.shadowColor = "rgba(0, 0, 0, 0)"; this.shadowOffsetX = 0; this.shadowOffsetY = 0; this.filter = "none"; this.letterSpacing = "0px";
  this.imageSmoothingEnabled = true; this.imageSmoothingQuality = "low"; this.direction = "inherit"; }

const prims = [];   // scratch: [kind, g0..g6, bbox x0,y0,x1,y1] per primitive
function prim(k, a, b, c, d, e, f, g, x0, y0, x1, y1) { prims.push([k, a, b, c, d, e, f, g, x0, y0, x1, y1]); }

class CanvasRenderingContext2D {
  constructor(canvas, sink) { this.canvas = canvas; this._sink = sink; this._s = new State(); this._stack = [];
    this._path = []; this._cur = null; this._has = false; this._lx = 0; this._ly = 0; }
  _reset() { this._s = new State(); this._stack = []; this.beginPath(); }
  // state
  save() { this._stack.push(new State(this._s)); }
  restore() { if (this._stack.length) this._s = this._stack.pop(); }
  get globalAlpha() { return this._s.alpha; } set globalAlpha(v) { v = +v; if (v >= 0 && v <= 1) this._s.alpha = v; }
  get globalCompositeOperation() { return this._s.comp; }
  set globalCompositeOperation(v) { if (typeof v === "string" && v in COMPS) this._s.comp = v; }
  get fillStyle() { return this._s.fillV; } set fillStyle(v) { const p = v instanceof CanvasGradient ? v : color(v); if (p) { this._s.fillV = v; this._s.fillP = p; } else if (typeof v === "object" && v) unsup("pattern"); }
  get strokeStyle() { return this._s.strokeV; } set strokeStyle(v) { const p = v instanceof CanvasGradient ? v : color(v); if (p) { this._s.strokeV = v; this._s.strokeP = p; } }
  get lineWidth() { return this._s.lw; } set lineWidth(v) { v = +v; if (v > 0 && isFinite(v)) this._s.lw = v; }
  // transforms
  setTransform(a, b, c, d, e, f) { if (typeof a === "object" && a) ({ a, b, c, d, e, f } = a); const v = [a, b, c, d, e, f]; if (v.every(isFinite)) this._s.m = v; }
  resetTransform() { this._s.m = [1, 0, 0, 1, 0, 0]; }
  getTransform() { const m = this._s.m; return { a: m[0], b: m[1], c: m[2], d: m[3], e: m[4], f: m[5] }; }
  transform(a, b, c, d, e, f) { const m = this._s.m; if (![a, b, c, d, e, f].every(isFinite)) return;
    this._s.m = [m[0] * a + m[2] * b, m[1] * a + m[3] * b, m[0] * c + m[2] * d, m[1] * c + m[3] * d, m[0] * e + m[2] * f + m[4], m[1] * e + m[3] * f + m[5]]; }
  translate(x, y) { if (!isFinite(x) || !isFinite(y)) return; const m = this._s.m; m[4] += m[0] * x + m[2] * y; m[5] += m[1] * x + m[3] * y; }
  scale(x, y) { if (!isFinite(x) || !isFinite(y)) return; const m = this._s.m; m[0] *= x; m[1] *= x; m[2] *= y; m[3] *= y; }
  rotate(t) { if (!isFinite(t)) return; const c = Math.cos(t), s = Math.sin(t); this.transform(c, s, -s, c, 0, 0); }
  // gradients
  createRadialGradient(x0, y0, r0, x1, y1, r1) { if (![x0, y0, r0, x1, y1, r1].every(isFinite)) throw new TypeError("non-finite");
    if (r0 < 0 || r1 < 0) throw new RangeError("radius"); return new CanvasGradient(1, [x0, y0, r0, x1, y1, r1]); }
  createLinearGradient(x0, y0, x1, y1) { if (![x0, y0, x1, y1].every(isFinite)) throw new TypeError("non-finite"); return new CanvasGradient(2, [x0, y0, x1, y1]); }
  createPattern() { unsup("createPattern"); return null; }
  // paths (points are transformed when added, as canvas does)
  beginPath() { this._path = []; this._cur = null; this._has = false; }
  _pt(x, y) { const m = this._s.m; return [m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5]]; }
  moveTo(x, y) { if (!isFinite(x) || !isFinite(y)) return; const [X, Y] = this._pt(x, y);
    this._cur = { p: [X, Y], closed: false, sh: null }; this._path.push(this._cur); this._has = true; this._lx = X; this._ly = Y; }
  _lineDev(X, Y) { if (!this._has) { this._cur = { p: [X, Y], closed: false, sh: null }; this._path.push(this._cur); this._has = true; }
    else { if (!this._cur) { this._cur = { p: [this._lx, this._ly], closed: false, sh: null }; this._path.push(this._cur); } this._cur.p.push(X, Y); }
    this._lx = X; this._ly = Y; }
  lineTo(x, y) { if (!isFinite(x) || !isFinite(y)) return; const [X, Y] = this._pt(x, y); this._lineDev(X, Y); }
  closePath() { const c = this._cur; if (!c) return; c.closed = true; this._lx = c.p[0]; this._ly = c.p[1]; this._cur = null; }
  rect(x, y, w, h) { if (![x, y, w, h].every(isFinite)) return; const m = this._s.m, a = this._pt(x, y), b = this._pt(x + w, y), c = this._pt(x + w, y + h), d = this._pt(x, y + h);
    const sub = { p: [a[0], a[1], b[0], b[1], c[0], c[1], d[0], d[1]], closed: true, sh: null };
    if (m[1] === 0 && m[2] === 0) sub.sh = { k: "rect", x0: Math.min(a[0], c[0]), y0: Math.min(a[1], c[1]), x1: Math.max(a[0], c[0]), y1: Math.max(a[1], c[1]) };
    this._path.push(sub); this._cur = null; this._has = true; this._lx = a[0]; this._ly = a[1]; }
  arc(x, y, r, a0, a1, ccw) { this.ellipse(x, y, r, r, 0, a0, a1, ccw); }
  ellipse(x, y, rx, ry, rot, a0, a1, ccw) {
    if (![x, y, rx, ry, rot, a0, a1].every(isFinite)) return; if (rx < 0 || ry < 0) throw new RangeError("ellipse: negative radius");
    let sw = a1 - a0; const full = ccw ? -sw >= TAU : sw >= TAU;
    if (!full) { sw %= TAU; if (!ccw && sw < 0) sw += TAU; if (ccw && sw > 0) sw -= TAU; } else sw = ccw ? -TAU : TAU;
    const m = this._s.m, sim = Math.abs(m[0] - m[3]) < 1e-9 && Math.abs(m[1] + m[2]) < 1e-9, sc = Math.sqrt(Math.abs(m[0] * m[3] - m[1] * m[2]));
    if (full && sim && !this._cur) {   // a whole circle or ellipse starting a subpath: one analytic instance
      const [cx, cy] = this._pt(x, y), ang = rot + Math.atan2(m[1], m[0]);
      this._path.push({ p: [], closed: false, sh: { k: "ell", cx, cy, rx: rx * sc, ry: ry * sc, a: ang } }); this._cur = null; this._has = true;
      const ex = x + Math.cos(rot) * rx * Math.cos(a1) - Math.sin(rot) * ry * Math.sin(a1), ey = y + Math.sin(rot) * rx * Math.cos(a1) + Math.cos(rot) * ry * Math.sin(a1);
      [this._lx, this._ly] = this._pt(ex, ey); return; }
    const n = Math.max(4, Math.min(256, Math.ceil(Math.abs(sw) * Math.max(rx, ry) * sc / 2))), cr = Math.cos(rot), sr = Math.sin(rot);
    for (let i = 0; i <= n; i++) { const t = a0 + sw * i / n, lx = rx * Math.cos(t), ly = ry * Math.sin(t);
      const [X, Y] = this._pt(x + lx * cr - ly * sr, y + lx * sr + ly * cr);
      if (i === 0 && !this._has) { this._cur = { p: [X, Y], closed: false, sh: null }; this._path.push(this._cur); this._has = true; this._lx = X; this._ly = Y; }
      else this._lineDev(X, Y); } }
  quadraticCurveTo(cx, cy, x, y) { if (![cx, cy, x, y].every(isFinite)) return; if (!this._has) this.moveTo(cx, cy);
    const m = this._s.m, inv = this._inv(); if (!inv) return; const p0 = [inv[0] * this._lx + inv[2] * this._ly + inv[4], inv[1] * this._lx + inv[3] * this._ly + inv[5]];
    for (let i = 1; i <= 16; i++) { const t = i / 16, u = 1 - t; this.lineTo(u * u * p0[0] + 2 * u * t * cx + t * t * x, u * u * p0[1] + 2 * u * t * cy + t * t * y); } }
  bezierCurveTo(c1x, c1y, c2x, c2y, x, y) { if (![c1x, c1y, c2x, c2y, x, y].every(isFinite)) return; if (!this._has) this.moveTo(c1x, c1y);
    const inv = this._inv(); if (!inv) return; const p0 = [inv[0] * this._lx + inv[2] * this._ly + inv[4], inv[1] * this._lx + inv[3] * this._ly + inv[5]];
    for (let i = 1; i <= 20; i++) { const t = i / 20, u = 1 - t;
      this.lineTo(u * u * u * p0[0] + 3 * u * u * t * c1x + 3 * u * t * t * c2x + t * t * t * x, u * u * u * p0[1] + 3 * u * u * t * c1y + 3 * u * t * t * c2y + t * t * t * y); } }
  arcTo(x1, y1) { unsup("arcTo"); this.lineTo(x1, y1); }
  roundRect(x, y, w, h) { unsup("roundRect"); this.rect(x, y, w, h); }
  _inv() { const m = this._s.m, d = m[0] * m[3] - m[1] * m[2]; if (!d) return null;
    return [m[3] / d, -m[1] / d, -m[2] / d, m[0] / d, (m[2] * m[5] - m[3] * m[4]) / d, (m[1] * m[4] - m[0] * m[5]) / d]; }
  // drawing
  clip() { unsup("clip"); }
  isPointInPath() { return false; }
  fill(a, b) { if (a && typeof a === "object") { unsup("Path2D"); return; } if ((typeof a === "string" ? a : b) === "evenodd") unsup("evenodd");
    prims.length = 0; for (const s of this._path) fillPrims(s); this._emit(this._s.fillP, false); }
  stroke(p) { if (p && typeof p === "object") { unsup("Path2D"); return; } const m = this._s.m, lw = this._s.lw * Math.sqrt(Math.abs(m[0] * m[3] - m[1] * m[2]));
    prims.length = 0; for (const s of this._path) strokePrims(s, lw); this._emit(this._s.strokeP, true); }
  fillRect(x, y, w, h) { if (!(isFinite(x) && isFinite(y) && isFinite(w) && isFinite(h)) || !w || !h) return; const s = this._s, m = s.m;
    if (m[1] === 0 && m[2] === 0) {   // the hot path (motes, pixels): one instance, no allocation
      if (s.alpha <= 0) return; const S = this._sink; if (!paintFrom(S, s.fillP, m)) return;
      if (s.shadowBlur > 0 || (s.filter && s.filter !== "none")) unsup("fillRect:effects");
      const X0 = m[0] * x + m[4], Y0 = m[3] * y + m[5], X1 = m[0] * (x + w) + m[4], Y1 = m[3] * (y + h) + m[5];
      const x0 = X0 < X1 ? X0 : X1, y0 = Y0 < Y1 ? Y0 : Y1, x1 = X0 < X1 ? X1 : X0, y1 = Y0 < Y1 ? Y1 : Y0, bl = BLEND[s.comp];
      if (bl === undefined) unsup("comp:" + s.comp);
      S.put(RECT | (bl || 0) << 5 | PT << 7 | S.tgt << 9, x0, y0, x1, y1, 0, 0, 0, s.alpha, P0, P1, P2, P3, PAL, x0 - 1, y0 - 1, x1 + 1, y1 + 1); return; }
    prims.length = 0; const a = this._pt(x, y), b = this._pt(x + w, y), c = this._pt(x + w, y + h), d = this._pt(x, y + h);
    fanPrims([a[0], a[1], b[0], b[1], c[0], c[1], d[0], d[1]]); this._emit(s.fillP, false); }
  strokeRect(x, y, w, h) { const p = this._path, c = this._cur, hs = this._has; this.beginPath(); this.rect(x, y, w, h); this.stroke(); this._path = p; this._cur = c; this._has = hs; }
  clearRect(x, y, w, h) { const S = this._sink, cv = this.canvas, m = this._s.m;
    const a = this._pt(x, y), c = this._pt(x + w, y + h);
    if (Math.min(a[0], c[0]) <= 0 && Math.min(a[1], c[1]) <= 0 && Math.max(a[0], c[0]) >= cv.width && Math.max(a[1], c[1]) >= cv.height) { S.reset(); return; }
    if (w && h) unsup("clearRect:partial"); }
  // one path's primitives -> instances. One primitive paints directly; several build a union in the coverage attachment
  // first and are painted once by a resolve instance (a canvas fill or stroke covers each pixel once per path).
  _emit(style, stroke) {
    const n = prims.length; if (!n) return; const s = this._s, S = this._sink;
    if (s.shadowBlur > 0 || s.shadowOffsetX || s.shadowOffsetY) { const sc = color(s.shadowColor); if (sc && sc[3] > 0) unsup("shadow"); }
    if (s.filter && s.filter !== "none") unsup("filter");
    if (s.alpha <= 0 || !paintFrom(S, style, s.m)) return;
    const bl = BLEND[s.comp], tg = S.tgt << 9, base = (bl === undefined ? 0 : bl) << 5 | PT << 7 | tg;
    if (bl === undefined) unsup("comp:" + s.comp);
    if (n === 1) { const p = prims[0]; S.put(p[0] | base, p[1], p[2], p[3], p[4], p[5], p[6], p[7], s.alpha, P0, P1, P2, P3, PAL, p[8], p[9], p[10], p[11]); return; }
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    for (const p of prims) { S.put(p[0] | 1 << 3 | tg, p[1], p[2], p[3], p[4], p[5], p[6], p[7], 0, 0, 0, 0, 0, 0, p[8], p[9], p[10], p[11]);
      if (p[8] < x0) x0 = p[8]; if (p[9] < y0) y0 = p[9]; if (p[10] > x1) x1 = p[10]; if (p[11] > y1) y1 = p[11]; }
    S.put(RES | base, 0, 0, 0, 0, 0, 0, 0, s.alpha, P0, P1, P2, P3, PAL, x0, y0, x1, y1); }
  drawImage(img, a, b, c, d, e, f, g, h) {
    if (!img || !img._ctx) { if (img) unsup("drawImage:source"); return; }
    const nArg = arguments.length, iw = img._w, ih = img._h;
    let sx = 0, sy = 0, sw = iw, sh = ih, dx, dy, dw, dh;
    if (nArg >= 9) { sx = a; sy = b; sw = c; sh = d; dx = e; dy = f; dw = g; dh = h; unsup("drawImage:subrect"); }
    else if (nArg >= 5) { dx = a; dy = b; dw = c; dh = d; } else { dx = a; dy = b; dw = iw; dh = ih; }
    if (!(isFinite(dx) && isFinite(dy) && isFinite(dw) && isFinite(dh)) || !dw || !dh || !sw || !sh) return;
    const src = img._ctx._sink, st = this._s, m = st.m, S = this._sink;
    if (src.n === 0 || st.alpha <= 0) return;
    if (src.n !== 1 || m[1] !== 0 || m[2] !== 0) { unsup(src.n !== 1 ? "drawImage:complex" : "drawImage:rotated"); return; }
    // the sprite's one fill, analysed once per sprite canvas (it never changes after it is drawn)
    let D = src._dimg;
    if (!D || D.ver !== src.ver) { const F = src.f, code = F[0] | 0, kind = code & 7, pt = code >> 7 & 3;
      if ((code >> 3 & 3) !== 0 || (kind !== RECT && kind !== ELL)) { unsup("drawImage:kind"); return; }
      if (kind === ELL && (F[6] > 0 || Math.abs(F[3] - F[4]) > 1e-6)) unsup("drawImage:ellipse");
      D = src._dimg = { ver: src.ver, kind, pt, a: F[8], g0: F[9], g1: F[10], g2: F[11], g3: F[12], grad: pt ? src.grads[F[13]] : null,
        sx0: kind === RECT ? Math.max(0, Math.min(F[1], F[3])) : 0, sy0: kind === RECT ? Math.max(0, Math.min(F[2], F[4])) : 0,
        sx1: kind === RECT ? Math.min(iw, Math.max(F[1], F[3])) : iw, sy1: kind === RECT ? Math.min(ih, Math.max(F[2], F[4])) : ih,
        ecx: F[1], ecy: F[2], er: F[3], tex: iw * 65536 + ih }; }
    // sprite space -> destination: X = ox + x * kx (axis-aligned)
    const kx = dw / sw * m[0], ky = dh / sh * m[3], ox = m[0] * dx + m[4] - sx * kx, oy = m[3] * dy + m[5] - sy * ky, pt = D.pt;
    let pal = 0, p0 = D.g0, p1 = D.g1, p2 = D.g2, p3 = D.g3;
    if (pt === 1) { const K = Math.sqrt(Math.abs(kx * ky)); p0 = ox + D.g0 * kx; p1 = oy + D.g1 * ky; p2 = D.g2 * K; p3 = D.g3 * K; pal = S.palOf(D.grad); }
    else if (pt === 2) { p0 = ox + D.g0 * kx; p1 = oy + D.g1 * ky; p2 = ox + D.g2 * kx; p3 = oy + D.g3 * ky; pal = S.palOf(D.grad); }
    const bl = BLEND[st.comp], base = (bl === undefined ? 0 : bl) << 5 | pt << 7 | S.tgt << 9;
    // one quad over the sprite's painted area within the destination rect; the shader samples the sprite's texels
    const ax = ox + Math.max(sx, D.sx0) * kx, bx = ox + Math.min(sx + sw, D.sx1) * kx, ay = oy + Math.max(sy, D.sy0) * ky, by = oy + Math.min(sy + sh, D.sy1) * ky;
    const x0 = ax < bx ? ax : bx, x1 = ax < bx ? bx : ax, y0 = ay < by ? ay : by, y1 = ay < by ? by : ay;
    if (x1 <= x0 || y1 <= y0) return;
    S.put(RECT | base, x0, y0, x1, y1, D.kind === ELL ? 1 : 0, D.ecx, D.ecy, st.alpha * D.a, p0, p1, p2, p3, pal, x0 - 1, y0 - 1, x1 + 1, y1 + 1);
    const o = (S.n - 1) * ST, ff = S.f; ff[o + 18] = D.tex; ff[o + 19] = D.kind === ELL ? D.er : 0; ff[o + 20] = ox; ff[o + 21] = oy; ff[o + 22] = kx; ff[o + 23] = ky; }
  // text and pixels: not on the calm path (hover labels only); see docs/NATIVE_PORT.md "Labels"
  fillText() { unsup("fillText"); } strokeText() { unsup("strokeText"); }
  measureText(t) { const px = parseFloat((/([\d.]+)px/.exec(this._s.font) || [0, 10])[1]); return { width: String(t).length * px * 0.55, actualBoundingBoxAscent: px * 0.7, actualBoundingBoxDescent: px * 0.2 }; }
  getImageData(x, y, w, h) { unsup("getImageData"); return { width: w, height: h, data: new Uint8ClampedArray(Math.max(0, w * h * 4)) }; }
  putImageData() { unsup("putImageData"); }
  createImageData(w, h) { return { width: w, height: h, data: new Uint8ClampedArray(w * h * 4) }; }
  setLineDash() { unsup("setLineDash"); } getLineDash() { return []; }
  drawFocusIfNeeded() {}
  // species layers (stage.html drawLayer): everything between the markers composites as one layer, source-over, as each
  // species' own iframe used to (docs/NATIVE_PORT.md: the per-layer look, not glows of two species adding)
  __beginLayer() { const S = this._sink; if (!S.main) return; S.tgt = 1; S.lb = [Infinity, Infinity, -Infinity, -Infinity]; }
  // hover labels (stage.html drawLabels wraps each SpritesLabels.draw in these): text, shadows, blur, clip and curves are
  // not instanced, so between the markers every call goes to app/native/cmdrec.js instead; at __endLabel the host
  // rasterizes the recording with CoreGraphics (CGCanvas.swift) into one texture, drawn here as ONE textured rect
  // (paint 3, slot in field 13, texture origin in device px in 9-10), source-over, in call order. Up to MAXLABELS a frame.
  // Without CmdCanvas or a host rasterizer (node tests) the calls record as before (text unsupported).
  __beginLabel() { const S = this._sink, CC = G.CmdCanvas, N = G.__native; if (!S.main || !CC || !N || typeof N.label !== "function" || this._lab) return false;
    const u = +N.dpr > 0 ? +N.dpr : 1, cv = this.canvas;
    if (!CC.begin(this, u, { bounds: [0, 0, cv._w / u, cv._h / u] })) return false; this._lab = u; return true; }
  __endLabel() { const u = this._lab; if (!u) return; this._lab = 0; const r = G.CmdCanvas.end(this), S = this._sink; if (!r) return;
    if (S.labn >= MAXLABELS) { unsup("labels>" + MAXLABELS); return; }
    const [bx, by, bw, bh] = r.box, slot = S.labn;
    if (G.__native.label(r.json, slot, bx, by, bw, bh, u) !== true) { unsup("label:raster"); return; }
    S.labn++; const x0 = bx * u, y0 = by * u, x1 = x0 + Math.round(bw * u), y1 = y0 + Math.round(bh * u);
    S.put(RECT | 3 << 7 | S.tgt << 9, x0, y0, x1, y1, 0, 0, 0, 1, x0, y0, 0, 0, slot, x0, y0, x1, y1); }
  __endLayer() { const S = this._sink; if (!S.main || !S.tgt) return; S.tgt = 0; const b = S.lb; if (b[2] <= b[0]) return;
    S.put(LAYER, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, Math.max(0, Math.floor(b[0])), Math.max(0, Math.floor(b[1])), Math.ceil(b[2]), Math.ceil(b[3])); S.layers++; }
}
const COMPS = { "source-over": 1, "lighter": 1, "source-in": 1, "source-atop": 1, "destination-out": 1, "destination-in": 1, "copy": 1, "multiply": 1, "screen": 1, "xor": 1 };
for (const k of ["font", "textAlign", "textBaseline", "lineCap", "lineJoin", "miterLimit", "shadowBlur", "shadowColor", "shadowOffsetX", "shadowOffsetY",
  "filter", "letterSpacing", "imageSmoothingEnabled", "imageSmoothingQuality", "direction", "lineDashOffset"])
  Object.defineProperty(CanvasRenderingContext2D.prototype, k, { configurable: true, enumerable: true, get() { return this._s[k]; }, set(v) { this._s[k] = v; } });

// path -> primitives
function fillPrims(s) {
  if (s.sh && s.sh.k === "ell") { const e = s.sh, r = Math.max(e.rx, e.ry) + 1.5; if (e.rx > 0 && e.ry > 0) prim(ELL, e.cx, e.cy, e.rx, e.ry, e.a, 0, 0, e.cx - r, e.cy - r, e.cx + r, e.cy + r); return; }
  if (s.sh && s.sh.k === "rect") { const r = s.sh; if (r.x1 > r.x0 && r.y1 > r.y0) prim(RECT, r.x0, r.y0, r.x1, r.y1, 0, 0, 0, r.x0 - 1, r.y0 - 1, r.x1 + 1, r.y1 + 1); return; }
  fanPrims(s.p); }
function fanPrims(p0) {
  const p = []; for (let i = 0; i < p0.length; i += 2) { const n = p.length; if (n && p[n - 2] === p0[i] && p[n - 1] === p0[i + 1]) continue; p.push(p0[i], p0[i + 1]); }
  if (p.length > 2 && p[0] === p[p.length - 2] && p[1] === p[p.length - 1]) p.length -= 2;
  const n = p.length / 2; if (n < 3) return;
  let sgn = 0, conv = true; for (let i = 0; i < n; i++) { const a = i * 2, b = (i + 1) % n * 2, c = (i + 2) % n * 2;
    const cr = (p[b] - p[a]) * (p[c + 1] - p[b + 1]) - (p[b + 1] - p[a + 1]) * (p[c] - p[b]); if (Math.abs(cr) < 1e-9) continue;
    if (!sgn) sgn = Math.sign(cr); else if (Math.sign(cr) !== sgn) conv = false; }
  if (!conv) unsup("fill:concave");
  for (let i = 1; i < n - 1; i++) { const ax = p[0], ay = p[1], bx = p[i * 2], by = p[i * 2 + 1], cx = p[i * 2 + 2], cy = p[i * 2 + 3];
    if (Math.abs((bx - ax) * (cy - ay) - (by - ay) * (cx - ax)) < 1e-6) continue;
    const ext = (i === 1 ? 1 : 0) | 2 | (i === n - 2 ? 4 : 0);
    prim(TRI, ax, ay, bx, by, cx, cy, ext, Math.min(ax, bx, cx) - 1.5, Math.min(ay, by, cy) - 1.5, Math.max(ax, bx, cx) + 1.5, Math.max(ay, by, cy) + 1.5); } }
// A segment quad with its ends pushed out by e0/e1 (px along the segment). Interior joints of a polyline extend both
// neighbours by half the line width (a square join), so the outer wedge a butt cap leaves open is covered; the path's
// union (max coverage) keeps the overlap from doubling. The path's own ends stay butt, as the canvas default.
function seg(x0, y0, x1, y1, lw, e0, e1) { const dx = x1 - x0, dy = y1 - y0, L = Math.hypot(dx, dy); if (!L) return;
  const ux = dx / L, uy = dy / L; x0 -= ux * e0; y0 -= uy * e0; x1 += ux * e1; y1 += uy * e1; const e = lw / 2 + 1.5;
  prim(SEG, x0, y0, x1, y1, lw, 0, 0, Math.min(x0, x1) - e, Math.min(y0, y1) - e, Math.max(x0, x1) + e, Math.max(y0, y1) + e); }
function strokePrims(s, lw) {
  if (s.sh && s.sh.k === "ell") { const e = s.sh, r = Math.max(e.rx, e.ry) + lw / 2 + 1.5; prim(ELL, e.cx, e.cy, e.rx, e.ry, e.a, lw, 0, e.cx - r, e.cy - r, e.cx + r, e.cy + r); return; }
  const p = s.p, n = p.length / 2, h = lw / 2, cl = s.closed && n > 2, m = cl ? n : n - 1;
  for (let i = 0; i < m; i++) { const j = (i + 1) % n;
    seg(p[i * 2], p[i * 2 + 1], p[j * 2], p[j * 2 + 1], lw, (cl || i > 0) ? h : 0, (cl || i < m - 1) ? h : 0); } }

// ---------- canvas elements ----------
let mainSink = null;
class HTMLCanvasElement {
  constructor() { this._w = 300; this._h = 150; this._ctx = null; this._main = false; this.style = {}; this.attrs = {}; this._isCanvas = true; }
  get width() { return this._w; } set width(v) { this._w = Math.max(0, v | 0); this._clear(); }
  get height() { return this._h; } set height(v) { this._h = Math.max(0, v | 0); this._clear(); }
  _clear() { if (this._ctx) { this._ctx._sink.reset(); this._ctx._reset(); } }
  getContext(kind) { if (kind !== "2d") return null;
    if (!this._ctx) this._ctx = new CanvasRenderingContext2D(this, this._main ? (mainSink = mainSink || new Sink(true)) : new Sink(false)); return this._ctx; }
  _attach() { if (this._main) return; this._main = true; mainSink = mainSink || new Sink(true); if (this._ctx) this._ctx._sink = mainSink; G.__rec = this; }
  setAttribute(k, v) { this.attrs[k] = String(v); } getAttribute(k) { return this.attrs[k] ?? null; }
  addEventListener() {} removeEventListener() {}
  getBoundingClientRect() { return { left: 0, top: 0, width: this._w, height: this._h, x: 0, y: 0 }; }
  toDataURL() { unsup("toDataURL"); return "data:,"; }
}
G.CanvasRenderingContext2D = CanvasRenderingContext2D; G.CanvasGradient = CanvasGradient; G.HTMLCanvasElement = HTMLCanvasElement;
// Swift reads the frame through this: the main canvas, its sink and counters
G.__nativeFrame = () => { const c = G.__rec, S = mainSink; if (!c || !S) return null;
  return { w: c._w, h: c._h, n: S.n, f: S.f, paln: S.paln, pal: S.pal, ver: S.ver, layers: S.layers, labn: S.labn }; };
G.__nativeVer = () => mainSink ? mainSink.ver : 0;
})(globalThis);
