/* Sprites native host, JS half: the few browser APIs that app/stage.html, visitors_runtime.js, the pieces and labels.js
 * use, provided inside a JavaScriptCore JSContext (docs/NATIVE_PORT.md). Load after canvas.js. The Swift side
 * (app/macos/Native.swift) passes `__native` = { now() ms, read(path) text|null, post(json), timer(id, ms, repeat),
 * cancel(id), log(text), present(), query, dpr, w, h }. Nothing here draws. */
(function (G) {
"use strict";
const N = G.__native;
G.window = G; G.self = G; G.top = G; G.parent = G;
G.devicePixelRatio = N.dpr; G.innerWidth = N.w; G.innerHeight = N.h;
G.location = { search: N.query ? "?" + N.query : "", href: "sprites://stage/app/stage.html" };
G.navigator = { userAgent: "SpritesNative" };
const say = (...a) => N.log(a.map(x => typeof x === "string" ? x : (() => { try { return JSON.stringify(x); } catch (e) { return String(x); } })()).join(" "));
G.console = { log: say, info: say, warn: say, error: say, debug() {} };
const t0 = N.now();
G.performance = { now: () => N.now() - t0, timeOrigin: Date.now() };

// timers: one Swift timer each (main run loop)
const timers = new Map(); let tid = 0;
function report(e) { (G.__errors = G.__errors || []).push(String(e && e.message || e)); say("js error: " + (e && e.stack || e)); }
function arm(fn, ms, rep, args) { if (typeof fn !== "function") return 0; const id = ++tid; timers.set(id, { fn, args, rep });
  N.timer(id, Math.max(rep ? 4 : 0, +ms || 0), rep); return id; }
G.setTimeout = (fn, ms, ...a) => arm(fn, ms, false, a);
G.setInterval = (fn, ms, ...a) => arm(fn, ms, true, a);
G.clearTimeout = G.clearInterval = id => { if (timers.delete(id)) N.cancel(id); };
// After every timer callback: if the recording changed (a frame was drawn or cleared), ask the host to present it.
let presented = -1;
function maybePresent() { const v = G.__nativeVer(); if (v !== presented) { presented = v; N.present(); } }
// QA (SPRITES_NATIVE_STATS): time per callback source, read with __nativeTimes()
const TS = {}; let tsOn = false;
function wrapT(o, k, tag) { const f = o[k]; if (typeof f !== "function" || f.__w) return; const g = function () { const t0 = G.performance.now();
    try { return f.apply(this, arguments); } finally { const e = TS[tag] || (TS[tag] = [0, 0]); e[0]++; e[1] += G.performance.now() - t0; } }; g.__w = 1; o[k] = g; }
G.__nativeTimesOn = () => { tsOn = true; setInterval(() => { const st = G.__stage; if (!st) return;
  for (const c in st.layers) { const L = st.layers[c]; if (!L.V || !L.V._def) continue; wrapT(L.V._def, "step", c + ".step"); wrapT(L.V._def, "draw", c + ".draw");
    wrapT(L.V, "_frame", c + "._frame"); } }, 2000); };
G.__nativeTimes = () => { const o = {}; for (const k in TS) o[k] = [TS[k][0], +(TS[k][1]).toFixed(1)]; for (const k in TS) delete TS[k]; return JSON.stringify(o); };
G.__nativeFire = id => { const t = timers.get(id); if (!t) return; if (!t.rep) timers.delete(id); const t0 = tsOn ? G.performance.now() : 0;
  try { t.fn(...t.args); } catch (e) { report(e); }
  drainRaf();
  if (tsOn) { const k = (t.fn.__tag || t.fn.name || String(t.fn).slice(0, 48)).replace(/\s+/g, " "), e = TS[k] || (TS[k] = [0, 0]); e[0]++; e[1] += G.performance.now() - t0; }
  maybePresent(); };
G.__nativePresented = () => { drainRaf(); maybePresent(); };
// The stage already lands its frames on a 24 fps wall-clock grid with setTimeout, then asks for an animation frame:
// that frame runs at once and is presented right after it.
// rAF callbacks run right after the timer callback that asked for them (the stage asks from its frame-grid setTimeout),
// in the same wakeup, then the frame is presented: one wakeup per frame, not two.
let rafQ = [], rafId = 0;
G.requestAnimationFrame = cb => { rafQ.push([++rafId, cb]); return rafId; };
G.cancelAnimationFrame = id => { rafQ = rafQ.filter(e => e[0] !== id); };
function drainRaf() { for (let n = 0; rafQ.length && n < 4; n++) { const q = rafQ; rafQ = []; const now = G.performance.now();
  for (const [, cb] of q) { const t0 = tsOn ? now : 0; try { cb(now); } catch (e) { report(e); }
    if (tsOn) { const e = TS.rAF || (TS.rAF = [0, 0]); e[0]++; e[1] += G.performance.now() - t0; } } } }
G.queueMicrotask = G.queueMicrotask || (fn => Promise.resolve().then(fn));

// events (the stage listens for mousedown and error on window; visibilitychange on document)
const L = {};
const on = (k, fn) => { if (typeof fn === "function") (L[k] = L[k] || []).push(fn); };
const off = (k, fn) => { const a = L[k]; if (a) { const i = a.indexOf(fn); if (i >= 0) a.splice(i, 1); } };
G.addEventListener = on; G.removeEventListener = off;
G.__nativeEvent = (k, e) => { for (const fn of (L[k] || []).slice()) try { fn(e); } catch (err) { report(err); } };
// `detail` is the window server's clickCount, as a DOM MouseEvent carries it: 1 for a single click, 2 for the second
// click of a double-click. The stage passes it to the host, which decides the gesture (Decide.swift clickGesture).
G.__nativeMouse = (x, y, detail) => G.__nativeEvent("mousedown", { clientX: x, clientY: y, button: 0,
  detail: typeof detail === "number" && detail > 0 ? detail : 1, preventDefault() {}, stopPropagation() {} });

// document: canvases are the recording canvases of canvas.js; anything else is an inert element
function el(tag) { return { tagName: String(tag).toUpperCase(), style: {}, children: [], appendChild(c) { this.children.push(c); return c; },
  setAttribute() {}, getAttribute() { return null; }, addEventListener() {}, removeEventListener() {},
  getBoundingClientRect() { return { left: 0, top: 0, width: 0, height: 0, x: 0, y: 0 }; } }; }
const body = el("body"); body.appendChild = c => { if (c && c._isCanvas) c._attach(); return c; };
// document.hidden is the host's to set (Native.swift: display sleep, session switch, panel occluded), as WebKit sets it for
// a hidden page: __nativeSetHidden(bool) changes it and fires "visibilitychange" once per change, so stage.html's own
// page-hidden pause (no frames while hidden) works here too.
let hidden = false;
G.__nativeSetHidden = h => { h = !!h; if (h === hidden) return; hidden = h; G.__nativeEvent("document:visibilitychange", { type: "visibilitychange" }); };
G.document = { body, documentElement: el("html"), get hidden() { return hidden; }, get visibilityState() { return hidden ? "hidden" : "visible"; },
  createElement: tag => String(tag).toLowerCase() === "canvas" ? new G.HTMLCanvasElement() : el(tag),
  getElementById: () => null, querySelector: () => null, addEventListener: (k, fn) => on("document:" + k, fn), removeEventListener() {} };
G.Image = class Image { constructor() { this.width = 0; this.height = 0; this.complete = false; } set src(v) { this._src = v; } get src() { return this._src || ""; } };

// URLSearchParams (the runtime reads its parameters through one)
G.URLSearchParams = class URLSearchParams {
  constructor(init) { this._p = [];
    if (typeof init === "string") { for (const kv of init.replace(/^\?/, "").split("&")) { if (!kv) continue; const i = kv.indexOf("=");
        const k = i < 0 ? kv : kv.slice(0, i), v = i < 0 ? "" : kv.slice(i + 1); this._p.push([decodeURIComponent(k.replace(/\+/g, " ")), decodeURIComponent(v.replace(/\+/g, " "))]); } }
    else if (init && typeof init === "object") for (const k of Object.keys(init)) this._p.push([k, String(init[k])]); }
  get(k) { const e = this._p.find(p => p[0] === k); return e ? e[1] : null; }
  has(k) { return this._p.some(p => p[0] === k); }
  set(k, v) { const e = this._p.find(p => p[0] === k); if (e) e[1] = String(v); else this._p.push([k, String(v)]); }
  append(k, v) { this._p.push([k, String(v)]); }
  delete(k) { this._p = this._p.filter(p => p[0] !== k); }
  toString() { return this._p.map(p => encodeURIComponent(p[0]) + "=" + encodeURIComponent(p[1])).join("&"); }
  *[Symbol.iterator]() { yield* this._p; }
};

// XMLHttpRequest: the stage reads each piece's HTML once (relative to app/stage.html)
G.XMLHttpRequest = class XMLHttpRequest {
  open(m, u) { this._u = String(u); this.readyState = 1; }
  send() { const txt = N.read("app/" + this._u); setTimeout(() => { this.readyState = 4;
    if (txt == null) { this.status = 404; if (this.onerror) this.onerror(); } else { this.status = 200; this.responseText = txt; if (this.onload) this.onload(); } }, 0); }
  setRequestHeader() {} abort() {}
};

// host messages: the stage posts {hits} and {click} as it does to WKWebView
G.webkit = { messageHandlers: { sprites: { postMessage: m => { try { N.post(JSON.stringify(m)); } catch (e) { report(e); } } } } };
G.VISITORS_SHARED = true;
})(globalThis);
