#!/usr/bin/env node
/* Hardening oracle for app/shared.js: one check per input-validation defect an adversarial probe found AFTER the 28/28
 * run (ticket MANDRAKEWORKFLOWS_HARDEN_SHARED_JS_ORACLE_PASSED_ANYWAY). The blind spot of test_shared.js was uniform: it
 * never passed a malformed value where an OBJECT is expected. Every check here does exactly that.
 *
 * 🔴 READ-ONLY during a local-model run (SHA-256 guarded). A pass is: exit 0 AND every check printed PASS AND zero FAIL.
 * Watched failing on 2932ece (the gemma module) before any fix. Run: node sprites/tests/node/test_shared_hardening.js
 */
"use strict";
const path = require("path");
const S = require(path.join(path.resolve(__dirname, "../.."), "app/shared.js"));

let fails = 0, passes = 0;
const check = (ok, msg, got) => {
  ok ? passes++ : fails++;
  console.log((ok ? "PASS " : "FAIL ") + msg + (ok || got === undefined ? "" : "  got " + JSON.stringify(got)));
};
const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const safe = f => { try { return { v: f() }; } catch (e) { return { err: String(e && e.message || e) }; } };
const localCast = () => ({ projects: {
  "orchard-mandrake": { concept: "c6_night", hex: "#CB50F0", iv: 0, short: "Orchard", visibility: "show" },
  "lodestar": { concept: "c1_choir", hex: "#FFFB00", iv: 2 } } });
const localBeh = () => ({ density: 100, drift: "off", enabled: true });
const shared = () => ({ schema: "sprites.shared", version: 1,
  projects: { "orchard-mandrake": { concept: "c3_sigils", iv: 4, hex: "#40C888" }, "granite": { concept: "c5_fireflies", iv: 1, hex: "#22DDAA" } },
  behaviors: { density: 55, drift: "slow" } });

// ---- defect 1: mergeBehaviors on an absent local object must not throw; nothing local is known, so nothing applies
for (const bad of [undefined, null, "oops", 7]) {
  const r = safe(() => S.mergeBehaviors(bad, shared(), true));
  check(!r.err && eq(r.v, {}), `mergeBehaviors(${JSON.stringify(bad) || "undefined"}, shared, true) returns {} without throwing`, r);
}
{
  const r = safe(() => S.mergeBehaviors(localBeh(), { behaviors: "oops" }, true));
  check(!r.err && eq(r.v, localBeh()), "mergeBehaviors ignores a shared behaviors value that is not an object", r);
}

// ---- defect 2: setProject refuses a key that is not a STRING matching the key pattern (RegExp.test stringifies)
for (const bad of [undefined, null, 42, ["granite"], { toString: () => "granite" }]) {
  const sh = shared();
  const r = safe(() => S.setProject(sh, bad, { hex: "#123456" }));
  const keys = r.v && r.v.projects ? Object.keys(r.v.projects).sort() : null;
  check(!r.err && eq(keys, ["orchard-mandrake", "granite"]) && eq(r.v.projects.granite, shared().projects.granite),
        `setProject refuses a non-string key (${Object.prototype.toString.call(bad)}) and adds or changes nothing`, r.err || keys);
}

// ---- defect 3: no shared references: the result is a fresh object on EVERY path, so mutating it never edits the input
{
  const lc = localCast(), before = JSON.stringify(lc);
  const got = S.mergeCast(lc, shared(), false);
  check(got !== lc && got.projects !== lc.projects, "mergeCast(no Waypoint) returns a new object, not the caller's own");
  got.projects["orchard-mandrake"].hex = "#000000"; got.projects.extra = {};
  check(JSON.stringify(lc) === before, "mutating mergeCast's no-Waypoint result leaves the local cast unchanged", lc);
}
{
  const lc = localCast(), before = JSON.stringify(lc);
  const got = S.mergeCast(lc, null, true);
  got.projects.lodestar.iv = 99;
  check(JSON.stringify(lc) === before, "mutating mergeCast's no-shared-file result leaves the local cast unchanged", lc);
}
{
  const lb = localBeh(), before = JSON.stringify(lb);
  const got = S.mergeBehaviors(lb, shared(), false);
  check(got !== lb && eq(got, lb), "mergeBehaviors(no Waypoint) returns an equal NEW object, not the caller's own");
  got.density = 1;
  check(JSON.stringify(lb) === before, "mutating mergeBehaviors' no-Waypoint result leaves the local behaviours unchanged", lb);
}
{
  const sh = shared(), before = JSON.stringify(sh);
  const got = S.setProject(sh, "Not A Key", { hex: "#123456" });
  got.projects.granite.iv = 9; got.behaviors.density = 1;
  check(JSON.stringify(sh) === before, "mutating setProject's refused-key result leaves the shared input unchanged", sh);
}

// ---- defect 4: a malformed `projects` (string, array, number) is treated as empty, never spread into fake projects
for (const bad of ["oops", ["a", "b"], 5]) {
  const tag = JSON.stringify(bad);
  const r = safe(() => S.mergeCast({ projects: bad }, shared(), true));
  const keys = r.v && r.v.projects ? Object.keys(r.v.projects).sort() : null;
  check(!r.err && eq(keys, ["orchard-mandrake", "granite"]), `mergeCast({projects:${tag}}, shared, true) holds only the shared projects`, r.err || keys);
  const r2 = safe(() => S.mergeCast({ projects: bad }, shared(), false));
  check(!r2.err && eq(r2.v, { projects: {} }), `mergeCast({projects:${tag}}, shared, false) normalises to {projects:{}}`, r2.err || r2.v);
}
{
  const r = safe(() => S.mergeCast(localCast(), { projects: ["x"] }, true));
  check(!r.err && eq(r.v, localCast()), "mergeCast ignores a shared projects value that is an array", r.err || r.v);
  const r2 = safe(() => S.setProject({ schema: "sprites.shared", version: 1, projects: ["x"] }, "granite", { iv: 2 }));
  check(!r2.err && eq(r2.v && r2.v.projects, { granite: { iv: 2 } }), "setProject replaces an array projects value with a real map", r2.err || (r2.v && r2.v.projects));
}

console.log(`${passes} passed, ${fails} failed`);
process.exit(fails ? 1 : 0);
