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

  const api = { build, index, castEntry, shortTable, keyOf, tables, registryRows, forMachine };
  if (typeof module !== "undefined" && module.exports) module.exports = api; else root.SpritesProjects = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
