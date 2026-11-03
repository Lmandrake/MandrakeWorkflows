/* Sprites hover-label shortnames (design, 2026-11-01; not wired into the app yet).
 * shortNames(projects) -> {name: short}. projects = [{name, alias?, short?}]
 *   short = the Settings override (wins, trimmed, max 12 chars)
 *   alias = the project's Waypoint launch alias, if any (used when shorter than the automatic name)
 * Automatic rule: drop the owner token "Mandrake" (when anything is left); keep it whole if <= 12 chars;
 * else keep whole leading words while <= 10 chars (a single unbreakable word may run to 12);
 * a result under 5 chars is too thin: take the whole name if <= 12, else add the initials of the rest
 * ("claude RC"); then make the set distinct (a collider takes its next word if <= 12, else the initials
 * of the rest, then a number).
 * Display: "_" and "-" show as a space. */
(function (root) {
  "use strict";
  const SOFT = 10, HARD = 12, OWNER = /^mandrake$/i;
  function words(name) {
    return String(name).split(/[_\-\s.]+/).flatMap(p => p.split(/(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])/)).filter(Boolean);
  }
  function auto(name) {
    let w = words(name); const kept = w.filter(x => !OWNER.test(x)); if (kept.length) w = kept;
    const sep = /[_\-\s]/.test(name) ? " " : "";
    const whole = w.join(sep); if (whole.length <= HARD) return { s: whole, w, n: w.length };
    let s = w[0]; let n = 1;
    if (s.length > HARD) return { s: s.slice(0, HARD), w, n: 1 };
    while (n < w.length && (s + sep + w[n]).length <= SOFT) { s += sep + w[n]; n++; }
    if (s.length < 5 && n < w.length) { const all = w.join(sep);
      if (all.length <= HARD) return { s: all, w, n: w.length };
      s += " " + w.slice(n).map(x => x[0].toUpperCase()).join(""); n = w.length; }
    return { s, w, n };
  }
  const sepOf = name => /[_\-\s]/.test(name) ? " " : "";
  function shortNames(projects) {
    const out = {}, why = {}, meta = {};
    for (const p of projects) {
      if (p.short && String(p.short).trim()) { out[p.name] = String(p.short).trim().slice(0, HARD); why[p.name] = "override"; continue; }
      const a = auto(p.name); meta[p.name] = a; out[p.name] = a.s; why[p.name] = "auto";
      if (p.alias && p.alias.length <= SOFT && p.alias.length < a.s.length + (a.n < a.w.length ? 99 : 0) && p.alias !== p.name) {
        out[p.name] = p.alias; why[p.name] = "alias"; }
    }
    // distinct: colliders (auto only) take the initial of their next unused word, then a number
    const seen = {}; for (const n in out) (seen[out[n].toLowerCase()] = seen[out[n].toLowerCase()] || []).push(n);
    for (const k in seen) { const g = seen[k]; if (g.length < 2) continue;
      g.filter(n => why[n] === "auto").sort((a, b) => a.length - b.length).slice(g.some(n => why[n] !== "auto") ? 0 : 1)
        .forEach((n, i) => { const m = meta[n], rest = m ? m.w.slice(m.n) : [], sep = sepOf(n);
          const add = !rest.length ? " " + (i + 2) : (out[n] + sep + rest[0]).length <= HARD ? sep + rest[0]
            : " " + rest.map(x => x[0].toUpperCase()).join("");
          out[n] = out[n] + add; why[n] = "auto, made distinct"; }); }
    return { short: out, why };
  }
  const display = s => String(s).replace(/[_\-]/g, " ");
  const api = { shortNames, display, words, auto };
  if (typeof module !== "undefined") module.exports = api; else root.SpritesShortNames = api;
})(this);
