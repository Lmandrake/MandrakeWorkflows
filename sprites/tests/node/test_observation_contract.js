#!/usr/bin/env node
/* The observation contract (docs/OBSERVATION_CONTRACT.md; build plan step 1 of
 * docs/design/2026-11-06-foreign-work/03-merged.md), fixture-tested against app/observe.js. No collector, no ssh, no
 * browser: every fetch outcome is handed in as data. Truth is hand-derived from the contract's rules, never read from
 * observe.js. Acceptance cases 1, 2, 3, 5 (logic level) and 6 are named in the output.
 * Run: node sprites/tests/node/test_observation_contract.js. Exit 0 = all pass. */
"use strict";
const fs = require("fs"), path = require("path");
const ROOT = path.resolve(__dirname, "../.."), O = require(path.join(ROOT, "app/observe.js"));
const FIX = path.join(ROOT, "tests/fixtures/observation");
let fails = 0, passes = 0;
const check = (ok, msg, got) => { ok ? passes++ : fails++; console.log((ok ? "PASS " : "FAIL ") + msg + (ok || got === undefined ? "" : "  got " + JSON.stringify(got))); };
const load = f => JSON.parse(fs.readFileSync(path.join(FIX, f), "utf8"));
const DESK = "mt-BBBBBB", LAP = "mt-AAAAAA";
const T = load("desktop_1_3.json").written_at;   // the fixtures' source clock

// A later snapshot of the same producer: every stamp moved forward by dt, seq + n.
function later(s, dt, n) { s = JSON.parse(JSON.stringify(s)); s.written_at += dt; s.valid_until += dt; s.seq += n || 1;
  const sh = o => { if (o && typeof o === "object") { if (typeof o.observed_at === "number") o.observed_at += dt; if (typeof o.valid_until === "number") o.valid_until += dt;
    for (const k in o) if (k !== "producer" && o[k] && typeof o[k] === "object") sh(o[k]); } };
  for (const k in s) if (k !== "producer") sh(s[k]); return s; }
const ok = (snap, mono, srcNow) => ({ mono, outcome: "ok", snapshot: snap, source_now: srcNow ?? snap.written_at });
const byId = (st, mono) => Object.fromEntries(O.view(st, mono).map(o => [o.id, o]));
const fresh = () => O.create({ viewer: DESK });

// ---- baseline: a complete 1.3 Desktop snapshot draws every object live; undeclared kinds stay "unknown" ----
const D0 = load("desktop_1_3.json");
let st = fresh(); O.deliver(st, DESK, ok(D0, 100));
let v = byId(st, 100);
check(Object.keys(v).length === 6, "baseline: 1 Claude session + 5 foreign objects", Object.keys(v));
check(Object.values(v).every(o => o.status === "live"), "baseline: all live", Object.values(v).map(o => o.status));
check(v["mux:tmux:default:%3:4242@1794159000"].kind === "unknown" && v["mux:tmux:default:%3:4242@1794159000"].declared === false,
  "an undeclared mux pane is kind unknown (ruling 8), never defaulted to the nearest kind");
{ const s = later(D0, 0, 0); s.foreign[0].kind = "gpu_render"; const t = fresh(); O.deliver(t, DESK, ok(s, 1));
  check(byId(t, 1)["run:granite-e7s4-01"].kind === "unknown", "a kind this version does not know reads unknown"); }
{ const s = later(D0, 0, 0); s.foreign[1].label = "secret-session-name"; s.foreign[1].attach = "deskrun:x"; const t = fresh(); O.deliver(t, DESK, ok(s, 1));
  const o = byId(t, 1)["mux:tmux:default:%3:4242@1794159000"];
  check(o.label === null && o.attach === null, "an undeclared item carries no label and no attach target (correction 4)", [o.label, o.attach]); }

// ---- source-relative age, advanced by the receiver's monotonic clock ----
check(Math.abs(v["run:granite-e7s4-01"].age - 30) < 1e-9, "age at fetch = source_now - observed_at (30 s)", v["run:granite-e7s4-01"].age);
check(Math.abs(byId(st, 145)["run:granite-e7s4-01"].age - 75) < 1e-9, "45 s of receiver mono later: 75 s", byId(st, 145)["run:granite-e7s4-01"].age);
check(byId(st, 145)["mux:tmux:default:%3:4242@1794159000"].status === "unknown" && byId(st, 145)["mux:tmux:default:%3:4242@1794159000"].why === "stale",
  "no new fetch past valid_for + grace: unknown (stale), still drawn, never removed");
check(O.ageWords(75) === "1m" && O.ageWords(12) === "12s" && O.ageWords(7300) === "2h", "age in words");

// ---- clock skew: the receiver never reads its own wall clock against the source's ----
{ const sk = 3600 * 5 + 17; const S = later(D0, sk, 0);   // the source's clock is 5 h ahead; every stamp and source_now move together
  const a = fresh(), b = fresh(); O.deliver(a, DESK, ok(D0, 100)); O.deliver(b, DESK, ok(S, 100));
  const va = O.view(a, 140).map(o => [o.id, o.status, +o.age.toFixed(6)]), vb = O.view(b, 140).map(o => [o.id, o.status, +o.age.toFixed(6)]);
  check(JSON.stringify(va) === JSON.stringify(vb), "clock skew of 5 h changes no status and no age", [va[0], vb[0]]); }

// ---- acceptance 1: mux failed, then mux complete with no jobs: only the second removes ----
{ const t = fresh(); O.deliver(t, DESK, ok(D0, 100)); const MUX = "mux:tmux:default:%3:4242@1794159000";
  const f1 = later(D0, 5); f1.coverage.mux = { observed_at: T + 3, valid_until: T + 15.5, unknown: "read_failed" }; f1.foreign = f1.foreign.filter(x => x.collector !== "mux");
  O.deliver(t, DESK, ok(f1, 105)); let w = byId(t, 105);
  check(!!w[MUX] && w[MUX].status === "unknown" && w[MUX].why === "collector:read_failed", "acceptance 1a: mux failed + job missing -> kept, unknown (collector:read_failed)", w[MUX]);
  check(w["run:granite-e7s4-01"].status === "live", "acceptance 1a: other collectors' objects unaffected");
  const f2 = later(D0, 10); f2.foreign = f2.foreign.filter(x => x.collector !== "mux");
  O.deliver(t, DESK, ok(f2, 110)); w = byId(t, 110);
  check(!w[MUX], "acceptance 1b: mux complete + job missing -> removed", Object.keys(w));
  const dep = t.departed.find(d => d.id === MUX);
  check(dep && dep.how === "absence_observed" && dep.terminal === null, "absence is recorded as absence observed, never as an exit status (correction 2)", dep);
  check(t.departed.length === 1, "acceptance 1: exactly one departure", t.departed.length); }

// ---- a transport success is not an observation: a mux stamp no newer than what we hold says nothing ----
{ const t = fresh(); O.deliver(t, DESK, ok(D0, 100)); const f = later(D0, 0, 1); f.foreign = f.foreign.filter(x => x.collector !== "mux");
  O.deliver(t, DESK, ok(f, 101));
  check(!!byId(t, 101)["mux:tmux:default:%3:4242@1794159000"], "a complete mux stamp NOT newer than the object's observation removes nothing"); }

// ---- acceptance 2: an old 1.2 producer with no foreign[] ----
{ const t = fresh(); O.deliver(t, DESK, ok(D0, 100));
  const old = load("laptop_1_2.json"); const asDesk = JSON.parse(JSON.stringify(old)); asDesk.producer.machine = DESK; asDesk.producer.pid = 9; asDesk.producer.started_at = T - 10;
  asDesk.sessions = D0.sessions; asDesk.sessions_at = { observed_at: T + 18, valid_until: T + 30.5 }; asDesk.written_at = T + 20; asDesk.valid_until = T + 30; asDesk.seq = 1;
  O.deliver(t, DESK, ok(asDesk, 120)); const w = byId(t, 120);
  check(Object.keys(w).length === 6 && t.departed.length === 0, "acceptance 2: a 1.2 snapshot (no foreign[], no coverage) removes no foreign object", Object.keys(w));
  check(["run:granite-e7s4-01", "ctr:abc123", "model:omlx:glm"].every(id => w[id].status === "unknown" && w[id].why === "collector:not_published"),
    "acceptance 2: each is unknown, why collector:not_published", ["run:granite-e7s4-01", "ctr:abc123"].map(id => w[id].why)); }
{ const t = O.create({ viewer: LAP }); const L = load("laptop_1_2.json"); O.deliver(t, LAP, ok(L, 50));
  check(O.view(t, 50).length === 1 && O.view(t, 50)[0].kind === "claude_session", "a 1.2 producer still yields its Claude sessions"); }

// ---- partial Docker failure: one socket failed, the other complete ----
{ const t = fresh(); O.deliver(t, DESK, ok(D0, 100)); const f = later(D0, 30);
  f.coverage.containers.scopes = { "colima:default": "complete", "colima:granite": "failed" }; f.foreign = f.foreign.filter(x => x.collector !== "containers");
  O.deliver(t, DESK, ok(f, 130)); const w = byId(t, 130);
  check(!w["ctr:def456"], "partial Docker: a container missing from the COMPLETE socket is removed");
  check(!!w["ctr:abc123"] && w["ctr:abc123"].status === "unknown" && w["ctr:abc123"].why === "scope:failed", "partial Docker: a container missing from the FAILED socket is kept, unknown", w["ctr:abc123"]); }
{ const t = fresh(); O.deliver(t, DESK, ok(D0, 100)); const f = later(D0, 30);
  f.coverage.containers.scopes = { "colima:default": "complete" }; f.foreign = f.foreign.filter(x => x.collector !== "containers");
  O.deliver(t, DESK, ok(f, 130));
  check(!!byId(t, 130)["ctr:abc123"], "a socket the collector did not report at all is not covered: kept"); }
{ const t = fresh(); O.deliver(t, DESK, ok(D0, 100)); const f = later(D0, 30);
  f.coverage.containers.scopes = { "colima:default": "partial", "colima:granite": "complete" }; f.foreign = f.foreign.filter(x => x.collector !== "containers");
  O.deliver(t, DESK, ok(f, 130));
  check(!!byId(t, 130)["ctr:def456"] && !byId(t, 130)["ctr:abc123"], "partial is not complete: kept; complete socket: removed"); }

// ---- acceptance 3: reused tmux name, recycled pid, replayed completion; sequence and incarnation ----
{ const t = fresh(); O.deliver(t, DESK, ok(D0, 100));
  // a second execution under the SAME session name gets a fresh run id; the pane pid is recycled with a new start time
  const f = later(D0, 10); f.foreign[0] = Object.assign({}, f.foreign[0], { id: "run:granite-e7s4-02", started_at: T + 9 });
  f.foreign[1] = Object.assign({}, f.foreign[1], { id: "mux:tmux:default:%3:4242@1794160008", started_at: T + 8 });
  f.coverage.declared.scopes = { "*": "partial" };   // the old run's ending is not observed yet
  O.deliver(t, DESK, ok(f, 110)); const w = byId(t, 110);
  check(!!w["run:granite-e7s4-01"] && !!w["run:granite-e7s4-02"], "acceptance 3: a reused session name is a second run, not a merge", Object.keys(w).filter(k => k.startsWith("run:")));
  check(!w["mux:tmux:default:%3:4242@1794159000"] && !!w["mux:tmux:default:%3:4242@1794160008"], "acceptance 3: a recycled pid with a new start time is a new pane (old one observed absent)");
  check(w["run:granite-e7s4-01"].status === "unknown", "acceptance 3: the first run does not end early (unknown, not ended)", w["run:granite-e7s4-01"].status); }
{ const t = fresh(); O.deliver(t, DESK, ok(D0, 100));
  const done = later(D0, 20); done.foreign[0].terminal = { outcome: "exited", exit_code: 0, ended_at: T + 15 };
  const replay = later(D0, 5); replay.seq = done.seq + 1; replay.foreign[0].terminal = { outcome: "failed", exit_code: 1, ended_at: T + 1 };
  O.deliver(t, DESK, ok(done, 120));
  let r = O.deliver(t, DESK, ok(later(done, -10, -5), 121));
  check(r.ignored === "replay", "sequence: a lower seq from the same incarnation is ignored", r);
  O.deliver(t, DESK, ok(replay, 122)); const o = byId(t, 122)["run:granite-e7s4-01"];
  check(o.status === "ended" && o.terminal.outcome === "exited", "acceptance 3: a replayed (older) completion does not overwrite the newer one", o.terminal);
  const after = later(done, 10); delete after.foreign[0].terminal; O.deliver(t, DESK, ok(after, 130));
  check(byId(t, 130)["run:granite-e7s4-01"].status === "ended", "terminal records are final: a later non-terminal record does not revive it");
  const gone = later(done, 40); gone.foreign = gone.foreign.slice(1); O.deliver(t, DESK, ok(gone, 160));
  const dep = t.departed.find(d => d.id === "run:granite-e7s4-01");
  check(dep && dep.how === "ended_then_absent" && dep.terminal.exit_code === 0, "an ended run that later disappears keeps its terminal record", dep); }
{ const t = fresh(); O.deliver(t, DESK, ok(D0, 100));
  const oldInc = later(D0, 30); oldInc.producer.started_at = D0.producer.started_at - 500; oldInc.producer.pid = 1; oldInc.foreign = [];
  const r = O.deliver(t, DESK, ok(oldInc, 130));
  check(r.ignored === "replay_old_incarnation" && O.view(t, 130).length === 6, "incarnation: a snapshot from an OLDER producer start is a replay, ignored", r); }

// ---- restart: a new incarnation (seq drops) is accepted; its warming-up collectors remove nothing ----
{ const t = fresh(); O.deliver(t, DESK, ok(D0, 100));
  const R = later(D0, 60); R.producer.pid = 7777; R.producer.started_at = T + 55; R.seq = 3; R.foreign = [];
  for (const k in R.coverage) R.coverage[k] = { observed_at: T + 58, valid_until: T + 70, unknown: "warming_up" };
  R.sessions = []; R.sessions_at = { observed_at: T + 58, valid_until: T + 70, unknown: "warming_up" };
  const r = O.deliver(t, DESK, ok(R, 160)); const w = O.view(t, 160);
  check(r.link === "ok" && w.length === 6 && t.departed.length === 0, "restart: seq drop is a new incarnation, accepted; warming_up removes nothing", [r, w.length]);
  check(w.every(o => o.status === "unknown"), "restart: everything is unknown until each collector completes", w.map(o => o.why));
  const R2 = later(R, 10); for (const k in R2.coverage) R2.coverage[k] = { observed_at: T + 68, valid_until: T + 200, scopes: k === "containers" ? { "colima:default": "complete", "colima:granite": "complete" } : k === "mux" ? { "tmux:default": "complete" } : k === "models" ? { omlx: "complete" } : { "*": "complete" } };
  R2.sessions_at = { observed_at: T + 68, valid_until: T + 80 };
  O.deliver(t, DESK, ok(R2, 170));
  check(O.view(t, 170).length === 0 && t.departed.every(d => d.across_restart === true), "after the restart a complete observation removes, marked across_restart", t.departed.length); }

// ---- acceptance 5 (logic level, no real ssh): auth failure, no rapid retry, no removals ----
{ const t = fresh(); O.deliver(t, DESK, ok(D0, 100));
  check(O.shouldAttempt(t, DESK, 115) === true, "after an ok fetch the next attempt is due at pull_s");
  const r = O.deliver(t, DESK, { mono: 115, outcome: "auth", reason: "publickey refused" });
  const w = O.view(t, 115);
  check(r.link === "auth" && w.length === 6 && w.every(o => o.status === "unknown" && o.why === "auth:publickey refused"), "acceptance 5: auth failed -> every object unknown (auth), none removed", w.map(o => o.why));
  check(!O.shouldAttempt(t, DESK, 116) && !O.shouldAttempt(t, DESK, 400) && O.shouldAttempt(t, DESK, 415), "acceptance 5: no retry for 300 s after an auth failure");
  O.deliver(t, DESK, { mono: 415, outcome: "auth", reason: "publickey refused" });
  check(!O.shouldAttempt(t, DESK, 1000) && O.shouldAttempt(t, DESK, 1015), "acceptance 5: the second auth failure backs off 600 s");
  check(t.departed.length === 0, "acceptance 5: no removals across auth failures"); }
{ const t = fresh(); O.deliver(t, DESK, ok(D0, 100)); O.deliver(t, DESK, { mono: 115, outcome: "connection", reason: "timeout" });
  check(O.view(t, 115).every(o => o.status === "unknown" && o.why === "connection:timeout"), "connection failure: unknown, none removed");
  check(!O.shouldAttempt(t, DESK, 129) && O.shouldAttempt(t, DESK, 130), "connection failure retries at the pull cadence, not faster");
  for (let i = 0; i < 10; i++) O.deliver(t, DESK, { mono: 200 + i, outcome: "connection", reason: "timeout" });
  check(t.host[DESK].next - 209 <= 120, "connection backoff is bounded (<= 120 s)", t.host[DESK].next - 209); }
{ const t = fresh(); O.deliver(t, DESK, ok(D0, 100));
  const stale = O.deliver(t, DESK, ok(D0, 130, T + 60));
  check(stale.link === "producer" && stale.reason === "stale_file" && O.view(t, 130).every(o => o.status === "unknown"), "reached it but its file is past valid_until: producer failure, unknown", stale);
  const wrong = later(D0, 30); wrong.producer.machine = LAP;
  check(O.deliver(t, DESK, ok(wrong, 140)).reason === "wrong_machine", "a snapshot naming another machine is refused");
  check(O.deliver(t, DESK, ok({ schema: "augur.snapshot", version: "2.0" }, 150)).reason === "unknown_schema", "a major version this reader does not know is refused");
  check(t.departed.length === 0, "no refusal removes anything"); }

// ---- disappearance: only a complete, newer observation removes; Claude sessions follow sessions_at ----
{ const t = fresh(); O.deliver(t, DESK, ok(D0, 100)); const SID = "4100@1794150000";
  const u = later(D0, 10); u.sessions = []; u.sessions_at = { observed_at: T + 8, valid_until: T + 20, unknown: "read_failed" };
  O.deliver(t, DESK, ok(u, 110)); check(!!byId(t, 110)[SID] && byId(t, 110)[SID].status === "unknown", "sessions [] with sessions_at unknown: the session is kept, unknown (Augur C3)");
  const g = later(D0, 20); g.sessions = []; O.deliver(t, DESK, ok(g, 120));
  check(!byId(t, 120)[SID], "sessions [] with a fresh sessions_at: the session is gone"); }

// ---- scope: the two Macs only (card 9) and ruling 7 (a screen shows what runs on it plus what it launched) ----
{ const t = fresh(); check(O.deliver(t, "archmagi", ok(D0, 1)).ignored === "out_of_scope", "archmagi is out of scope: ignored, neither drawn nor marked");
  O.deliver(t, DESK, ok(D0, 100)); const L = load("laptop_1_2.json"); O.deliver(t, LAP, ok(L, 100));
  const all = O.view(t, 100), onLap = O.visible(all, LAP).map(o => o.id).sort(), onDesk = O.visible(all, DESK).map(o => o.id);
  check(JSON.stringify(onLap) === JSON.stringify(["19778@1794098220", "run:granite-e7s4-01"].sort()), "ruling 7: the Laptop draws its own work plus the run it launched on the Desktop", onLap);
  check(onDesk.length === 6 && !onDesk.includes("19778@1794098220"), "ruling 7: the Desktop draws what runs on it, not the Laptop's own work", onDesk); }

// ---- acceptance 6: clicking a stale job launches nothing and brings nothing to the front ----
{ const t = fresh(); O.deliver(t, DESK, ok(D0, 100));
  const live = byId(t, 100)["run:granite-e7s4-01"], c = O.clickFor(live);
  check(c.act === "attach" && c.target === "deskrun:granite" && c.front === false, "a live declared job: attach-only, never brought to the front", c);
  O.deliver(t, DESK, { mono: 115, outcome: "connection", reason: "timeout" });
  const s = O.clickFor(byId(t, 115)["run:granite-e7s4-01"]);
  check(s.act === false, "acceptance 6: a stale (unknown) job: nothing is launched", s);
  check(O.clickFor(byId(t, 100)["mux:tmux:default:%3:4242@1794159000"]).act === false, "an undeclared job is unclickable");
  check(O.clickFor(byId(t, 100)["model:omlx:glm"]).act === false, "a resident model is unclickable");
  const en = later(D0, 10); en.foreign[0].terminal = { outcome: "interrupted" }; const t2 = fresh(); O.deliver(t2, DESK, ok(en, 1));
  check(O.clickFor(byId(t2, 1)["run:granite-e7s4-01"]).act === false, "an ended job is unclickable"); }

// ---- the guard can see: a deliberately broken reducer would fail acceptance 1 ----
{ const t = fresh(); O.deliver(t, DESK, ok(D0, 100)); const f = later(D0, 5);
  f.coverage.mux = { observed_at: T + 3, valid_until: T + 15.5, unknown: "read_failed" }; f.foreign = f.foreign.filter(x => x.collector !== "mux");
  O.deliver(t, DESK, ok(f, 105)); const naive = new Set(f.foreign.map(x => x.id).concat(f.sessions.map(x => x.id)));   // "transport ok = absence"
  check(O.view(t, 105).some(o => !naive.has(o.id)), "control: the naive rule would have removed the mux pane; the reducer kept it"); }

console.log(passes + " passed, " + fails + " failed"); process.exit(fails ? 1 : 0);
