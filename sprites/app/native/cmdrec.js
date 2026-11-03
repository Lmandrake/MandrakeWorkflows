/* Sprites native renderer: full-fidelity 2D command recorder for the hover labels (docs/NATIVE_PORT.md "Labels").
 * canvas.js turns the calm-path canvas calls into GPU instances; the labels (prototype/labels/labels.js) use what that
 * cannot express (text, shadows, filter blur, clip, curves, offscreen glyph canvases, source-in), so while a label draws,
 * its calls are recorded here into one compact op array that app/macos/CGCanvas.swift replays into a Core Graphics
 * bitmap, drawn by Metal as one textured quad.
 *
 * ---- JS API (globalThis.CmdCanvas) ----
 *   new CmdCanvas(w = 300, h = 150)   a canvas element; getContext("2d") -> CmdCanvas.Context2D (records, never draws).
 *   CmdCanvas.begin(ctx, dpr, opt)    from now on every 2D call and setter on `ctx` (any context object, e.g. canvas.js's)
 *                                     is recorded here instead (own-property forwarders shadow its prototype; nothing of
 *                                     ctx's own state changes). The recording starts from ctx's state (canvas.js `_s`, else
 *                                     its getters); its current transform is read as device px and divided by `dpr`.
 *                                     While recording, document.createElement("canvas") returns CmdCanvas elements (the
 *                                     labels' glyph caches are created inside draw and stay CmdCanvas for good).
 *                                     opt.bounds = [x, y, w, h] CSS px clamps the returned box (e.g. the screen).
 *   CmdCanvas.end(ctx) -> null | { ops, box: [x, y, w, h], json }   removes the forwarders. box: integral CSS px enclosing
 *                                     every recorded pixel (strokes, shadows and blur included, clipped by clip());
 *                                     json = JSON.stringify(ops) (lazy). null when nothing was drawn.
 *     Hand both to Swift: CGCanvas.render(ops:, width: box.w, height: box.h, scale: dpr, originX: box.x, originY: box.y).
 *   CmdCanvas.stats.unsupported       counts of calls that are not replayed exactly (Path2D, patterns, line dash, ...).
 *
 * ---- host interface: __native.cg(request: string, out?: Uint8ClampedArray) -> string (synchronous) ----
 *   Implemented by CGCanvas.install(into: __native) (app/macos/CGCanvas.swift). request is JSON:
 *   {"q":"measure","font":CSS font,"text":s}  -> JSON {w, l, r, a, d, fa, fd, ea, ed, hg}: CoreText advance width and ink
 *        bounds (left/right of the origin, ascent/descent of the alphabetic baseline) of `text` with no letter spacing,
 *        plus the font's ascent/descent (rounded, as Blink), normalized OS/2 typo em ascent/descent and hanging baseline.
 *        Cached here per font + text; letterSpacing, textAlign and textBaseline are applied in JS.
 *   {"q":"pixels","ops":[D ops],"key":k,"x","y","w","h"} -> "ok" (or "error: ..."): rasterizes the offscreen canvas
 *        definitions in ops (see "D" below; Swift caches rasters by key), then writes the rectangle of canvas `key` into
 *        `out` (length w*h*4) as unpremultiplied RGBA, as getImageData returns it. Pixels outside the canvas are 0.
 *
 * ---- op array (flat, JSON-serialisable: an op string followed by its arguments) ----
 *   Units: "CSS space" = the main canvas's CSS px (device px / dpr); for an offscreen canvas, its own px. Path points are
 *   transformed when added (canvas semantics) and stored in CSS space; everything else is in user space under "M".
 *   s / r                         save / restore (state and clip)
 *   M a b c d e f                 current transform, user -> CSS space
 *   A alpha · C comp (string) · IS 0|1 (imageSmoothingEnabled) · IQ quality (string)
 *   F paint · S paint             fill / stroke paint. paint = 0 r g b a (0..1, unpremultiplied)
 *                                 | 1 x0 y0 x1 y1 n (o r g b a)*n (linear) | 2 x0 y0 r0 x1 y1 r1 n (o r g b a)*n (radial)
 *   W lw · LC cap · LJ join · ML miterLimit
 *   SH blur ox oy r g b a         shadow, blur/offsets in CSS space units (canvas values are device px, so / dpr)
 *   FI sigma                      filter: Gaussian blur sigma in CSS space units (0 = none)
 *   FN css font · LS px           font (CSS string, parsed by Swift) · letter spacing (user space px)
 *   P [path]                      current path: 0 x y move · 1 x y line · 2 cx cy x y quad · 3 c1x c1y c2x c2y x y cubic · 4 close
 *   f rule · k · c rule           fill / stroke / clip the current path (rule "nonzero" | "evenodd")
 *   X                             clear the current path's area (clearRect)
 *   T mode text x y sx            fill (0) or stroke (1) text: origin is the LEFT end of the ALPHABETIC baseline in user
 *                                 space (align and baseline already applied here), sx = horizontal scale (maxWidth)
 *   I key sx sy sw sh dx dy dw dh drawImage of offscreen canvas `key`, source rect in its px, destination in user space
 *   D key w h [ops]               defines offscreen canvas `key` (w x h px, its own op array); precedes any I or pixel read
 *                                 that uses it. Keys are "<id>@<version>", unique per JS load, so a raster cache is safe.
 * Unrecorded state is the canvas default: identity, alpha 1, source-over, black, lw 1, butt, miter, 10, no shadow,
 * no filter, "10px sans-serif", no spacing, smoothing on ("low"). */
(function (G) {
"use strict";
const TAU = Math.PI * 2;
const stats = { unsupported: {} };
const unsup = k => { stats.unsupported[k] = (stats.unsupported[k] || 0) + 1; };
const TOKEN = Math.floor(Math.random() * 2176782336).toString(36);
let NEXT = 0;

// ---------- colours: CSS -> [r, g, b, a] 0..1, 8-bit as the browser stores them ----------
const NAMED = { transparent: [0, 0, 0, 0], black: [0, 0, 0, 1], white: [1, 1, 1, 1], red: [1, 0, 0, 1], green: [0, 128 / 255, 0, 1],
  blue: [0, 0, 1, 1], yellow: [1, 1, 0, 1], gray: [128 / 255, 128 / 255, 128 / 255, 1], grey: [128 / 255, 128 / 255, 128 / 255, 1],
  orange: [1, 165 / 255, 0, 1], cyan: [0, 1, 1, 1], magenta: [1, 0, 1, 1] };
const ccache = new Map();
const b8 = v => Math.round(Math.max(0, Math.min(1, v)) * 255) / 255;
const num = (s, full) => s.endsWith("%") ? parseFloat(s) / 100 * full : parseFloat(s);
function parseColor(s) {
  if (s[0] === "#") { let h = s.slice(1); if (h.length === 3 || h.length === 4) h = h.split("").map(c => c + c).join("");
    if (!/^[0-9a-f]{6}([0-9a-f]{2})?$/.test(h)) return null; const n = parseInt(h.slice(0, 6), 16);
    return [(n >> 16) / 255, (n >> 8 & 255) / 255, (n & 255) / 255, h.length === 8 ? parseInt(h.slice(6), 16) / 255 : 1]; }
  const m = /^(rgba?|hsla?)\((.*)\)$/.exec(s); if (!m) return NAMED[s] ? NAMED[s].slice() : null;
  const p = m[2].split(/[\s,\/]+/).filter(Boolean); if (p.length < 3) return null;
  const a = p.length > 3 ? b8(num(p[3], 1)) : 1; if (!isFinite(a)) return null;
  if (m[1][0] === "r") { const c = [0, 1, 2].map(i => b8(num(p[i], 255) / 255)); if (!c.every(isFinite)) return null; c.push(a); return c; }
  let H = parseFloat(p[0]); if (p[0].endsWith("turn")) H *= 360; else if (p[0].endsWith("rad")) H *= 180 / Math.PI;
  const S = Math.max(0, Math.min(1, parseFloat(p[1]) / 100)), L = Math.max(0, Math.min(1, parseFloat(p[2]) / 100));
  if (!(isFinite(H) && isFinite(S) && isFinite(L))) return null;
  const hh = ((H % 360) + 360) % 360, A = S * Math.min(L, 1 - L);
  const f = n => { const k = (n + hh / 30) % 12; return L - A * Math.max(-1, Math.min(k - 3, 9 - k, 1)); };
  return [b8(f(0)), b8(f(8)), b8(f(4)), a];
}
function color(v) { if (typeof v !== "string") return null; let c = ccache.get(v); if (c !== undefined) return c;
  if (ccache.size > 5000) ccache.clear(); c = parseColor(v.trim().toLowerCase()); ccache.set(v, c); return c; }

class CmdGradient {
  constructor(type, g) { this.type = type; this.g = g; this.stops = []; this.gen = 0; this.id = ++NEXT; }
  addColorStop(o, c) { o = +o; if (!(o >= 0 && o <= 1)) throw new RangeError("addColorStop: offset out of range");
    const col = color(String(c)); if (!col) throw new SyntaxError("addColorStop: bad colour " + c);
    let i = this.stops.length; while (i > 0 && this.stops[i - 1][0] > o) i--;
    this.stops.splice(i, 0, [o, col[0], col[1], col[2], col[3]]); this.gen++; }
}
// a gradient object from another implementation (canvas.js: type 1 radial / 2 linear, g, stops [o, r, g, b, a])
function adoptGradient(v) { if (v instanceof CmdGradient) return v;
  if (v && v.g && v.stops && (v.type === 1 || v.type === 2)) { const g = new CmdGradient(v.type === 1 ? 2 : 1, v.g.slice()); g.stops = v.stops.map(s => s.slice()); return g; }
  return null; }

// ---------- text metrics through the host, cached per font + text ----------
const mcache = new Map();
function hostMeasure(font, text) { const key = font + "\u0001" + text; let m = mcache.get(key); if (m) return m;
  const cg = G.__native && G.__native.cg;
  if (typeof cg === "function") { try { m = JSON.parse(cg(JSON.stringify({ q: "measure", font, text }))); } catch (e) { m = null; } }
  if (!m) { unsup("measure:nohost"); const px = fontPx(font); m = { w: [...text].length * px * 0.55, l: 0, r: [...text].length * px * 0.55, a: px * 0.7, d: px * 0.2,
    fa: Math.round(px * 0.9), fd: Math.round(px * 0.25), ea: px * 0.78, ed: px * 0.22, hg: px * 0.72 }; }
  if (mcache.size > 4000) mcache.clear(); mcache.set(key, m); return m; }
function fontPx(font) { const m = /(?:^|\s)([\d.]+)(px|pt|em|rem|%)(?:\s*\/\s*\S+)?\s+[^\s]/.exec(font || ""); if (!m) return 10;
  const v = parseFloat(m[1]), u = m[2] || "px"; return u === "pt" ? v * 4 / 3 : u === "em" || u === "rem" ? v * 16 : u === "%" ? v / 100 * 16 : v; }

// ---------- state ----------
const DEF = { alpha: 1, comp: "source-over", fillV: "#000000", fillP: [0, 0, 0, 1], strokeV: "#000000", strokeP: [0, 0, 0, 1], lw: 1,
  lineCap: "butt", lineJoin: "miter", miterLimit: 10, shadowBlur: 0, shadowColor: "rgba(0, 0, 0, 0)", shadowC: [0, 0, 0, 0],
  shadowOffsetX: 0, shadowOffsetY: 0, filter: "none", fsig: 0, font: "10px sans-serif", textAlign: "start", textBaseline: "alphabetic",
  letterSpacing: "0px", direction: "inherit", imageSmoothingEnabled: true, imageSmoothingQuality: "low", lineDashOffset: 0,
  wordSpacing: "0px", fontKerning: "auto", clipB: null };
class State { constructor(o) { if (o) { Object.assign(this, o); this.m = o.m.slice(); } else { Object.assign(this, DEF); this.m = [1, 0, 0, 1, 0, 0]; } } }
const COMPS = new Set(["source-over", "source-in", "source-out", "source-atop", "destination-over", "destination-in", "destination-out",
  "destination-atop", "lighter", "copy", "xor", "multiply", "screen", "overlay", "darken", "lighten", "color-dodge", "color-burn",
  "hard-light", "soft-light", "difference", "exclusion", "hue", "saturation", "color", "luminosity"]);
const UNBOUNDED = new Set(["source-in", "source-out", "destination-in", "destination-atop", "copy"]);
// the emitted-state mirror: what Swift currently holds (default = Swift's initial state)
const EDEF = { M: "1,0,0,1,0,0", A: 1, C: "source-over", F: "c0,0,0,1", S: "c0,0,0,1", W: 1, LC: "butt", LJ: "miter", ML: 10,
  SH: "0,0,0,0,0,0,0", FI: 0, FN: "10px sans-serif", LS: 0, IS: 1, IQ: "low" };
const NF = 1, NS = 2, NL = 4, NT = 8, NI = 16;   // what a draw needs synced besides M, A, C, SH, FI

class Context2D {
  constructor(canvas, u) { this.canvas = canvas; this._u = u || 1; this._init(); }
  _init() { this._s = new State(); this._st = []; this._o = []; this._E = Object.assign({}, EDEF); this._Es = [];
    this._p = []; this._pd = true; this._has = false; this._cx = 0; this._cy = 0; this._sx = 0; this._sy = 0;
    this._bb = [Infinity, Infinity, -Infinity, -Infinity]; this._deps = new Map(); this._ver = (this._ver || 0) + 1; this._drew = false; }
  // ----- state -----
  save() { this._st.push(new State(this._s)); this._Es.push(Object.assign({}, this._E)); this._push("s"); }
  restore() { if (!this._st.length) return; this._s = this._st.pop(); this._E = this._Es.pop(); this._push("r"); }
  reset() { this._init(); }
  get globalAlpha() { return this._s.alpha; } set globalAlpha(v) { v = +v; if (v >= 0 && v <= 1) this._s.alpha = v; }
  get globalCompositeOperation() { return this._s.comp; } set globalCompositeOperation(v) { if (COMPS.has(v)) this._s.comp = v; }
  get fillStyle() { return this._s.fillV; } set fillStyle(v) { const p = this._paint(v); if (p) { this._s.fillV = v; this._s.fillP = p; } }
  get strokeStyle() { return this._s.strokeV; } set strokeStyle(v) { const p = this._paint(v); if (p) { this._s.strokeV = v; this._s.strokeP = p; } }
  _paint(v) { if (typeof v === "string") return color(v); const g = adoptGradient(v); if (g) return g; if (v && typeof v === "object") unsup("pattern"); return null; }
  get lineWidth() { return this._s.lw; } set lineWidth(v) { v = +v; if (v > 0 && isFinite(v)) this._s.lw = v; }
  get lineCap() { return this._s.lineCap; } set lineCap(v) { if (v === "butt" || v === "round" || v === "square") this._s.lineCap = v; }
  get lineJoin() { return this._s.lineJoin; } set lineJoin(v) { if (v === "miter" || v === "round" || v === "bevel") this._s.lineJoin = v; }
  get miterLimit() { return this._s.miterLimit; } set miterLimit(v) { v = +v; if (v > 0 && isFinite(v)) this._s.miterLimit = v; }
  get shadowBlur() { return this._s.shadowBlur; } set shadowBlur(v) { v = +v; if (v >= 0 && isFinite(v)) this._s.shadowBlur = v; }
  get shadowOffsetX() { return this._s.shadowOffsetX; } set shadowOffsetX(v) { v = +v; if (isFinite(v)) this._s.shadowOffsetX = v; }
  get shadowOffsetY() { return this._s.shadowOffsetY; } set shadowOffsetY(v) { v = +v; if (isFinite(v)) this._s.shadowOffsetY = v; }
  get shadowColor() { return this._s.shadowColor; } set shadowColor(v) { const c = color(v); if (c) { this._s.shadowColor = v; this._s.shadowC = c; } }
  get filter() { return this._s.filter; }
  set filter(v) { if (typeof v !== "string") return; const t = v.trim(); if (t === "none" || t === "") { this._s.filter = "none"; this._s.fsig = 0; return; }
    const m = /^blur\(\s*([\d.]+)(px)?\s*\)$/.exec(t); if (m) { this._s.filter = v; this._s.fsig = parseFloat(m[1]); return; }
    unsup("filter:" + t.split("(")[0]); this._s.filter = v; this._s.fsig = 0; }
  get font() { return this._s.font; } set font(v) { if (typeof v === "string" && /\d/.test(v)) this._s.font = v; }
  get textAlign() { return this._s.textAlign; } set textAlign(v) { if (["start", "end", "left", "right", "center"].includes(v)) this._s.textAlign = v; }
  get textBaseline() { return this._s.textBaseline; } set textBaseline(v) { if (["top", "hanging", "middle", "alphabetic", "ideographic", "bottom"].includes(v)) this._s.textBaseline = v; }
  get letterSpacing() { return this._s.letterSpacing; } set letterSpacing(v) { if (typeof v === "string" && /^-?[\d.]+(px|em|rem)$/.test(v.trim())) this._s.letterSpacing = v; }
  get direction() { return this._s.direction; } set direction(v) { if (["ltr", "rtl", "inherit"].includes(v)) this._s.direction = v; }
  get imageSmoothingEnabled() { return this._s.imageSmoothingEnabled; } set imageSmoothingEnabled(v) { this._s.imageSmoothingEnabled = !!v; }
  get imageSmoothingQuality() { return this._s.imageSmoothingQuality; } set imageSmoothingQuality(v) { if (["low", "medium", "high"].includes(v)) this._s.imageSmoothingQuality = v; }
  get lineDashOffset() { return this._s.lineDashOffset; } set lineDashOffset(v) { v = +v; if (isFinite(v)) this._s.lineDashOffset = v; }
  get wordSpacing() { return this._s.wordSpacing; } set wordSpacing(v) { this._s.wordSpacing = v; }
  get fontKerning() { return this._s.fontKerning; } set fontKerning(v) { this._s.fontKerning = v; }
  setLineDash(a) { if (Array.isArray(a) && a.length) unsup("setLineDash"); } getLineDash() { return []; }
  // ----- transforms (m: user -> CSS space) -----
  setTransform(a, b, c, d, e, f) { if (typeof a === "object" && a) ({ a, b, c, d, e, f } = a); const v = [a, b, c, d, e, f];
    if (v.every(isFinite)) { const u = this._u; this._s.m = v.map(x => x / u); } }
  resetTransform() { const u = this._u; this._s.m = [1 / u, 0, 0, 1 / u, 0, 0]; }
  getTransform() { const m = this._s.m, u = this._u; return { a: m[0] * u, b: m[1] * u, c: m[2] * u, d: m[3] * u, e: m[4] * u, f: m[5] * u, is2D: true }; }
  transform(a, b, c, d, e, f) { if (![a, b, c, d, e, f].every(isFinite)) return; const m = this._s.m;
    this._s.m = [m[0] * a + m[2] * b, m[1] * a + m[3] * b, m[0] * c + m[2] * d, m[1] * c + m[3] * d, m[0] * e + m[2] * f + m[4], m[1] * e + m[3] * f + m[5]]; }
  translate(x, y) { if (!isFinite(x) || !isFinite(y)) return; const m = this._s.m; m[4] += m[0] * x + m[2] * y; m[5] += m[1] * x + m[3] * y; }
  scale(x, y) { if (!isFinite(x) || !isFinite(y)) return; const m = this._s.m; m[0] *= x; m[1] *= x; m[2] *= y; m[3] *= y; }
  rotate(t) { if (!isFinite(t)) return; const c = Math.cos(t), s = Math.sin(t); this.transform(c, s, -s, c, 0, 0); }
  // ----- gradients -----
  createLinearGradient(x0, y0, x1, y1) { if (![x0, y0, x1, y1].every(isFinite)) throw new TypeError("non-finite"); return new CmdGradient(1, [x0, y0, x1, y1]); }
  createRadialGradient(x0, y0, r0, x1, y1, r1) { if (![x0, y0, r0, x1, y1, r1].every(isFinite)) throw new TypeError("non-finite");
    if (r0 < 0 || r1 < 0) throw new RangeError("radius"); return new CmdGradient(2, [x0, y0, r0, x1, y1, r1]); }
  createConicGradient() { unsup("createConicGradient"); return new CmdGradient(1, [0, 0, 0, 0]); }
  createPattern() { unsup("createPattern"); return null; }
  // ----- paths (points transformed when added, kept in CSS space) -----
  _T(x, y) { const m = this._s.m; return [m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5]]; }
  _uinv(X, Y) { const m = this._s.m, d = m[0] * m[3] - m[1] * m[2]; if (!d) return null; const x = X - m[4], y = Y - m[5]; return [(m[3] * x - m[2] * y) / d, (m[0] * y - m[1] * x) / d]; }
  beginPath() { this._p = []; this._has = false; this._pd = true; }
  _mv(X, Y) { this._p.push(0, X, Y); this._has = true; this._cx = this._sx = X; this._cy = this._sy = Y; this._pd = true; }
  _ln(X, Y) { if (!this._has) return this._mv(X, Y); this._p.push(1, X, Y); this._cx = X; this._cy = Y; this._pd = true; }
  moveTo(x, y) { if (!isFinite(x) || !isFinite(y)) return; const [X, Y] = this._T(x, y); this._mv(X, Y); }
  lineTo(x, y) { if (!isFinite(x) || !isFinite(y)) return; const [X, Y] = this._T(x, y); this._ln(X, Y); }
  closePath() { if (!this._has) return; this._p.push(4); this._cx = this._sx; this._cy = this._sy; this._pd = true; }
  quadraticCurveTo(cx, cy, x, y) { if (![cx, cy, x, y].every(isFinite)) return; if (!this._has) this.moveTo(cx, cy);
    const c = this._T(cx, cy), p = this._T(x, y); this._p.push(2, c[0], c[1], p[0], p[1]); this._cx = p[0]; this._cy = p[1]; this._pd = true; }
  bezierCurveTo(ax, ay, bx, by, x, y) { if (![ax, ay, bx, by, x, y].every(isFinite)) return; if (!this._has) this.moveTo(ax, ay);
    const a = this._T(ax, ay), b = this._T(bx, by), p = this._T(x, y); this._p.push(3, a[0], a[1], b[0], b[1], p[0], p[1]); this._cx = p[0]; this._cy = p[1]; this._pd = true; }
  rect(x, y, w, h) { if (![x, y, w, h].every(isFinite)) return; this.moveTo(x, y); this.lineTo(x + w, y); this.lineTo(x + w, y + h); this.lineTo(x, y + h); this.closePath(); }
  roundRect(x, y, w, h, radii) { if (![x, y, w, h].every(isFinite)) return;
    let r = Array.isArray(radii) ? radii : [radii == null ? 0 : radii]; r = r.map(v => typeof v === "object" && v ? (+v.x || 0) : +v || 0);
    const R = r.length === 1 ? [r[0], r[0], r[0], r[0]] : r.length === 2 ? [r[0], r[1], r[0], r[1]] : r.length === 3 ? [r[0], r[1], r[2], r[1]] : r.slice(0, 4);
    const sx = Math.sign(w) || 1, sy = Math.sign(h) || 1, aw = Math.abs(w), ah = Math.abs(h);
    let f = 1; const tot = [R[0] + R[1], R[1] + R[2], R[2] + R[3], R[3] + R[0]], lim = [aw, ah, aw, ah];
    for (let i = 0; i < 4; i++) if (tot[i] > lim[i]) f = Math.min(f, lim[i] / tot[i]);
    const [a, b, c, d] = R.map(v => Math.max(0, v * f));
    this.moveTo(x + sx * a, y); this.lineTo(x + w - sx * b, y); if (b) this.ellipse(x + w - sx * b, y + sy * b, b, b, 0, -Math.PI / 2, 0, false);
    this.lineTo(x + w, y + h - sy * c); if (c) this.ellipse(x + w - sx * c, y + h - sy * c, c, c, 0, 0, Math.PI / 2, false);
    this.lineTo(x + sx * d, y + h); if (d) this.ellipse(x + sx * d, y + h - sy * d, d, d, 0, Math.PI / 2, Math.PI, false);
    this.lineTo(x, y + sy * a); if (a) this.ellipse(x + sx * a, y + sy * a, a, a, 0, Math.PI, Math.PI * 1.5, false);
    this.closePath(); }
  arc(x, y, r, a0, a1, ccw) { this.ellipse(x, y, r, r, 0, a0, a1, ccw); }
  ellipse(x, y, rx, ry, rot, a0, a1, ccw) {
    if (![x, y, rx, ry, rot, a0, a1].every(isFinite)) return; if (rx < 0 || ry < 0) throw new RangeError("ellipse: negative radius");
    ccw = !!ccw; let e = a1;   // Blink's adjustEndAngle
    if (!ccw && a1 - a0 >= TAU) e = a0 + TAU; else if (ccw && a0 - a1 >= TAU) e = a0 - TAU;
    else if (!ccw && a0 > a1) e = a0 + (TAU - ((a0 - a1) % TAU)); else if (ccw && a0 < a1) e = a0 - (TAU - ((a1 - a0) % TAU));
    const sw = e - a0, cr = Math.cos(rot), sr = Math.sin(rot);
    const P = t => { const lx = rx * Math.cos(t), ly = ry * Math.sin(t); return this._T(x + lx * cr - ly * sr, y + lx * sr + ly * cr); };
    const s0 = P(a0); this._has ? this._ln(s0[0], s0[1]) : this._mv(s0[0], s0[1]);
    if (!sw || (!rx && !ry)) return;
    const n = Math.max(1, Math.ceil(Math.abs(sw) / (Math.PI / 2) - 1e-9)), d = sw / n, k = 4 / 3 * Math.tan(d / 4);
    for (let i = 0; i < n; i++) { const t0 = a0 + d * i, t1 = t0 + d;
      const c0 = Math.cos(t0), s0_ = Math.sin(t0), c1 = Math.cos(t1), s1 = Math.sin(t1);
      const L = (lx, ly) => this._T(x + lx * cr - ly * sr, y + lx * sr + ly * cr);
      const A = L(rx * (c0 - k * s0_), ry * (s0_ + k * c0)), B = L(rx * (c1 + k * s1), ry * (s1 - k * c1)), C = L(rx * c1, ry * s1);
      this._p.push(3, A[0], A[1], B[0], B[1], C[0], C[1]); this._cx = C[0]; this._cy = C[1]; }
    this._pd = true; }
  arcTo(x1, y1, x2, y2, r) { if (![x1, y1, x2, y2, r].every(isFinite)) return; if (r < 0) throw new RangeError("arcTo: negative radius");
    if (!this._has) this.moveTo(x1, y1); const p0 = this._uinv(this._cx, this._cy); if (!p0) return;
    const [x0, y0] = p0, d1x = x0 - x1, d1y = y0 - y1, d2x = x2 - x1, d2y = y2 - y1;
    const l1 = Math.hypot(d1x, d1y), l2 = Math.hypot(d2x, d2y), cross = d1x * d2y - d1y * d2x;
    if ((x0 === x1 && y0 === y1) || (x1 === x2 && y1 === y2) || r === 0 || Math.abs(cross) < 1e-12 * l1 * l2) { this.lineTo(x1, y1); return; }
    const cos = (d1x * d2x + d1y * d2y) / (l1 * l2), half = Math.acos(Math.max(-1, Math.min(1, cos))) / 2, t = r / Math.tan(half);
    const t1x = x1 + d1x / l1 * t, t1y = y1 + d1y / l1 * t, t2x = x1 + d2x / l2 * t, t2y = y1 + d2y / l2 * t;
    const bx = d1x / l1 + d2x / l2, by = d1y / l1 + d2y / l2, bl = Math.hypot(bx, by), h = r / Math.sin(half);
    const cx = x1 + bx / bl * h, cy = y1 + by / bl * h;
    this.lineTo(t1x, t1y); this.ellipse(cx, cy, r, r, 0, Math.atan2(t1y - cy, t1x - cx), Math.atan2(t2y - cy, t2x - cx), cross > 0); }
  isPointInPath() { return false; } isPointInStroke() { return false; }
  // ----- emission -----
  _push(...a) { for (const v of a) this._o.push(v); this._ver++; }
  _set(k, v, ...args) { if (this._E[k] === v) return; this._E[k] = v; this._push(k, ...args); }
  _paintKey(p) { return Array.isArray(p) ? "c" + p.join(",") : "g" + p.id + ":" + p.gen; }
  _paintArgs(p) { if (Array.isArray(p)) return [0, p[0], p[1], p[2], p[3]]; const a = [p.type, ...p.g, p.stops.length]; for (const s of p.stops) a.push(...s); return a; }
  _sync(need) { const s = this._s, u = this._u;
    this._set("M", s.m.join(","), ...s.m); this._set("A", s.alpha, s.alpha); this._set("C", s.comp, s.comp);
    const sc = s.shadowC, sh = [s.shadowBlur / u, s.shadowOffsetX / u, s.shadowOffsetY / u, sc[0], sc[1], sc[2], sc[3]];
    this._set("SH", sh.join(","), ...sh); this._set("FI", s.fsig / u, s.fsig / u);
    if (need & NF) this._set("F", this._paintKey(s.fillP), ...this._paintArgs(s.fillP));
    if (need & NS) this._set("S", this._paintKey(s.strokeP), ...this._paintArgs(s.strokeP));
    if (need & NL) { this._set("W", s.lw, s.lw); this._set("LC", s.lineCap, s.lineCap); this._set("LJ", s.lineJoin, s.lineJoin); this._set("ML", s.miterLimit, s.miterLimit); }
    if (need & NT) { this._set("FN", s.font, s.font); const ls = this._ls(); this._set("LS", ls, ls); }
    if (need & NI) { this._set("IS", s.imageSmoothingEnabled ? 1 : 0, s.imageSmoothingEnabled ? 1 : 0); this._set("IQ", s.imageSmoothingQuality, s.imageSmoothingQuality); } }
  _ls() { const v = this._s.letterSpacing.trim(), x = parseFloat(v); if (!x) return 0; return v.endsWith("px") ? x : x * fontPx(this._s.font); }
  _emitPath() { if (!this._pd) return; this._push("P", this._p.slice()); this._pd = false; }
  _tempPath(pts, close) { const a = []; for (let i = 0; i < pts.length; i++) a.push(i ? 1 : 0, pts[i][0], pts[i][1]); if (close) a.push(4);
    this._push("P", a); this._pd = true; return a; }
  _pathBox(a) { let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    for (let i = 0; i < a.length;) { const k = a[i++], n = k === 0 || k === 1 ? 1 : k === 2 ? 2 : k === 3 ? 3 : 0;
      for (let j = 0; j < n; j++) { const X = a[i++], Y = a[i++]; if (X < x0) x0 = X; if (X > x1) x1 = X; if (Y < y0) y0 = Y; if (Y > y1) y1 = Y; } }
    return x1 >= x0 ? [x0, y0, x1, y1] : null; }
  _mscale() { const m = this._s.m; return Math.max(Math.hypot(m[0], m[1]), Math.hypot(m[2], m[3])); }
  _strokePad() { const s = this._s; let f = 0.5; if (s.lineJoin === "miter") f = Math.max(f, s.miterLimit / 2); if (s.lineCap === "square") f = Math.max(f, Math.SQRT1_2);
    return s.lw * this._mscale() * f + 1; }
  // grow the recording's box by a drawn CSS-space box, with shadow and blur spread, clipped
  _grow(b, pad) { if (!b) return; const s = this._s, u = this._u; let [x0, y0, x1, y1] = b; pad = (pad || 0) + 3 * s.fsig / u + 1;
    x0 -= pad; y0 -= pad; x1 += pad; y1 += pad;
    if (s.shadowC[3] > 0 && (s.shadowBlur > 0 || s.shadowOffsetX || s.shadowOffsetY)) { const sp = 1.5 * s.shadowBlur / u + 1, ox = s.shadowOffsetX / u, oy = s.shadowOffsetY / u;
      x0 = Math.min(x0, x0 + ox - sp); y0 = Math.min(y0, y0 + oy - sp); x1 = Math.max(x1, x1 + ox + sp); y1 = Math.max(y1, y1 + oy + sp); }
    const c = s.clipB; if (c) { x0 = Math.max(x0, c[0]); y0 = Math.max(y0, c[1]); x1 = Math.min(x1, c[2]); y1 = Math.min(y1, c[3]); }
    if (x1 <= x0 || y1 <= y0) return; const B = this._bb;
    if (x0 < B[0]) B[0] = x0; if (y0 < B[1]) B[1] = y0; if (x1 > B[2]) B[2] = x1; if (y1 > B[3]) B[3] = y1; this._drew = true; }
  _rule(r) { return r === "evenodd" ? "evenodd" : "nonzero"; }
  fill(a, b) { if (a && typeof a === "object") { unsup("Path2D"); return; } if (!this._has) return;
    this._sync(NF); this._emitPath(); this._push("f", this._rule(typeof a === "string" ? a : b)); this._grow(this._pathBox(this._p), 0); }
  stroke(a) { if (a && typeof a === "object") { unsup("Path2D"); return; } if (!this._has) return;
    this._sync(NS | NL); this._emitPath(); this._push("k"); this._grow(this._pathBox(this._p), this._strokePad()); }
  clip(a, b) { if (a && typeof a === "object") { unsup("Path2D"); return; }
    this._emitPath(); this._push("c", this._rule(typeof a === "string" ? a : b));
    const pb = this._has ? this._pathBox(this._p) : null, s = this._s, c = s.clipB, nb = pb || [0, 0, 0, 0];
    s.clipB = c ? [Math.max(c[0], nb[0]), Math.max(c[1], nb[1]), Math.min(c[2], nb[2]), Math.min(c[3], nb[3])] : nb; }
  _rectPts(x, y, w, h) { return [this._T(x, y), this._T(x + w, y), this._T(x + w, y + h), this._T(x, y + h)]; }
  fillRect(x, y, w, h) { if (![x, y, w, h].every(isFinite) || !w || !h) return; this._sync(NF);
    const a = this._tempPath(this._rectPts(x, y, w, h), true); this._push("f", "nonzero"); this._grow(this._pathBox(a), 0); }
  strokeRect(x, y, w, h) { if (![x, y, w, h].every(isFinite) || (!w && !h)) return; this._sync(NS | NL);
    const a = this._tempPath(this._rectPts(x, y, w, h), true); this._push("k"); this._grow(this._pathBox(a), this._strokePad()); }
  clearRect(x, y, w, h) { if (![x, y, w, h].every(isFinite) || !w || !h) return; this._sync(0); this._tempPath(this._rectPts(x, y, w, h), true); this._push("X"); }
  // ----- text -----
  _metrics(text) { const s = this._s, raw = hostMeasure(s.font, text), ls = this._ls(), n = [...text].length;
    const w = raw.w + ls * n, ax = s.textAlign === "center" ? -w / 2 : (s.textAlign === "right" || (s.textAlign === "end" && s.direction !== "rtl") || (s.textAlign === "start" && s.direction === "rtl")) ? -w : 0;
    const bl = s.textBaseline, b = bl === "top" ? raw.ea : bl === "hanging" ? raw.hg : bl === "middle" ? (raw.ea - raw.ed) / 2 : bl === "ideographic" ? -raw.fd : bl === "bottom" ? -raw.ed : 0;
    return { raw, w, ax, b, ls, n }; }
  measureText(t) { const text = String(t), M = this._metrics(text), r = M.raw;
    return { width: M.w, actualBoundingBoxLeft: r.l - M.ax, actualBoundingBoxRight: r.r + M.ls * Math.max(0, M.n - 1) + M.ax,
      actualBoundingBoxAscent: r.a - M.b, actualBoundingBoxDescent: r.d + M.b, fontBoundingBoxAscent: r.fa - M.b, fontBoundingBoxDescent: r.fd + M.b,
      emHeightAscent: r.ea - M.b, emHeightDescent: r.ed + M.b, hangingBaseline: r.hg - M.b, alphabeticBaseline: -M.b, ideographicBaseline: -r.fd - M.b }; }
  _text(mode, t, x, y, maxW) { if (!isFinite(x) || !isFinite(y)) return; const text = String(t); if (!text) return;
    const M = this._metrics(text); let sx = 1; if (maxW !== undefined) { maxW = +maxW; if (!(maxW > 0)) return; if (M.w > maxW) sx = maxW / M.w; }
    const X = x + M.ax * sx, Y = y + M.b, r = M.raw;
    this._sync((mode ? NS | NL : NF) | NT); this._push("T", mode, text, X, Y, sx);
    const x0 = X - Math.max(0, r.l) * sx - r.a * 0.3, x1 = X + (Math.max(r.r, r.w) + M.ls * M.n) * sx + r.a * 0.3, y0 = Y - Math.max(r.a, r.fa), y1 = Y + Math.max(r.d, r.fd);
    const c = [this._T(x0, y0), this._T(x1, y0), this._T(x1, y1), this._T(x0, y1)];
    this._grow([Math.min(...c.map(p => p[0])), Math.min(...c.map(p => p[1])), Math.max(...c.map(p => p[0])), Math.max(...c.map(p => p[1]))], mode ? this._strokePad() : 0); }
  fillText(t, x, y, w) { this._text(0, t, x, y, w); }
  strokeText(t, x, y, w) { this._text(1, t, x, y, w); }
  // ----- images -----
  drawImage(img, a, b, c, d, e, f, g, h) {
    const R = img && img._cmd ? img.getContext("2d") : null; if (!R) { unsup("drawImage:source"); return; }
    let sx = 0, sy = 0, sw = img.width, sh = img.height, dx, dy, dw, dh;
    if (arguments.length >= 9) { sx = a; sy = b; sw = c; sh = d; dx = e; dy = f; dw = g; dh = h; }
    else if (arguments.length >= 5) { dx = a; dy = b; dw = c; dh = d; } else { dx = a; dy = b; dw = img.width; dh = img.height; }
    if (![sx, sy, sw, sh, dx, dy, dw, dh].every(isFinite) || !dw || !dh || !sw || !sh || !img.width || !img.height) return;
    const snap = R._snapshot(); this._deps.set(snap.key, snap);
    this._sync(NI); this._push("I", snap.key, sx, sy, sw, sh, dx, dy, dw, dh);
    const cs = [this._T(dx, dy), this._T(dx + dw, dy), this._T(dx + dw, dy + dh), this._T(dx, dy + dh)];
    this._grow([Math.min(...cs.map(p => p[0])), Math.min(...cs.map(p => p[1])), Math.max(...cs.map(p => p[0])), Math.max(...cs.map(p => p[1]))], 1); }
  // this canvas's content as a definition, rebuilt only when it changed
  _snapshot() { const cv = this.canvas; if (this._snap && this._snap.ver === this._ver) return this._snap;
    this._snap = { key: cv._id + "@" + this._ver, ver: this._ver, w: cv.width, h: cv.height, ops: this._o.slice(), deps: [...this._deps.values()] }; return this._snap; }
  // definitions this recording depends on, dependencies first
  _defs(out, seen) { out = out || []; seen = seen || new Set();
    const walk = s => { if (seen.has(s.key)) return; seen.add(s.key); for (const d of s.deps) walk(d); out.push("D", s.key, s.w, s.h, s.ops); };
    for (const d of this._deps.values()) walk(d); return out; }
  getImageData(x, y, w, h) { x = Math.floor(x); y = Math.floor(y); w = Math.floor(w); h = Math.floor(h);
    if (!(w > 0 && h > 0)) throw new RangeError("getImageData: empty"); const data = new Uint8ClampedArray(w * h * 4), cg = G.__native && G.__native.cg;
    const cv = this.canvas; if (!cv || !cv._cmd || cv._overlay || typeof cg !== "function") { unsup("getImageData"); return { width: w, height: h, data, colorSpace: "srgb" }; }
    const snap = this._snapshot(), defs = []; const seen = new Set();
    const walk = s => { if (seen.has(s.key)) return; seen.add(s.key); for (const d of s.deps) walk(d); defs.push("D", s.key, s.w, s.h, s.ops); }; walk(snap);
    const r = cg(JSON.stringify({ q: "pixels", ops: defs, key: snap.key, x, y, w, h }), data); if (r !== "ok") unsup("getImageData:" + r);
    return { width: w, height: h, data, colorSpace: "srgb" }; }
  putImageData() { unsup("putImageData"); }
  createImageData(w, h) { if (typeof w === "object" && w) { h = w.height; w = w.width; } return { width: w, height: h, data: new Uint8ClampedArray(Math.max(0, w * h * 4)), colorSpace: "srgb" }; }
  drawFocusIfNeeded() {}
  getContextAttributes() { return { alpha: true, colorSpace: "srgb", desynchronized: false, willReadFrequently: false }; }
}

// ---------- the canvas element ----------
class CmdCanvas {
  constructor(w, h) { this._id = TOKEN + "." + (++NEXT); this._w = w == null ? 300 : Math.max(0, w | 0); this._h = h == null ? 150 : Math.max(0, h | 0);
    this._ctx = null; this._cmd = true; this._isCanvas = true; this.style = {}; this.attrs = {}; }
  get width() { return this._w; } set width(v) { this._w = Math.max(0, v | 0); if (this._ctx) this._ctx._init(); }
  get height() { return this._h; } set height(v) { this._h = Math.max(0, v | 0); if (this._ctx) this._ctx._init(); }
  getContext(kind) { if (kind !== "2d") return null; return this._ctx || (this._ctx = new Context2D(this, 1)); }
  setAttribute(k, v) { this.attrs[k] = String(v); } getAttribute(k) { return this.attrs[k] ?? null; }
  addEventListener() {} removeEventListener() {}
  getBoundingClientRect() { return { left: 0, top: 0, width: this._w, height: this._h, x: 0, y: 0 }; }
  toDataURL() { unsup("toDataURL"); return "data:,"; }
}

// ---------- overlay recording on an existing context ----------
const METHODS = ["save", "restore", "reset", "scale", "rotate", "translate", "transform", "setTransform", "getTransform", "resetTransform",
  "createLinearGradient", "createRadialGradient", "createConicGradient", "createPattern", "beginPath", "moveTo", "lineTo", "closePath",
  "quadraticCurveTo", "bezierCurveTo", "arcTo", "arc", "ellipse", "rect", "roundRect", "fill", "stroke", "clip", "isPointInPath",
  "isPointInStroke", "fillRect", "strokeRect", "clearRect", "fillText", "strokeText", "measureText", "drawImage", "getImageData",
  "putImageData", "createImageData", "setLineDash", "getLineDash", "drawFocusIfNeeded", "getContextAttributes"];
const PROPS = ["globalAlpha", "globalCompositeOperation", "fillStyle", "strokeStyle", "lineWidth", "lineCap", "lineJoin", "miterLimit",
  "lineDashOffset", "shadowBlur", "shadowColor", "shadowOffsetX", "shadowOffsetY", "filter", "font", "textAlign", "textBaseline",
  "letterSpacing", "direction", "imageSmoothingEnabled", "imageSmoothingQuality", "wordSpacing", "fontKerning"];
const active = new WeakMap();
function begin(ctx, dpr, opt) {
  if (!ctx || active.has(ctx)) return false; const u = +dpr > 0 ? +dpr : 1;
  const cv = { _cmd: true, _overlay: true, _id: TOKEN + ".main" + (++NEXT), width: 0, height: 0 }, R = new Context2D(cv, u);
  // starting state: canvas.js keeps it in _s; otherwise read the public getters
  const s0 = ctx._s && Array.isArray(ctx._s.m) ? ctx._s : null, get = k => s0 ? s0[k] : ctx[k];
  const m = s0 ? s0.m : (ctx.getTransform ? (t => [t.a, t.b, t.c, t.d, t.e, t.f])(ctx.getTransform()) : [u, 0, 0, u, 0, 0]);
  R._s.m = m.map(x => x / u);
  const alpha = s0 ? s0.alpha : ctx.globalAlpha; if (alpha != null) R.globalAlpha = alpha;
  const comp = s0 ? s0.comp : ctx.globalCompositeOperation; if (comp) R.globalCompositeOperation = comp;
  for (const [k, sk] of [["fillStyle", "fillV"], ["strokeStyle", "strokeV"], ["lineWidth", "lw"]]) { const v = s0 ? s0[sk] : ctx[k]; if (v != null) R[k] = v; }
  for (const k of ["lineCap", "lineJoin", "miterLimit", "shadowBlur", "shadowColor", "shadowOffsetX", "shadowOffsetY", "filter", "font",
    "textAlign", "textBaseline", "letterSpacing", "direction", "imageSmoothingEnabled", "imageSmoothingQuality"]) { const v = get(k); if (v != null) R[k] = v; }
  const saved = { own: {}, doc: null };
  for (const k of METHODS.concat(PROPS)) { const d = Object.getOwnPropertyDescriptor(ctx, k); if (d) saved.own[k] = d; }
  for (const k of METHODS) Object.defineProperty(ctx, k, { configurable: true, writable: true, value: R[k].bind(R) });
  for (const k of PROPS) Object.defineProperty(ctx, k, { configurable: true, get() { return R[k]; }, set(v) { R[k] = v; } });
  const D = G.document; if (D && typeof D.createElement === "function") { saved.doc = D.createElement;
    D.createElement = function (tag) { return String(tag).toLowerCase() === "canvas" ? new CmdCanvas() : saved.doc.apply(this, arguments); }; }
  active.set(ctx, { R, saved, opt: opt || {} }); return true; }
function end(ctx) {
  const a = active.get(ctx); if (!a) return null; active.delete(ctx); const { R, saved, opt } = a;
  for (const k of METHODS.concat(PROPS)) { delete ctx[k]; if (saved.own[k]) Object.defineProperty(ctx, k, saved.own[k]); }
  if (saved.doc && G.document) G.document.createElement = saved.doc;
  if (!R._drew) return null;
  let [x0, y0, x1, y1] = R._bb; x0 = Math.floor(x0); y0 = Math.floor(y0); x1 = Math.ceil(x1); y1 = Math.ceil(y1);
  if (opt.bounds) { const b = opt.bounds; x0 = Math.max(x0, b[0]); y0 = Math.max(y0, b[1]); x1 = Math.min(x1, b[0] + b[2]); y1 = Math.min(y1, b[1] + b[3]); }
  if (x1 <= x0 || y1 <= y0) return null;
  const ops = R._defs().concat(R._o); let json = null;
  return { ops, box: [x0, y0, x1 - x0, y1 - y0], get json() { return json || (json = JSON.stringify(ops)); } }; }

CmdCanvas.Context2D = Context2D; CmdCanvas.Gradient = CmdGradient; CmdCanvas.begin = begin; CmdCanvas.end = end; CmdCanvas.stats = stats;
CmdCanvas.recording = ctx => active.has(ctx); CmdCanvas.clearMeasureCache = () => mcache.clear(); CmdCanvas.UNBOUNDED = UNBOUNDED;
G.CmdCanvas = CmdCanvas;
})(globalThis);
