/* Sprites observation contract (docs/OBSERVATION_CONTRACT.md): the ONE reducer from fetch outcomes to drawable
 * objects, for snapshots that arrive from another Mac (build plan step 1 of
 * docs/design/2026-11-06-foreign-work/03-merged.md). No collector and no transport is wired to it yet: D (local scan)
 * and A (pull) feed it later. Fixture-tested in tests/node/test_observation_contract.js.
 *
 * The invariant (correction 1): an object is removed ONLY by a newer, authoritative observation that covers its scope
 * and does not contain it. A failed fetch, a refused file, a failed or partial collector, a 1.2 producer with no
 * foreign[], a warming-up restart: each may only make an object unknown, never remove it. Absence is not success
 * (correction 2): a departure records "absence observed", never an exit status; only a terminal record says how it ended.
 *
 * Clocks: the receiver never compares its wall clock with the producer's. Each ok delivery carries `source_now` (the
 * producer host's wall clock, read in the same command as the snapshot); ages are source_now - observed_at at the
 * fetch, then advanced by the receiver's MONOTONIC clock (`mono`). Clock skew therefore changes nothing.
 *
 * API (all pure data, JSON-safe):
 *   create({viewer, hosts?, pull_s?, grace_s?})   state
 *   deliver(state, host, {mono, outcome, reason?, source_now?, snapshot?})   -> {link} | {ignored}
 *   view(state, mono)                              -> [{id, host, kind, status: live|unknown|ended, why, age, ...}]
 *   visible(view, viewer)                          -> what the viewer's screen draws (ruling 7)
 *   shouldAttempt(state, host, mono)               -> false while a backoff holds (auth failure: no rapid retry)
 *   clickFor(obj)                                  -> {act: false, why} | {act: "attach", target} (never launch/front)
 *   ageWords(seconds)                              -> "12s" | "4m" | "2h" */
(function (root) {
  "use strict";
  const HOSTS = ["mt-BBBBBB", "mt-AAAAAA"];   // owner, 2026-11-08 (card 9): Sprites is for the two work Macs only
  const KINDS = new Set(["claude_session", "remote_job", "container", "resident_model"]);   // anything else: "unknown"
  const OUTCOMES = new Set(["ok", "connection", "auth"]);
  const AUTH_BACKOFF_S = [300, 600, 1200, 3600], CONN_MAX_S = 120;
  const fin = v => typeof v === "number" && isFinite(v);
  const obj = v => !!v && typeof v === "object" && !Array.isArray(v);
  const minor = v => { const m = /^1\.(\d+)$/.exec(String(v == null ? "" : v)); return m ? +m[1] : null; };

  function create(o) { o = o || {}; const pull = fin(o.pull_s) ? o.pull_s : 15;
    return { viewer: o.viewer || null, hosts: (o.hosts || HOSTS).slice(), pull_s: pull, grace_s: fin(o.grace_s) ? o.grace_s : pull,
      host: {}, objects: {}, departed: [] }; }
  function hostRec(st, h) { return st.host[h] || (st.host[h] = { link: "never", reason: null, fails: 0, next: -Infinity, inc: null, seq: -1, cov: {} }); }
  const incKey = s => s.producer.pid + "@" + s.producer.started_at;

  // Producer-class refusals of a fetched file (it arrived; it is not a usable observation).
  function envelope(s, host) {
    if (!obj(s)) return "unparseable";
    if (s.schema !== "augur.snapshot" || minor(s.version) === null) return "unknown_schema";
    if (s.off === true) return "off";
    if (!fin(s.written_at) || !fin(s.valid_until) || !Number.isInteger(s.seq) || !Array.isArray(s.sessions)) return "malformed";
    const p = s.producer; if (!obj(p) || !fin(p.pid) || !fin(p.started_at)) return "malformed";
    if (p.machine !== host) return "wrong_machine";
    return null; }

  // Coverage per collector, in the source's own clock. "sessions" comes from sessions_at (1.1); every foreign
  // collector from `coverage` (1.3). A 1.2 producer publishes no coverage, so no foreign scope is ever authoritative.
  function coverage(s, now) { const out = {}, sa = s.sessions_at;
    out.sessions = !obj(sa) || !fin(sa.observed_at) || !fin(sa.valid_until) ? { status: "not_published" }
      : sa.unknown ? { status: "failed", reason: String(sa.unknown) } : now > sa.valid_until ? { status: "stale" }
      : { status: "reported", fresh: true, observed_at: sa.observed_at, valid_until: sa.valid_until, scopes: { "*": "complete" } };
    const C = minor(s.version) >= 3 && obj(s.coverage) ? s.coverage : {};
    for (const name in C) { if (name === "sessions") continue; const c = C[name];
      if (!obj(c) || !fin(c.observed_at) || !fin(c.valid_until)) { out[name] = { status: "malformed" }; continue; }
      if (c.unknown) { out[name] = { status: "failed", reason: String(c.unknown) }; continue; }
      if (now > c.valid_until) { out[name] = { status: "stale" }; continue; }
      out[name] = { status: "reported", fresh: true, observed_at: c.observed_at, valid_until: c.valid_until, scopes: obj(c.scopes) ? c.scopes : {} }; }
    return out; }

  function upsert(st, host, it, now, mono, inc) { const key = host + "|" + it.id, o = st.objects[key];
    if (o && it.observed_at < o.observed_at) return key;            // an older record (a replayed completion): ignored
    if (o && o.status === "ended" && !it.terminal) return key;      // a terminal record is final
    st.objects[key] = { key, id: it.id, host, collector: it.collector, scope: it.scope, kind: it.kind, declared: it.declared,
      label: it.label, launched_from: it.launched_from, attach: it.attach, started_at: it.started_at,
      observed_at: it.observed_at, valid_for: Math.max(0, it.valid_until - it.observed_at), age0: Math.max(0, now - it.observed_at), mono,
      status: it.terminal ? "ended" : "live", terminal: it.terminal || null, inc, miss: null };
    return key; }

  function foreignItem(f) {
    if (!obj(f) || typeof f.id !== "string" || !f.id || typeof f.collector !== "string" || !fin(f.observed_at) || !fin(f.valid_until)) return null;
    const t = obj(f.terminal) && ["exited", "failed", "interrupted"].includes(f.terminal.outcome)
      ? { outcome: f.terminal.outcome, exit_code: Number.isInteger(f.terminal.exit_code) ? f.terminal.exit_code : null, ended_at: fin(f.terminal.ended_at) ? f.terminal.ended_at : null } : null;
    return { id: f.id, collector: f.collector, scope: typeof f.scope === "string" && f.scope ? f.scope : "*",
      kind: KINDS.has(f.kind) && f.kind !== "claude_session" ? f.kind : "unknown", declared: f.declared === true,
      label: f.declared === true && typeof f.label === "string" ? f.label : null, launched_from: typeof f.launched_from === "string" ? f.launched_from : null,
      attach: f.declared === true && typeof f.attach === "string" ? f.attach : null, started_at: fin(f.started_at) ? f.started_at : null,
      observed_at: f.observed_at, valid_until: f.valid_until, terminal: t }; }

  function fail(H, st, mono, cls, reason) {
    H.fails = H.link === cls ? H.fails + 1 : 1; H.link = cls; H.reason = reason || cls;
    H.next = mono + (cls === "auth" ? AUTH_BACKOFF_S[Math.min(H.fails - 1, AUTH_BACKOFF_S.length - 1)]
      : cls === "connection" ? Math.min(CONN_MAX_S, st.pull_s * Math.pow(2, H.fails - 1)) : st.pull_s);
    return { link: cls, reason: H.reason }; }

  function deliver(st, host, d) {
    if (!st.hosts.includes(host)) return { ignored: "out_of_scope" };
    d = d || {}; const H = hostRec(st, host), mono = d.mono;
    if (!fin(mono)) return { ignored: "no_mono" };
    if (d.outcome !== "ok") return fail(H, st, mono, OUTCOMES.has(d.outcome) ? d.outcome : "connection", d.reason || d.outcome);
    const s = d.snapshot, why = envelope(s, host); if (why) return fail(H, st, mono, "producer", why);
    if (!fin(d.source_now)) return fail(H, st, mono, "producer", "no_source_clock");
    if (d.source_now > s.valid_until) return fail(H, st, mono, "producer", "stale_file");   // its Augur is dead or asleep
    const inc = incKey(s), same = H.inc && H.inc.key === inc;
    if (same && s.seq < H.seq) return { ignored: "replay" };
    if (H.inc && !same && s.producer.started_at < H.inc.started_at) return { ignored: "replay_old_incarnation" };
    H.inc = { key: inc, started_at: s.producer.started_at }; H.seq = s.seq;
    H.link = "ok"; H.reason = null; H.fails = 0; H.next = mono + st.pull_s;
    const now = d.source_now, cov = coverage(s, now), seen = new Set(); H.cov = cov;
    // Claude sessions: present only when the list itself is measured (Augur publishes [] when it is not, C3)
    if (cov.sessions.status === "reported") { const sa = s.sessions_at;
      for (const x of s.sessions) { if (!obj(x) || x.id == null) continue;
        seen.add(upsert(st, host, { id: String(x.id), collector: "sessions", scope: "*", kind: "claude_session", declared: true,
          label: null, launched_from: typeof x.launched_from === "string" ? x.launched_from : null, attach: null,
          started_at: fin(x.started_at) ? x.started_at : null, observed_at: sa.observed_at, valid_until: sa.valid_until, terminal: null }, now, mono, inc)); } }
    // foreign[] (1.3): presence is evidence whatever its collector's coverage says
    if (Array.isArray(s.foreign)) for (const f of s.foreign) { const it = foreignItem(f); if (it) seen.add(upsert(st, host, it, now, mono, inc)); }
    // removal: only a fresh, newer, complete observation of the object's own scope
    for (const key of Object.keys(st.objects)) { const o = st.objects[key]; if (o.host !== host || seen.has(key)) continue;
      const c = cov[o.collector];
      if (!c || !c.fresh) { o.miss = "collector:" + (c ? c.reason || c.status : "not_published"); continue; }
      const sc = Object.prototype.hasOwnProperty.call(c.scopes, o.scope) ? c.scopes[o.scope] : c.scopes["*"];
      if (sc !== "complete") { o.miss = "scope:" + (sc || "not_covered"); continue; }
      if (!(c.observed_at > o.observed_at)) continue;   // not newer than what we hold: says nothing yet
      delete st.objects[key];
      st.departed.push({ key, id: o.id, host, how: o.status === "ended" ? "ended_then_absent" : "absence_observed",
        terminal: o.terminal, across_restart: o.inc !== inc, mono }); }
    return { link: "ok" }; }

  function view(st, mono) { const out = [];
    for (const key in st.objects) { const o = st.objects[key], H = st.host[o.host], age = o.age0 + Math.max(0, mono - o.mono);
      let status = o.status, why = null;
      if (status === "live") {
        if (H.link !== "ok") { status = "unknown"; why = H.link + ":" + H.reason; }
        else if (o.miss) { status = "unknown"; why = o.miss; }   // not seen, and nothing able to say it is gone
        else if (age > o.valid_for + st.grace_s) { status = "unknown"; why = "stale"; } }
      out.push({ key, id: o.id, host: o.host, kind: o.kind, declared: o.declared, label: o.label, launched_from: o.launched_from,
        attach: o.attach, status, why, age, terminal: o.terminal }); }
    return out.sort((a, b) => a.key < b.key ? -1 : a.key > b.key ? 1 : 0); }

  // Ruling 7 (owner, 2026-11-08): a screen shows what runs on it, plus what it launched elsewhere; never a third screen.
  function visible(v, viewer) { return v.filter(o => o.host === viewer || (o.launched_from != null && o.launched_from === viewer)); }
  function shouldAttempt(st, host, mono) { const H = st.host[host]; return st.hosts.includes(host) && (!H || mono >= H.next); }
  // Correction 15: a click is attach-only, bound to execution identity; it never launches, creates or brings to front.
  function clickFor(o) {
    if (!o || o.status !== "live") return { act: false, why: "not live (" + (o ? o.status : "none") + ")" };
    if (o.kind !== "remote_job" || !o.declared || !o.attach) return { act: false, why: "no declared attach target" };
    return { act: "attach", target: o.attach, host: o.host, front: false }; }
  function ageWords(s) { s = fin(s) ? Math.max(0, s) : 0;
    return s < 60 ? Math.floor(s) + "s" : s < 3600 ? Math.floor(s / 60) + "m" : s < 86400 ? Math.floor(s / 3600) + "h" : Math.floor(s / 86400) + "d"; }

  const api = { HOSTS, create, deliver, view, visible, shouldAttempt, clickFor, ageWords, coverage };
  if (typeof module !== "undefined" && module.exports) module.exports = api; else root.SpritesObserve = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
