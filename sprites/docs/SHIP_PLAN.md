# Sprites v1: shipping the design (2026-10-31)

Owner: "It's good enough, let's ship the design! ... Let's do this!"

## Architecture decision (v1)
Native macOS shell + the existing HTML pieces. Porting five concepts to SpriteKit/Metal would re-do the art the
owner just approved; v1 hosts the approved pieces in a transparent WKWebView and measures the cost. If idle CPU
is too high, the port is v2, concept by concept, against these pieces as the reference.

- `app/stage.html`: full-screen transparent stage. One transparent layer (iframe) per concept that has sprites;
  each layer gets only its own sessions. Layers share the focus rect, so all avoid the focused window.
- `app/macos/` (Swift, AppKit + WebKit): borderless non-activating NSPanel, level .floating (was .screenSaver; R2_MACOS #1),
  collectionBehavior [.canJoinAllSpaces, .stationary, .fullScreenAuxiliary, .ignoresCycle]. Click-through
  except over a sprite (hit rects reported by the stage). Feeds the stage: the state file + the focused
  window's rect. Hover = slow + name (in JS). Click = activate the session's terminal window (switches Space).
  Menu-bar item: hide/show, quit. Hotkey to hide (meeting mode). LaunchAgent via `make install`.
- Frame budget: 30 fps while anything moves, 10 fps when calm, 0 when hidden or the screen is locked;
  `requestAnimationFrame` throttled by the host. **Superseded (owner, 2026-11-01):** one constant 24 fps whenever anything is
  visible ("Movement and terrain" rule 7).

## Data contract (the owner's sampler will write this; nothing here gathers data)
File: `$SPRITES_STATE`, default `~/agent-storage/sprites/live/state.json`, rewritten atomically, any cadence.
```json
{ "schema": 1, "t": 1793500000.0,
  "sessions": [ { "id": "43901", "pid": 43901, "project": "SidePulse", "hue": 350,
                  "concept": "c5_fireflies", "iv": 3,
                  "cpu": 0.8, "mem": 1.2, "procs": 4, "state": "working|idle|needs",
                  "rx": 0.5, "tx": 0.1 } ],
  "m":   { "level": 0.0, "thermal": 0, "mempress": 0 },
  "net": { "mbps": 0.6, "vpn": "up|down", "loss": 0, "strain": 0.0 } }
```
Units as in the scenarios: cpu cores, mem GB, rx/tx Mbit/s, level 0 light..3 danger, strain 0..1.
`concept`/`iv`/`hue` are optional: when absent the cast (`config/cast.json`, project -> concept + variant,
seeded from Waypoint colours) decides. Until the sampler lands, `tools/demo_feed.py` writes this file from
the gallery scenarios so the app can be run and judged.

## Settings (owner, 2026-10-31)
"There should be a beautiful settings menu that can be accessed from the little menu at the top right of the
Desktop. It allows you to preview the different species of Sprites you can select for each of the Waypoint
focus projects, if Waypoint is installed. If it isn't, then it just randomly assigns them to your Claude
sessions for the duration of that session."
- Menu-bar status item (top right) -> "Sprites Settings…" opens a dark, glowing settings window (WKWebView,
  same runtime, so previews are the real sprites).
- With Waypoint (`~/dev/Waypoint/launches.md` readable): one row per **focus** project (Focus = yes), its
  Waypoint colour, a species picker (5) with live previews side by side, then a variant strip (8 live
  thumbnails); click to choose. Saved to `~/agent-storage/sprites/config/cast.json`; the stage reloads it live.
- Without Waypoint, or a session whose project is not in the cast: a random species + variant + hue chosen
  at session start (seeded by session id) and kept for that session only, never saved.
  **As built (pending the owner's word, R1-SPEC S9):** an uncast managed project is seeded by its project_key, so all its
  sessions share one form, today and tomorrow; only white (unmanaged) sprites are seeded by session id. Reversible in
  app/stage.html castFor (seedKey).
- Also in the window: show/hide, meeting-mode hotkey, frame-rate cap. (**Superseded:** no frame-rate cap; the rate is a
  constant 24 fps, "Movement and terrain" rule 7.)

## Demo mode (owner, 2026-10-31)
"It should also have a demo mode where you can see a random assortment of the critters floating around,
avoiding focus windows and cursors, etc."
- Menu-bar toggle "Demo Mode" (remembered). On: the stage invents a random assortment of 6-8 sprites (white and ghost
  included; app/stage.html demoState, 7-8 at any moment) across
  all 5 species, cycling through every behaviour (work, idle, needs-you, strain, bandwidth + jam, VPN drop,
  play, arrivals and departures). The real focused window and cursor still apply.
- The app starts in demo mode when no state file exists, so a fresh install shows something.
- Cursor: gentle repulsion (weaker than the focus window); within hover range sprites slow and show the name.

## Behaviours (owner, 2026-10-31) — every one a switch in Settings, default ON
Owner: "Selectable behavior like 'move away from cursor' 'move out of focus windows' 'interact occasionally'
'show curiosity' 'approach focus when agent needs you'... All the different behaviors you included should be
switchable and default to ON... They should never be intrusive and focus-stealing, just available."
Hard rule: no behaviour may take focus, move the cursor, block a click or make a sound.

Existing: avoidFocus, avoidCursor, play, needsApproach, vpnHuddle, strainAgitation, arrivals, hoverName.
New (owner chose all but "flock by project" and "day/night"; 11 redefined by him):
| key | behaviour |
|---|---|
| curiosity | a sprite drifts a little toward a resting cursor, then loses interest; shy while the cursor moves |
| edgeWhileTyping | while you type or scroll, sprites ease to the margins and dim a touch; return when you stop |
| sleepWhenAway | after minutes of no input, a slow dim sleep; on return a soft wake that shows what changed |
| perch | idle sprites sometimes rest on the top edge of a background window |
| followOwnWindow | each sprite tends to hang near its own session's terminal window |
| celebrateDone | working -> done: one small loop/flare, at most one celebration every few seconds |
| greetNewcomers | one nearby sprite drifts briefly toward a newly arrived session (brief, plainly not data) |
| avoidDockMenu | extra margin: never over the Dock, menu-bar icons or notification banners |
| fullScreenFade | owner: "full screen mode causes them to fade away in that space" — fade out on a full-screen Space |
| quietUnderStrain | under heavy machine strain, cut own frame rate and particles (red glow stays). **Frame-rate half superseded** (constant 24 fps). As built: skips the finished-work flourish only; the particle cut is unbuilt (R2-SPEC #2), the Settings text says what is built |
| nudgeLongWait | needs-you for > 10 min: edge a little closer to the focused window each minute, hard cap, never touching it |

Hover comes to the cursor (owner, 2026-11-01 ~07:10: "It's hard to keep my cursor on some of the Sprites to see their name
form. If I hover over them, they should go toward my cursor, not away from it."). Part of hoverName. Hovered = the cursor
within 1.3 x the creature's reported extent, with 300 ms grace after it leaves. The hovered creature stops avoiding the
cursor and eases toward it (exponential, tau 0.42 s, no overshoot, no orbit), then holds centred under it while the label
forms. avoidCursor still applies to every creature that is not hovered. Terrain still holds: it may follow over a non-focus
window but never onto the focused window (it stops at the edge). Unhovered, it eases back (tau 0.9 s) and resumes
wandering. Constant fps as always. Built as a display offset in the runtime (visitors_runtime.js `pull`), no piece changes.
Test: ~/agent-storage/sprites/live/verify/hover_follow_test.py (cursor parked: within 6 px at 1.5 s and 4 px at 5 s; never
inside the focus after a drag onto it).

## Sprite Size (owner, 2026-10-31)
"Settings should also have a Sprite Size bar at the top to set the scale for the Sprites overall."
Slider in the settings header, 50%..200%, default 100%; host stores it and calls `SpritesStage.setScale(s)`.
Owner, 2026-11-01 04:45: "The sprites you're playing with now are at the largest end of what should be permitted. I was
thinking they would typically be significantly smaller." So the slider keeps 50%..200% but the live base is halved
(`LIVE_BASE = 0.5` in prototype/visitors_runtime.js): 200% = the size he saw, 100% = half, 50% = a quarter. Running-light
pips keep a 1.8 px floor; hit radii keep an 18 px floor; cursor avoidance scales with size.

## From Augur (owner rulings relayed 2026-10-31; Augur DESIGN.md §11, commit 4225632)
- **Superseded by docs/BURNING_CONCEPTS.md ruling 5** (Lodestar follows the ghost rule: present while it burns, fades when
  nothing does). Was: One sprite is ALWAYS Lodestar: Lodestar plus all non-project work (private-store, Hestia, unrouted mail,
  unmapped burning codes). Present even with no Lodestar session open (then it rests, no session load).
- Claude Code sessions in projects Lodestar does not manage (`managed: false`) are WHITE sprites of a
  different shape/type, with no action, bearing or burning data.
- Key sprites by Augur's opaque `id` (pid@start). Absent fields are absent: draw calm, never as zero.
- Lost-VPN behaviour only when vpn is down AND not on site (else the flock huddles all day on site).
- The adapter in app/stage.html maps Augur's snapshot; nothing of Augur is built yet.
Open design (for the owner): the white "unmanaged" sprite's form, and how the always-present Lodestar sprite
looks when it has no session.

## One input shape (owner, 2026-10-31 23:50)
"Remove their previous readers ... to avoid duplicate code, functionality, and CPU load." Sprites reads Augur's snapshot
only (augur/schema/snapshot.schema.json); the SHIP_PLAN `schema: 1` state.json above is retired. `tools/demo_feed.py`
writes the Augur shape for demos and tests (`$SPRITES_STATE`). Rulings on Burning, Lodestar and white sprites:
docs/BURNING_CONCEPTS.md. Build status: docs/LIVE_MODE.md.

## Movement and terrain (owner, 2026-11-01) — consolidated; supersedes the scattered notes above
Owner, verbatim: "they shouldn't hurl themselves into tight little spaces and hang half-off-screen bouncing up and down
like that. Stay where they fit and have space." / "They should only wander where they can travel to, not get 'pulled'
to other clear areas." / "If a user moves a window such that they no longer fit where they are, they should 'go around'
the focus window even if they don't fit, following a path around it to get to where they do." / "If there isn't enough
space on the screen because the focus window is huge, they should simply [not] show on that Space. Moving Spaces should
cause them to instantly re-choose where they wish to go, and they start to go there via a valid path. They should try
to stay over the background (most preferred), then over non-focus windows (semi-preferred), then over focus window
(least preferred, move off immediately to more preferred terrain)." / "Their fps shouldn't change, just their velocity."
Rules as built (prototype/visitors_runtime.js `nav`, used by every piece; stage.html):
1. Terrain cost grid (24 px cells, rebuilt only when windows/focus change): background 1, other windows 3, focused
   window 60, outside the visible frame = wall.
2. FIT: a creature rests only where its whole extent (body + glow + lights + margin) clears the frame edges and the focused
   window. No slivers, never half off-screen.
3. REACHABLE: paths are min-cost (Dijkstra) and the focused window is one-way (a creature may leave it, never enter or
   cross it). Wander targets are moved to the nearest fitting, reachable, cheapest-terrain cell; a creature on the far
   side of the focus stays on its side. A straight move that already fits is left as the piece drew it.
4. EVICTION: when a window covers a creature it travels the planned path around the focus at its normal speed; never a
   teleport.
5. NO ROOM: if nothing fits anywhere (huge focused window), the creature fades out on that Space and fades in at a
   fitting spot when room appears. Space change = new windows = immediate re-plan.
6. NO JITTER: targets are fixed per plan (re-planned when the layout changes or the wanted target moves > 4 cells).
7. CONSTANT FPS: one frame rate (24) whenever anything is visible; hover and sleep slow simulated time, not frames.
8. VPN huddle: ONE beacon for the whole desktop (runtime draws it once), placed in open space on the flock's side of the
   focus; every species huddles to it.
9. Ghosts: edge spots no window covers (setWindows).
Tests: ~/agent-storage/sprites/live/verify/move_test.py (evict, split by focus, sliver/huge focus, jitter, terrain), huddle_test.py.

## VPN lost, on site (owner, 2026-11-01 05:30)
On site the VPN is off but the machine is on the site network, so either the network must be the site's
or the VPN must be on, or both. Built in app/stage.html adaptState + vpnDebounce: lost = Augur
machine.vpn.state "down" AND on_site is not true (absent on_site counts as off site: we cannot confirm). Lost must hold 20 s
before the flock huddles (walking around the site flaps on_site); recovery (VPN up or arriving on the on-site network) is immediate and fires
the reconnect bloom in every piece. Test: ~/agent-storage/sprites/live/verify/vpn_truth.py (truth table, flap, debounce).
Refinement (owner idea, 2026-11-01 05:35, "truer to the source"): when Augur's `machine.api` is present (an agent made an API
call recently), it decides: lost = state "failing" AND error_kind "network"; rate-limit, server and other errors never
huddle; "ok" is not lost even with the VPN down. Absent `machine.api` = the VPN/on-site rule above. Same 20 s debounce;
failing -> ok fires the bloom. Built against the coordinator's field description; re-check names when the schema lands.

**Superseded by the owner's ruling, 2026-11-01 ~08:15:** "we need to check VPN, on-site network, AND we need to monitor for API
cannot be reached... they are interrelated and each informative." All three are combined (app/stage.html adaptState ->
`net.linkRaw`, `linkDebounce`):
| machine.api | machine.vpn | on the on-site network (vpn.on_site) | shown |
|---|---|---|---|
| failing, error_kind network | any (or absent) | any | **LOST**: huddle + searchlight + red beacon |
| any (ok, absent, or failing for another reason) | down | false or absent | **LOST**: huddle + searchlight + red beacon (owner ruling 2026-11-03, "panic on VPN down"; was AT RISK, a faint beacon, until a hibernation wake with no busy agent showed it had no API evidence to escalate on) |
| ok, absent, or failing for another reason | up, or down with on_site true | any | **OK** |
| absent | absent | - | nothing (all unknown is never assumed ok or lost) |
Entering LOST holds 20 s first (AT RISK is no longer produced by the adapter; the debounce and layers still carry it); recovery is immediate; LOST -> OK fires the reconnect
bloom. Hovering the beacon names the signal(s) down in the chosen label style ("API unreachable", "VPN down", "not on Lab
WiFi"). Test: ~/agent-storage/sprites/live/verify/vpn_truth.py (all 42 combinations, flap, both debounces, live risk/lost
beacon + hover text). Built against the Augur schema as it stands (machine.api latency fix in progress there).

## Click (owner, 2026-11-01 05:47)
"When I click on the Sprites, it should take me to the related Claude window and bring it to focus. If they're a ghost, it
should open one." Live creature: app/macos/Activate.swift `activateSession` selects the iTerm2 window, tab and session whose
tty is the session pid's tty, and activates it (Terminal likewise). Ghost: `openGhost` opens a new iTerm2 window running
`launch <Name>` (Waypoint alias matched case-insensitively; Lodestar ghost -> `launch Lodestar`), else `cd ~/dev/<project> &&
claude`; one window per project per 3 s (double-click debounce). Ghosts are now in the hit list.

## Desktop icon dimming (owner, 2026-11-01)
Design: ~/dev/Machinist/knowledge/desktop-icon-dimming.md option 7. Built in app/macos/Stage.swift `DimLayer`,
driven from App.swift: one borderless black window per screen, `ignoresMouseEvents`, `canJoinAllSpaces, stationary,
ignoresCycle`, at `CGWindowLevelForKey(.desktopIconWindow) + 1`. Measured with CGWindowListCopyWindowInfo on macOS 26.7.1:
wallpaper -2147483624, Finder's desktop-icon window -2147483603 (= the desktopIcon key), dim layer -2147483602, widgets
-2147483601, app windows 0, Sprites stage 1000 (screenSaver). Test 2026-11-01: dim window seen at -2147483602, mouse-transparent, CPU 0.51 s vs 0.49 s per 30 s at 45 % vs 0 % (static layer costs nothing). So it shades icons, labels and wallpaper only; app windows and
the creatures stay at full brightness. Windows are reused across didChangeScreenParameters (no rebuild flash); 0 = ordered out.
Setting "Dim desktop icons", 0-80 %, default 45.
PENDING (Settings UI owner): write `"dimIcons": <integer percent 0-80>` into behaviors.json
(~/agent-storage/sprites/config/behaviors.json) through the existing `saveBehaviors` message, alongside the boolean switches;
missing key = 45, 0 = off, values clamp to 0-80, a boolean is ignored (= 45). The host re-reads it within 2 s (FileWatch) or
at once on saveBehaviors. Note `behaviorOn` treats non-Bool keys as absent, so the number does not disturb the switches.
Test override: `Sprites -dimIcons N` (argument domain, not persisted).

## Warning hold time (owner, 2026-11-01 13:27)
Any adverse time counts toward the 20 s hold: after LOST, if the API recovers while the VPN is still down off site, AT RISK shows at once, with no false "ok" gap. (Settles SPRITES_REVIEW_R1 #15.)

## Contract, as read by the stage (package E, 2026-11-01; CONTRACT_REVIEW_R1 C2, C5)
- app/stage.html adaptState refuses (draws nothing) any snapshot whose `schema` is not "augur.snapshot", whose `version` major
  is not 1, whose `valid_until` is not a number, or that is `off`. A block with no `valid_until` is absent. Minor versions
  (1.1, ...) are accepted.
- Satellites = `tasks.background` (1.1), absent = none drawn. Never `tasks.total` (it counts foreground shells) and never
  `load.procs` (every OS process).
- The host may send the screen's visible frame (`SpritesStage.setVisible({x,y,w,h})`, NSScreen.visibleFrame in stage px);
  it bounds the terrain of every species, and avoidDockMenu adds 8 px inside it. Without it, the old fixed TOP 44 / BOT 86.
  Notification banners: out of scope (they come and go; no reserve).
- Stage panel level: `.floating` (3), package C (SPRITES_REVIEW_R2_MACOS #1; it was `.screenSaver`, 1000). Above app
  windows, below the Dock (20), menu bar (24), modal panels (8), menus (101) and system alerts; `.fullScreenAuxiliary`
  kept. The host also refuses a click while a window not ours above layer 0 (a menu, sheet, banner, prompt) holds the
  cursor, and sends `setVisible` per screen at build and on every didChangeScreenParameters (R1-SPEC S4).

## Coordinator decisions while the owner was AFK (2026-11-01 ~17:10; owner may reverse)
- Uncast projects take their random form seeded by `project_key`, so a project keeps the same form across sessions and reboots, matching the owner's "like any new project not yet selected" ruling. (R1-SPEC S9)
- The `~/dev/MandrakeWorkflows/visualize` folder maps to `mandrakeworkflows`: MandrakeVisualize was folded in on 2026-10-28 and its registry row is retired. (R2-SPEC #3)
- The particle half of quietUnderStrain, and the dims of edgeWhileTyping and sleepWhenAway, are deferred. The Settings text describes what is built.

## VPN down off site is LOST (owner, 2026-11-03)
After a hibernation wake at home with the VPN off, Augur correctly reported `vpn.state: down, on_site: false`, but no agent was busy so `machine.api` was absent and the table gave only AT RISK. Owner chose "panic on VPN down": `down` and not on site is LOST whatever the API says. Confirmed by a real outage the same morning: no huddle while the session sat at a question card (no API evidence under the old rule), huddle once an agent made a failing call, recovery correct. Test: `tests/stage/test_link.py`.
