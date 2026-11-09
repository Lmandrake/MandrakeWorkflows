// Aether wake reader (owner card 2026-11-08 18:30 PST): "an idle sprite at play sometimes follows another sprite's
// leftover current a little ... keep it rare and subtle so it never reads as one project following another".
// Node only, fake clock, no render. The host's currents arrive by SpritesStage.setCurrents(k, {id: [vx, vy]}).
// Run: node sprites/tests/js/test_wake_reader.js
"use strict";
const { makeStage, snapshot, check, done } = require("./harness.js");
const W = 1728, H = 1117, SP = "c5_fireflies", A = "100@1", B = "101@1";
function stage() {
  const st = makeStage({ query: "stale=0&vpndebounce=0" });
  st.ev(`SpritesStage.setSize(${W},${H}); SpritesStage.setCast({projects:{Alpha:{concept:"${SP}",iv:1,hex:"#55aaff"},Beta:{concept:"${SP}",iv:2,hex:"#ffaa55"}}})`);
  st.ev(`SpritesStage.setBehaviors({play:false})`);   // play pairs would exempt them; this isolates the wander branch
  st.ev(`SpritesStage.update(${JSON.stringify(snapshot([{ project: "Alpha" }, { project: "Beta" }]))})`); st.fire(); st.step(48);
  return st;
}
const reads = st => JSON.parse(st.ev(`JSON.stringify(__stage.V("${SP}").__reads())`));
const rep = st => JSON.parse(st.ev(`JSON.stringify(__stage.V("${SP}").__report().reports)`));
function run(k, map, secs, every) { const st = stage(); st.ev(`SpritesStage.setCurrents(${k}, ${JSON.stringify(map)})`);
  for (let t = 0; t < secs; t++) { st.step(24); if (every) every(st, t); } return st; }
const MIN = 60, cur = { [A]: [30, 0], [B]: [0, -12] };
// 1. off: never a read, even with currents present
{ const st = run(0, cur, 6 * MIN); check(reads(st).length === 0, "reader off (k 0): no sprite ever follows a current", reads(st).length); }
// 2. full strength: reads happen, rarely, small, along the current, each sprite on its own schedule
{ const st = run(1, cur, 12 * MIN), r = reads(st), a = r.filter(x => x.id === A), b = r.filter(x => x.id === B);
  check(a.length >= 3 && b.length >= 3, "k 1: both sprites read their currents", [a.length, b.length]);
  check(a.length <= 12 * 60 / 45 + 1 && b.length <= 12 * 60 / 45 + 1, "rare: never more than one read per 45 s per sprite", [a.length, b.length]);
  check(r.every(x => Math.hypot(x.dx, x.dy) <= 40 + 1e-9), "subtle: every nudge is at most 40 px", r.map(x => Math.round(Math.hypot(x.dx, x.dy))));
  check(a.every(x => x.dx > 0 && Math.abs(x.dy) < 1e-9) && b.every(x => x.dy < 0 && Math.abs(x.dx) < 1e-9), "each nudge points along that sprite's own current");
  const ta = a.map(x => Math.round(x.t)), tb = b.map(x => Math.round(x.t));
  check(ta.join() !== tb.join(), "each sprite reads on its own schedule (no lockstep between projects)", [ta.slice(0, 4), tb.slice(0, 4)]); }
// 3. default strength (0.3): only some read moments read
{ const st = run(0.3, cur, 20 * MIN), r = reads(st).length, moments = 2 * 20 * 60 / (45 + 75 / 2);
  check(r > 0 && r < 0.6 * moments, "default: only some read moments read (sometimes, never always)", { reads: r, moments: Math.round(moments) }); }
// 4. no current, or a weak one: no read
{ const st = run(1, { [A]: [1, 1] }, 6 * MIN); check(reads(st).length === 0, "a sprite with no (or only a faint) leftover current never reads", reads(st)); }
// 5. it moves the sprite a little, along the current: same stage with and without, the difference while a read holds
{ let off = null; const pos = [];
  const st0 = run(0, cur, 6 * MIN, (s, t) => { pos[t] = rep(s)[A]; });
  let diff = 0, n = 0, worst = 0;
  const st1 = run(1, cur, 6 * MIN, (s, t) => { const r = reads(s).filter(x => x.id === A), p = rep(s)[A], q = pos[t];
    if (r.length && t > r[r.length - 1].t - 1 && p && q) { const dx = p.x - q.x; diff += dx; n++; worst = Math.max(worst, Math.hypot(p.x - q.x, p.y - q.y)); } });
  off = n ? diff / n : 0;
  check(n > 0 && off > 2, "a read nudges the sprite along the current (x, compared with the same run without)", { n, off: +off.toFixed(1) });
  check(worst < 120, "and never far: the nudged sprite stays within ~3 body widths of where it would be", +worst.toFixed(1)); }
done();
