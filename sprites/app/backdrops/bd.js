/* Sprites backdrops, WebGL2 side: compiles backdrops.sl (the same source the host compiles as Metal) and renders a
 * backdrop into any 2D canvas through ONE shared offscreen WebGL canvas (so the settings grid costs one context).
 *   SpritesBackdrops.load(base) -> Promise<{catalog, ok}>     base = URL of this folder ("backdrops/")
 *   SpritesBackdrops.draw(canvas2d, n, t, {boost, nc, mode}) draws backdrop n (1..12) at design time t (s)
 *   SpritesBackdrops.catalog                                   catalog.json contents
 * Used by app/settings.js (Backdrop tab) and backdrops/preview.html (QA renders). */
(function () {
  "use strict";
  const VS = `#version 300 es
in vec2 a; void main() { gl_Position = vec4(a, 0.0, 1.0); }`;
  const HEAD = `#version 300 es
precision highp float; precision highp int;
#define atan2 atan
uniform vec2 uRes; uniform float uId, uT, uNc, uMode, uBoost; uniform vec2 uOff; uniform vec2 uFull;
out vec4 o;
`;
  const MAIN = `
void main() { vec2 p = vec2(gl_FragCoord.x, uRes.y - gl_FragCoord.y);
  vec2 sc = uFull / uRes; vec2 P = p * sc + uOff;          // render a uRes view of a uFull-sized screen (previews)
  vec3 lin = pick(uId, P, uFull, uT, uNc);
  o = vec4(encodeOut(lin, p, uMode, uBoost), 1.0); }`;
  let gl = null, cv = null, prog = null, U = {}, src = null, catalog = null;
  function compile(text) {
    cv = document.createElement("canvas"); gl = cv.getContext("webgl2", { preserveDrawingBuffer: true, antialias: false, premultipliedAlpha: false });
    if (!gl) throw new Error("no WebGL2");
    const sh = (type, s) => { const x = gl.createShader(type); gl.shaderSource(x, s); gl.compileShader(x);
      if (!gl.getShaderParameter(x, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(x)); return x; };
    prog = gl.createProgram(); gl.attachShader(prog, sh(gl.VERTEX_SHADER, VS)); gl.attachShader(prog, sh(gl.FRAGMENT_SHADER, HEAD + text + MAIN));
    gl.linkProgram(prog); if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(prog));
    gl.useProgram(prog);
    const b = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, b); gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
    const loc = gl.getAttribLocation(prog, "a"); gl.enableVertexAttribArray(loc); gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
    ["uRes", "uId", "uT", "uNc", "uMode", "uBoost", "uOff", "uFull"].forEach(k => U[k] = gl.getUniformLocation(prog, k)); }
  const get = u => new Promise((res, rej) => { const x = new XMLHttpRequest(); x.open("GET", u); x.onload = () => res(x.responseText); x.onerror = () => rej(new Error("cannot load " + u)); x.send(); });
  async function load(base) { base = base || ""; const [s, c] = await Promise.all([get(base + "backdrops.sl"), get(base + "catalog.json")]);
    src = s; catalog = JSON.parse(c); compile(src); return { catalog, ok: true }; }
  /* opts.full = [W,H] of the screen being previewed (default: the canvas size, i.e. 1:1). A preview at tile size uses
   * full = [1728,1117] so stars and comets keep their screen-relative size and density. */
  function draw(target, n, t, opts) { opts = opts || {}; const w = target.width, h = target.height;
    if (cv.width !== w || cv.height !== h) { cv.width = w; cv.height = h; }
    gl.viewport(0, 0, w, h); const full = opts.full || [w, h];
    gl.uniform2f(U.uRes, w, h); gl.uniform2f(U.uFull, full[0], full[1]); gl.uniform2f(U.uOff, (opts.off || [0, 0])[0], (opts.off || [0, 0])[1]);
    gl.uniform1f(U.uId, n); gl.uniform1f(U.uT, t); gl.uniform1f(U.uNc, opts.nc ? 1 : 0); gl.uniform1f(U.uMode, opts.mode || 0); gl.uniform1f(U.uBoost, opts.boost ? 1 : 0);
    gl.drawArrays(gl.TRIANGLES, 0, 3);
    const x = target.getContext("2d"); x.drawImage(cv, 0, 0); }
  window.SpritesBackdrops = { load, draw, get catalog() { return catalog; }, get source() { return src; } };
})();
