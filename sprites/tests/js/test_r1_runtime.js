// R1 findings 5, 6, 7, 14, 15, 19 (reviews/SPRITES_REVIEW_R1.md). Node only: the stage runs in a vm with a fake clock
// (tests/js/harness.js); nothing renders, no browser. Exit 1 on any failure. Run: node sprites/tests/js/test_r1_runtime.js
"use strict";
const fs = require("fs"), path = require("path");
const { makeStage, snapshot, check, done, ROOT } = require("./harness.js");
const only = process.argv[2];
const W = 1728, H = 1117;
function scene(sp, opts = {}) {
  const st = makeStage({ query: "stale=0&vpndebounce=0", before: opts.before });
  st.ev(`SpritesStage.setSize(${W},${H}); SpritesStage.setCast({projects:{Alpha:{concept:"${sp}",iv:1,hex:"#55aaff"},Beta:{concept:"${sp}",iv:2,hex:"#ffaa55"}}})`);
  return st; }
const upd = (st, snap) => st.ev(`SpritesStage.update(${JSON.stringify(snap)})`);
const rep = (st, sp) => st.ev(`JSON.stringify(__stage.V("${sp}").__report().reports)`);
const reports = (st, sp) => JSON.parse(rep(st, sp));
const hits = st => JSON.parse(st.ev("JSON.stringify(__stage.allHits())"));
const SPECIES = ["c1_choir", "c2_siphon", "c3_sigils", "c4_kaleido", "c5_fireflies"];

// ---- 5: a creature faded out (nothing fits: full-screen focus) has no hit disc; a ghost (0.3) keeps its disc ----
if (!only || only === "5") for (const sp of SPECIES) {
  const st = scene(sp); upd(st, snapshot([{ project: "Alpha" }])); st.fire(); st.step(48);
  const before = hits(st).length;
  st.ev(`SpritesStage.setWindows([{x:0,y:0,w:${W},h:${H},pid:1}]); SpritesStage.setFocus({x:0,y:0,w:${W},h:${H}})`); st.step(24 * 4);
  const a = +st.ev(`__stage.V("${sp}").alpha("100@1")`), hs = hits(st);
  check(before === 1 && a < 0.01 && hs.length === 0, `#5 ${sp}: faded out under a full-screen focus (alpha ${a.toFixed(4)}) leaves no hit disc`, hs);
}
if (!only || only === "5") {
  const st = scene("c5_fireflies"); upd(st, snapshot([{ project: "Alpha" }], { projects: [{ key: "beta", name: "Beta", counts: { burning: 2 } }] }));
  st.fire(); st.step(48); const hs = hits(st).map(h => h.id);
  check(hs.includes("ghost:beta"), "#5 ghost (alpha 0.3) keeps its hit disc", hs);
}

// ---- 6: hover-follow is bounded (<= max(24, 1.5 r) from the creature's own position) and its hit disc never overlaps
//         the focused window ----
if (!only || only === "6") for (const sp of SPECIES) {
  const st = scene(sp); upd(st, snapshot([{ project: "Alpha" }])); st.fire(); st.step(48);
  let r = reports(st, sp)["100@1"]; let cx = r.x + 0.3 * r.r, cy = r.y;
  st.ev(`SpritesStage.setCursor({x:${cx},y:${cy}})`); st.step(24);
  let worst = 0, under = false;
  for (let k = 0; k < 60; k++) { cx += 4; st.ev(`SpritesStage.setCursor({x:${cx},y:${cy}})`); st.step(2);   // 4 px per 1/12 s, slow
    r = reports(st, sp)["100@1"]; const cap = Math.max(24, 1.5 * r.r); worst = Math.max(worst, Math.hypot(r.x - r.bx, r.y - r.by) / cap); }
  const h = hits(st).find(z => z.id === "100@1"); under = !!h && Math.hypot(h.x - cx, h.y - cy) <= h.r;
  check(worst <= 1.0001 && !under, `#6 ${sp}: cursor dragged 240 px away; displacement <= cap (worst ${worst.toFixed(2)} x cap), disc not under the cursor (${under})`);
  // focus just right of the creature; cursor parked inside the focus at its edge: the hit disc must stay out of it
  st.ev("SpritesStage.setCursor(null)"); st.step(48);
  r = reports(st, sp)["100@1"]; const fx = Math.round(r.bx + Math.max(18, r.r) + 14);
  st.ev(`SpritesStage.setWindows([{x:${fx},y:0,w:${W - fx},h:${H},pid:1}]); SpritesStage.setFocus({x:${fx},y:0,w:${W - fx},h:${H}})`); st.step(24 * 3);
  r = reports(st, sp)["100@1"];
  st.ev(`SpritesStage.setCursor({x:${r.x + 0.5 * r.r},y:${r.y}})`); st.step(6);
  let over = 0;
  for (let k = 0; k < 24 * 3; k++) { r = reports(st, sp)["100@1"]; const cxx = Math.min(fx + 6, r.x + 0.5 * r.r + 3);
    st.ev(`SpritesStage.setCursor({x:${cxx},y:${r.y}})`); st.step(1);
    const hh = hits(st).find(z => z.id === "100@1"); if (hh) over = Math.max(over, hh.x + hh.r - fx); }
  check(over <= 0, `#6 ${sp}: hover at the focus edge, hit disc stays outside the focus (max overlap ${over} px)`);
}

// ---- 7: the reconnect bloom fires on LOST -> OK only, not on LOST -> still-LOST (VPN down off site) or LOST -> none ----
// 2026-11-03 (owner, "panic on VPN down"): VPN down off site is LOST, so "AT RISK" is no longer reachable; the bloom-free
// control is OK -> OK and the must-not-bloom case is the API recovering while the VPN is still down.
// Truth: the bloom is extra drawing (rings, sparks, confetti) right after the transition. Measured as recorded instances
// in the 4 frames after it, relative to the frame before; LOST -> OK is the positive control.
const NET = { lost: { vpn: { state: "up", on_site: true }, api: { state: "failing", error_kind: "network" } },
  vpnDown: { vpn: { state: "down", on_site: false }, api: { state: "ok" } }, ok: { vpn: { state: "up", on_site: true }, api: { state: "ok" } }, none: {} };
function bloomExtra(sp, a, b) { const st = scene(sp), two = [{ project: "Alpha" }, { project: "Beta" }];
  upd(st, snapshot(two, { machine: NET[a] })); st.fire(); st.step(24 * 4);
  const n = () => +st.ev("__nativeFrame().n"), pre = n(); upd(st, snapshot(two, { machine: NET[b] })); let mx = -1e9;
  for (let i = 0; i < 4; i++) { st.step(2); mx = Math.max(mx, n() - pre); } return mx; }
if (!only || only === "7") for (const sp of SPECIES) {
  const ok = bloomExtra(sp, "lost", "ok"), risk = bloomExtra(sp, "lost", "vpnDown"), none = bloomExtra(sp, "lost", "none"), base = bloomExtra(sp, "ok", "ok");
  check(ok >= base + 25, `#7 ${sp}: LOST -> OK blooms (control: +${ok} instances vs OK -> OK +${base})`);
  // leaving LOST also un-drains the flock (lights and traffic resume), which adds some drawing without a bloom, so the
  // bar is the midpoint between the bloom-free edge and the bloom control (before the fix both equal the control)
  const bar = (ok + base) / 2;
  check(risk < bar && none < bar, `#7 ${sp}: LOST -> still-LOST, VPN down (+${risk}) and LOST -> none (+${none}) do not bloom (bar < ${bar})`);
}

// ---- 14: pip core >= 1.8 px across at the 50 % size slider ----
if (!only || only === "14") {
  const arcs = [];
  const st = scene("c5_fireflies", { before: g => { const P = g.CanvasRenderingContext2D.prototype, f = P.arc;
    P.arc = function (x, y, r) { if (this.fillStyle === "rgba(255,244,220,1)") arcs.push(r); return f.apply(this, arguments); }; } });
  st.ev("SpritesStage.setScale(0.5)");
  upd(st, snapshot([{ project: "Alpha" }], { projects: [{ key: "alpha", name: "Alpha", counts: { burning: 3 } }] })); st.fire(); st.step(24 * 3);
  arcs.length = 0; st.step(2); const d = 2 * Math.min(...arcs);
  check(arcs.length > 0 && d >= 1.8 - 1e-9, `#14 pip core at 50 %: ${d.toFixed(3)} px across (>= 1.8), ${arcs.length} pips`);
}

// ---- 15: debounce corners (pinned choice: any adverse time counts toward the hold; owner may reverse) ----
if (!only || only === "15") {
  const st = makeStage({ query: "stale=0&vpndebounce=2" });
  const seq = steps => JSON.parse(st.ev(`(() => { __stage.resetVpn(); return JSON.stringify(${JSON.stringify(steps)}.map(([r, t]) => __stage.linkDebounce(r, t))); })()`));
  let r = seq([["none", 0], ["lost", 100], ["lost", 2099], ["lost", 2100]]);
  check(JSON.stringify(r) === JSON.stringify(["none", "none", "none", "lost"]), "#15 none -> lost reports none (not ok) during the hold", r);
  r = seq([["none", 0], ["risk", 100], ["risk", 2100]]);
  check(JSON.stringify(r) === JSON.stringify(["none", "none", "risk"]), "#15 none -> risk reports none during the hold", r);
  r = seq([["ok", 0], ["lost", 100], ["lost", 2099]]);
  check(JSON.stringify(r) === JSON.stringify(["ok", "ok", "ok"]), "#15 ok -> lost reports ok during the hold", r);
  r = seq([["lost", 0], ["risk", 1900], ["risk", 2000]]);
  check(JSON.stringify(r) === JSON.stringify(["ok", "ok", "risk"]), "#15 pinned: 1.9 s LOST then AT RISK shows at 2.0 s (adverse time counts)", r);
  r = seq([["lost", 0], ["lost", 2500], ["risk", 2600], ["risk", 2700]]);
  check(JSON.stringify(r) === JSON.stringify(["ok", "lost", "risk", "risk"]), "#15 pinned: shown LOST -> API ok, VPN down off site: AT RISK at once, no ok gap", r);
  r = seq([["none", 0], ["lost", 100], ["lost", 2100], ["none", 2200]]);
  check(JSON.stringify(r) === JSON.stringify(["none", "none", "lost", "none"]), "#15 lost -> none: recovery immediate", r);
}

// ---- 19: the quietUnderStrain text must not promise a frame-rate cut (constant fps, SHIP_PLAN ruling 7) ----
if (!only || only === "19") {
  const vm = require("vm"), g = { window: {} }; vm.createContext(g); vm.runInContext(fs.readFileSync(path.join(ROOT, "app/behaviors.js"), "utf8"), g);
  const b = g.window.SPRITES_BEHAVIORS.find(x => x.key === "quietUnderStrain");
  const sj = fs.readFileSync(path.join(ROOT, "app/settings.js"), "utf8").split("\n").find(l => /^\s*quietUnderStrain:/.test(l)) || "";
  for (const [where, t] of [["behaviors.js", b.label + " " + b.desc], ["settings.js", sj]])
    check(!/frame rate|fps/i.test(t) && /flourish/i.test(t), `#19 ${where}: text matches what the runtime does (skip flourishes; no fps change)`, t.trim());
}
// ---- package D (reviews/SPRITES_REVIEW_R1_SPEC.md S2, S3; R2_SPEC #1, #4). Truths derived by hand from the layout. ----
// S2/S3: a near-maximised focus (0,30,1480x1087) leaves a 248 px bare strip at x 1480..1728, wide enough for every
// species at live size (reported r <= 40), so "nothing fits" is false: the creature must end VISIBLE and OUTSIDE the
// focus, and leave the focus at its normal speed (owner: "move off immediately"). Bar: the shortest way out is 875 ->
// 1480 + r, about 640 px; at the pieces' cruising speed (c2 vmax 170 px/s outside the focus) that is 3.8 s, so 6 s.
const inF = (r, F) => r.x + r.r > F[0] && r.x - r.r < F[0] + F[2] && r.y + r.r > F[1] && r.y - r.r < F[1] + F[3];
if (!only || only === "S2") for (const sp of SPECIES) for (const mem of [0.3, 1.0, 2.5]) {
  const st = scene(sp); upd(st, snapshot([{ project: "Alpha", load: { cpu_cores: 0.03, mem_gb: mem, procs: 1 } }])); st.fire(); st.step(48);
  st.ev(`(() => { const V = __stage.V("${sp}"); V._def.place(V, "100@1", 875, 300); })()`);
  const F = [0, 30, 1480, 1087];
  st.ev(`SpritesStage.setWindows([{x:0,y:30,w:1480,h:1087,pid:1}]); SpritesStage.setFocus({x:0,y:30,w:1480,h:1087})`);
  let left = -1, r = null, a = 0;
  for (let i = 0; i < 24 * 12; i++) { st.step(1); r = reports(st, sp)["100@1"]; a = +st.ev(`__stage.V("${sp}").alpha("100@1")`);
    if (left < 0 && !inF(r, F) && a > 0.5) left = i / 24; }
  check(a > 0.5 && !inF(r, F), `S2 ${sp}: near-maximised focus, the 248 px strip fits: ends visible outside (mem ${mem} GB, a ${a.toFixed(2)} at ${Math.round(r.x)},${Math.round(r.y)} r ${Math.round(r.r)})`);
  check(left >= 0 && left <= 6, `S3 ${sp}: leaves the focus within 6 s (mem ${mem} GB, left at ${left} s)`);
}
// R2S-1: cursor parked half a radius off-centre for 60 s: the creature stays hovered (owner: "holds centred under it").
if (!only || only === "R2S1") for (const sp of SPECIES) {
  const st = scene(sp); upd(st, snapshot([{ project: "Alpha" }])); st.fire(); st.step(48);
  const r0 = reports(st, sp)["100@1"]; st.ev(`SpritesStage.setCursor({x:${r0.x + 0.5 * r0.r},y:${r0.y}})`); st.step(24);
  let hov = 0, n = 0; for (let k = 0; k < 60 * 6; k++) { st.step(4); n++; if (st.ev(`(() => { const h = __stage.V("${sp}")._hover(); return !!h && h.id === "100@1"; })()`)) hov++; }
  check(hov / n >= 0.98, `R2S-1 ${sp}: parked cursor, hovered ${(100 * hov / n).toFixed(0)} % of 60 s (>= 98 %)`);
}
// R2S-4: a faded-out creature (full-screen focus, nothing fits) is not hovered by a cursor at its last spot.
if (!only || only === "R2S4") for (const sp of SPECIES) {
  const st = scene(sp); upd(st, snapshot([{ project: "Alpha" }])); st.fire(); st.step(48);
  st.ev(`SpritesStage.setWindows([{x:0,y:0,w:${W},h:${H},pid:1}]); SpritesStage.setFocus({x:0,y:0,w:${W},h:${H}})`); st.step(24 * 4);
  const r = reports(st, sp)["100@1"], a = +st.ev(`__stage.V("${sp}").alpha("100@1")`);
  st.ev(`SpritesStage.setCursor({x:${r.x},y:${r.y}})`); st.step(12);
  const h = st.ev(`JSON.stringify(__stage.V("${sp}")._hover())`);
  check(a < 0.1 && h === "null", `R2S-4 ${sp}: faded (a ${a.toFixed(3)}) and not hovered`, h === "null" ? undefined : h.slice(0, 80));
}
// S1: a needs-you creature routes round the focus. Focus (200,120,1328x700); the creature rests outside, below it
// (placed at 1000,1000: the strip y 820..1031 is bare desktop), then turns needs-you. Its hit disc (what captures clicks)
// must never overlap the focused window on the way to the knock spot. Truth: disc rect test against the focus rect.
// S8: nudgeLongWait: waiting 20 min (k = 0.5 cap) it rests nearer the focus than waiting 1 min, never touching it.
const needSnap = (sec, mem) => snapshot([{ project: "Alpha", attention: { state: "needs_you", since: Date.now() / 1000 - sec }, load: { cpu_cores: 0.03, mem_gb: mem || 0.3, procs: 1 } }]);
function discIn(h, F) { return rectGap(h, F) < h.r; }   // the hit disc is a circle: it overlaps when the focus rect is nearer than r
function rectGap(r, F) { const dx = Math.max(F[0] - r.x, 0, r.x - (F[0] + F[2])), dy = Math.max(F[1] - r.y, 0, r.y - (F[1] + F[3])); return Math.hypot(dx, dy); }
function needsRun(sp, sec, secs, mem) {
  const st = scene(sp); upd(st, snapshot([{ project: "Alpha", load: { cpu_cores: 0.03, mem_gb: mem || 0.3, procs: 1 } }])); st.fire(); st.step(24);
  const F = [200, 120, 1328, 700];
  st.ev(`SpritesStage.setWindows([{x:200,y:120,w:1328,h:700,pid:1}]); SpritesStage.setFocus({x:200,y:120,w:1328,h:700})`); st.step(6);
  st.ev(`(() => { const V = __stage.V("${sp}"); V._def.place(V, "100@1", 1000, 1000); })()`); st.step(24 * 3);
  upd(st, needSnap(sec, mem)); st.fire(); let inside = 0, n = 0, worst = 0;
  for (let i = 0; i < 24 * secs; i += 4) { st.step(4); const h = hits(st).find(z => z.id === "100@1"); if (!h) continue; n++;
    if (discIn(h, F)) { inside++; worst = Math.max(worst, h.r - rectGap(h, F)); if (process.env.DBG) console.log("in", i / 24, JSON.stringify(h)); } }
  const r = reports(st, sp)["100@1"], h = hits(st).find(z => z.id === "100@1");
  return { inside, n, worst, gap: rectGap(r, F) - r.r, hgap: h ? rectGap(h, F) - h.r : NaN, r }; }
if (!only || only === "S1") for (const sp of SPECIES) {
  for (const mem of [0.3, 1.0, 2.5]) { const o = needsRun(sp, 5, 12, mem);
  check(o.n > 0 && o.inside === 0, `S1 ${sp}: needs-you route keeps the hit disc off the focus (${o.inside}/${o.n} samples inside, worst ${o.worst.toFixed(0)} px, mem ${mem} GB)`); }
}
if (!only || only === "S8") for (const sp of SPECIES) {
  // Truth (SHIP_PLAN nudgeLongWait, runtime navNeed): at 20 min k = 0.5, so the hit disc's gap to the focus beyond the
  // 6 px floor halves: expect b <= 6 + (a - 6) / 2 + 4 (4 px for the knock wobble), and b > 0 (never touching).
  const a = needsRun(sp, 60, 14), b = needsRun(sp, 1200, 14), want = 6 + (a.hgap - 6) / 2 + 4;
  check(b.hgap <= want && b.hgap > 0 && b.inside === 0, `S8 ${sp}: 20 min wait: disc gap ${b.hgap.toFixed(0)} px (<= ${want.toFixed(0)}; 1 min ${a.hgap.toFixed(0)}), never touching (${b.inside} inside)`);
}
// S6: edgeWhileTyping "dims a touch" (alpha -> ~0.8 while typing) and sleepWhenAway "a slow dim sleep" (alpha eases to
// ~0.4 after 5 min idle, not at once), then "a soft wake that shows what changed": a session whose state changed while
// away gets one flare on return (extra recorded instances), one whose state did not change gets none.
// OPEN (package D stopped at budget): no runtime dim/wake yet, so this runs only on request (node ... S6), not by default.
if (only === "S6") for (const sp of SPECIES) {
  const st = scene(sp), two = [{ project: "Alpha" }, { project: "Beta" }]; upd(st, snapshot(two)); st.fire(); st.step(48);
  const al = id => +st.ev(`__stage.V("${sp}").alpha("${id}")`), a0 = al("100@1");
  st.ev(`SpritesStage.setActivity({typing:true, idleSec:0})`); st.step(24 * 3); const aT = al("100@1");
  st.ev(`SpritesStage.setActivity({typing:false, idleSec:0})`); st.step(24 * 3); const aB = al("100@1");
  check(Math.abs(a0 - 1) < 0.01 && Math.abs(aT - 0.8) < 0.05 && Math.abs(aB - 1) < 0.02, `S6 ${sp}: typing dims a touch (alpha ${a0.toFixed(2)} -> ${aT.toFixed(2)} -> ${aB.toFixed(2)})`);
  st.ev(`SpritesStage.setActivity({typing:false, idleSec:400})`); st.step(12); const aS0 = al("100@1"); st.step(24 * 8); const aS = al("100@1");
  check(aS0 > 0.85 && Math.abs(aS - 0.4) < 0.06, `S6 ${sp}: away = slow dim sleep (alpha ${aS0.toFixed(2)} after 0.5 s, ${aS.toFixed(2)} after 8 s)`);
  // while away, Alpha starts working; Beta stays idle. Return: count flares the runtime holds for each.
  upd(st, snapshot([{ project: "Alpha", attention: { state: "working" } }, { project: "Beta" }])); st.fire(); st.step(24 * 2);
  st.ev(`SpritesStage.setActivity({typing:false, idleSec:0})`); st.step(6);
  const fl = JSON.parse(st.ev(`JSON.stringify(__stage.V("${sp}").__flares())`));
  check(fl.includes("100@1") && !fl.includes("101@1"), `S6 ${sp}: soft wake marks the session that changed while away (flares ${JSON.stringify(fl)})`);
  st.step(24 * 3); const aW = al("100@1");
  check(Math.abs(aW - 1) < 0.03, `S6 ${sp}: awake again, full alpha (${aW.toFixed(2)})`);
}
// R2S-2: quietUnderStrain "cut particles (red glow stays)". Truth: the runtime contract defines P.density as "lit elements /
// particles per creature"; under strain level >= 2 with the switch on it is halved (live only), off or below level 2 it
// is untouched, so the recorded instance count drops under strain with the switch on and is identical otherwise.
// OPEN (package D stopped at budget): no particle cut yet; runs only on request (node ... R2S2).
if (only === "R2S2") for (const sp of SPECIES) {
  const run = (score, quiet) => { const st = scene(sp); st.ev(`SpritesStage.setBehaviors({quietUnderStrain:${quiet}})`);
    upd(st, snapshot([{ project: "Alpha", load: { cpu_cores: 2.5, mem_gb: 2.0, procs: 6 }, attention: { state: "working" } }],
      { machine: { vpn: { state: "up", on_site: true }, strain: { score }, thermal: { state: 2 } } })); st.fire(); st.step(24 * 6);
    let n = 0, d = 0; for (let i = 0; i < 8; i++) { st.step(3); n += +st.ev("__nativeFrame().n"); } d = +st.ev(`__stage.V("${sp}").P.density`); return [n, d]; };
  const [hiOn, dOn] = run(3.2, true), [hiOff, dOff] = run(3.2, false), [loOn] = run(1.0, true), [loOff] = run(1.0, false);
  check(dOn === 0.5 * dOff && hiOn < hiOff, `R2S-2 ${sp}: level >= 2, switch on: density ${dOn} (off ${dOff}), instances ${hiOn} < ${hiOff}`);
  check(loOn === loOff, `R2S-2 ${sp}: level < 2: switch changes nothing (${loOn} vs ${loOff})`);
}
// R3-SPEC #1, #2: the host captures the mouse over every posted hit, so demo and a stale snapshot post none (no dead zones)
if (!only || only === "R3S") {
  const st = makeStage({ query: "vpndebounce=0" });
  st.ev(`SpritesStage.setSize(${W},${H}); SpritesStage.setCast({projects:{Alpha:{concept:"c5_fireflies",iv:1,hex:"#55aaff"}}})`);
  const ch = () => JSON.parse(st.ev("JSON.stringify(__stage.clickHits())")).length;
  upd(st, snapshot([{ project: "Alpha" }], { valid_until: Date.now() / 1000 + 3600 })); st.fire(); st.step(48);
  check(ch() === 1, "R3S live snapshot: one clickable hit", ch());
  upd(st, snapshot([{ project: "Alpha" }], { valid_until: Date.now() / 1000 - 60 })); st.fire(); st.step(24);
  check(ch() === 0, "R3S snapshot 60 s past valid_until: no clickable hits", ch());
  st.ev("SpritesStage.setDemo(true)"); st.step(24 * 10);
  check(hits(st).length > 0 && ch() === 0, `R3S demo: ${hits(st).length} drawn, none clickable`, ch());
}
done();
