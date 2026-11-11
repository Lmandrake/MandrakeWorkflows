#!/usr/bin/env node
/* Acceptance test for app/shared.js: sharing Sprite appearance across Waypoint-managed machines.
 * Spec: sprites/design/specs/2026-11-09-shared-appearance/01-spec.md
 * Ticket: MANDRAKEWORKFLOWS_SHARE_SPRITE_LOOKS_GEMMA_WRITES_IT
 *
 * 🔴 READ-ONLY. This file is the acceptance oracle for a token-free generation experiment and is
 * SHA-256 guarded during the run. Do not edit it to make an implementation pass.
 *
 * A pass is: exit 0 AND every check printed PASS AND zero FAIL lines. Exit status alone is not a
 * pass -- a module that calls process.exit(0) satisfies a naive rc==0 rule with zero assertions run.
 *
 * Run: node sprites/tests/node/test_shared.js
 */
"use strict";
const path = require("path");
const ROOT = path.resolve(__dirname, "../..");
const S = require(path.join(ROOT, "app/shared.js"));

let fails = 0, passes = 0;
const check = (ok, msg, got) => {
  ok ? passes++ : fails++;
  console.log((ok ? "PASS " : "FAIL ") + msg + (ok || got === undefined ? "" : "  got " + JSON.stringify(got)));
};
const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const clone = o => JSON.parse(JSON.stringify(o));

// ---------------------------------------------------------------- fixtures
const localCast = () => ({
  projects: {
    "orchard-mandrake": { concept: "c6_night", hex: "#CB50F0", iv: 0, short: "Orchard", visibility: "show" },
    "lodestar": { concept: "c1_choir", hex: "#FFFB00", iv: 2 },
  },
});
const localBeh = () => ({ density: 100, temperature: 27.5, drift: "off", enabled: true, stirring: 0.7 });
const shared = () => ({
  schema: "sprites.shared",
  version: 1,
  projects: {
    "orchard-mandrake": { concept: "c3_sigils", iv: 4, hex: "#40C888" },
    "granite": { concept: "c5_fireflies", iv: 1, hex: "#22DDAA" },
  },
  behaviors: { density: 55, drift: "slow", stirring: 0.25 },
});

// ---------------------------------------------------------------- the module's surface
check(S && typeof S.mergeCast === "function" && typeof S.mergeBehaviors === "function" &&
      typeof S.setProject === "function",
      "app/shared.js exports mergeCast, mergeBehaviors and setProject");
if (!S || typeof S.mergeCast !== "function") { console.log("FAIL module unusable; stopping"); process.exit(1); }

// ---------------------------------------------------------------- mergeCast: the no-Waypoint guarantee
{
  const got = S.mergeCast(localCast(), shared(), false);
  check(eq(got, localCast()), "mergeCast with hasWaypoint false returns the local cast untouched", got);
}
{
  const got = S.mergeCast(localCast(), null, true);
  check(eq(got, localCast()), "mergeCast with no shared file returns the local cast untouched", got);
}
{
  const got = S.mergeCast(localCast(), "not an object", true);
  check(eq(got, localCast()), "mergeCast ignores a malformed shared value", got);
}
{
  const got = S.mergeCast(undefined, shared(), false);
  check(got && typeof got === "object" && got.projects && typeof got.projects === "object" &&
        Object.keys(got.projects).length === 0,
        "mergeCast normalises an absent local cast to {projects:{}} when Waypoint is absent", got);
}

// ---------------------------------------------------------------- mergeCast: the overlay
{
  const got = S.mergeCast(localCast(), shared(), true);
  const a = got.projects["orchard-mandrake"];
  check(a && a.concept === "c3_sigils" && a.iv === 4 && a.hex === "#40C888",
        "mergeCast overlays shared concept, iv and hex onto an existing project", a);
  check(a && a.short === "Orchard" && a.visibility === "show",
        "mergeCast preserves the local short and visibility, which are never shared", a);
  check(got.projects["granite"] && got.projects["granite"].concept === "c5_fireflies",
        "mergeCast creates an entry for a shared project with no local entry", got.projects["granite"]);
  check(eq(got.projects["lodestar"], localCast().projects["lodestar"]),
        "mergeCast leaves a local-only project untouched", got.projects["lodestar"]);
}

// ---------------------------------------------------------------- mergeCast: no mutation
{
  const lc = localCast(), sh = shared(), lcBefore = clone(lc), shBefore = clone(sh);
  S.mergeCast(lc, sh, true);
  check(eq(lc, lcBefore) && eq(sh, shBefore), "mergeCast mutates neither of its inputs");
}

// ---------------------------------------------------------------- mergeCast: per-field validation
{
  const sh = shared();
  sh.projects["orchard-mandrake"] = { concept: "", iv: -3, hex: "lilac" };
  const got = S.mergeCast(localCast(), sh, true).projects["orchard-mandrake"];
  check(got && got.concept === "c6_night" && got.iv === 0 && got.hex === "#CB50F0",
        "mergeCast drops an empty concept, a negative iv and a non-hex colour, keeping the local values", got);
}
{
  const sh = shared();
  sh.projects["orchard-mandrake"] = { concept: "c4_kaleido", iv: 1.5, hex: "#ZZZZZZ" };
  const got = S.mergeCast(localCast(), sh, true).projects["orchard-mandrake"];
  check(got && got.concept === "c4_kaleido" && got.iv === 0 && got.hex === "#CB50F0",
        "mergeCast validates per field, not per file: a good concept applies beside a bad iv and hex", got);
}
{
  const sh = shared();
  sh.projects["orchard-mandrake"] = { hex: "#abcdef" };
  const got = S.mergeCast(localCast(), sh, true).projects["orchard-mandrake"];
  check(got && got.hex === "#ABCDEF", "mergeCast normalises a shared hex to uppercase", got);
}

// ---------------------------------------------------------------- mergeBehaviors
{
  const got = S.mergeBehaviors(localBeh(), shared(), false);
  check(eq(got, localBeh()), "mergeBehaviors with hasWaypoint false returns the local behaviours untouched", got);
}
{
  const got = S.mergeBehaviors(localBeh(), shared(), true);
  check(got.density === 55 && got.drift === "slow" && got.stirring === 0.25,
        "mergeBehaviors overlays shared slider values of matching type", got);
  check(got.temperature === 27.5 && got.enabled === true,
        "mergeBehaviors leaves local keys the shared file does not mention", got);
}
{
  const sh = shared();
  sh.behaviors = { density: "lots", enabled: 1, unknownSlider: 7 };
  const got = S.mergeBehaviors(localBeh(), sh, true);
  check(got.density === 100 && got.enabled === true,
        "mergeBehaviors refuses a type mismatch: a string over a number and a number over a boolean", got);
  check(!("unknownSlider" in got),
        "mergeBehaviors ignores a shared key the local behaviours do not know", Object.keys(got));
}
{
  const lb = localBeh(), sh = shared(), lbBefore = clone(lb), shBefore = clone(sh);
  S.mergeBehaviors(lb, sh, true);
  check(eq(lb, lbBefore) && eq(sh, shBefore), "mergeBehaviors mutates neither of its inputs");
}

// ---------------------------------------------------------------- setProject
{
  const sh = shared(), before = clone(sh);
  const got = S.setProject(sh, "lodestar", { concept: "c2_siphon", iv: 3, hex: "#ffd700" });
  check(got.projects["lodestar"] && got.projects["lodestar"].concept === "c2_siphon" &&
        got.projects["lodestar"].iv === 3 && got.projects["lodestar"].hex === "#EECC22",
        "setProject writes concept, iv and an uppercased hex under the key", got.projects["lodestar"]);
  check(got.projects["granite"] && got.projects["granite"].concept === "c5_fireflies",
        "setProject preserves the other projects", got.projects["granite"]);
  check(eq(sh, before), "setProject does not mutate its input");
  check(got.schema === "sprites.shared" && got.version === 1,
        "setProject stamps the schema and version", { schema: got.schema, version: got.version });
}
{
  const got = S.setProject(null, "atlas", { concept: "c1_choir", iv: 0, hex: "#B5FF00" });
  check(got && got.schema === "sprites.shared" && got.version === 1 &&
        got.projects && got.projects["atlas"] && got.projects["atlas"].concept === "c1_choir",
        "setProject builds the envelope when the shared file does not exist yet", got);
}
{
  const sh = shared();
  const got = S.setProject(sh, "Not A Key!", { concept: "c1_choir" });
  check(!Object.keys(got.projects).some(k => k.includes(" ") || k.includes("!")),
        "setProject refuses a key that is not a plausible project key", Object.keys(got.projects));
}
{
  const sh = shared();
  const got = S.setProject(sh, "ember28", { concept: "c6_night", iv: "two", hex: "#00B5B5" });
  const e = got.projects["ember28"];
  check(e && e.concept === "c6_night" && e.hex === "#00B5B5" && !("iv" in e),
        "setProject drops an invalid field and still writes the valid ones beside it", e);
}
{
  const sh = shared();
  const got = S.setProject(sh, "lodestar", { hex: "#123456" });
  check(got.behaviors && got.behaviors.density === 55,
        "setProject leaves the shared behaviours alone", got.behaviors);
}

// ---------------------------------------------------------------- round trip
{
  const written = S.setProject(null, "orchard-mandrake", { concept: "c3_sigils", iv: 4, hex: "#40C888" });
  const merged = S.mergeCast(localCast(), written, true).projects["orchard-mandrake"];
  check(merged.concept === "c3_sigils" && merged.iv === 4 && merged.hex === "#40C888" && merged.short === "Orchard",
        "a value written by setProject comes back out of mergeCast, local-only fields intact", merged);
}

console.log(`${passes} passed, ${fails} failed`);
process.exit(fails ? 1 : 0);
