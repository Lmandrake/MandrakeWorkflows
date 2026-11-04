#!/usr/bin/env node
/* Augur 1.2 headless children (sessions[].parent): drawn as satellites of the parent creature, never as their own
 * creatures; a hidden parent hides them; a child whose parent is not in the snapshot falls back to a white sprite.
 * app/stage.html in a node vm (stage_vm.js), nothing rendered except through the native canvas shim (draw errors land
 * in __errors). Run: node sprites/tests/node/test_headless_satellites.js. Exit 0 = all pass. */
"use strict";
const path = require("path"), ROOT = path.resolve(__dirname, "../.."), load = require("./stage_vm.js");
let fails = 0, passes = 0;
const check = (ok, msg, got) => { ok ? passes++ : fails++; console.log((ok ? "PASS " : "FAIL ") + msg + (ok || got === undefined ? "" : "  got " + JSON.stringify(got))); };
const sess = (id, key, extra) => Object.assign({ id, pid: parseInt(id), started_at: parseInt(id), project: key, project_key: key, managed: true,
  attention: { state: "working" }, load: { cpu_cores: 0.1, mem_gb: 0.3, procs: 2 }, tasks: { background: 1 } }, extra || {});
const snap = sessions => ({ schema: "augur.snapshot", version: "1.2", valid_until: 9e12, sessions, projects: [], machine: { vpn: { state: "up", on_site: false } } });
function stage(cast, sn) { const S = load(ROOT), c = S.ctx; c.SpritesStage.setProjects([]); c.SpritesStage.setSize(1440, 900);
  c.SpritesStage.setCast(cast); c.SpritesStage.update(sn); S.advance(3000); return S; }
const A = sess("100@1", "ember28"), C1 = sess("200@2", "ember28", { headless: true, parent: "100@1", load: { cpu_cores: 0.7, mem_gb: 0.2, procs: 1 } }),
  C2 = sess("300@3", "ember28", { headless: true, parent: "100@1", load: { unknown: "warming_up" } });

let S = stage({ projects: {} }, snap([A, C1, C2]));
let m = S.ctx.__stage.model, ids = m.sessions.map(x => x.id);
check(JSON.stringify(ids) === '["100@1"]', "children are not creatures of their own", ids);
const h = m.S.s["100@1"].heads || [];
check(h.length === 2 && h[0].id === "200@2" && h[0].cpu === 0.7 && !("cpu" in h[1]), "parent carries one satellite per child with its cpu_cores (unset when unmeasured)", h);
check(m.S.s["100@1"].procs === 1, "background-task satellites are unchanged", m.S.s["100@1"].procs);
check(!(S.ctx.__errors || []).length, "draws without errors", S.ctx.__errors);

S = stage({ projects: { ember28: { visibility: "hide" } } }, snap([A, C1]));
ids = S.ctx.__stage.model.sessions.map(x => x.id);
check(ids.length === 0, "a hidden parent hides its children", ids);

S = stage({ projects: {} }, snap([C1]));
m = S.ctx.__stage.model; const o = m.sessions.find(x => x.id === "200@2");
check(!!o && o.white === true, "a child whose parent is not in the snapshot is a white sprite", o && o.white);

S = stage({ projects: {} }, snap([A]));
check(!("heads" in S.ctx.__stage.model.S.s["100@1"]), "no children: no heads key");

const D = S.ctx.__stage.demoState(); const dh = Object.values(D.S.s).filter(d => d.heads && d.heads.length);
check(dh.length >= 1, "demo mode shows headless satellites", dh.length);
const lay = Object.values(S.ctx.__stage.layers).map(l => l.V).find(v => v && v.headBright), hb = lay && lay.headBright;
check(!!hb, "runtime exposes headBright", !!hb);
if (hb) { check(Math.abs(hb(0) - 0.35) < 1e-9, "0 cores -> 35% floor", hb(0)); check(hb(1) === 1 && hb(3) === 1, "1+ cores -> full", [hb(1), hb(3)]);
  check(hb(undefined) === 0.35 && hb(NaN) === 0.35 && hb(null) === 0.35, "missing cpu -> floor, never invisible", hb(undefined));
  check(hb(0.25) > 0.35 && hb(0.25) < 1 && hb(0.25) < hb(0.7), "mid cpu is between floor and full, monotonic", [hb(0.25), hb(0.7)]); }
console.log(passes + " passed, " + fails + " failed"); process.exit(fails ? 1 : 0);
