// Headless stage for logic tests: app/native/canvas.js + shim.js + app/stage.html's scripts in a node vm, with a FAKE
// clock (no real time, no renders, no browser). Timers fire when due on that clock; step(n) advances 1/24 s n times,
// so the stage's own 24 fps loop draws each frame.
"use strict";
const fs = require("fs"), path = require("path"), vm = require("vm");
const ROOT = path.resolve(__dirname, "../..");
function makeStage(opts = {}) {
  let clock = 1000; const timers = new Map();
  const g = vm.createContext({ console }); g.globalThis = g;
  g.__native = { now: () => clock, read: rel => { try { return fs.readFileSync(path.join(ROOT, rel), "utf8"); } catch (e) { return null; } },
    post: () => {}, timer: (id, ms, rep) => timers.set(id, { due: clock + ms, ms, rep }), cancel: id => timers.delete(id), log: () => {}, present: () => {},
    query: opts.query || "stale=0", dpr: 2, w: opts.w || 1728, h: opts.h || 1117 };
  const run = f => vm.runInContext(fs.readFileSync(path.join(ROOT, f), "utf8"), g, { filename: f });
  run("app/native/canvas.js"); run("app/native/shim.js");
  if (opts.before) opts.before(g);
  const html = fs.readFileSync(path.join(ROOT, "app/stage.html"), "utf8"); let inline = null;
  for (const m of html.matchAll(/<script(?:\s+src="([^"]+)")?[^>]*>([\s\S]*?)<\/script>/g)) { if (m[1]) run(path.normalize("app/" + m[1])); else inline = m[2]; }
  vm.runInContext(inline, g, { filename: "stage.html" });
  function advance(ms) { const end = clock + ms;
    for (let guard = 0; guard < 100000; guard++) { let id = null, due = Infinity; for (const [k, t] of timers) if (t.due < due) { due = t.due; id = k; }
      if (id === null || due > end) break; clock = Math.max(clock, due); const t = timers.get(id);
      if (t.rep) t.due = clock + Math.max(4, t.ms); else timers.delete(id); g.__nativeFire(id); }
    clock = end; }
  const fire = () => advance(0);
  const ev = s => vm.runInContext(s, g);
  const step = (n = 1) => advance(n * 1000 / 24);
  return { g, ev, step, fire, get clock() { return clock; } };
}
function snapshot(sessions, extra = {}) {
  return Object.assign({ schema: "augur.snapshot", version: "1.1", valid_until: 9e12, sessions: sessions.map((s, i) => Object.assign({ id: (100 + i) + "@1", pid: 100 + i, started_at: 1 + i, project: s.project,
    project_key: s.project.toLowerCase(), managed: true, attention: { state: "idle" }, load: { cpu_cores: 0.1, mem_gb: 0.3, procs: 2 } }, s)),
    machine: { vpn: { state: "up", on_site: true } }, projects: [] }, extra);
}
let failures = 0, passes = 0;
function check(ok, name, detail) { if (ok) passes++; else failures++; console.log((ok ? "PASS " : "FAIL ") + name + (detail !== undefined ? "  " + JSON.stringify(detail) : "")); }
function done() { console.log(`${passes} pass, ${failures} fail`); process.exit(failures ? 1 : 0); }
module.exports = { makeStage, snapshot, check, done, ROOT };
