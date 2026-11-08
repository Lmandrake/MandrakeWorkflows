/* EXPERIMENT ONLY (species_styles.html): one idle glyph, two styles, real canvas at the page's dpr.
 * Compositing is the species' own: dark #0b0d12 ground, globalCompositeOperation "lighter", session hue.
 * vec: the unit-box loops stroked at lw CSS px (1 device px at 23, 1 CSS at 64, 2 CSS at 256), no fill.
 * dot: the generated lattice, drawn in DEVICE px as integer-aligned squares (so every dot is a hard square of
 *      whole device pixels), interior at the body tone, edge dots at the rim tone. No halo, no glow. */
(function () {
"use strict";
const q = new URLSearchParams(location.search);
const name = q.get("g"), style = q.get("s") || "vec", E = +(q.get("E") || 64), hue = +(q.get("hue") || 200);
const dpr = window.devicePixelRatio || 1;
const G = window.SPRITES_SPECIES_GLYPHS[name];
const css = Math.ceil(E * 1.25 / 2) * 2 + 8;           // even, so the centre is a whole device pixel
const cv = document.getElementById("c");
cv.style.width = cv.style.height = css + "px"; cv.width = cv.height = css * dpr;
const ctx = cv.getContext("2d");
ctx.fillStyle = "#0b0d12"; ctx.fillRect(0, 0, cv.width, cv.height);
ctx.globalCompositeOperation = "lighter";
const hsl = (h, s, l) => `hsl(${h},${s}%,${l}%)`;
const B = 0.5 * 0.94;                                   // idle brightness (armC: 0.5 x mean breathe)
const cx = cv.width / 2, cy = cv.height / 2;
if (style === "vec") {
  const R = E / 2 * dpr, lw = (E <= 23 ? 0.5 : E <= 64 ? 1 : 2) * dpr;
  ctx.setTransform(R, 0, 0, R, cx, cy);
  ctx.lineJoin = "round"; ctx.lineCap = "round"; ctx.lineWidth = lw / R;
  ctx.strokeStyle = hsl(hue, 83, 86); ctx.globalAlpha = Math.min(1, 1.0 * B + 0.45);
  ctx.beginPath();
  for (const p of G.loops) { ctx.moveTo(p[0][0], p[0][1]); for (let k = 1; k < p.length; k++) ctx.lineTo(p[k][0], p[k][1]); ctx.closePath(); }
  ctx.stroke();
} else {
  const D = { 23: 1, 64: 2, 256: 4 }[E] || 2, pts = G.dots[String(E)];
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  for (const edge of [0, 1]) {
    ctx.fillStyle = edge ? hsl(hue, 83, 84) : hsl(hue, 92, 58); ctx.globalAlpha = edge ? Math.min(1, B + 0.45) : Math.min(1, B + 0.3);
    for (const p of pts) if (p[2] === edge) ctx.fillRect(Math.round(cx + p[0] - D / 2), Math.round(cy + p[1] - D / 2), D, D);
  }
}
window.__done = true;
})();
