/* Sprites Settings window. Host contract:
 *   SpritesSettings.init({cast, projects:[{key, name, alias, hex, focus}]})   the host's project table (app/projects.js,
 *     SpritesProjects.build); one row per focus entry, plus every project active on the stage (init {snapshot}, the Augur
 *     snapshot; SpritesSettings.setSnapshot(snap) as it changes), plus a collapsed Hidden section. Each row is Focus,
 *     Untracked or Hidden (owner, 2026-11-08): Focus = the table's focus (Waypoint, else the host's local projects file);
 *     Hidden = cast.projects[key].visibility "hide"; Untracked = neither, listed only while active. Editing an Untracked
 *     row makes it Focus (otherwise the edit would not be kept). cast.projects is keyed by project_key (review R1 #2), the
 *     key the stage and the ghost launch use; a row shows its launch alias. Entries without a key ({name, hex}) key by name.
 *   SpritesSettings.init({cast, waypoint:false})            no Waypoint: browse only
 *   SpritesSettings.init({..., behaviors:{key:bool}, demo:bool, size:number})  Behaviours tab; missing keys are ON; size 0.5..2 posts {setSize}.
 *   Behaviour saves: settings.postMessage({saveBehaviors:{...}}) and ({setDemo:bool}); browser: localStorage.
 *   Show/hide and meeting mode (review R1 #13): init({..., hidden:bool, meeting:bool, hotkey:"⌃⌥⌘S", hotkeyOK:bool}); the
 *   switches post {setHidden:bool} and {setMeeting:bool} (host state, never saved in behaviours);
 *   SpritesSettings.setVisibility({hidden, meeting}) mirrors a change made from the menu or the hotkey, posting nothing.
 *   Name label: behaviors.labelStyle ("filament"|"orbit"|"constellation"|"tag"|"whisper", default constellation) rides in the
 *   same saveBehaviors object. Backdrop tab: behaviors.backdrop ("none"|"b01".."b12", default none) and behaviors.backdropSpeed
 *   ({id: multiplier}) ride in it too (app/macos/Backdrop.swift applies them). Unknown keys (dimIcons, ...) are carried through. On screen: cast.projects[key].visibility ("hide"|"hide_at_work", absent = show). Short name: cast.projects[key].short (blank = automatic: SpritesProjects.shortTable over the whole table, as the stage does).
 * Saves via webkit.messageHandlers.settings.postMessage({saveCast: cast}); without the bridge, localStorage.
 * Browser test: settings.html?demo=1 (add &nowp=1 for the no-Waypoint view).
 * CPU: only the hero preview and the hovered tile run live; every other tile is a still frame rendered
 * once through the piece's own __renderAt() in one reused hidden iframe, then cached. */
(function () {
  "use strict";
  const PROTO = "../prototype/";
  const SPECIES = [
    { id: "c1_choir", name: "Mothership Choir", blurb: "A slow mothership ringed by a choir of lights that chase faster as it works." },
    { id: "c2_siphon", name: "Siphonophores", blurb: "A drifting bell trailing tentacles, one for each task it carries." },
    { id: "c3_sigils", name: "Living Sigils", blurb: "A pixel glyph that breathes and glints, its lights running the strokes." },
    { id: "c4_kaleido", name: "Kaleidoscope Seeds", blurb: "A turning mandala seed, folding light through its petals." },
    { id: "c5_fireflies", name: "Firefly Murmurations", blurb: "A murmuration of fireflies tracing one figure around a bright queen." },
    { id: "c6_night", name: "Night Signals", blurb: "A signal lamp's emblem as a crisp outline: one pop-culture mark per session." },
    { id: "c7_patches", name: "Mission Patches", blurb: "A mission patch's emblem as a crisp outline: one spaceflight mark per session." },
    { id: "c8_instruments", name: "Instrument Marks", blurb: "A laboratory mark as a crisp outline: one science or computing emblem per session." },
    { id: "c9_wild", name: "Wild Signs", blurb: "A natural-world sign as a crisp outline: one creature or element per session." },
    { id: "c10_made", name: "Made Marks", blurb: "A built thing in fine hard dots: one tool or structure per session." },
    { id: "c11_old", name: "Old Signs", blurb: "A heraldic charge as a crisp outline: one old emblem per session." },
  ];
  // Fallback only: the real names are read from each piece's window.VARIANT_NAMES.
  const NAMES = {
    c1_choir: ["Halo", "Twin Deck", "Gyre", "Crown", "Lantern", "Pinwheel", "Comet", "Spindle"],
    c2_siphon: ["Moon", "Lantern", "Saucer", "Box", "Lyre", "Spire", "Pagoda", "Corolla"],
    c3_sigils: ["Lantern", "Trident", "Halo", "Star", "Invader", "Ascent", "Lattice", "Eye"],
    c4_kaleido: ["Lotus", "Trefoil", "Pentagram", "Snowflake", "Quatrefoil", "Spirograph", "Dandelion", "Honeycomb"],
    c5_fireflies: ["Galaxy", "Halo", "Infinity", "Coil", "Lissajous", "Trefoil", "Comet", "Braid"],
    c6_night: ["Batman", "Bat Signal", "Delta", "Autobot", "TARDIS", "Fuji", "Starbird", "Cog"],
    c7_patches: ["Voyager", "Golden Record", "DSN dish", "Juno", "ISS", "JWST mirror", "Mars rover", "Orbit with primary"],
    c8_instruments: ["Bohr atom", "Chip", "Light bulb", "Water molecule", "Binary tree", "Bell curve", "Neural net", "Gear"],
    c9_wild: ["Sun", "Mountain", "Tree", "Seed", "Water drop", "Antlers", "Butterfly", "Owl"],
    c10_made: ["Arch", "Ladder", "Lighthouse", "Pyramid", "Target", "Balance", "Bell", "Hourglass"],
    c11_old: ["Shield", "Sword", "Skull", "Wing pair", "Phoenix", "Ankh", "Heart", "Anchor"],
  };
  const DEMO = [["Orchard", "#CB50F0"], ["ProjectCert", "#3388EE"], ["ProjectDial", "#66BB22"], ["Lodestar", "#FFCA42"],
    ["Granite", "#22DDAA"], ["SidePulse", "#FF3355"]];
  // Logical stage sizes the pieces render at (the iframe scales them to the tile).
  const STAGE = { hero: [380, 245], species: [165, 110], variant: [112, 112] };
  const BROWSE_HEX = "#5FB4FF";

  const $ = id => document.getElementById(id);
  const el = (tag, cls, html) => { const e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; };
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  function hexHue(h) { const r = parseInt(h.slice(1, 3), 16) / 255, g = parseInt(h.slice(3, 5), 16) / 255, b = parseInt(h.slice(5, 7), 16) / 255;
    const mx = Math.max(r, g, b), mn = Math.min(r, g, b), d = mx - mn; if (!d) return 0;
    const x = mx === r ? ((g - b) / d) % 6 : mx === g ? (b - r) / d + 2 : (r - g) / d + 4; return Math.round((x * 60 + 360) % 360); }
  // norm: which column of prototype/size_norm.js sizes the creature (tools/size_calibrate.py measures each context)
  const NORM = { hero: "hero", species: "tile", variant: "form" };
  const url = (c, iv, hue, [w, h], live, size) => `${PROTO}${c}.html?tl=g_cast&w=${w}&h=${h}&chrome=0&bg=0&dim=0&hover=0` +
    `&hue=${hue}&iv=${iv}` + "&fit=1&norm=" + NORM[size] + (live ? "&autostart=1&loop=1" : "&autostart=0");   // fit: hero and tiles size the craft to the cell

  // Debug trace (host SPRITES_DEBUG_SETTINGS=1 passes init {debug:true}): every programmatic write to a colour input, with
  // its stack, and every host entry point, posted to the host log. Off by default.
  let dbg = false;
  const trace = (...a) => { if (!dbg) return; const t = (performance.now() / 1000).toFixed(3) + " " + a.map(x => typeof x === "string" ? x : JSON.stringify(x)).join(" ");
    try { webkit.messageHandlers.settings.postMessage({ debugLog: t }); } catch (e) { console.log(t); } };
  function armTrace() { if (armTrace.done) return; armTrace.done = true;
    const d = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value");
    Object.defineProperty(HTMLInputElement.prototype, "value", { configurable: true, get() { return d.get.call(this); },
      set(v) { if (dbg && this.type === "color") { const old = d.get.call(this);
          trace("SET", this.id || this.getAttribute("aria-label"), old, "->", String(v), "connected", this.isConnected, "focused", document.activeElement === this,
            (new Error().stack || "").split("\n").slice(1, 6).map(s => s.trim()).join(" < ")); }
        d.set.call(this, v); } });
    document.addEventListener("input", e => { if (e.target && e.target.type === "color") trace("INPUT", e.target.id || e.target.getAttribute("aria-label"), e.target.value); }, true);
    document.addEventListener("change", e => { if (e.target && e.target.type === "color") trace("CHANGE", e.target.id || e.target.getAttribute("aria-label"), e.target.value); }, true); }

  const SP = window.SpritesProjects;
  // centry: the cast entry of a row (by key; an entry saved before #2 under the alias or registry Name still counts)
  const centry = p => (p && (SP ? SP.castEntry(cast, p.key, p) : cast.projects[p.key])) || {};
  function putCast(p, e) { for (const n of [p.alias, p.name]) if (n && n !== p.key) delete cast.projects[n]; cast.projects[p.key] = e; }
  let table = [];
  let cast = { projects: {} }, projects = [], waypoint = true, sel = 0, browse = { concept: "c5_fireflies", iv: 0, hex: BROWSE_HEX };

  // ---------- still frames: one hidden loader iframe, a queue, a cache ----------
  const stills = new Map(), names = {}, waiters = new Map();
  let canStill = true, queue = [], busy = false;
  const loader = el("iframe"); loader.style.cssText = "position:fixed;left:-9999px;top:0;width:200px;height:200px;border:0;visibility:hidden";
  loader.setAttribute("aria-hidden", "true"); document.body.appendChild(loader);
  function still(c, iv, hue, size) { const k = [c, iv, hue, size].join("|");
    if (stills.has(k)) return Promise.resolve(stills.get(k));
    return new Promise(res => { if (!waiters.has(k)) { waiters.set(k, []); queue.push({ k, c, iv, hue, size }); } waiters.get(k).push(res); pump(); }); }
  function finish(k, v) { stills.set(k, v); (waiters.get(k) || []).forEach(f => f(v)); waiters.delete(k); }
  function pump() { if (busy) return; if (!queue.length) { loader.onload = null; if (loader.src !== "about:blank") loader.src = "about:blank"; return; } busy = true; const j = queue.shift(); const st = STAGE[j.size];
    let done = false; const tm = setTimeout(() => step(null), 6000);
    function step(img) { if (done) return; done = true; clearTimeout(tm); finish(j.k, img); busy = false; setTimeout(pump, 0); }
    loader.onload = () => { try { const w = loader.contentWindow;
        if (w.VARIANT_NAMES && !names[j.c]) { names[j.c] = Array.from(w.VARIANT_NAMES); onNames(j.c); }
        w.__renderAt(4.5); const cs = w.document.querySelectorAll("canvas"), out = document.createElement("canvas");
        out.width = cs[0].width; out.height = cs[0].height; const x = out.getContext("2d");
        x.fillStyle = "#000"; x.fillRect(0, 0, out.width, out.height); cs.forEach(cv => x.drawImage(cv, 0, 0));
        step(out); }
      catch (e) { canStill = false; step(null); } };
    loader.src = url(j.c, j.iv, j.hue, st, false, j.size); }
  const nameOf = (c, iv) => (names[c] || NAMES[c])[iv] || ("Form " + (iv + 1));
  function onNames(c) { if (cur().concept === c) { paintVariantLabels(); paintInfo(); } paintList(); }

  // A tile: a still frame normally; live iframe while hovered (or always, if stills are unavailable).
  function tile(cell, c, iv, hue, size) { const t = cell.querySelector(".tile"); t.innerHTML = ""; t._live = null;
    const key = [c, iv, hue].join("|"); t._key = key;
    still(c, iv, hue, size).then(img => { if (t._key !== key) return;
      if (img) { const cv = document.createElement("canvas"); cv.width = img.width; cv.height = img.height;
        cv.getContext("2d").drawImage(img, 0, 0); if (!t._live) t.appendChild(cv); t._still = cv; }
      else if (cell.classList.contains("on")) live(t, true); });
    cell.onmouseenter = () => live(t, true); cell.onmouseleave = () => { if (canStill) live(t, false); };
    t._args = [c, iv, hue, size]; }
  function live(t, on) { if (!t._args) return;
    if (on && !t._live) { const f = el("iframe", "loading"); f.tabIndex = -1; f.onload = () => f.classList.remove("loading");
      f.src = url(t._args[0], t._args[1], t._args[2], STAGE[t._args[3]], true, t._args[3]); t.appendChild(f); t._live = f;
      if (t._still) setTimeout(() => { if (t._live === f && t._still) t._still.style.opacity = "0"; }, 350); }
    else if (!on && t._live) { t._live.src = "about:blank"; t._live.remove(); t._live = null; if (t._still) t._still.style.opacity = "1"; } }

  // ---------- hero: always live, cross-faded ----------
  let heroKey = "";
  function paintHero(force) { const c = cur(), hue = hexHue(c.hex), k = [c.concept, c.iv, hue].join("|");
    if (k === heroKey && !force) return; heroKey = k; const slot = $("heroSlot"), old = [...slot.children];
    if (document.hidden) { old.forEach(o => o.remove()); return; }
    const f = el("iframe", "loading"); f.tabIndex = -1; f.title = "preview";
    f.onload = () => { f.classList.remove("loading"); setTimeout(() => old.forEach(o => { o.src = "about:blank"; o.remove(); }), 650); };
    f.src = url(c.concept, c.iv, hue, STAGE.hero, true, "hero"); slot.appendChild(f); }
  document.addEventListener("visibilitychange", () => { if (document.hidden) { $("heroSlot").innerHTML = "";
      document.querySelectorAll(".tile").forEach(t => live(t, false)); } else paintHero(true); });

  // ---------- model ----------
  // An un-cast project's species and form: the stage's own seeded draw (app/stage.html castFor), so the preview is the
  // sprite on the desktop. A white (unmanaged, not focused) session is seeded by its session id, a project by its key.
  function hashStr(s) { let h = 2166136261; s = String(s); for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return h >>> 0; }
  function seedOf(p) { const a = actByKey.get(p.key); return a && a.white && !p.focus ? a.id : p.key; }
  function defaults(p) { const h = hashStr(seedOf(p)); return { concept: SPECIES[h % SPECIES.length].id, iv: (h >>> 3) % 8 }; }
  function cur() { if (!waypoint) return browse; const p = projects[sel]; if (!p) return browse;
    const c = centry(p); const d = defaults(p);
    return { concept: SPECIES.some(s => s.id === c.concept) ? c.concept : d.concept,
      iv: Number.isInteger(c.iv) ? c.iv : d.iv, hex: p.hex, name: p.label }; }
  function choose(patch) {
    if (!waypoint) { Object.assign(browse, patch); return render(); }
    const p = projects[sel], c = cur(); promote(p); const prev = centry(p);
    putCast(p, Object.assign({}, prev, { concept: patch.concept || c.concept, iv: patch.iv != null ? patch.iv : c.iv, hex: p.hex }));
    save(); render(); }
  let savedT = 0;
  function save() { const msg = { saveCast: JSON.parse(JSON.stringify(cast)) };
    try { if (window.webkit && webkit.messageHandlers && webkit.messageHandlers.settings) webkit.messageHandlers.settings.postMessage(msg);
      else localStorage.setItem("sprites.cast", JSON.stringify(cast)); } catch (e) { console.warn("save failed", e); return; }
    $("saved").classList.add("on"); clearTimeout(savedT); savedT = setTimeout(() => $("saved").classList.remove("on"), 1400); }

  // ---------- painting ----------
  // Rows: Focus and Untracked in #projects, Hidden in the collapsed #hiddenProjects. Each row: its live state and the
  // three-way control (the same one as the selected project's Tracking row).
  const LIVE = { needs: "needs you", working: "working", idle: "idle", ghost: "ghost" };
  const TRACK = [["focus", "Focus"], ["untracked", "Untracked"], ["hidden", "Hidden"]];
  function liveOf(p) { const a = actByKey.get(p.key); return a ? LIVE[a.state] || "idle" : "not running"; }
  let listSig = "";
  function paintList() { const ul = $("projects"), hl = $("hiddenProjects"); if (!waypoint) return;
    const sig = projects.map(p => [p.key, p.label, p.hex, tracking(p), liveOf(p)].join("|")).join("\n");
    if (sig !== listSig || ul.children.length + hl.children.length !== projects.length) { listSig = sig; ul.innerHTML = ""; hl.innerHTML = "";
      projects.forEach((p, i) => { const li = el("li"), t = tracking(p), lv = liveOf(p); li.style.setProperty("--c", p.hex); li.dataset.key = p.key; li.dataset.i = i;
        li.classList.toggle("live", lv !== "not running"); li.dataset.t = t;
        li.innerHTML = `<span class="dot"></span><span class="nm" title="${esc(p.name)}">${esc(p.label)}</span><span class="st">${esc(lv)}</span>` +
          `<span class="seg rowseg" role="radiogroup">${TRACK.map(([v, n]) => `<button data-t="${v}" role="radio" aria-checked="${v === t}">${n}</button>`).join("")}</span>`;
        li.onclick = () => { sel = i; render(); };
        li.querySelectorAll(".rowseg button").forEach(b => b.onclick = e => { e.stopPropagation(); sel = i; setTracking(p, b.dataset.t); render(); });
        (t === "hidden" ? hl : ul).appendChild(li); }); }
    const nh = projects.filter(p => tracking(p) === "hidden").length;
    $("hiddenBox").classList.toggle("hidden", !nh); $("hiddenN").textContent = nh;
    [...ul.children, ...hl.children].forEach(li => li.classList.toggle("on", +li.dataset.i === sel)); }
  function paintInfo() { const c = cur(), sp = SPECIES.find(s => s.id === c.concept);
    $("pname").textContent = waypoint ? c.name : "Random each session";
    $("sname").textContent = sp.name; $("vname").textContent = nameOf(c.concept, c.iv);
    $("blurb").textContent = sp.blurb; $("formOf").textContent = "of " + sp.name;
    document.documentElement.style.setProperty("--hue", c.hex); paintShort(); }
  // ---------- short name (owner: "shortnames for the long-named critters") ----------
  // the same table and rule as the stage's hover label (app/projects.js shortTable), without this window's overrides
  function autoShort(p) { try { return (SP ? SP.shortTable(table, null) : {})[p.key] || p.label; } catch (e) { return p.label; } }
  function shortOf(p) { const c = centry(p); return c.short ? String(c.short) : autoShort(p); }
  function paintShort() { const row = $("shortRow"), inp = $("short"); row.classList.toggle("hidden", !waypoint); $("visRow").classList.toggle("hidden", !waypoint);
    $("clrRow").classList.toggle("hidden", !waypoint); $("focusRow").classList.toggle("hidden", !waypoint); if (!waypoint) return;
    const p = projects[sel]; if (!p) return; if (document.activeElement !== inp) inp.value = centry(p).short || "";
    inp.placeholder = autoShort(p); paintVis(p); paintColour(p); paintFocus(p); }
  let shortT = 0;
  $("short").oninput = () => { const p = projects[sel]; if (!p) return; const v = $("short").value.trim().slice(0, 12), c = cur(); promote(p);
    const e = Object.assign({ concept: c.concept, iv: c.iv, hex: p.hex }, centry(p));
    if (v) e.short = v; else delete e.short; putCast(p, e);
    clearTimeout(shortT); shortT = setTimeout(save, 350); };
  // ---------- project colour and focus (owner, 2026-11-05) ----------
  // ONE colour per project, shared: the sprite, the iTerm2 text and the SidePulse LED all read it, so a new
  // colour rewrites the project's canonical hex (Waypoint: the `]10;` escape in its launches.md Command cell)
  // rather than a sprite-only field. The hue drives the SAME --hue / hexHue() path the species pickers use, so
  // the hero, the stills and the label preview follow the moment it changes.
  // Focus: the launches.md `Focus` column, through `waypoint focus add|remove`. A project with no launch alias
  // on this machine (no launch row, or a directory the registry does not know) is focused and coloured in the
  // host's local projects file instead, keyed by project key (owner, 2026-11-08: never a silent no-op).
  // Without Waypoint both go to the host's local settings file (app/macos/Config.swift Paths.projects, beside
  // cast.json and behaviors.json); in a plain browser, to localStorage.
  let hasWaypoint = true, writeN = 0;
  const pending = new Map();
  const LOCAL_KEY = "sprites.projects";
  function localProjects() { try { const o = JSON.parse(localStorage.getItem(LOCAL_KEY) || "null"); return (o && o.projects) || {}; } catch (e) { return {}; } }
  function putLocalProject(p, patch) { const all = localProjects(); all[p.key] = Object.assign({}, all[p.key], patch);
    try { localStorage.setItem(LOCAL_KEY, JSON.stringify({ projects: all })); return null; } catch (e) { return String(e.message || e); } }
  /** Send one project write to the host; `revert` runs with the message if it fails, `ok` when it lands. Returns its id. */
  function writeProject(kind, p, patch, revert, ok) {
    const id = "w" + ++writeN, msg = {};
    msg[kind] = Object.assign({ id: id, key: p.key, alias: p.alias || "" }, patch);
    if (post(msg)) { pending.set(id, { revert, ok }); return id; }
    const err = putLocalProject(p, patch);   // no host bridge: the browser's own store
    if (err) revert(err); else { if (ok) ok(); flashSaved(); }
    return id;
  }
  function writeResult(o) { o = o || {}; trace("writeResult", o); const w = pending.get(o.id); if (!w) return; pending.delete(o.id);
    if (o.error) w.revert(String(o.error)); else { if (w.ok) w.ok(); flashSaved(); } }
  /** The one place that says why a control is unavailable (and clears it). */
  function say(msg, bad) { const w = $("focusWhy"); w.textContent = msg || ""; w.classList.toggle("bad", !!msg && !!bad); }
  /** Nothing is disabled for a missing alias any more: the host falls back to its local file. */
  function needsAlias(p) { return false; }
  // 🔴 A programmatic .value on a colour input that is open in NSColorPanel moves the PANEL too, so the next brightness
  // drag starts from that value (owner, 2026-11-08: "it reverts back to the previous color"). Never write over the
  // project he is editing: `editing` is the key he last dragged and when; only a real failed write forces the revert.
  const EDIT_HOLD = 3000;
  let clrEdit = { key: null, t: 0 };
  const editingClr = p => p && clrEdit.key === p.key && (performance.now() - clrEdit.t < EDIT_HOLD || document.activeElement === $("clr"));
  function paintColour(p, force) { trace("paintColour", p && p.key, p && p.hex); const row = $("clrRow"); row.classList.toggle("hidden", !waypoint);
    if (!waypoint || !p) return; const hex = /^#[0-9a-f]{6}$/i.test(p.hex || "") ? p.hex.toUpperCase() : "#8899AA";
    if (force || !editingClr(p)) { if ($("clr").value !== hex.toLowerCase()) $("clr").value = hex.toLowerCase(); $("clrHex").textContent = hex; }
    $("clr").disabled = false; $("clrWrap").title = hasWaypoint && !p.alias
      ? "No launch alias on this machine: the colour is kept in Sprites' own projects file" : "This project's one colour: its sprite, its iTerm2 text and its SidePulse LED all use it"; }
  const F2T = { "1": "focus", "0": "untracked", h: "hidden" };
  function paintFocus(p) { const row = $("focusRow"); row.classList.toggle("hidden", !waypoint);
    if (!waypoint || !p) return; const t = tracking(p);
    [...$("focusSeg").children].forEach(b => { b.setAttribute("aria-checked", F2T[b.dataset.f] === t ? "true" : "false"); b.disabled = false; }); }
  /** Focus, Untracked or Hidden. Hidden wins: a project hidden from the On screen row reads Hidden whatever its focus. */
  function tracking(p) { return SP && p ? SP.tracking(cast, p.key, p) : p && p.focus ? "focus" : "untracked"; }
  /** Move a row to Focus, Untracked or Hidden. Hidden is the cast's visibility "hide" (the stage then draws nothing for
   * the key); Focus is the focus write (Waypoint, else the local file). The three are exclusive, so Hidden also drops
   * focus. Focusing freezes the species, form and colour on show into the cast, so they are what is retained. */
  function setTracking(p, t) { if (!p || !TRACK.some(x => x[0] === t)) return; const was = tracking(p); if (t === was) return;
    if (t === "hidden") { const e = Object.assign({}, centry(p), { visibility: "hide" });
      if (!table.some(x => x && x.key === p.key)) e.name = p.name; putCast(p, e); save(); }
    else if (was === "hidden") { const e = Object.assign({}, centry(p)); delete e.visibility; delete e.name;
      if (Object.keys(e).length) putCast(p, e); else { putCast(p, e); delete cast.projects[p.key]; } save(); }
    if (t === "focus" && !SPECIES.some(s => s.id === centry(p).concept)) { const c = curOf(p);
      putCast(p, Object.assign({}, centry(p), { concept: c.concept, iv: c.iv, hex: p.hex })); save(); }
    const on = t === "focus"; if (on !== !!p.focus) writeFocus(p, on);
    say(t === "untracked" && !actByKey.has(p.key) ? "Untracked: it leaves this list once it is no longer active." : "", false);
    paintFocus(p); paintVis(p); }
  function writeFocus(p, on) { p.focus = on; const t = table.find(e => e && e.key === p.key); if (t) t.focus = on;
    writeProject("setProjectFocus", p, { focus: on, name: p.name || "", dir: p.dir || "" }, err => { p.focus = !on; if (t) t.focus = !on; paintFocus(p); paintList();
      say((on ? "Could not add focus: " : "Could not remove focus: ") + err, true); }); }
  /** An edit to an Untracked row would be lost, so it makes the row Focus first, and says so. */
  function promote(p) { if (!p || tracking(p) !== "untracked") return; setTracking(p, "focus");
    say("Now a focus project, so this choice is kept.", false); }
  function curOf(p) { const s = sel, i = projects.indexOf(p); if (i < 0) return cur(); sel = i; const c = cur(); sel = s; return c; }
  let clrT = 0;
  const clrOk = new Map(), clrOkN = new Map(), clrLast = new Map();   // key -> the last colour the host confirmed; key -> id of the newest write
  // `input` fires continuously while the native picker is dragged: the preview follows every event, the write
  // is debounced to the colour he settles on (as the short-name field and the sliders do).
  $("clr").oninput = () => { const p = projects[sel]; if (!p) return; clrEdit = { key: p.key, t: performance.now() }; promote(p);
    const hex = String($("clr").value || "").toUpperCase(); if (!/^#[0-9A-F]{6}$/.test(hex)) return;
    if (!clrOk.has(p.key)) clrOk.set(p.key, p.hex);   // the colour before this edit: what a failed write restores
    if (hex === (p.hex || "").toUpperCase()) return;
    p.hex = hex; const t = table.find(e => e && e.key === p.key); if (t) t.hex = hex;
    $("clrHex").textContent = hex; rowKey = varKey = ""; render();   // the hue path: hero, stills, label preview
    clearTimeout(clrT); clrT = setTimeout(() => { $("clrRow").classList.add("busy");
      // the cast mirrors the project's hex, and the stage prefers the cast's: move it too, or a stale cast
      // entry would keep painting the old colour after the table changed.
      castHex(p, hex);
      // only the NEWEST write may revert, and only to the last colour the host confirmed: an older write's answer
      // arriving mid-drag must never pull the picker back (a stale echo)
      const id = "w" + (writeN + 1);   // the id writeProject is about to use: the no-bridge path calls back before it returns
      clrLast.set(p.key, id);
      writeProject("setProjectColour", p, { hex: hex }, err => { if (clrLast.get(p.key) !== id) return;
        const was = clrOk.get(p.key); p.hex = was; if (t) t.hex = was; castHex(p, was); clrEdit = { key: null, t: 0 };
        rowKey = varKey = ""; $("clrRow").classList.remove("busy"); render(); paintColour(p, true); say("Colour not saved: " + err, true); },
        () => { const n = +id.slice(1); if (n > (clrOkN.get(p.key) || 0)) { clrOkN.set(p.key, n); clrOk.set(p.key, hex); } });
      setTimeout(() => $("clrRow").classList.remove("busy"), 1200); }, 220); };
  function castHex(p, hex) { const e = centry(p); if (!e || !Object.keys(e).length) return;   // nothing saved yet: nothing to correct
    if (/^#[0-9A-F]{6}$/i.test(hex || "")) { putCast(p, Object.assign({}, e, { hex: hex })); save(); } }
  [...$("focusSeg").children].forEach(b => b.onclick = () => { const p = projects[sel]; if (!p) return; setTracking(p, F2T[b.dataset.f]); paintList(); });

  // ---------- on screen: Show / Hide / Hide @ Work (owner, 2026-11-04; ProjectCert "is an outside project") ----------
  // cast.projects[key].visibility "hide" | "hide_at_work" (absent = show); the stage drops the project's sprites and
  // ghost, for hide_at_work while Augur reads vpn.on_site true (at work).
  const VIS = ["show", "hide", "hide_at_work"];
  function paintVis(p) { const v = VIS.includes(centry(p).visibility) ? centry(p).visibility : "show";
    [...$("visSeg").children].forEach(b => b.setAttribute("aria-checked", b.dataset.v === v ? "true" : "false")); }
  [...$("visSeg").children].forEach(b => b.onclick = () => { const p = projects[sel]; if (!p) return; const c = cur();
    const e = Object.assign({ concept: c.concept, iv: c.iv, hex: p.hex }, centry(p));
    if (b.dataset.v === "show") delete e.visibility; else e.visibility = b.dataset.v; putCast(p, e); save(); paintVis(p); paintFocus(p); paintList(); });
  let rowKey = "", varKey = "";
  function paintSpecies() { const c = cur(), hue = hexHue(c.hex), row = $("species");
    if (!row.children.length) SPECIES.forEach(s => { const cell = el("div", "cell", `<div class="tile"></div><div class="lab">${s.name}</div>`);
      cell.title = s.name; cell.onclick = () => { const c = cur(), kept = centry(projects[sel]);
        choose({ concept: s.id, iv: kept.concept === s.id ? kept.iv : c.iv }); }; row.appendChild(cell); });
    [...row.children].forEach((cell, i) => cell.classList.toggle("on", SPECIES[i].id === c.concept));
    const k = hue + "|" + c.iv; if (k === rowKey) return; rowKey = k;
    [...row.children].forEach((cell, i) => tile(cell, SPECIES[i].id, c.iv, hue, "species")); }
  function paintVariantLabels() { const c = cur();
    [...$("variants").children].forEach((cell, i) => { cell.querySelector(".lab").textContent = nameOf(c.concept, i);
      cell.title = nameOf(c.concept, i); }); }
  function paintVariants() { const c = cur(), hue = hexHue(c.hex), row = $("variants");
    if (!row.children.length) for (let i = 0; i < 8; i++) { const cell = el("div", "cell", `<div class="tile"></div><div class="lab"></div>`);
      cell.onclick = () => choose({ iv: i }); row.appendChild(cell); }
    [...row.children].forEach((cell, i) => cell.classList.toggle("on", i === c.iv)); paintVariantLabels();
    const k = c.concept + "|" + hue; if (k === varKey) return; varKey = k;
    [...row.children].forEach((cell, i) => tile(cell, c.concept, i, hue, "variant")); }
  function render() { paintList(); paintInfo(); paintHero(); paintVariants(); paintSpecies(); }

  $("surprise").onclick = () => { const c = cur(); let s, v;
    do { s = SPECIES[Math.floor(Math.random() * SPECIES.length)].id; v = Math.floor(Math.random() * 8); } while (s === c.concept && v === c.iv);
    if (!waypoint) browse.hex = "#" + hsl2hex(Math.floor(Math.random() * 360));
    choose({ concept: s, iv: v }); };
  function hsl2hex(h) { const l = 0.6, a = 0.9 * Math.min(l, 1 - l), f = n => { const k = (n + h / 30) % 12;
      return Math.round(255 * (l - a * Math.max(-1, Math.min(k - 3, 9 - k, 1)))).toString(16).padStart(2, "0"); };
    return f(0) + f(8) + f(4); }
  addEventListener("keydown", e => { if (!waypoint || !projects.length) return;
    if (e.key === "ArrowDown" || e.key === "ArrowUp") { sel = (sel + (e.key === "ArrowDown" ? 1 : projects.length - 1)) % projects.length; render(); e.preventDefault(); } });

  // ---------- behaviours tab ----------
  const GROUPS = [
    ["Space & windows", ["avoidFocus", "avoidDockMenu", "fullScreenFade", "edgeWhileTyping", "perch", "followOwnWindow"]],
    ["You", ["avoidCursor", "curiosity", "hoverName", "sleepWhenAway"]],
    ["Signals", ["needsApproach", "nudgeLongWait", "vpnHuddle", "strainAgitation", "quietUnderStrain"]],
    ["Social", ["play", "greetNewcomers", "celebrateDone", "arrivals"]],
  ];
  const FALLBACK = {
    avoidFocus: ["Keep clear of the focused window", "Drift out from over the window you are working in."],
    avoidDockMenu: ["Keep clear of Dock and menu bar", "Extra margin around the Dock, menu-bar icons and banners."],
    fullScreenFade: ["Fade away in full screen", "Fade out on a full-screen Space; return when you leave it."],
    edgeWhileTyping: ["Step aside while you type", "Ease to the margins while you type or scroll."],
    perch: ["Perch on window edges", "Idle sprites sometimes rest on the top edge of a background window."],
    followOwnWindow: ["Stay near their own terminal", "Each sprite hangs near its own session's window."],
    avoidCursor: ["Keep clear of the cursor", "Gently move away from the pointer."],
    curiosity: ["Show curiosity", "Drift a little toward a resting cursor, then lose interest."],
    hoverName: ["Show name on hover", "Slow down and show the project name when the cursor is near."],
    sleepWhenAway: ["Sleep when you are away", "Slow right down after minutes of no input; wake softly when you return."],
    needsApproach: ["Come closer when you are needed", "A sprite that needs you edges toward your focus."],
    nudgeLongWait: ["Edge closer on long waits", "After 10 minutes waiting, creep a little nearer, never touching."],
    vpnHuddle: ["Huddle when the VPN drops", "Sprites gather together when the connection is lost."],
    strainAgitation: ["Show machine strain", "Sprites grow restless when the machine is under load."],
    quietUnderStrain: ["Go quiet under strain", "Skip the finished-work flourish while the machine is under heavy strain."],
    play: ["Play occasionally", "Idle sprites sometimes interact with one another."],
    greetNewcomers: ["Greet newcomers", "A nearby sprite drifts briefly toward a new session."],
    celebrateDone: ["Celebrate finished work", "One small flourish when a session completes."],
    arrivals: ["Arrivals and departures", "Sprites fade in and out as sessions start and end."],
  };
  function behMeta(k) { let m = null; try { const t = window.SPRITES_BEHAVIORS || (window.parent && window.parent.SPRITES_BEHAVIORS);
      m = t && (Array.isArray(t) ? t.find(x => x && x.key === k) : t[k]); } catch (e) {}
    const f = FALLBACK[k] || [k, ""];
    if (Array.isArray(m)) return { label: m[0] || f[0], desc: m[1] || f[1] };
    if (m && typeof m === "object") return { label: m.label || m.name || m.title || f[0], desc: m.desc || m.description || m.blurb || f[1] };
    return { label: f[0], desc: f[1] }; }
  let beh = {}, demoOn = false, behExtra = {};   // behExtra: keys this window does not edit (dimIcons, ...) ride through saves
  const post = msg => { try { if (window.webkit && webkit.messageHandlers && webkit.messageHandlers.settings) { webkit.messageHandlers.settings.postMessage(msg); return true; } } catch (e) { console.warn("save failed", e); } return false; };
  function flashSaved() { $("saved").classList.add("on"); clearTimeout(savedT); savedT = setTimeout(() => $("saved").classList.remove("on"), 1400); }
  function setSw(b, on) { b.setAttribute("aria-checked", on ? "true" : "false"); }
  function saveBeh() { const all = Object.assign({}, behExtra); GROUPS.forEach(g => g[1].forEach(k => { all[k] = beh[k] !== false; })); all.labelStyle = labelStyle;
    all.backdrop = bd.id; all.backdropSpeed = Object.assign({}, bd.speeds); all.aether = aeOut();
    if (!post({ saveBehaviors: all })) localStorage.setItem("sprites.behaviors", JSON.stringify(all)); flashSaved(); }
  function paintBeh() { const grid = $("behGrid"); grid.innerHTML = "";
    const cols = [el("div", "behCol"), el("div", "behCol")];
    GROUPS.forEach((g, gi) => { const col = cols[gi === 0 || gi === 3 ? 0 : 1]; col.appendChild(el("div", "cap", esc(g[0])));
      g[1].forEach(k => { const m = behMeta(k), row = el("div", "brow"), b = el("button", "sw");
        row.innerHTML = `<div class="rt"><div class="rl">${esc(m.label)}</div><div class="rd">${esc(m.desc)}</div></div>`;
        b.setAttribute("role", "switch"); b.setAttribute("aria-label", m.label); b.dataset.key = k; setSw(b, beh[k] !== false);
        const flip = () => { beh[k] = !(beh[k] !== false); setSw(b, beh[k]); saveBeh(); };
        b.onclick = e => { e.stopPropagation(); flip(); }; row.onclick = flip; row.appendChild(b); col.appendChild(row); }); });
    cols.forEach(c => grid.appendChild(c)); setSw($("demoSw"), demoOn); }
  $("demoSw").onclick = () => { demoOn = !demoOn; setSw($("demoSw"), demoOn);
    if (!post({ setDemo: demoOn })) localStorage.setItem("sprites.demo", JSON.stringify(demoOn)); flashSaved(); };
  // ---------- show/hide and meeting mode (host state; the menu and the hotkey change it too) ----------
  let vis = { hidden: false, meeting: false };
  function setVisibility(o) { o = o || {}; if (typeof o.hidden === "boolean") vis.hidden = o.hidden; if (typeof o.meeting === "boolean") vis.meeting = o.meeting;
    setSw($("showSw"), !vis.hidden); setSw($("meetSw"), vis.meeting); }
  function initVis(o) { setVisibility({ hidden: !!o.hidden, meeting: !!o.meeting });
    $("meetKey").textContent = typeof o.hotkey === "string" ? o.hotkey : "⌃⌥⌘S";
    $("meetDesc").textContent = o.hotkeyOK === false ? "Hide everything at once for a shared screen. The hotkey is unavailable (another app holds it): use this switch or the menu."
      : "Hide everything at once for a shared screen; press the hotkey again to bring them back. Mirrors the menu item."; }
  $("showSw").onclick = () => { vis.hidden = !vis.hidden; setSw($("showSw"), !vis.hidden);
    if (!post({ setHidden: vis.hidden })) localStorage.setItem("sprites.hidden", JSON.stringify(vis.hidden)); flashSaved(); };
  $("meetSw").onclick = () => { vis.meeting = !vis.meeting; setSw($("meetSw"), vis.meeting);
    if (!post({ setMeeting: vis.meeting })) localStorage.setItem("sprites.meeting", JSON.stringify(vis.meeting)); flashSaved(); };
  function showTab(t) { const b = t === "behaviours", l = t === "labels", k = t === "backdrop", a = t === "aether";
    $("aeView").classList.toggle("hidden", !a); if (a) { document.documentElement.style.setProperty("--hue", "#7fd6a8"); paintAether(); }
    $("speciesView").classList.toggle("hidden", b || l || k || a); $("behView").classList.toggle("hidden", !b); $("labView").classList.toggle("hidden", !l);
    $("bdView").classList.toggle("hidden", !k);
    document.querySelectorAll("#tabs button").forEach(x => x.classList.toggle("on", x.dataset.tab === t));
    $("sub").classList.toggle("hidden", b || l || k || a); labAnim(l); bdAnim(k);
    if (b) { paintBeh(); document.documentElement.style.setProperty("--hue", BROWSE_HEX); } else if (l) paintLabels();
    else if (k) { document.documentElement.style.setProperty("--hue", "#6f8fd8"); paintBackdrops(); } else render(); }
  document.querySelectorAll("#tabs button").forEach(x => x.onclick = () => showTab(x.dataset.tab));
  // ---------- overall size (owner: "a Sprite Size bar at the top to set the scale for the Sprites overall") ----------
  let size = 1, sizeT = null;
  function paintSize() { $("size").value = size; $("sizeVal").textContent = Math.round(size * 100) + "%";
    document.querySelectorAll("iframe").forEach(f => { try { const u = new URL(f.src); if (u.searchParams.get("size") !== String(size)) { u.searchParams.set("size", size); f.dataset.sizeSrc = u.href; } } catch (e) {} }); }
  $("size").oninput = () => { size = +$("size").value; $("sizeVal").textContent = Math.round(size * 100) + "%";
    clearTimeout(sizeT); sizeT = setTimeout(() => { if (!post({ setSize: size })) localStorage.setItem("sprites.size", JSON.stringify(size)); flashSaved(); }, 250); };
  function initBeh(o) { if (typeof o.size === "number" && o.size > 0) size = o.size; paintSize(); beh = o.behaviors && typeof o.behaviors === "object" ? Object.assign({}, o.behaviors) : {};
    labelStyle = LSTYLES.includes(beh.labelStyle) ? beh.labelStyle : LDEFAULT; delete beh.labelStyle;
    bd.id = typeof beh.backdrop === "string" ? beh.backdrop : "none"; bd.speeds = beh.backdropSpeed && typeof beh.backdropSpeed === "object" ? Object.assign({}, beh.backdropSpeed) : {};
    delete beh.backdrop; delete beh.backdropSpeed;
    ae = aeRead(beh.aether); delete beh.aether;
    const known = new Set(GROUPS.flatMap(g => g[1])); behExtra = {}; Object.keys(beh).forEach(k => { if (!known.has(k)) { behExtra[k] = beh[k]; delete beh[k]; } }); paintDim();
    initVis(o); demoOn = !!o.demo; if ($("behView").classList.contains("hidden")) setSw($("demoSw"), demoOn); else paintBeh(); }

  // ---------- the row set: focus entries + every active sprite + hidden (owner, 2026-11-08) ----------
  let plain = false, actByKey = new Map();
  const rowCache = new Map();   // key -> row object, kept across recomposes (writes and reverts hold the object)
  function setActive(snap) { let a = []; try { a = SP && snap ? SP.active(typeof snap === "string" ? JSON.parse(snap) : snap) : []; } catch (e) { a = []; }
    actByKey = new Map(a.map(x => [x.key, x])); }
  const WHITE_HEX = "#B8C0CC";
  function rowFor(key) { if (rowCache.has(key)) return rowCache.get(key);
    const t = table.find(e => e && e.key === key), a = actByKey.get(key), c = (cast.projects && cast.projects[key]) || {};
    const p = t ? Object.assign({}, t) : { key, name: a ? a.name : c.name || key, alias: null, dir: null, focus: false };
    p.key = key; p.label = p.alias || p.name;
    // a project with no colour of its own: the cast's, else the stage's seeded hue (grey for an unmanaged session)
    if (!/^#[0-9a-f]{6}$/i.test(p.hex || "")) p.hex = /^#[0-9a-f]{6}$/i.test(c.hex || "") ? c.hex.toUpperCase()
      : a && a.white && !p.focus ? WHITE_HEX : "#" + hsl2hex((hashStr(key) >>> 7) % 360).toUpperCase();
    rowCache.set(key, p); return p; }
  /** The rows, by SpritesProjects.settingsRows (node-tested), over the table as this window has edited it. */
  function compose() { const eff = table.map(e => (e && e.key && rowCache.get(e.key)) || e);
    for (const p of rowCache.values()) if (!table.some(e => e && e.key === p.key)) eff.push(p);
    return SP.settingsRows(eff, cast, [...actByKey.values()], hasWaypoint).map(r => rowFor(r.key)); }
  /** The host's snapshot changed: re-derive the rows, keep the selection on the same project. */
  function setSnapshot(snap) { trace("setSnapshot"); if (plain || !$("projects")) return; setActive(snap);
    const was = projects[sel] && projects[sel].key, next = compose();
    if (!next.length && !projects.length) return;
    projects = next; const i = projects.findIndex(p => p.key === was); const moved = i < 0;
    sel = moved ? 0 : i; if (!waypoint && projects.length) { init(Object.assign({}, lastInit, { snapshot: snap })); return; }
    if (moved) render(); else { paintList(); paintFocus(projects[sel]); } }
  let lastInit = {};

  // ---------- entry ----------
  function init(o) { o = o || {}; if (o.debug) { dbg = true; armTrace(); } trace("init", { projects: Array.isArray(o.projects) ? o.projects.length : o.projects });
    lastInit = o;cast = o.cast && typeof o.cast === "object" ? o.cast : { projects: {} };
    if (!cast.projects || typeof cast.projects !== "object") cast.projects = {};
    setActive(o.snapshot);
    waypoint = o.waypoint !== false && Array.isArray(o.projects) && (o.projects.length > 0 || actByKey.size > 0);
    // Real detection, by the host (app/macos/Config.swift waypointCLIPath: an EXECUTABLE CLI and a
    // launches.md that parses into launch rows, not a path that merely exists). Absent: the colour and
    // focus writes go to the host's local settings file instead, and the same `nowp=1` switch still
    // drives whether this window shows the project list at all.
    hasWaypoint = o.hasWaypoint !== false && o.waypoint !== false;
    pending.clear(); clrOk.clear(); clrOkN.clear(); clrLast.clear(); say("", false);
    const rows = waypoint ? o.projects.filter(p => p && p.name && /^#[0-9a-f]{6}$/i.test(p.hex || "")) : [];
    // a full table (entries carry focus) lists its focus rows; a plain [{name, hex}] list is all rows, keyed by name
    const isTable = waypoint && o.projects.some(p => p && "focus" in p);
    table = waypoint ? o.projects.filter(p => p && p.name).map(p => Object.assign({}, p)) : [];
    // a full table's row with key null (a launch dir that is no registry project, e.g. MandrakeVisualize) can match no
    // session: Augur keys sessions by registry project, so its cast would be read by nothing (R2-SPEC #3). Not listed.
    // Without Waypoint nothing is focused until he says so, so a focus-only filter would leave the list
    // empty and there would be nothing to colour or focus: every keyed row is listed instead.
    plain = !isTable; rowCache.clear(); listSig = "";
    setActive(o.snapshot);
    if (plain) { projects = rows.map(p => Object.assign({}, p, { key: p.key || p.alias || p.name, label: p.alias || p.name })); table = projects; }
    else projects = compose();
    if (!projects.length) waypoint = false;
    sel = 0; rowKey = varKey = heroKey = "";
    $("projects").classList.toggle("hidden", !waypoint); $("sideCap").classList.toggle("hidden", !waypoint);
    $("nowp").classList.toggle("hidden", waypoint); document.body.classList.toggle("browse", !waypoint);
    if (!waypoint) $("hiddenBox").classList.add("hidden");
    $("sub").textContent = waypoint ? "Choose a species for each project; Focus keeps it" : "Species gallery";
    $("surprise").lastChild.textContent = waypoint ? "Surprise me" : "Show me another";
    initBeh(o); if (!$("behView").classList.contains("hidden") || !$("labView").classList.contains("hidden") || !$("bdView").classList.contains("hidden")) showTab("species"); render(); }

  // ---------- name label tab (owner, 2026-11-01 06:40: "ALL of those label options switchable ... Constellation as the default") ----------
  // Each tile: the selected project's creature (a still frame, as the species row uses) with its label looping in, holding and
  // out. Only the selected and the hovered tile animate (CPU); the others hold a finished frame.
  const LSTYLES = window.SpritesLabels ? SpritesLabels.STYLES : ["filament", "orbit", "constellation", "tag", "whisper"];
  const LDEFAULT = window.SpritesLabels ? SpritesLabels.DEFAULT : "constellation";
  let labelStyle = LDEFAULT, labHover = null, labRaf = 0, labT0 = performance.now();
  const LTW = 220, LTH = 165;
  function labSubject() { if (waypoint && projects[sel]) { const c = cur(); return { name: c.name, short: shortOf(projects[sel]), hex: c.hex, concept: c.concept, iv: c.iv }; }
    return { name: "Lodestar", short: "Lodestar", hex: "#FFCA42", concept: browse.concept, iv: browse.iv }; }
  let labImg = null, labKey = "";
  function paintLabels() { const row = $("labels"), who = labSubject();
    $("labWho").textContent = who.short + (waypoint ? "" : " (example)");
    $("labNote").textContent = "The label takes the project's own colour. A soft dark halo appears only over bright windows; over the wallpaper and terminals the light stays pure.";
    document.documentElement.style.setProperty("--hue", who.hex);
    if (!row.children.length) LSTYLES.forEach(st => { const cell = el("div", "cell", `<div class="tile"><canvas></canvas>${st === LDEFAULT ? '<span class="def">default</span>' : ""}</div><div class="lab"></div>`);
      cell.dataset.style = st; cell.querySelector(".lab").textContent = SpritesLabels.TITLES[st];
      const cv = cell.querySelector("canvas"), dpr = devicePixelRatio || 1; cv.width = LTW * dpr; cv.height = LTH * dpr;
      cell.onclick = () => { labelStyle = st; saveBeh(); paintLabels(); };
      cell.onmouseenter = () => { labHover = st; }; cell.onmouseleave = () => { if (labHover === st) labHover = null; };
      row.appendChild(cell); });
    [...row.children].forEach(c => c.classList.toggle("on", c.dataset.style === labelStyle));
    const k = [who.concept, who.iv, who.hex].join("|");
    if (k !== labKey) { labKey = k; labImg = null; still(who.concept, who.iv, hexHue(who.hex), "species").then(img => { if (labKey === k) { labImg = img; labFrame(true); } }); }
    labFrame(true); }
  function labFrame(all) { const row = $("labels"), who = labSubject(), now = (performance.now() - labT0) / 1000;
    [...row.children].forEach(cell => { const st = cell.dataset.style, animate = st === labelStyle || st === labHover;
      if (!all && !animate) return;
      const cv = cell.querySelector("canvas"), x = cv.getContext("2d"), dpr = cv.width / LTW;
      x.setTransform(1, 0, 0, 1, 0, 0); x.fillStyle = "#07080d"; x.fillRect(0, 0, cv.width, cv.height); x.setTransform(dpr, 0, 0, dpr, 0, 0);
      const cx = LTW / 2, cy = LTH * 0.44, r = LTH * 0.2;   // the species still (165x110 stage) drawn at tile width: the creature spans ~40% of the height
      if (labImg) { const s = LTW / labImg.width; x.globalCompositeOperation = "screen";
        x.drawImage(labImg, cx - labImg.width * s / 2, cy - labImg.height * s / 2 - LTH * 0.06, labImg.width * s, labImg.height * s); x.globalCompositeOperation = "source-over"; }
      // loop: in, hold, out, rest
      let ph = "hold", p = 1;
      if (animate) { const L = { filament: [0.9, 0.35], orbit: [0.8, 0.3], constellation: [1.2, 0.7], tag: [0.7, 0.3], whisper: [0.9, 0.6] }[st] || [1, 0.5];
        const cyc = L[0] + 2.4 + L[1] + 0.6, u = now % cyc;
        if (u < L[0]) { ph = "in"; p = u / L[0]; } else if (u < L[0] + 2.4) { ph = "hold"; } else if (u < L[0] + 2.4 + L[1]) { ph = "out"; p = (u - L[0] - 2.4) / L[1]; } else return; }
      SpritesLabels.draw(x, { style: st, name: who.name, short: who.short, hex: who.hex, x: cx, y: cy, r, scale: 1, t: now, phase: ph, p, ground: "dark", W: LTW, H: LTH }); }); }
  function labAnim(on) { cancelAnimationFrame(labRaf); if (!on) return; let last = 0;
    const tick = ts => { if ($("labView").classList.contains("hidden") || document.hidden) return; if (ts - last > 40) { last = ts; labFrame(false); } labRaf = requestAnimationFrame(tick); };
    labRaf = requestAnimationFrame(tick); }

  // ---------- backdrop tab (owner, 2026-11-01 08:05: "Implement them all as choices, with adjustable speed settings") ----------
  // One tile per backdrop plus None (the default: nothing changes until he picks). Tiles are drawn through ONE shared
  // WebGL context (backdrops/bd.js, the same shader the host runs). Only the selected and the hovered tile animate, at
  // 4 fps; the preview runs time PREVIEW_X faster than real so motion is visible in a glance (said on the tab).
  const bd = { id: "none", speeds: {}, cat: null, ready: null, hover: null, raf: 0, t0: performance.now(), boost: false };
  const PREVIEW_X = 60;
  function bdSpeed(m) { const v = bd.speeds[m.id]; return typeof v === "number" ? Math.max(0, Math.min(m.max, v)) : m.speed; }
  function bdLoad() { if (!bd.ready) bd.ready = (window.SpritesBackdrops ? SpritesBackdrops.load("backdrops/") : Promise.reject(new Error("no bd.js")))
      .then(r => { bd.cat = r.catalog.backdrops; return bd.cat; }).catch(e => { $("bdNote").textContent = "Previews unavailable: " + e.message; bd.cat = []; return []; });
    return bd.ready; }
  function paintBackdrops() { bdLoad().then(cat => { const row = $("backdrops");
    if (!row.children.length) { [{ id: "none", name: "None", desc: "Your current wallpaper, untouched." }].concat(cat).forEach(m => {
        const cell = el("div", "cell", `<div class="tile"><canvas></canvas>${m.id === "none" ? '<span class="none">your wallpaper</span><span class="def">default</span>' : ""}</div><div class="lab"></div>`);
        cell.dataset.id = m.id; cell.querySelector(".lab").innerHTML = esc(m.name) + "<small>" + esc(m.desc) + "</small>";
        const cv = cell.querySelector("canvas"); cv.width = 432; cv.height = 279;
        cell.onclick = () => { bd.id = m.id; saveBeh(); paintBackdrops(); };
        cell.onmouseenter = () => { bd.hover = m.id; }; cell.onmouseleave = () => { if (bd.hover === m.id) bd.hover = null; };
        row.appendChild(cell); }); }
    [...row.children].forEach(c => c.classList.toggle("on", c.dataset.id === bd.id));
    const m = cat.find(x => x.id === bd.id), sr = $("bdSpeedRow"), sl = $("bdSpeed");
    sr.classList.toggle("off", !m || !(m.max > 0));
    if (m && m.max > 0) { sl.max = m.max; sl.value = bdSpeed(m); $("bdSpeedVal").textContent = bdSpeed(m) === 0 ? "frozen" : bdSpeed(m).toFixed(2).replace(/0$/, "") + "x"; }
    else $("bdSpeedVal").textContent = m ? "still" : "-";
    $("bdNote").textContent = (m ? (bdSpeed(m) === 0 || !(m.max > 0) ? "Still: set as your wallpaper on every Space. " : "Moving: drawn by Sprites at " + m.fps + " frames a second, paused when covered or locked. ") : "Nothing is changed. ") +
      "Previews run " + PREVIEW_X + "x faster than real so you can see the motion; the real thing is slower than you can watch.";
    bdFrame(true); }); }
  function bdFrame(all) { if (!bd.cat || !window.SpritesBackdrops || !SpritesBackdrops.catalog) return; const now = (performance.now() - bd.t0) / 1000;
    [...$("backdrops").children].forEach(cell => { const id = cell.dataset.id; if (id === "none") return; const m = bd.cat.find(x => x.id === id); if (!m) return;
      const live = (id === bd.id || id === bd.hover) && m.max > 0; if (!all && !live) return;
      const sp = id === bd.id ? bdSpeed(m) : m.speed, t = 2300 + (live ? now * PREVIEW_X * sp : 0);
      SpritesBackdrops.draw(cell.querySelector("canvas"), m.n, t, { full: [1728, 1117], boost: bd.boost }); }); }
  function bdAnim(on) { cancelAnimationFrame(bd.raf); if (!on) return; let last = 0;
    const tick = ts => { if ($("bdView").classList.contains("hidden") || document.hidden) return; if (ts - last > 250) { last = ts; bdFrame(false); } bd.raf = requestAnimationFrame(tick); };
    bd.raf = requestAnimationFrame(tick); }
  let bdT = null;
  $("bdSpeed").oninput = () => { const m = bd.cat && bd.cat.find(x => x.id === bd.id); if (!m) return; const v = +$("bdSpeed").value;
    bd.speeds[m.id] = Math.abs(v - m.speed) < 0.06 ? m.speed : v; $("bdSpeedVal").textContent = bd.speeds[m.id] === 0 ? "frozen" : bd.speeds[m.id].toFixed(2).replace(/0$/, "") + "x";
    clearTimeout(bdT); bdT = setTimeout(() => { saveBeh(); paintBackdrops(); }, 300); };
  // ---------- aether tab (behaviors.aether; parsed by AetherSettings.from in app/macos/Aether.swift; drawn by AetherHost.swift while enabled) ----------
  const AE_DEFAULT = { enabled: false, motion: "settle-typing", boundary: "thermal", temperature: 27.5, density: 100, particleSize: 2.5, fieldStrength: 0.5, stirring: 0.7, cooling: 45, minTemperature: 1.5, temperatureVariation: 0.85, attraction: 1, attractionRange: 2, repulsion: 0.5, repulsionRange: 2, chainForming: 0.5, colour: "green", brightness: 2, drift: "off", driftPeriod: 30, edgeTemperature: 1, driftCoupling: 1, fronts: 0.4, needleMemory: 0.5, knots: 0.4, dew: 0.3, speciesWakes: 0.5, handedness: 0.4, wakeReader: 0.3 };
  const AE_KNOBS = [   // [key, label, min, max, step, format]: sliders; the choice knobs follow below
    ["temperature", "Temperature", 0, 40, 0.5, v => v <= 0.5 ? "frozen" : v < 5 ? "cool" : v < 12 ? "mild" : v < 22 ? "warm" : "hot"],
    ["density", "Density", 100, 1600, 10, v => v < 250 ? "sparse" : v > 1000 ? "dense" : "medium"],
    ["stirring", "Sprite stirring", 0, 2, 0.1, v => v === 0 ? "off" : v < 0.65 ? "subtle" : v < 1.0 ? "moderate" : "strong"],
    ["cooling", "Cooling (drag)", 5, 120, 1, v => "settles in ~" + Math.round(v) + " s" + (v < 15 ? " (quick)" : v > 60 ? " (glides)" : "")],
    ["minTemperature", "Minimum temperature", 0, 10, 0.5, v => v === 0 ? "may freeze" : v.toFixed(1) + " pt/s drift"],
    ["temperatureVariation", "Temperature variation", 0, 1, 0.05, v => v === 0 ? "uniform" : v === 1 ? "free" : v < 0.5 ? "evens out" : "hot and cold spots persist"],
    ["attraction", "Attraction strength", 0, 3, 0.1, v => v === 0 ? "off" : v < 0.8 ? "faint" : v < 1.8 ? "sticky" : "clumps"],
    ["attractionRange", "Attraction range", 1.5, 3, 0.1, v => v.toFixed(1) + " particle widths"],
    ["repulsion", "Repulsion strength", 0, 2, 0.1, v => v === 0 ? "off" : v < 0.8 ? "gentle" : "spreads clumps"],
    ["repulsionRange", "Repulsion range", 1, 4, 0.5, v => Math.round(v * 48) + " pt"],
    ["chainForming", "Chain forming", 0, 1, 0.05, v => v === 0 ? "droplets" : v < 0.6 ? "some chains" : "needles"],
    ["particleSize", "Particle size", 0.5, 6, 0.1, v => v.toFixed(1) + " pt"],
    ["fieldStrength", "Field strength", 0, 2, 0.1, v => v === 0 ? "off" : v < 0.7 ? "subtle" : v < 1.3 ? "vivid" : "strong"],
    ["brightness", "Brightness", 1, 3, 1, v => ["dim", "normal", "bright"][v - 1]],
    ["driftPeriod", "Drift period", 10, 120, 5, v => "~" + Math.round(v) + " min swells"],
    // owner card 2026-11-08 18:30 PST: attraction and repulsion drift together, so the desktop never clumps
    ["driftCoupling", "Drift coupling", 0, 1, 0.05, v => v === 0 ? "independent" : v < 0.7 ? "partly coupled" : "attraction and repulsion together"],
    // owner card 2026-11-08 18:30 PST: drift varies by region, the borders wander over about an hour (needs Drift on)
    ["fronts", "Weather fronts", 0, 1, 0.05, v => v === 0 ? "one universe everywhere" : v < 0.5 ? "gentle regions" : "strong regions"],
    // owner card 2026-11-08 18:30 PST: broken needles leave their direction behind; a knot sometimes forms where two wakes cross
    ["needleMemory", "Needle memory", 0, 1, 0.05, v => v === 0 ? "forgets at once" : v < 0.7 ? "remembers for seconds" : "remembers for minutes"],
    ["knots", "Knots where wakes cross", 0, 1, 0.05, v => v === 0 ? "off" : v < 0.5 ? "sometimes" : v < 1 ? "often" : "every crossing"],
    // owner card 2026-11-08 18:30 PST: dots bead along a window edge still for ~10 min (behaviors.json dewAfter, seconds), shake off on a move
    ["dew", "Window dew", 0, 1, 0.05, v => v === 0 ? "off" : v < 0.5 ? "a few beads" : "beaded edges"],
    // owner card 2026-11-08 18:30 PST: each species shapes its wake (Siphonophores comb, the Mothership a bow); never work or status
    ["speciesWakes", "Species wakes", 0, 1, 0.05, v => v === 0 ? "all round" : v < 0.7 ? "a hint of each species" : "each species its own shape"],
    // owner card 2026-11-08 18:30 PST: each project curls its wake one way (from its key), so two wakes braid or cancel
    ["handedness", "Handedness by project", 0, 1, 0.05, v => v === 0 ? "off" : v < 0.6 ? "a gentle curl" : "a strong curl"],
    // owner card 2026-11-08 18:30 PST: an idle sprite sometimes follows another's leftover current a little (rare, small)
    ["wakeReader", "Wake reader", 0, 1, 0.05, v => v === 0 ? "off" : v < 0.5 ? "now and then" : "often"]];
  const AE_CHOICES = [
    ["motion", "Motion", [["living", "Always living"], ["settle-typing", "Living, settles while typing"], ["stir-settle", "Stirs, then settles"]]],
    ["boundary", "Boundary", [["thermal", "Thermal walls"], ["reflect", "Reflect"], ["reservoir", "Reservoir"]]],
    ["drift", "Drift", [["off", "Off"], ["gentle", "Gentle"], ["wild", "Wild"]]]];
  // Drifting constants (owner, 2026-11-08 ~5 PM): the host sends the drifted values about once a second while drift is on;
  // each drifting slider shows its current value faintly beside it. "Hold this universe" writes them into the sliders.
  const AE_DRIFTING = ["attraction", "attractionRange", "repulsion", "repulsionRange", "chainForming", "cooling", "temperatureVariation", "edgeTemperature", "fieldStrength", "stirring"];
  let aeDrift = null;
  const aeFmt = v => Math.abs(v) >= 10 ? v.toFixed(0) : v.toFixed(2);
  function setAetherDrift(d) { trace("setAetherDrift"); aeDrift = d && typeof d === "object" ? d : null; paintAeDrift(); }
  function paintAeDrift() { const on = !!(aeDrift && ae.drift !== "off" || aeDrift && aeDrift.amplitude > 0);
    document.querySelectorAll("#aeGrid .aeDrift[data-key]").forEach(sp => { const v = aeDrift && aeDrift[sp.dataset.key];
      sp.textContent = on && typeof v === "number" ? "now " + aeFmt(v) : ""; });
    const h = $("aeHold"); if (h) h.disabled = !on; }
  // Colour: a real picker (any "#rrggbb") plus the three phosphor presets as quick swatches. The hex of each preset is
  // only what the picker shows; the saved value stays the preset's name, so the host keeps its exact phosphor tone.
  const AE_SWATCHES = [["green", "#47ff73"], ["amber", "#ffad2e"], ["white", "#d1e0eb"]];
  const aeHex = c => { const s = AE_SWATCHES.find(x => x[0] === c); return s ? s[1] : c; };
  let ae = Object.assign({}, AE_DEFAULT), aeExtra = {}, aeT = null, aeClr = null;
  function aeRead(o) { o = o && typeof o === "object" ? o : {}; aeExtra = {}; const r = Object.assign({}, AE_DEFAULT);
    Object.keys(o).forEach(k => { if (!(k in AE_DEFAULT)) aeExtra[k] = o[k]; });   // chains, collisionSize, ...: carried through
    if (o.enabled === true) r.enabled = true;
    AE_CHOICES.forEach(c => { if (c[2].some(x => x[0] === o[c[0]])) r[c[0]] = o[c[0]]; });
    if (typeof o.colour === "string" && (AE_SWATCHES.some(x => x[0] === o.colour) || /^#[0-9a-f]{6}$/i.test(o.colour))) r.colour = o.colour.toLowerCase();
    AE_KNOBS.forEach(k => { if (typeof o[k[0]] === "number" && isFinite(o[k[0]])) r[k[0]] = Math.min(k[3], Math.max(k[2], o[k[0]])); });
    if (typeof o.edgeTemperature === "number" && isFinite(o.edgeTemperature)) r.edgeTemperature = Math.min(2, Math.max(0.5, o.edgeTemperature));
    return r; }
  function aeOut() { return Object.assign({}, aeExtra, ae); }
  function aeSave() { clearTimeout(aeT); aeT = setTimeout(saveBeh, 250); }
  function paintAether() { trace("paintAether", ae.colour); setSw($("aeSw"), ae.enabled); const g = $("aeGrid");
    // Every row is rebuilt except the colour row, which is built ONCE and never leaves the grid: NSColorPanel is bound
    // to the input it opened on, so replacing or detaching it (or pushing a value into it) mid-drag cut the panel loose
    // or moved it back (owner, 2026-11-08). Its value is written only when it differs and he is not editing it.
    [...g.children].forEach(r => { if (!aeClr || r !== aeClr.row) r.remove(); });
    let after = false; const put = r => aeClr && !after && aeClr.row.parentNode === g ? g.insertBefore(r, aeClr.row) : g.appendChild(r);
    AE_CHOICES.forEach(c => { const row = el("div", "aeRow"); row.appendChild(el("div", "aeLab", c[1])); const seg = el("div", "aeSeg");
      c[2].forEach(o => { const b = el("button", "aeOpt" + (ae[c[0]] === o[0] ? " on" : ""), o[1]); b.onclick = () => { ae[c[0]] = o[0]; paintAether(); aeSave(); }; seg.appendChild(b); });
      row.appendChild(seg); put(row); });
    after = true;
    if (!aeClr || aeClr.row.parentNode !== g) { const row = el("div", "aeRow"); row.appendChild(el("div", "aeLab", "Colour")); const seg = el("div", "aeSeg");
      AE_SWATCHES.forEach(s => { const b = el("button", "aeOpt aeSwatch", s[0][0].toUpperCase() + s[0].slice(1)); b.dataset.c = s[0];
        b.style.setProperty("--sw", s[1]); b.onclick = () => { ae.colour = s[0]; aeClr.t = 0; paintAether(); aeSave(); }; seg.appendChild(b); });
      const w = el("label", "swatch"), i = document.createElement("input"); i.type = "color"; i.setAttribute("aria-label", "Aether colour");
      const h = el("span", "hx"); w.appendChild(i); w.appendChild(h); seg.appendChild(w); row.appendChild(seg); g.appendChild(row);
      aeClr = { row, seg, inp: i, hx: h, t: 0 };
      i.oninput = () => { aeClr.t = performance.now(); ae.colour = i.value.toLowerCase(); h.textContent = ae.colour;
        seg.querySelectorAll(".aeSwatch").forEach(b => b.classList.remove("on")); aeSave(); }; }
    { const hexNow = aeHex(ae.colour), busy = performance.now() - aeClr.t < EDIT_HOLD || document.activeElement === aeClr.inp;
      if (!busy) { if (aeClr.inp.value !== hexNow) aeClr.inp.value = hexNow; aeClr.hx.textContent = hexNow;
        aeClr.seg.querySelectorAll(".aeSwatch").forEach(b => b.classList.toggle("on", b.dataset.c === ae.colour)); } }
    AE_KNOBS.forEach(k => { const row = el("div", "aeRow"); row.appendChild(el("div", "aeLab", k[1]));
      const inp = document.createElement("input"); inp.type = "range"; inp.min = k[2]; inp.max = k[3]; inp.step = k[4]; inp.value = ae[k[0]];
      const val = el("span", "aeVal", k[5](ae[k[0]]));
      inp.oninput = () => { ae[k[0]] = +inp.value; val.textContent = k[5](ae[k[0]]); aeSave(); };
      row.appendChild(inp); row.appendChild(val);
      const d = el("span", "aeDrift"); if (AE_DRIFTING.includes(k[0])) d.dataset.key = k[0]; row.appendChild(d);   // every row: the sliders line up
      g.appendChild(row); });
    { const row = el("div", "aeRow"); row.appendChild(el("div", "aeLab", "This universe"));
      row.appendChild(el("div", "aeHint", "Edge temperature " + aeFmt(ae.edgeTemperature) + "x."));
      const d = el("span", "aeDrift"); d.dataset.key = "edgeTemperature"; row.appendChild(d);
      const b = el("button", "aeOpt", "Hold this universe"); b.id = "aeHold"; b.title = "Freeze the drifting values into the sliders and turn drift off";
      b.onclick = () => { if (!aeDrift) return; AE_DRIFTING.forEach(k => { if (typeof aeDrift[k] === "number") ae[k] = aeDrift[k]; });
        ae.drift = "off"; aeDrift = null; paintAether(); saveBeh(); };
      row.appendChild(b); g.appendChild(row); }
    paintAeDrift(); }
  $("aeSw").onclick = () => { ae.enabled = !ae.enabled; setSw($("aeSw"), ae.enabled); aeSave(); };
  window.SpritesAether = { defaults: AE_DEFAULT, read: aeRead };
  // ---------- dim desktop icons (host DimLayer, behaviors.dimIcons 0-80, missing = 45, 0 = off) ----------
  const DIM_DEFAULT = 45; let dimT = null;
  function dimNow() { const v = behExtra.dimIcons; return typeof v === "number" ? Math.max(0, Math.min(80, Math.round(v))) : DIM_DEFAULT; }
  function paintDim() { const v = dimNow(); $("dimIcons").value = v; $("dimVal").textContent = v === 0 ? "off" : v + "%"; }
  $("dimIcons").oninput = () => { const v = +$("dimIcons").value; behExtra.dimIcons = v; $("dimVal").textContent = v === 0 ? "off" : v + "%";
    clearTimeout(dimT); dimT = setTimeout(saveBeh, 200); };
  $("bdBoost").onchange = () => { bd.boost = $("bdBoost").checked; bdFrame(true); };
  window.SpritesSettings = { init, setAetherDrift, get cast() { return cast; }, get labelStyle() { return labelStyle; }, showTab, setVisibility, writeResult, setSnapshot, get projects() { return projects; } };
  const q = new URLSearchParams(location.search);
  if (q.get("demo") === "1") { let saved = null, sb = null, sd = false; const rd = k => { try { return JSON.parse(localStorage.getItem(k) || "null"); } catch (e) { return null; } };
    saved = rd("sprites.cast"); sb = rd("sprites.behaviors"); sd = !!rd("sprites.demo"); const sz = rd("sprites.size"), vh = !!rd("sprites.hidden"), vm = !!rd("sprites.meeting");
    const base = { cast: saved, behaviors: sb, demo: sd, size: sz, hidden: vh, meeting: vm };
    const nowp = q.get("nowp");
    // nowp=1: nothing to list at all -> the browse-only gallery (unchanged).
    // nowp=local: no Waypoint but projects exist -> the colour and focus controls write to the local store,
    // which is the shape the host hands over when its waypointCLIPath() finds no CLI or no launch rows.
    // local=true reads the browser's own store, as the host reads its local settings file.
    const demoTable = (local, dflt) => DEMO.map(([name, hex]) => { const k = SP ? SP.keyOf(name) : name.toLowerCase();
      const e = local ? (localProjects()[k] || {}) : {};
      return { key: k, name: name, dir: "/x/" + name, alias: name, hex: e.hex || hex,
        focus: typeof e.focus === "boolean" ? e.focus : dflt }; });
    if (nowp === "1") init(Object.assign({ waypoint: false }, base));
    else if (nowp === "local") init(Object.assign({ projects: demoTable(true, false), hasWaypoint: false }, base));
    else init(Object.assign({ projects: demoTable(false, true) }, base)); }
})();
