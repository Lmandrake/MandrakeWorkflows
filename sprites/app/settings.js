/* Sprites Settings window. Host contract:
 *   SpritesSettings.init({cast, projects:[{key, name, alias, hex, focus}]})   the host's project table (app/projects.js,
 *     SpritesProjects.build); one row per focus entry. cast.projects is keyed by project_key (review R1 #2), the key the
 *     stage and the ghost launch use; a row shows its launch alias. Entries without a key ({name, hex}) key by name.
 *   SpritesSettings.init({cast, waypoint:false})            no Waypoint: browse only
 *   SpritesSettings.init({..., behaviors:{key:bool}, demo:bool, size:number})  Behaviours tab; missing keys are ON; size 0.5..2 posts {setSize}.
 *   Behaviour saves: settings.postMessage({saveBehaviors:{...}}) and ({setDemo:bool}); browser: localStorage.
 *   Show/hide and meeting mode (review R1 #13): init({..., hidden:bool, meeting:bool, hotkey:"⌃⌥⌘S", hotkeyOK:bool}); the
 *   switches post {setHidden:bool} and {setMeeting:bool} (host state, never saved in behaviours);
 *   SpritesSettings.setVisibility({hidden, meeting}) mirrors a change made from the menu or the hotkey, posting nothing.
 *   Name label: behaviors.labelStyle ("filament"|"orbit"|"constellation"|"tag"|"whisper", default constellation) rides in the
 *   same saveBehaviors object. Backdrop tab: behaviors.backdrop ("none"|"b01".."b12", default none) and behaviors.backdropSpeed
 *   ({id: multiplier}) ride in it too (app/macos/Backdrop.swift applies them). Unknown keys (dimIcons, ...) are carried through. Short name: cast.projects[key].short (blank = automatic: SpritesProjects.shortTable over the whole table, as the stage does).
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
  ];
  // Fallback only: the real names are read from each piece's window.VARIANT_NAMES.
  const NAMES = {
    c1_choir: ["Halo", "Twin Deck", "Gyre", "Crown", "Lantern", "Pinwheel", "Comet", "Spindle"],
    c2_siphon: ["Moon", "Lantern", "Saucer", "Box", "Lyre", "Spire", "Pagoda", "Corolla"],
    c3_sigils: ["Lantern", "Trident", "Halo", "Star", "Invader", "Ascent", "Lattice", "Eye"],
    c4_kaleido: ["Lotus", "Trefoil", "Pentagram", "Snowflake", "Quatrefoil", "Spirograph", "Dandelion", "Honeycomb"],
    c5_fireflies: ["Galaxy", "Halo", "Infinity", "Coil", "Lissajous", "Trefoil", "Comet", "Braid"],
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
  const url = (c, iv, hue, [w, h], live) => `${PROTO}${c}.html?tl=g_cast&w=${w}&h=${h}&chrome=0&bg=0&dim=0&hover=0` +
    `&hue=${hue}&iv=${iv}` + (live ? "&autostart=1&loop=1" : "&autostart=0");

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
    loader.src = url(j.c, j.iv, j.hue, st, false); }
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
      f.src = url(t._args[0], t._args[1], t._args[2], STAGE[t._args[3]], true); t.appendChild(f); t._live = f;
      if (t._still) setTimeout(() => { if (t._live === f && t._still) t._still.style.opacity = "0"; }, 350); }
    else if (!on && t._live) { t._live.src = "about:blank"; t._live.remove(); t._live = null; if (t._still) t._still.style.opacity = "1"; } }

  // ---------- hero: always live, cross-faded ----------
  let heroKey = "";
  function paintHero(force) { const c = cur(), hue = hexHue(c.hex), k = [c.concept, c.iv, hue].join("|");
    if (k === heroKey && !force) return; heroKey = k; const slot = $("heroSlot"), old = [...slot.children];
    if (document.hidden) { old.forEach(o => o.remove()); return; }
    const f = el("iframe", "loading"); f.tabIndex = -1; f.title = "preview";
    f.onload = () => { f.classList.remove("loading"); setTimeout(() => old.forEach(o => { o.src = "about:blank"; o.remove(); }), 650); };
    f.src = url(c.concept, c.iv, hue, STAGE.hero, true); slot.appendChild(f); }
  document.addEventListener("visibilitychange", () => { if (document.hidden) { $("heroSlot").innerHTML = "";
      document.querySelectorAll(".tile").forEach(t => live(t, false)); } else paintHero(true); });

  // ---------- model ----------
  function defaults(i) { return { concept: SPECIES[i % 5].id, iv: (i * 3) % 8 }; }
  function cur() { if (!waypoint) return browse; const p = projects[sel]; if (!p) return browse;
    const c = centry(p); const d = defaults(sel);
    return { concept: SPECIES.some(s => s.id === c.concept) ? c.concept : d.concept,
      iv: Number.isInteger(c.iv) ? c.iv : d.iv, hex: p.hex, name: p.label }; }
  function choose(patch) {
    if (!waypoint) { Object.assign(browse, patch); return render(); }
    const p = projects[sel], c = cur(); const prev = centry(p);
    putCast(p, Object.assign({}, prev, { concept: patch.concept || c.concept, iv: patch.iv != null ? patch.iv : c.iv, hex: p.hex }));
    save(); render(); }
  let savedT = 0;
  function save() { const msg = { saveCast: JSON.parse(JSON.stringify(cast)) };
    try { if (window.webkit && webkit.messageHandlers && webkit.messageHandlers.settings) webkit.messageHandlers.settings.postMessage(msg);
      else localStorage.setItem("sprites.cast", JSON.stringify(cast)); } catch (e) { console.warn("save failed", e); return; }
    $("saved").classList.add("on"); clearTimeout(savedT); savedT = setTimeout(() => $("saved").classList.remove("on"), 1400); }

  // ---------- painting ----------
  function paintList() { const ul = $("projects"); if (!waypoint) return;
    if (ul.children.length !== projects.length) { ul.innerHTML = "";
      projects.forEach((p, i) => { const li = el("li"); li.style.setProperty("--c", p.hex);
        li.innerHTML = `<span class="dot"></span><span class="nm" title="${esc(p.name)}">${esc(p.label)}</span><span class="sp"></span>`;
        li.onclick = () => { sel = i; render(); }; ul.appendChild(li); }); }
    [...ul.children].forEach((li, i) => { li.classList.toggle("on", i === sel);
      const s = sel; sel = i; const c = cur(); sel = s; li.querySelector(".sp").textContent = nameOf(c.concept, c.iv); }); }
  function paintInfo() { const c = cur(), sp = SPECIES.find(s => s.id === c.concept);
    $("pname").textContent = waypoint ? c.name : "Random each session";
    $("sname").textContent = sp.name; $("vname").textContent = nameOf(c.concept, c.iv);
    $("blurb").textContent = sp.blurb; $("formOf").textContent = "of " + sp.name;
    document.documentElement.style.setProperty("--hue", c.hex); paintShort(); }
  // ---------- short name (owner: "shortnames for the long-named critters") ----------
  // the same table and rule as the stage's hover label (app/projects.js shortTable), without this window's overrides
  function autoShort(p) { try { return (SP ? SP.shortTable(table, null) : {})[p.key] || p.label; } catch (e) { return p.label; } }
  function shortOf(p) { const c = centry(p); return c.short ? String(c.short) : autoShort(p); }
  function paintShort() { const row = $("shortRow"), inp = $("short"); row.classList.toggle("hidden", !waypoint); if (!waypoint) return;
    const p = projects[sel]; if (!p) return; if (document.activeElement !== inp) inp.value = centry(p).short || "";
    inp.placeholder = autoShort(p); }
  let shortT = 0;
  $("short").oninput = () => { const p = projects[sel]; if (!p) return; const v = $("short").value.trim().slice(0, 12), c = cur();
    const e = Object.assign({ concept: c.concept, iv: c.iv, hex: p.hex }, centry(p));
    if (v) e.short = v; else delete e.short; putCast(p, e);
    clearTimeout(shortT); shortT = setTimeout(save, 350); };
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
    do { s = SPECIES[Math.floor(Math.random() * 5)].id; v = Math.floor(Math.random() * 8); } while (s === c.concept && v === c.iv);
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
    all.backdrop = bd.id; all.backdropSpeed = Object.assign({}, bd.speeds);
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
  function showTab(t) { const b = t === "behaviours", l = t === "labels", k = t === "backdrop";
    $("speciesView").classList.toggle("hidden", b || l || k); $("behView").classList.toggle("hidden", !b); $("labView").classList.toggle("hidden", !l);
    $("bdView").classList.toggle("hidden", !k);
    document.querySelectorAll("#tabs button").forEach(x => x.classList.toggle("on", x.dataset.tab === t));
    $("sub").classList.toggle("hidden", b || l || k); labAnim(l); bdAnim(k);
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
    const known = new Set(GROUPS.flatMap(g => g[1])); behExtra = {}; Object.keys(beh).forEach(k => { if (!known.has(k)) { behExtra[k] = beh[k]; delete beh[k]; } }); paintDim();
    initVis(o); demoOn = !!o.demo; if ($("behView").classList.contains("hidden")) setSw($("demoSw"), demoOn); else paintBeh(); }

  // ---------- entry ----------
  function init(o) { o = o || {}; cast = o.cast && typeof o.cast === "object" ? o.cast : { projects: {} };
    if (!cast.projects || typeof cast.projects !== "object") cast.projects = {};
    waypoint = o.waypoint !== false && Array.isArray(o.projects) && o.projects.length > 0;
    const rows = waypoint ? o.projects.filter(p => p && p.name && /^#[0-9a-f]{6}$/i.test(p.hex || "")) : [];
    // a full table (entries carry focus) lists its focus rows; a plain [{name, hex}] list is all rows, keyed by name
    const isTable = rows.some(p => "focus" in p);
    table = waypoint ? o.projects.filter(p => p && p.name).map(p => Object.assign({}, p)) : [];
    // a full table's row with key null (a launch dir that is no registry project, e.g. MandrakeVisualize) can match no
    // session: Augur keys sessions by registry project, so its cast would be read by nothing (R2-SPEC #3). Not listed.
    projects = (isTable ? rows.filter(p => p.focus && p.key) : rows).map(p => Object.assign({}, p, { key: p.key || p.alias || p.name, label: p.alias || p.name }));
    if (!isTable) table = projects;
    if (!projects.length) waypoint = false;
    sel = 0; rowKey = varKey = heroKey = "";
    $("projects").classList.toggle("hidden", !waypoint); $("sideCap").classList.toggle("hidden", !waypoint);
    $("nowp").classList.toggle("hidden", waypoint); document.body.classList.toggle("browse", !waypoint);
    $("sub").textContent = waypoint ? "Choose a species for each focus project" : "Species gallery";
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
  // ---------- dim desktop icons (host DimLayer, behaviors.dimIcons 0-80, missing = 45, 0 = off) ----------
  const DIM_DEFAULT = 45; let dimT = null;
  function dimNow() { const v = behExtra.dimIcons; return typeof v === "number" ? Math.max(0, Math.min(80, Math.round(v))) : DIM_DEFAULT; }
  function paintDim() { const v = dimNow(); $("dimIcons").value = v; $("dimVal").textContent = v === 0 ? "off" : v + "%"; }
  $("dimIcons").oninput = () => { const v = +$("dimIcons").value; behExtra.dimIcons = v; $("dimVal").textContent = v === 0 ? "off" : v + "%";
    clearTimeout(dimT); dimT = setTimeout(saveBeh, 200); };
  $("bdBoost").onchange = () => { bd.boost = $("bdBoost").checked; bdFrame(true); };
  window.SpritesSettings = { init, get cast() { return cast; }, get labelStyle() { return labelStyle; }, showTab, setVisibility };
  const q = new URLSearchParams(location.search);
  if (q.get("demo") === "1") { let saved = null, sb = null, sd = false; const rd = k => { try { return JSON.parse(localStorage.getItem(k) || "null"); } catch (e) { return null; } };
    saved = rd("sprites.cast"); sb = rd("sprites.behaviors"); sd = !!rd("sprites.demo"); const sz = rd("sprites.size"), vh = !!rd("sprites.hidden"), vm = !!rd("sprites.meeting");
    init(q.get("nowp") === "1" ? { cast: saved, waypoint: false, behaviors: sb, demo: sd, size: sz, hidden: vh, meeting: vm } : { cast: saved, projects: DEMO.map(([name, hex]) => ({ name, hex })), behaviors: sb, demo: sd, size: sz, hidden: vh, meeting: vm }); }
})();
