#!/usr/bin/env node
/* Unknown is drawn (docs/OBSERVATION_CONTRACT.md "Drawing unknown"; foreign-work 03-merged C18: "_absent is computed and
 * never drawn"). app/stage.html in a node vm (stage_vm.js, fake clock, native canvas shim, nothing rendered).
 * Hand truth: a creature whose state, cpu or memory was filled calm carries the mark (V.unknownDrawn counts it, and the
 * three grey dots are recorded fills); a fully measured creature, a ghost and a creature whose only absent fields are
 * tasks/net carry none; the hover words name what is unknown and its age from the last fresh reading.
 * Run: node sprites/tests/node/test_unknown_drawn.js. Exit 0 = all pass. */
"use strict";
const path = require("path"), ROOT = path.resolve(__dirname, "../.."), load = require("./stage_vm.js");
let fails = 0, passes = 0;
const check = (ok, msg, got) => { ok ? passes++ : fails++; console.log((ok ? "PASS " : "FAIL ") + msg + (ok || got === undefined ? "" : "  got " + JSON.stringify(got))); };
const NOW = Date.now() / 1000;   // adaptState reads the wall clock; stamps are relative to it
const sig = (o, age) => Object.assign({ observed_at: NOW - (age || 1), valid_until: NOW + 60 }, o);
const full = (id, key, age) => ({ id, pid: parseInt(id), started_at: 1, project: key, project_key: key, managed: true,
  attention: sig({ state: "working" }, age), load: sig({ cpu_cores: 0.4, mem_gb: 0.3, procs: 2 }, age),
  tasks: sig({ background: 1 }, age), net: sig({ rx_mbps: 0.1, tx_mbps: 0.1 }, age) });
const snap = (sessions, extra) => Object.assign({ schema: "augur.snapshot", version: "1.2", written_at: NOW, valid_until: NOW + 60, sessions,
  projects: [], machine: { vpn: sig({ state: "up", on_site: true }) } }, extra || {});
const CAST = { projects: { alpha: { concept: "c5_fireflies", iv: 1, hex: "#55aaff" }, beta: { concept: "c5_fireflies", iv: 2, hex: "#ffaa55" } } };
function stage(sn, query) { const S = load(ROOT, query || "dpr=1&vpndebounce=0"), c = S.ctx; c.SpritesStage.setProjects([]); c.SpritesStage.setSize(1440, 900);
  c.SpritesStage.setCast(CAST); c.SpritesStage.update(sn); S.advance(3000); return S; }
const V = S => S.ctx.__stage.V("c5_fireflies");
const absentOf = (S, id) => { const u = V(S).unknownOf(id); return u ? u.absent.slice().sort() : []; };

// 1. fully measured: no mark
let S = stage(snap([full("100@1", "alpha")]));
check(absentOf(S, "100@1").length === 0 && V(S).unknownDrawn() === 0, "a fully measured creature carries no unknown mark", [absentOf(S, "100@1"), V(S).unknownDrawn()]);

// 2. load failed (read_failed): cpu and memory unknown -> mark drawn, hover words with the age since the last fresh reading
S = stage(snap([full("100@1", "alpha", 5)]));
S.advance(1000);
const failed = full("100@1", "alpha"); failed.load = sig({ unknown: "read_failed" }); S.ctx.SpritesStage.update(snap([failed])); S.advance(1500);
check(JSON.stringify(absentOf(S, "100@1")) === '["cpu","mem"]', "load read_failed: _absent = cpu, mem", absentOf(S, "100@1"));
check(V(S).unknownDrawn() === 1, "load read_failed: the unknown mark is drawn", V(S).unknownDrawn());
const w = S.ctx.__stage.unknownWords("100@1", ["cpu", "mem"], NOW + 120);
check(/^cpu, memory unknown 2m$/.test(w), "hover words name what is unknown and since when (last fresh load 5 s before NOW, read at NOW+120 -> 2m)", w);

// 3. hover: the label text carries the unknown words
{ const c = S.ctx, got = [], D = c.SpritesLabels.draw; c.SpritesLabels.draw = (x, o, ...r) => { got.push(o.short); return D(x, o, ...r); };
  const h = c.__stage.allHits().find(z => z.id === "100@1"); c.SpritesStage.setCursor({ x: h.x, y: h.y }); S.advance(2000);
  c.SpritesLabels.draw = D; const txt = [...new Set(got)];
  check(txt.length >= 1 && txt.every(t => /cpu, memory unknown \d+s$/.test(t)), "the hover label reads '<name> · cpu, memory unknown <age>'", txt); }

// 4. the whole snapshot past valid_until: every body field unknown -> "unknown", mark on every creature
S = stage(snap([full("100@1", "alpha"), full("200@2", "beta")], { valid_until: NOW - 1 }));
check(V(S).unknownDrawn() === 2, "a stale snapshot draws the unknown mark on every creature (stale must stop looking live)", V(S).unknownDrawn());
check(/^unknown( \d+[smhd])?$/.test(S.ctx.__stage.unknownWords("100@1", ["state", "cpu", "mem", "procs", "rx", "tx"])), "all body fields absent reads simply 'unknown'",
  S.ctx.__stage.unknownWords("100@1", ["state", "cpu", "mem", "procs", "rx", "tx"]));

// 5. only tasks/net absent: no mark and no hover words (satellites and pulses draw nothing when absent; the label
//    stays the plain name, as test_project_keys expects); with a body field also absent the words list them all
{ const x = full("100@1", "alpha"); x.net = sig({ unknown: "read_failed" }); delete x.tasks;
  S = stage(snap([x]));
  check(JSON.stringify(absentOf(S, "100@1")) === '["procs","rx","tx"]' && V(S).unknownDrawn() === 0, "net and tasks absent: flagged, no mark", [absentOf(S, "100@1"), V(S).unknownDrawn()]);
  const c = S.ctx, got = [], D = c.SpritesLabels.draw; c.SpritesLabels.draw = (q, o, ...r) => { got.push(o.short); return D(q, o, ...r); };
  const h = c.__stage.allHits().find(z => z.id === "100@1"); c.SpritesStage.setCursor({ x: h.x, y: h.y }); S.advance(2000); c.SpritesLabels.draw = D;
  check(got.length && got.every(s => !/unknown/.test(s)), "net and tasks absent only: the hover label is the plain name", [...new Set(got)]);
  check(S.ctx.__stage.unknownWords("100@1", ["cpu", "procs", "rx", "tx"]).startsWith("cpu, tasks, net unknown"), "with cpu also absent the words list all of them"); }

// 6. a ghost (burning, no session) is never marked unknown: its calm is the ghost's own meaning
S = stage(snap([], { projects: [{ key: "alpha", name: "alpha", kind: "managed", sessions: 0, counts: sig({ burning: 2 }) }] }));
check(S.ctx.__stage.model.sessions.some(x => x.ghost) && V(S).unknownDrawn() === 0, "a ghost carries no unknown mark");

// 7. the mark is visible ink: three neutral grey dots recorded per marked creature, and no draw errors
{ const x = full("100@1", "alpha"); x.load = sig({ unknown: "timeout" }); delete x.attention;
  const S2 = load(ROOT, "dpr=1&vpndebounce=0"), c = S2.ctx, P = c.CanvasRenderingContext2D.prototype, f = P.fill; let grey = 0;
  P.fill = function () { if (this.fillStyle === "rgba(206,212,222,1)" || this.fillStyle === "#ced4de") grey++; return f.apply(this, arguments); };
  c.SpritesStage.setProjects([]); c.SpritesStage.setSize(1440, 900); c.SpritesStage.setCast(CAST); c.SpritesStage.update(snap([x])); S2.advance(3000);
  grey = 0; S2.advance(1000 / 24 * 3);
  check(grey >= 3 && grey % 3 === 0, "the mark draws three grey dots per frame", grey);
  check(!(c.__errors || []).length && !Object.keys(c.__nativeStats.unsupported).some(k => /arc|ellipse/.test(k)), "draws without errors or unsupported calls", [c.__errors, c.__nativeStats.unsupported]); }

console.log(passes + " passed, " + fails + " failed"); process.exit(fails ? 1 : 0);
