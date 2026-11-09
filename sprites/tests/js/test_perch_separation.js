// Gentle separation (owner 2026-11-08: sprites perching on one window stood on top of each other). Node only, fake clock,
// no render. Run: node sprites/tests/js/test_perch_separation.js
"use strict";
const { makeStage, snapshot, check, done } = require("./harness.js");
const W = 1728, H = 1117, SP = "c5_fireflies";
function run(n, win, secs) {
  const st = makeStage({ query: "stale=0&vpndebounce=0" });
  st.ev(`SpritesStage.setSize(${W},${H}); SpritesStage.setCast({projects:{Alpha:{concept:"${SP}",iv:1,hex:"#55aaff"},Beta:{concept:"${SP}",iv:2,hex:"#ffaa55"}}})`);
  st.ev(`SpritesStage.update(${JSON.stringify(snapshot([{ project: "Alpha" }, { project: "Beta" }].slice(0, n)))})`); st.fire(); st.step(48);
  st.ev(`SpritesStage.setWindows(${JSON.stringify(win)})`);
  const rep = () => JSON.parse(st.ev(`JSON.stringify(__stage.V("${SP}").__report().reports)`));
  const steer = () => JSON.parse(st.ev(`JSON.stringify(Object.fromEntries(Object.entries(__stage.V("${SP}").__idMaps()._steer).map(([k, v]) => [k, v.perch])))`));
  let min = 1e9, body = 0, samples = 0, last = "";
  for (let t = 0; t < 24 * secs; t++) { st.step(1);
    if (t % 6) continue; const p = steer(), a = p["100@1"], b = p["101@1"]; if (!a || !b) continue;   // both have a perch spot at once
    const r = rep(); body = 2 * Math.max(r["100@1"].r, r["101@1"].r); const key = a.join() + b.join();
    if (key !== last) { last = key; samples++; min = Math.min(min, Math.hypot(a[0] - b[0], a[1] - b[1])); } }   // one sample per distinct pair of spots
  return { min, body, samples }; }
// One narrow window: the old random pick often put both perchers within a body width of each other.
const win = [{ x: 500, y: 500, w: 130, h: 300, pid: 1 }];
const r = run(2, win, 2400);
check(r.samples >= 4, "both sprites perched on the one window for a while", r);
check(r.min >= r.body, `two idle sprites perched on one window stay at least a body width apart (min ${r.min.toFixed(1)} vs body ${r.body.toFixed(1)})`, r);
// Interaction exemption: a greeting pair may overlap, the pull must not act on it.
{ const st = makeStage({ query: "stale=0&vpndebounce=0" });
  st.ev(`SpritesStage.setSize(${W},${H}); SpritesStage.setCast({projects:{Alpha:{concept:"${SP}",iv:1,hex:"#55aaff"},Beta:{concept:"${SP}",iv:2,hex:"#ffaa55"}}})`);
  st.ev(`SpritesStage.update(${JSON.stringify(snapshot([{ project: "Alpha" }, { project: "Beta" }]))})`); st.fire(); st.step(48);
  const V = `__stage.V("${SP}")`;
  const hits = JSON.parse(st.ev(`JSON.stringify(__stage.allHits())`));
  check(hits.length === 2 && hits.every(h => !h.ix), "idle sprites are not flagged as interacting", hits);
  st.ev(`${V}._onLive({ greet: { id: "100@1", x: 800, y: 500 } })`);
  const g = JSON.parse(st.ev(`JSON.stringify(${V}.__report().reports)`)); st.step(12);
  const h2 = JSON.parse(st.ev(`JSON.stringify(__stage.allHits())`));
  check(h2.some(h => h.ix), "a greeting sprite is flagged as interacting (exempt from the pull)", h2); }
done();
