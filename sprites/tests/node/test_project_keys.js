#!/usr/bin/env node
/* Review R1 #1, #2, #16 and the stage half of #17, at the stage level: app/stage.html in a node vm (stage_vm.js, a fake
 * clock, nothing rendered). The project table below is written by hand from the data files (reviews/SPRITES_REVIEW_R1.md
 * Fixer response: launches.md -> waypoints.md -> registry Path -> registry Id), not produced by app/projects.js.
 * Hand truths: shortname.js drops the owner token, so Orchard_Mandrake -> "Orchard"; a Waypoint alias <= 10 chars that is
 * shorter wins, so KestrelWorks_Mandrake ("Kestrel Works", 13) -> "KesMine"; a cast short overrides. Hues by hand from the
 * hex: #CB50F0: max B, (R-G)/d + 4 = 123/160 + 4 = 4.769 -> 286 deg; #40C888: max G, (B-R)/d + 2 = 72/136 + 2 -> 152 deg.
 * Run: node sprites/tests/node/test_project_keys.js. Exit 0 = all pass. */
"use strict";
const path = require("path"), ROOT = path.resolve(__dirname, "../.."), load = require("./stage_vm.js");
let fails = 0, passes = 0;
const check = (ok, msg, got) => { ok ? passes++ : fails++; console.log((ok ? "PASS " : "FAIL ") + msg + (ok || got === undefined ? "" : "  got " + JSON.stringify(got))); };
const TABLE = [
  { key: "orchard-mandrake", name: "Orchard_Mandrake", dir: "/Users/x/dev/Orchard_Mandrake", alias: "Orchard", hex: "#CB50F0", focus: true },
  { key: "kestrel", name: "KestrelWorks_Mandrake", dir: "/Users/x/dev/KestrelWorks_Mandrake", alias: "KesMine", hex: "#40C888", focus: false },
  { key: "kestrel-team", name: "KestrelWorks", dir: "/Users/x/dev/KestrelWorks", alias: "KestrelWorks", hex: "#40C888", focus: true },
  { key: "microsoftgraphaccess", name: "MicrosoftGraphAccess", dir: "/Users/x/dev/MicrosoftGraphAccess", alias: "MSGRAPH", hex: "#3060F0", focus: false },
  { key: "lodestar", name: "Lodestar", dir: "/Users/x/dev/Lodestar", alias: "Lodestar", hex: "#FFCA42", focus: true },
];
const sess = (id, project, key, extra) => Object.assign({ id, pid: parseInt(id), started_at: parseInt(id), project, project_key: key, managed: true,
  attention: { state: "idle" }, load: { cpu_cores: 0.1, mem_gb: 0.3, procs: 2 } }, extra || {});
const snap = (sessions, projects) => ({ schema: "augur.snapshot", version: "1.1", valid_until: 9e12, sessions, projects: projects || [], machine: { vpn: { state: "up", on_site: true } } });
function stage(table, cast, sn) { const S = load(ROOT), c = S.ctx;
  if (typeof c.SpritesStage.setProjects === "function") c.SpritesStage.setProjects(table); else check(false, "SpritesStage.setProjects exists");
  c.SpritesStage.setSize(1440, 900); c.SpritesStage.setCast(cast); c.SpritesStage.update(sn); S.advance(3000); return S; }
function hoverShort(S, id) { const c = S.ctx, got = [], D = c.SpritesLabels.draw;
  c.SpritesLabels.draw = (x, o, ...r) => { got.push(o.short); return D(x, o, ...r); };
  const h = c.__stage.allHits().find(z => z.id === id); if (!h) return ["(no hit)"];
  c.SpritesStage.setCursor({ x: h.x, y: h.y }); S.advance(2000); c.SpritesStage.setCursor(null); S.advance(1500);
  c.SpritesLabels.draw = D; return [...new Set(got)]; }
const one = (key, project) => snap([sess("101@1", project, key)]);

// ---- #1 short names on the live stage ----
let S = stage(TABLE, { projects: {} }, one("orchard-mandrake", "Orchard_Mandrake"));
check(JSON.stringify(hoverShort(S, "101@1")) === '["Orchard"]', "#1 hover Orchard_Mandrake reads Orchard", hoverShort(S, "101@1"));
S = stage(TABLE, { projects: {} }, one("kestrel", "KestrelWorks_Mandrake"));
check(JSON.stringify(hoverShort(S, "101@1")) === '["KesMine"]', "#1 hover KestrelWorks_Mandrake reads its launch alias KesMine", hoverShort(S, "101@1"));
S = stage(TABLE, { projects: { "orchard-mandrake": { concept: "c1_choir", iv: 0, hex: "#CB50F0", short: "Aim" } } }, one("orchard-mandrake", "Orchard_Mandrake"));
check(JSON.stringify(hoverShort(S, "101@1")) === '["Aim"]', "#1 the cast's short name (keyed by project_key) overrides", hoverShort(S, "101@1"));
S = stage([], { projects: {} }, one("hestia-x", "Hestia_Mandrake"));
check(JSON.stringify(hoverShort(S, "101@1")) === '["Hestia"]', "#1 a project outside the table still gets its automatic short name", hoverShort(S, "101@1"));

// ---- #2 one namespace: cast and hue by project_key ----
const sOf = (S, id) => S.ctx.__stage.model.sessions.find(x => x.id === id) || {};
S = stage(TABLE, { projects: { "orchard-mandrake": { concept: "c3_sigils", iv: 5, hex: "#CB50F0" } } }, one("orchard-mandrake", "Orchard_Mandrake"));
let x = sOf(S, "101@1");
check(x.concept === "c3_sigils" && x.iv === 5 && x.hue === 286, "#2 cast saved under project_key applies: c3_sigils form 5, hue 286", [x.concept, x.iv, x.hue]);
S = stage(TABLE, { projects: { Orchard: { concept: "c2_siphon", iv: 3, hex: "#CB50F0" } } }, one("orchard-mandrake", "Orchard_Mandrake"));
x = sOf(S, "101@1");
check(x.concept === "c2_siphon" && x.iv === 3, "#2 a cast saved before under the launch alias (Orchard) still applies", [x.concept, x.iv]);
S = stage(TABLE, { projects: { KestrelWorks: { concept: "c4_kaleido", iv: 2, hex: "#40C888" } } }, one("kestrel", "KestrelWorks_Mandrake"));
x = sOf(S, "101@1");
check(x.concept !== "c4_kaleido" || x.iv !== 2, "#2 the TEAM repo's cast (KestrelWorks) does not leak onto the private KesMine sessions", [x.concept, x.iv]);
check(x.hue === 152, "#2 no cast: the hue is the project's Waypoint colour #40C888 (152)", x.hue);
S = stage(TABLE, { projects: {} }, snap([], [{ key: "microsoftgraphaccess", name: "MicrosoftGraphAccess", counts: { burning: 2 } }]));
x = sOf(S, "ghost:microsoftgraphaccess");
check(x.ghost === true && x.key === "microsoftgraphaccess" && x.hue === 225,
  "#2 ghost keeps its key and the Waypoint hue (#3060F0: max B, (R-G)/d + 4 = -0.25 + 4 -> 225)", [x.ghost, x.key, x.hue]);

// ---- #17 (stage half): clicks say ghost explicitly and carry the key ----
const hit = (S, id) => S.ctx.__stage.allHits().find(h => h.id === id) || {};
let h = hit(S, "ghost:microsoftgraphaccess");
check(h.ghost === true && h.key === "microsoftgraphaccess", "#17 a ghost hit carries ghost: true and its project_key", h);
S = stage(TABLE, { projects: {} }, snap([sess("ghost:7@1", "Lodestar", "lodestar")]));
h = hit(S, "ghost:7@1");
check(h.ghost === false && h.key === "lodestar", "#17 a real session whose id starts with ghost: is not a ghost", h);
S.ctx.__posts.length = 0; if (h.x != null) S.ctx.__nativeMouse(h.x, h.y);
const clk = (S.ctx.__posts.find(p => p.click) || {}).click || {};
check(clk.ghost === false && clk.key === "lodestar" && clk.id === "ghost:7@1", "#17 the click message says ghost: false with the key", clk);

// ---- #16 adapter edge cases ----
const ad = (sn) => { const T = load(ROOT); try { return T.ctx.__stage.adaptState(sn, 1); } catch (e) { return { error: e.message }; } };
let a = ad(snap([sess("5@1", "ollama", "ollama", { managed: false })], [{ key: "ollama", name: "ollama", counts: { burning: 3 } }]));
check(a.sessions && JSON.stringify(a.sessions.map(z => z.id)) === '["5@1"]', "#16a a project whose only session is unmanaged gets no ghost beside its white sprite", a.sessions && a.sessions.map(z => z.id));
a = ad(snap([sess("6@1", "constructor", "constructor")], [{ key: "constructor", name: "constructor", counts: { burning: 2 } }, { key: "toString", name: "toString", counts: { burning: 1 } }]));
check(a.S && a.S.s["6@1"] && a.S.s["6@1"].burning === 2, "#16b project key 'constructor' gets its lights", a.S && a.S.s["6@1"]);
a = ad(snap([sess("7@1", "toString", "toString")], [{ key: "toString", name: "toString", counts: { burning: 4 } }]));
check(a.S && a.S.s["7@1"] && a.S.s["7@1"].burning === 4, "#16b project key 'toString' gets its lights", a.S && a.S.s["7@1"]);
a = ad(snap([], [{ key: "toString", name: "toString", counts: { burning: 1 } }]));
check(a.sessions && a.sessions.some(z => z.id === "ghost:toString"), "#16b project key 'toString' with no session gets its ghost", a.sessions && a.sessions.map(z => z.id));
a = ad(Object.assign(snap([sess("8@1", "Lodestar", "lodestar")]), { projects: { lodestar: 1 } }));
check(!a.error && a.sessions && a.sessions.length === 1, "#16c a non-array snapshot.projects does not blank the stage", a.error || a.sessions);
a = ad(Object.assign(snap([sess("9@1", "Lodestar", "lodestar")]), { projects: [null, 7, { key: "lodestar", counts: { burning: 1 } }] }));
check(!a.error && a.S.s["9@1"].burning === 1, "#16c junk entries in projects are skipped", a.error || a.S.s["9@1"]);


// ---- package E: the adapter contract (CONTRACT R1 C2, C5), label hooks (H2), visible frame (R1-SPEC S4), demo (S9) ----
const fs = require("fs");
const FIX = JSON.parse(fs.readFileSync(path.join(ROOT, "tests/fixtures/augur_test_snapshot.json"), "utf8"));
const NOW = FIX.written_at;   // inside every stamp of the fixture
const adNow = (sn, q) => { const T = load(ROOT, q || "dpr=1"); try { return T.ctx.__stage.adaptState(sn, NOW); } catch (e) { return { error: e.message }; } };
const clone = o => JSON.parse(JSON.stringify(o));
// C2: hand truth = schema rule 4 (refuse an unknown major) + the required stamps: each refusal draws nothing at all
let base = adNow(FIX);
check(base.sessions && base.sessions.length === 3, "C2 control: the fixture as is gives its 3 sessions", base.sessions && base.sessions.length);
const refuse = { "schema missing": f => { delete f.schema; }, "schema wrong": f => { f.schema = "sprites.state"; },
  "version missing": f => { delete f.version; }, "major 2": f => { f.version = "2.0"; }, "valid_until missing": f => { delete f.valid_until; },
  "valid_until not a number": f => { f.valid_until = "soon"; }, "off": f => { f.off = true; } };
for (const [why, mut] of Object.entries(refuse)) { const f = clone(FIX); mut(f); const a = adNow(f);
  check(a.sessions && a.sessions.length === 0 && a.S === null, `C2 refused (${why}): the empty model`, a.error || (a.sessions && a.sessions.length)); }
{ const f = clone(FIX); f.version = "1.7"; const a = adNow(f); check(a.sessions && a.sessions.length === 3, "C2 a later minor (1.7) is accepted", a.sessions && a.sessions.length); }
{ const f = clone(FIX); delete f.sessions[0].load.valid_until; const a = adNow(f), d = a.S && a.S.s["88586@1793461778"];
  check(d && !("cpu" in d) && !("mem" in d) && d.state === "working", "C2 a block with no valid_until is absent (cpu, mem), its siblings kept", d); }
// C5: satellites = tasks.background (BURNING_CONCEPTS: satellites = background tasks; augur DESIGN s11: no load.procs fallback).
// Hand truth from the fixture: Lodestar background 1 (bg_shells 0 + subagents 1 + other 0), total 2, load.procs 5.
{ const a = adNow(FIX), d = a.S.s["88586@1793461778"]; check(d.procs === 1, "C5 Lodestar's satellites = tasks.background 1 (not total 2, not procs 5)", d.procs); }
{ const f = clone(FIX); delete f.sessions[0].tasks.background; const d = adNow(f).S.s["88586@1793461778"];
  check(!("procs" in d), "C5 tasks.background absent: satellites unset (no fallback to total or load.procs)", d.procs); }
{ const f = clone(FIX); f.sessions[0].tasks = { observed_at: NOW, valid_until: NOW + 10, unknown: "warming_up" }; const d = adNow(f).S.s["88586@1793461778"];
  check(!("procs" in d), "C5 tasks unknown for a tick: satellites unset, never load.procs 5", d.procs); }
// H2: drawLabels wraps each SpritesLabels.draw in ctx.__beginLabel / __endLabel (native label quad hook API)
{ const T = load(ROOT), c = T.ctx, seq = [], cx = c.__stage.canvas.getContext("2d");
  const B = cx.__beginLabel, E = cx.__endLabel;
  cx.__beginLabel = function () { seq.push("B"); return B ? B.apply(this, arguments) : false; };
  cx.__endLabel = function () { seq.push("E"); return E ? E.apply(this, arguments) : undefined; };
  c.SpritesStage.setSize(1440, 900); c.SpritesStage.setCast({ projects: {} }); c.SpritesStage.update(snap([sess("101@1", "Lodestar", "lodestar")])); T.advance(3000);
  const D = c.SpritesLabels.draw; c.SpritesLabels.draw = function () { seq.push("D"); return D.apply(this, arguments); };
  const h = c.__stage.allHits().find(z => z.id === "101@1"); if (h) { c.SpritesStage.setCursor({ x: h.x, y: h.y }); T.advance(1500); }
  const s = seq.join(""), bad = s.replace(/BDE/g, "");
  check(s.includes("BDE") && bad === "", "H2 every SpritesLabels.draw sits between __beginLabel and __endLabel", s.slice(0, 40)); }
// S4: the host's visible frame (NSScreen.visibleFrame in stage px) reaches every layer, and creatures stay inside it.
// Hand truth: a 1440x900 stage, menu bar 24 px, Dock on the right 60 px wide -> visible {0, 24, 1380, 876}; nothing may
// rest over the Dock, so every hit disc ends left of x 1380 (and below y 24).
{ const T = load(ROOT), c = T.ctx, got = [];
  c.SpritesStage.setSize(1440, 900); c.SpritesStage.setCast({ projects: {} });
  const many = []; for (let i = 0; i < 6; i++) many.push(sess((201 + i) + "@1", "P" + i, "p" + i));
  c.SpritesStage.update(snap(many)); T.advance(1500);
  const seen = new Set(), tap = V => { const o = V._onLive; V._onLive = m => { if (m.visible) seen.add(V); return o(m); }; };
  for (const k in c.__stage.layers) if (c.__stage.layers[k].V) tap(c.__stage.layers[k].V);
  const RC = c.VisitorsRuntime.create; c.VisitorsRuntime.create = function () { const V = RC.apply(this, arguments); tap(V); return V; };   // layers rebuilt by new margins
  if (typeof c.SpritesStage.setVisible === "function") c.SpritesStage.setVisible({ x: 0, y: 24, w: 1380, h: 876 });
  else check(false, "S4 SpritesStage.setVisible exists");
  T.advance(500);
  const Ls = Object.values(c.__stage.layers).filter(L => L.V), nL = Ls.length;
  check(nL > 0 && Ls.every(L => seen.has(L.V)), `S4 the visible frame reaches all ${nL} layers`, Ls.filter(L => !seen.has(L.V)).map(L => L.concept));
  let worst = -1e9, top = 1e9; for (let s = 0; s < 40; s++) { T.advance(500);
    for (const h of c.__stage.allHits()) { worst = Math.max(worst, h.x + h.r); top = Math.min(top, h.y - h.r); } }
  check(worst <= 1380 && top >= 24, `S4 Dock on the right: no hit disc over it in 20 s (max right edge ${worst.toFixed(0)} <= 1380, top ${top.toFixed(0)} >= 24)`); }
// S9: demo shows 6-8 sprites at every moment of its 240 s cycle (SHIP_PLAN Demo mode), counting white and ghosts.
{ const T = load(ROOT), c = T.ctx; let lo = 99, hi = 0;
  for (let u = 0; u < 240; u++) { const n = c.__stage.demoState().sessions.length; lo = Math.min(lo, n); hi = Math.max(hi, n); T.advance(1000); }
  check(lo >= 6 && hi <= 8, `S9 demo count stays within 6-8 over the cycle (min ${lo}, max ${hi})`); }
// R2S-2 / S6 text: the Settings text promises only what the runtime does. Hand truth (read prototype/visitors_runtime.js):
// edgeWhileTyping moves the target only; sleepWhenAway slows simulated time only; no alpha path reads activity, so neither
// may say "dim". Both copies of the text (behaviors.js, settings.js) must agree.
{ const g = {}; vm2(fs.readFileSync(path.join(ROOT, "app/behaviors.js"), "utf8"), g); const B = Object.fromEntries(g.window.SPRITES_BEHAVIORS.map(b => [b.key, b.desc]));
  const st = fs.readFileSync(path.join(ROOT, "app/settings.js"), "utf8");
  for (const k of ["edgeWhileTyping", "sleepWhenAway", "quietUnderStrain"]) {
    const m = new RegExp(k + ': \\[\"[^\"]*\", \"([^\"]*)\"\\]').exec(st), sd = m && m[1];
    check(sd === B[k], `text ${k}: settings.js and behaviors.js agree`, [sd, B[k]]);
    if (k !== "quietUnderStrain") check(!/dim/i.test(B[k] || ""), `text ${k}: promises no dimming (none is built)`, B[k]); } }
function vm2(src, g) { g.window = g; require("vm").runInNewContext(src, g); }

// R2M-7: launches.md rows count only when Status is active (hand truth: launches.md's Status column; waypoint treats
// blocked as an exclusion and anything but active as not live). Blank Status = active (waypoint's default).
{ const P = require(path.join(ROOT, "app/projects.js")), row = (name, status, machine) => ({ name, status, machine: machine || "" });
  const got = P.forMachine([row("A", "active"), row("B", "blocked"), row("C", "stale"), row("D", "retired"), row("E", ""), row("F", "Active")], "mt-1").map(r => r.name);
  check(JSON.stringify(got) === '["A","E","F"]', "R2M-7 forMachine keeps only active rows (and blank = active)", got); }

console.log(`${passes} pass, ${fails} fail`); process.exit(fails ? 1 : 0);
