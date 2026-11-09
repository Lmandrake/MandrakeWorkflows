/* Sprites project map: ONE canonical project key (review R1 #1, #2, #16, #17). The key is Augur's `project_key`, which is
 * the Lodestar registry Id (augur/augur/collectors/sessions.py parse_registry; blank Id -> sanitize_key(Name)). Every
 * other name hangs off it here:
 *   name   the registry Name (what Augur reports as `project`; the full display name)
 *   alias  the Waypoint launch alias (`launch <alias>`), joined launches.md Waypoint -> waypoints.md Path -> registry Path
 *   hex    the launch row's text colour (`]10;#RRGGBB`), focus = the launch row's Focus
 *   dir    the registry Path on this machine (Machine paths override), the only directory a ghost click may open
 * build() runs in the Swift host (app/macos/ProjectMap.swift, JavaScriptCore) over the four files; its table is handed to
 * the stage (SpritesStage.setProjects) and to Settings (init {projects}); the ghost launch looks the key up in it. The
 * stage and Settings also load this file for the lookups below, so names, short names, hue and cast resolve one way.
 * Per-machine rows: waypoints.md and launches.md resolve like waypoint's resolve_for_machine (exact Machine, else the
 * blank row; only Status active, blank = active); the registry like Augur (active rows; Machines column by role or key; Machine paths).
 * A launch row whose directory is no registry Path (MandrakeVisualize -> ~/dev/MandrakeWorkflows/visualize; its registry
 * row is retired) has key null: Augur can never report it, so nothing on the stage can match it. */
(function (root) {
  "use strict";
  const KEY_RE = /^[a-z0-9][a-z0-9._-]*$/;
  function keyOf(name) { let k = String(name || "").toLowerCase().replace(/[^a-z0-9._-]+/g, "-").replace(/^[^a-z0-9]+/, "");
    return KEY_RE.test(k) ? k : "unknown"; }
  const own = (o, k) => o != null && typeof o === "object" && Object.prototype.hasOwnProperty.call(o, k);

  // ---------- markdown tables (as Augur's md_tables: a header row followed by a separator row) ----------
  const isRow = l => l.trim().startsWith("|");
  const isSep = l => { const s = l.trim(); return s.startsWith("|") && /^[|\-: \t]+$/.test(s) && s.includes("-"); };
  function cells(line) { let s = line.trim(); if (s.startsWith("|")) s = s.slice(1); if (s.endsWith("|") && !s.endsWith("\\|")) s = s.slice(0, -1);
    return s.split(/(?<!\\)\|/).map(c => c.trim().replace(/\\\|/g, "|")); }
  function tables(text) { const lines = String(text || "").split("\n"), out = [];
    for (let i = 0; i < lines.length - 1; i++) { if (!(isRow(lines[i]) && isSep(lines[i + 1]))) continue;
      const head = cells(lines[i]).map(h => h.toLowerCase()), rows = []; let j = i + 2;
      for (; j < lines.length && isRow(lines[j]); j++) { const c = cells(lines[j]); if (!c.some(Boolean)) continue;
        const r = Object.create(null); head.forEach((h, k) => { r[h] = k < c.length ? c[k] : ""; }); rows.push(r); }
      out.push({ head, rows }); i = j - 1; }
    return out; }
  const clean = v => String(v || "").trim().replace(/^`+|`+$/g, "").trim();
  const expand = (p, home) => { p = clean(p); if (p === "~" || p.startsWith("~/")) p = home + p.slice(1); return p.length > 1 ? p.replace(/\/+$/, "") : p; };

  // ---------- registry (Augur's parse_registry + machine_role) ----------
  function machineRole(text, key) { for (const t of tables(text)) if (t.head.includes("key") && t.head.includes("role"))
    for (const r of t.rows) if (clean(r.key).toLowerCase() === key) return clean(r.role).toLowerCase() || null; return null; }
  function registryRows(text, role, key, home) {
    const ts = tables(text); if (!ts.length || !ts[0].head.includes("name") || !ts[0].head.includes("path")) return null;
    const over = new Map();
    for (const t of ts.slice(1)) if (t.head.includes("machine") && t.head.includes("path")) for (const r of t.rows) {
      const n = clean(r.repo || r.name), w = clean(r.machine).toLowerCase(), p = clean(r.path); if (n && w && p) over.set(n + "\n" + w, p); }
    const here = [role, key].filter(Boolean).map(v => v.toLowerCase()), out = [];
    for (const r of ts[0].rows) { const name = clean(r.name); let path = clean(r.path); if (!name || !path) continue;
      if ((clean(r.state).toLowerCase() || "active") !== "active") continue;
      const m = clean(r.machines).toLowerCase(), ms = !m || ["all", "*", "-", "—"].includes(m) ? [] : m.split(/[,\s]+/).filter(Boolean);
      if (ms.length && here.length && !here.some(h => ms.includes(h))) continue;
      for (const w of here) if (over.has(name + "\n" + w)) { path = over.get(name + "\n" + w); break; }
      out.push({ key: clean(r.id) || keyOf(name), name, dir: expand(path, home) }); }
    return out; }

  // ---------- Waypoint (waypoints.md, launches.md; waypoint's resolve_for_machine) ----------
  function wpTable(text, first) { for (const t of tables(text)) if (t.head[0] === "name" && t.head.includes(first)) return t.rows; return []; }
  function forMachine(rows, machine) { const by = new Map(), m = String(machine || "").toLowerCase();
    for (const r of rows) { if (!clean(r.name) || (clean(r.status).toLowerCase() || "active") !== "active") continue;   // only live rows (R2 MACOS #7)
      const n = clean(r.name).toUpperCase(); if (!by.has(n)) by.set(n, []); by.get(n).push(r); }
    const out = []; for (const rs of by.values()) { const pick = rs.find(r => clean(r.machine).toLowerCase() === m) || rs.find(r => !clean(r.machine)); if (pick) out.push(pick); }
    return out; }
  const HEX = /\]10;#([0-9A-Fa-f]{6})/;

  /** The table: one entry per active registry project on this machine (key, name, dir, alias, hex, focus), then each
   * launch row that matches no registry project (key null). Launch order is launches.md order; registry order otherwise. */
  function build(o) { o = o || {}; const home = String(o.home || "").replace(/\/+$/, "");
    const lkey = String(o.lodestarMachine || o.machine || "").toLowerCase();
    const reg = registryRows(o.registry, o.machines ? machineRole(o.machines, lkey) : null, lkey, home) || [];
    const wp = new Map(forMachine(wpTable(o.waypoints, "path"), o.machine).map(r => [clean(r.name).toUpperCase(), expand(r.path, home)]));
    const byDir = new Map(); reg.forEach(e => { if (!byDir.has(e.dir)) byDir.set(e.dir, e); });
    const out = reg.map(e => ({ key: e.key, name: e.name, dir: e.dir, alias: null, hex: null, focus: false }));
    const at = new Map(out.map(e => [e.key, e]));
    const lrows = wpTable(o.launches, "waypoint"), launches = new Set(forMachine(lrows, o.machine));
    for (const r of lrows) { if (!launches.has(r)) continue;   // one row per Name for this machine, in launches.md order
      const w = clean(r.waypoint), dir = w ? wp.get(w.toUpperCase()) : expand(r.path, home); if (!dir) continue;
      const alias = clean(r.name), hm = HEX.exec(r.command || ""), hex = hm ? "#" + hm[1].toUpperCase() : null;
      const focus = ["yes", "y", "true", "1", "x"].includes(clean(r.focus).toLowerCase()), hit = byDir.get(dir);
      if (hit) { const e = at.get(hit.key); if (e.alias && !(focus && !e.focus)) continue;   // first row wins; a focus row beats a non-focus one
        Object.assign(e, { alias, hex, focus }); }
      else out.push({ key: null, name: alias, dir, alias, hex, focus }); }
    return mergeLocal(out, o.local, o.hasWaypoint !== false); }

  /** The host's local projects file (Config.swift Paths.projects: {"<key>": {focus, hex, name, dir}}) over the table
   * (owner, 2026-11-08: "with a click could become Focused and thus retained"). Without Waypoint it is the only source of
   * focus and colour; with Waypoint it fills in only for projects Waypoint cannot hold, those with no launch alias (a
   * registry project with no launch row, or an active sprite in a directory the registry does not know, which gets an
   * entry of its own). Keyless table rows and alias rows under Waypoint are untouched. */
  function mergeLocal(table, local, hasWaypoint) {
    if (!local || typeof local !== "object") return table;
    const seen = new Set();
    for (const e of table) { if (!e.key) continue; seen.add(e.key);
      const l = own(local, e.key) && local[e.key] && typeof local[e.key] === "object" ? local[e.key] : null;
      if (hasWaypoint && e.alias) continue;
      if (!hasWaypoint) e.focus = !!(l && l.focus === true);
      else if (l && typeof l.focus === "boolean") e.focus = l.focus;
      if (l && /^#[0-9a-f]{6}$/i.test(l.hex || "")) e.hex = l.hex.toUpperCase(); }
    for (const k of Object.keys(local)) { const l = local[k]; if (seen.has(k) || !l || l.focus !== true || !KEY_RE.test(k)) continue;
      table.push({ key: k, name: clean(l.name) || k, dir: clean(l.dir) || null, alias: null,
        hex: /^#[0-9a-f]{6}$/i.test(l.hex || "") ? l.hex.toUpperCase() : null, focus: true, local: true }); }
    return table; }

  /** What is on the stage now, from an Augur snapshot, by the stage's own rules (app/stage.html adaptState): one entry per
   * project key, sessions first (a headless child is its parent's satellite, not a sprite), then ghosts (burning, no
   * session). state: "needs" | "working" | "idle" | "ghost"; white = an unmanaged session (a dir with no registry row).
   * Visibility is NOT applied: a hidden project is still active, and Settings lists it under Hidden. */
  function active(snap, nowSec) {
    if (!snap || typeof snap !== "object" || !Array.isArray(snap.sessions) || snap.schema !== "augur.snapshot" ||
        String(snap.version ?? "").split(".")[0] !== "1" || snap.off === true) return [];
    const ids = new Set(), out = [], at = new Map();
    for (const x of snap.sessions) if (x && x.id != null) ids.add(String(x.id));
    const rank = { needs: 3, working: 2, idle: 1 };
    for (const x of snap.sessions) { if (!x || x.id == null || (x.parent != null && ids.has(String(x.parent)))) continue;
      const key = x.project_key ? String(x.project_key) : keyOf(x.project), a = x.attention && x.attention.state;
      const state = a === "needs_you" ? "needs" : a === "working" ? "working" : "idle", white = x.managed === false;
      const e = at.get(key);
      if (!e) { const n = { key, id: String(x.id), name: String(x.project || key), state, white, sessions: 1 }; at.set(key, n); out.push(n); }
      else { e.sessions++; if (rank[state] > rank[e.state]) e.state = state; if (!white) e.white = false; } }
    const now = nowSec ?? Date.now() / 1000;   // a ghost needs fresh counts, as the stage's blk() does
    for (const p of Array.isArray(snap.projects) ? snap.projects : []) { const c = p && p.counts;
      if (!p || !p.key || at.has(String(p.key)) || !c || !(c.burning > 0) || !(c.valid_until >= now)) continue;
      const n = { key: String(p.key), name: String(p.name || p.key), state: "ghost", white: false, sessions: 0 }; at.set(n.key, n); out.push(n); }
    return out; }

  // ---------- lookups (stage and Settings) ----------
  /** key -> entry, from a table (entries without a key are skipped). */
  function index(table) { const m = new Map(); for (const e of Array.isArray(table) ? table : []) if (e && typeof e.key === "string" && e.key && !m.has(e.key)) m.set(e.key, e); return m; }
  /** The cast entry of a project: cast.projects[key]; before #2 the cast was keyed by the launch alias or the registry
   * Name, so an entry under either is still honoured until Settings next saves under the key. */
  function castEntry(cast, key, entry) { const P = cast && cast.projects; if (!P || typeof P !== "object") return null;
    if (key && own(P, key)) return P[key];
    for (const n of entry ? [entry.alias, entry.name] : []) if (n && own(P, n)) return P[n];
    return null; }
  /** key -> short label (SpritesShortNames over every project in the table plus `extra` [{key, name}] not in it, so the
   * same project gets the same short name on the stage and in Settings). Override: castEntry(...).short. */
  function shortTable(table, cast, extra) { const SN = root.SpritesShortNames || (typeof require === "function" ? require("../prototype/labels/shortname.js") : null);
    const items = [], seen = new Set();
    for (const e of Array.isArray(table) ? table : []) { if (!e || !e.name) continue; const k = e.key || "launch:" + e.alias; if (seen.has(k)) continue; seen.add(k);
      const c = castEntry(cast, e.key, e) || {}; items.push({ k, p: { name: e.name, alias: e.alias && e.alias !== e.name ? e.alias : undefined, short: c.short } }); }
    for (const x of extra || []) { if (!x || !x.key || seen.has(x.key)) continue; seen.add(x.key);
      const c = castEntry(cast, x.key, { name: x.name }) || {}; items.push({ k: x.key, p: { name: x.name || x.key, short: c.short } }); }
    const out = Object.create(null); if (!SN) { items.forEach(i => { out[i.k] = i.p.short || i.p.name; }); return out; }
    // shortNames is keyed by name: two keys with one name (rare) take the first's
    let r = {}; try { r = SN.shortNames(items.map(i => i.p)).short || {}; } catch (e) { r = {}; }
    items.forEach(i => { out[i.k] = SN.display(own(r, i.p.name) ? r[i.p.name] : i.p.name); });
    return out; }

  /** Settings' row set (owner, 2026-11-08: "Focus, Untracked, or Hidden (don't show again)"). tracking: "hidden" when the
   * cast says visibility "hide" (wins), "focus" when the entry is focused, else "untracked". Rows: every focus entry (in
   * table order; without Waypoint every keyed entry, as before), every active project (snapshot order), every hidden cast
   * key; an Untracked row is listed only while active. Focus and Untracked first, then Hidden. Each row:
   * {key, entry (the table's, or null), live (the active() entry, or null), tracking}. */
  function tracking(cast, key, entry) { const c = castEntry(cast, key, entry || { name: key }) || {};
    return c.visibility === "hide" ? "hidden" : entry && entry.focus ? "focus" : "untracked"; }
  function settingsRows(table, cast, act, hasWaypoint) {
    const by = index(table), live = new Map((act || []).map(a => [a.key, a])), keys = [], seen = new Set();
    const add = k => { if (k && !seen.has(k)) { seen.add(k); keys.push(k); } };
    for (const e of Array.isArray(table) ? table : []) if (e && e.key && (hasWaypoint === false || e.focus)) add(e.key);
    for (const k of live.keys()) add(k);
    const P = cast && cast.projects && typeof cast.projects === "object" ? cast.projects : {};
    for (const k of Object.keys(P)) if (P[k] && P[k].visibility === "hide" && KEY_RE.test(k)) add(k);
    const rows = keys.map(k => { const e = by.get(k) || null; return { key: k, entry: e, live: live.get(k) || null, tracking: tracking(cast, k, e) }; })
      .filter(r => r.tracking !== "untracked" || r.live || hasWaypoint === false && r.entry);
    return rows.filter(r => r.tracking !== "hidden").concat(rows.filter(r => r.tracking === "hidden")); }

  const api = { build, mergeLocal, active, tracking, settingsRows, index, castEntry, shortTable, keyOf, tables, registryRows, forMachine };
  if (typeof module !== "undefined" && module.exports) module.exports = api; else root.SpritesProjects = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
