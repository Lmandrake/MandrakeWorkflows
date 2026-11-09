#!/usr/bin/env node
/* Focus / Untracked / Hidden (owner, 2026-11-08: "Any active sprites should be listed in Settings and with a click could
 * become Focused and thus retained with settings. There should be Focus, Untracked, or Hidden (don't show again).").
 * The row set is app/projects.js settingsRows over the table (build + mergeLocal: the host's local projects file) and
 * active(snapshot); the stage half is app/stage.html in a node vm (stage_vm.js, fake clock, nothing rendered).
 * Hand truth: the tables and snapshots below. Run: node sprites/tests/node/test_settings_tracking.js. Exit 0 = all pass. */
"use strict";
const path = require("path"), ROOT = path.resolve(__dirname, "../.."), load = require("./stage_vm.js"), SP = require("../../app/projects.js");
let fails = 0, passes = 0;
const check = (ok, msg, got) => { ok ? passes++ : fails++; console.log((ok ? "PASS " : "FAIL ") + msg + (ok || got === undefined ? "" : "  got " + JSON.stringify(got))); };
const NOW = Date.now() / 1000;
const sess = (id, project, key, extra) => Object.assign({ id, pid: parseInt(id), started_at: 1, project, project_key: key, managed: true,
  attention: { state: "idle", observed_at: NOW, valid_until: NOW + 60 } }, extra || {});
const snap = (sessions, projects) => ({ schema: "augur.snapshot", version: "1.2", written_at: NOW, valid_until: NOW + 60, sessions, projects: projects || [],
  machine: { vpn: { observed_at: NOW, valid_until: NOW + 60, state: "up", on_site: false } } });
const REG = "| Name | Path | Id |\n|---|---|---|\n| Lodestar | ~/dev/Lodestar | lodestar |\n| Hestia | ~/dev/Hestia | hestia |\n| Granite | ~/dev/Granite | granite |\n";
const LAUNCH = "| Name | Waypoint | Path | Command | Focus |\n|---|---|---|---|---|\n| Lodestar | | ~/dev/Lodestar | x | yes |\n| Granite | | ~/dev/Granite | x | |\n";
const table = local => SP.build({ registry: REG, launches: LAUNCH, home: "/h", local, hasWaypoint: true });
const keysOf = rows => rows.map(r => r.key + ":" + r.tracking);

// ---- 1. the list includes active non-focus sprites (a focus-less launch row, a registry project with no launch row,
//         an unmanaged dir) beside the focus entries; an inactive focus entry stays listed
const S1 = snap([sess("1@1", "Granite", "granite"), sess("2@1", "Hestia", "hestia", { attention: { state: "working" } }),
  sess("3@1", "Scratchpad", "scratchpad", { managed: false })], [{ key: "ember28", name: "Ember28", counts: { burning: 2, observed_at: NOW, valid_until: NOW + 60 } }]);
let rows = SP.settingsRows(table(null), { projects: {} }, SP.active(S1), true);
check(JSON.stringify(keysOf(rows)) === '["lodestar:focus","granite:untracked","hestia:untracked","scratchpad:untracked","ember28:untracked"]',
  "rows: the inactive focus entry, then every active sprite (non-focus launch row, no-launch project, unmanaged dir, ghost)", keysOf(rows));
check(rows.find(r => r.key === "hestia").live.state === "working" && rows.find(r => r.key === "lodestar").live === null &&
  rows.find(r => r.key === "ember28").live.state === "ghost", "each row carries its live state (working / not running / ghost)", rows.map(r => r.live && r.live.state));
check(rows.find(r => r.key === "scratchpad").live.white === true, "an unmanaged session is marked white");

// ---- 2. Untracked drops off when no longer active
rows = SP.settingsRows(table(null), { projects: {} }, SP.active(snap([sess("1@1", "Granite", "granite")])), true);
check(JSON.stringify(keysOf(rows)) === '["lodestar:focus","granite:untracked"]', "Untracked hestia, scratchpad and ember28 leave the list once inactive", keysOf(rows));
rows = SP.settingsRows(table(null), { projects: {} }, [], true);
check(JSON.stringify(keysOf(rows)) === '["lodestar:focus"]', "nothing active: only the focus entry", keysOf(rows));

// ---- 3. Focus with no launch alias persists through the local projects file across a restart (simulated: the file's
//         content, a fresh build and a fresh row set with nothing active)
const local = { hestia: { focus: true, hex: "#112233" }, scratchpad: { focus: true, name: "Scratchpad", dir: "/h/scratch" } };
const t2 = table(JSON.parse(JSON.stringify(local)));   // as the host re-reads projects.json after a relaunch
const cast = { projects: { hestia: { concept: "c3_sigils", iv: 2, hex: "#112233" }, scratchpad: { concept: "c9_wild", iv: 7, hex: "#B8C0CC", short: "Scr" } } };
rows = SP.settingsRows(t2, cast, [], true);
check(JSON.stringify(keysOf(rows)) === '["lodestar:focus","hestia:focus","scratchpad:focus"]', "after a restart, focused hestia and scratchpad are listed though inactive", keysOf(rows));
const h = t2.find(e => e.key === "hestia"), sc = t2.find(e => e.key === "scratchpad");
check(h.hex === "#112233" && h.alias === null, "a registry project with no launch row takes its focus and colour from the local file", h);
check(sc && sc.name === "Scratchpad" && sc.dir === "/h/scratch" && sc.local === true, "a dir the registry does not know gets an entry of its own from the file", sc);
check(t2.find(e => e.key === "lodestar").focus === true && table({ lodestar: { focus: false } }).find(e => e.key === "lodestar").focus === true,
  "with Waypoint the local file never overrides a project that has a launch alias");
const nowp = SP.build({ registry: REG, home: "/h", local: { granite: { focus: true } }, hasWaypoint: false });
check(nowp.find(e => e.key === "granite").focus === true && nowp.find(e => e.key === "lodestar").focus === false, "without Waypoint the local file is the only source of focus");

// ---- 4. Hidden wins, stays listed (last, for the collapsed section), and is restorable
const hc = { projects: { granite: { visibility: "hide" }, scratchpad: { visibility: "hide", name: "Scratchpad" } } };
rows = SP.settingsRows(table(null), hc, [], true);
check(JSON.stringify(keysOf(rows)) === '["lodestar:focus","granite:hidden","scratchpad:hidden"]', "Hidden projects stay listed, after the rest, even inactive", keysOf(rows));
check(SP.tracking({ projects: { lodestar: { visibility: "hide" } } }, "lodestar", { focus: true }) === "hidden", "Hidden wins over focus");
check(SP.tracking({ projects: { lodestar: { visibility: "hide_at_work" } } }, "lodestar", { focus: true }) === "focus", "Hide @ Work is not Hidden");

// ---- 5. the stage honours Hidden: no sprite, no ghost, no arrival; managed and unmanaged alike; Show brings it back
function stage(cast, sn, tbl) { const S = load(ROOT, "dpr=1&vpndebounce=0"), c = S.ctx; c.SpritesStage.setProjects(tbl || []); c.SpritesStage.setSize(1440, 900);
  c.SpritesStage.setCast(cast); c.SpritesStage.update(sn); S.advance(3000); return S; }
const ids = S => S.ctx.__stage.model.sessions.map(x => x.id).sort();
let S = stage({ projects: {} }, S1);
check(JSON.stringify(ids(S)) === '["1@1","2@1","3@1","ghost:ember28"]', "control: four sprites drawn", ids(S));
S = stage(hc, S1);
check(!ids(S).includes("1@1"), "a hidden managed project draws no sprite", ids(S));
S = stage({ projects: { scratchpad: { visibility: "hide" }, ember28: { visibility: "hide" } } }, S1);
check(JSON.stringify(ids(S)) === '["1@1","2@1"]', "a hidden unmanaged dir draws no sprite; a hidden project gets no ghost", ids(S));
const hits = S.ctx.__stage.allHits().map(z => z.id);
check(!hits.includes("3@1") && !hits.includes("ghost:ember28"), "and offers no hit circle (nothing clickable)", hits);
// arrival: hidden from the start, a new session of that key never appears on any layer
S = stage({ projects: { granite: { visibility: "hide" } } }, snap([sess("2@1", "Hestia", "hestia")]));
S.ctx.SpritesStage.update(snap([sess("2@1", "Hestia", "hestia"), sess("9@1", "Granite", "granite")])); S.advance(3000);
const onLayers = Object.keys(S.ctx.__stage.layers).some(c => { const V = S.ctx.__stage.V(c); return V && V.sessions && V.sessions.some(x => x.id === "9@1"); });
check(!ids(S).includes("9@1") && !onLayers, "a session arriving for a hidden project never reaches a layer (no arrival)", ids(S));
S.ctx.SpritesStage.setCast({ projects: {} }); S.advance(1500);
check(ids(S).includes("9@1"), "set back (visibility cleared): the sprite returns", ids(S));
// an unmanaged dir focused in Settings keeps its cast instead of drawing white and random
const tf = [{ key: "scratchpad", name: "Scratchpad", dir: "/h/scratch", alias: null, hex: "#B8C0CC", focus: true, local: true }];
S = stage({ projects: { scratchpad: { concept: "c9_wild", iv: 7, hex: "#33AA55" } } }, S1, tf);
const sx = S.ctx.__stage.model.sessions.find(x => x.id === "3@1");
check(sx && sx.white === false && sx.concept === "c9_wild" && sx.iv === 7, "a focused unmanaged dir draws its retained species and form", sx && [sx.white, sx.concept, sx.iv]);
S = stage({ projects: { scratchpad: { concept: "c9_wild", iv: 7 } } }, S1, []);
check(S.ctx.__stage.model.sessions.find(x => x.id === "3@1").white === true, "the same cast without a focus entry: still white (Untracked keeps nothing)");

console.log(passes + " passed, " + fails + " failed"); process.exit(fails ? 1 : 0);
