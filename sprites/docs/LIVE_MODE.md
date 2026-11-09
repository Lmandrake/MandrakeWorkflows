# Sprites live mode: status (2026-11-01)

Built and run on the Laptop desktop in demo mode. The LaunchAgent is NOT installed (the owner sees it first: `make install-agent`).

## Pieces
- `app/stage.html`: implements `window.SpritesStage` exactly as `app/macos` calls it (update, setCast, setBehaviors,
  setDemo, setPaused, setCursor, setFocus, setActivity, setWindows, setSize, setScale). Since 764a1b2: ONE full-screen
  canvas and ONE frame loop; each species is a runtime instance (`VisitorsRuntime.create`, shared mode) running its piece's
  own script, read unchanged from `prototype/cN_*.html`, dropped 2.5 s after its last creature leaves (it was one iframe each). Posts `{hits}` at most 10 Hz
  (only on change) and `{click}` on mousedown over a creature.
- `adaptState(snapshot)`: the ONE reader, Augur shape only (owner 2026-10-31 23:50; SHIP_PLAN shape removed). Mapping per
  augur/DESIGN.md §11. Any block past its valid_until, `unknown`, or a snapshot past valid_until = absent; the runtime
  fills absent values calm (flagged `_absent`), never 0, and draws the unknown mark plus hover words with the age (docs/OBSERVATION_CONTRACT.md "Drawing unknown"). needs_you -> needs, stopped -> idle, tasks.total else load.procs,
  strain level = score x 0.75, thermal clamp 2, VPN lost only when down and not on site, bandwidth strain absent = no jam.
- Casting: cast.json project -> {concept, iv, hex}; anything uncast and every unmanaged session draws randomly (seeded
  by name, or by id for unmanaged), unmanaged drawn white (V.hsl desaturates while inside V.creature).
- Burning: per-project count from `projects[].counts.burning`; lights on the oldest session of the project; a project with
  burning > 0 and no session gets a ghost visitor (faint, almost still, screen edge). Lodestar follows the same rule.
- `prototype/visitors_runtime.js` live mode: membership by id (re-init + piece `carry` hook keeps positions), arrivals
  and departures fade (1.5 s), `V.on(key)` switches, `V.steer` (perch, followOwnWindow, curiosity, edgeWhileTyping,
  greetNewcomers, nudgeLongWait, ghosts), cursor repulsion inside `V.avoid`, eased `setScale` (no reseed; pieces got
  a `resize` hook where needed), celebrateDone flare, sleepWhenAway slows time, running lights (`lightSpots` per piece),
  frame rate 30 when anything moves, 10 when calm, 12 under heavy strain (quietUnderStrain), 0 when paused.
  (**Superseded**, owner 2026-11-01: one constant 24 fps whenever anything is visible; quietUnderStrain only skips the flourish.)
- `app/behaviors.js`: the 19 switches (`window.SPRITES_BEHAVIORS`), read by stage and Settings.
- `tools/demo_feed.py`: Augur-shape demo/test feed with scenarios (calm, busy, needs, strain, vpn_down, bw_jam, churn,
  lodestar_closed, lodestar_closed_quiet, ghosts, twin, unmanaged); `--check` validates against the schema.
- Host (`app/macos`): reads `$SPRITES_STATE`, else `$AUGUR_SNAPSHOT`, else default `augurSnapshot`, else
  ~/agent-storage/augur/live/snapshot.json. `--demo` / `--no-demo` for smoke tests.

## Verified (evidence under ~/agent-storage/sprites/live/)
- Headless (one Chromium, nice 10): `verify/stage_test.py` -> `verify/results.json` + PNGs. Demo, demo_feed t=0/200/400,
  six scenarios and the Augur sample render with zero page or frame errors; transparent background (rgba 0); hits
  reported for every non-ghost creature; ghost:lodestar present in lodestar_closed and absent in lodestar_closed_quiet;
  a departing session leaves survivors in place (moved <= 1 px); the stale Augur sample adapts to sessions with no values.
- Desktop (`app_run/`): app ran in demo mode and with the calm feed; it never took focus (frontmost stayed iTerm2);
  transparent over the desktop (`desktop_demo_small.png`, `desktop_calm_small.png`). Quit afterwards.
- CPU, ps time over 60 s, app + its 3 WebKit processes: demo mode (8 sprites, always busy) 37.4 % of one core; calm feed
  (4 idle sprites) 11.2 % (`cpu_demo_60s.txt`, `cpu_calm_60s.txt`). Most of it is the WebKit GPU process.

## Not verified yet (needs the owner at the desk)
- Click-through except over creatures, click-to-session (switches Space), full-screen fade, hover name: not driven, to
  avoid clicking into the owner's working terminal. The demo has no pids, so its clicks do nothing by design.
- Visual review of the five pieces at desktop scale in live mode (piece edits were syntax-checked and the gallery path
  reasoned unchanged; the gallery was not re-rendered).

## Known issues / next
- Idle cost 11 % of a core is above a desktop ornament's budget; candidates: one canvas for all species instead of five
  full-screen iframes, 5 fps when calm, or the v2 native port (SHIP_PLAN).
- Demo mode is never "calm", so it always runs at 30 fps.

## CPU and checks (2026-11-01, overnight)
Measured (app + its WebKit GPU/WebContent/Networking processes, ps CPU time over 60 s; tool
~/agent-storage/sprites/live/cpu/measure.sh, log ~/agent-storage/sprites/live/cpu/results.txt). Load was 7-25 throughout, so
treat as indicative:
| build | calm (4 idle sprites) | demo |
|---|---|---|
| bddcb59 (5 layers, 30/10 fps) | 11.8 % (16.8 % under load) | 35-37 % |
| frames on one wall-clock grid (30c6bde) | 7.3 % | |
| calm 4-5 fps | 4.2-6.1 % | 32.7 % |
| calm 3 fps | 2.6 % | |
| demo capped 15 fps | | 19.6 % |
| constant 24 fps (f570073, owner: "fps shouldn't change") | 12.0 % (one run, load 7) | 29.8 % (one run) |
A/B (calm): no layers 0.7 %; layers but no drawing 9.1 %; static page 2.6 %; one layer 5.9 %; dpr 1 vs 2 no change. Cost is
per rendered frame per layer (compositing five full-screen transparent WebViews), not pixels or JS.
The owner's constant-fps ruling retires the 3-5 fps calm trick, so <= 3 % at a smooth constant rate needs ONE canvas instead of
five full-screen iframes (all species drawing into one document), then 20-24 fps. Not built yet.

PENDING, gated (load testing runs only on a trusted on-site network without the VPN): re-measure only
when Augur reads machine.vpn.on_site == true and state != "up":
  python3 -c "import json;v=json.load(open('$HOME/agent-storage/augur/live/snapshot.json'))['machine']['vpn'];exit(0 if v.get('on_site') is True and v.get('state')!='up' else 1)" && for r in 1 2 3; do ~/agent-storage/sprites/live/cpu/measure.sh fps24_calm_$r calm 60; ~/agent-storage/sprites/live/cpu/measure.sh fps24_demo_$r demo 60; done

GUI checks still to do with the owner idle > 120 s (ioreg HIDIdleTime): click-through on empty desktop, click a live creature
-> its iTerm2 window focused, click a ghost once -> new window via `launch <Name>` (then close it), full-screen fade, no focus
steal while typing. Verified so far: never takes focus (frontmost stayed iTerm2 through every launch), transparent.
Tests that pass (headless): verify/move_test.py 25/25, verify/vpn_truth.py all, verify/huddle_test.py (all five species
within 20-55 px of the one beacon by 8 s), smooth.py (24 fps calm and on hover, < 0.7 px/frame).
Gallery re-render: PENDING under the same load gate. Only c1_choir 8/12 re-rendered (~/agent-storage/sprites/gallery/v, 05:53);
round-2 reference kept at ~/agent-storage/sprites/gallery/v_round2; resume with ~/agent-storage/sprites/live/gallery_compare/run.sh
then compare.py (untested).

## One canvas (764a1b2, 2026-11-01)
Built: one WebView, one canvas, one rAF loop at a constant 24 fps; each piece draws in its own save/restore with its own
drawing state carried frame to frame; hit testing, ghosts, running lights, the shared beacon and terrain stay in the runtime.
Frames stop entirely with no creatures, when paused (hidden, full screen, locked) or page hidden; with creatures all faded,
the simulation steps at 2 Hz on a timer and nothing paints. c2 Siphonophore glows are pre-rendered sprites (126 gradients per
frame -> 3). Also in this unit: hover comes to the cursor, the hover-label hook (prototype/labels, Constellation default),
and the VPN + on-site network + API link states (SHIP_PLAN).

Profile, passive (sample(1) of the running app's WebKit processes, no load generated): the GPU process time is replaying
canvas display lists (CA::CG DrawOp/RadialGradient, Metal submits); WebContent is rAF callbacks + updateRendering + layer
commit; JS is small. Safari Web Inspector timelines not reached (the WKWebView is not inspectable; enabling it means a host change).

CPU, live Augur feed (real cast that day: 1 working session + 3 ghosts, 27/8/2 burning lights), ps time over 60 s, app +
its WebKit GPU/WebContent/Networking, before and after builds interleaved (load 12-14, so indicative):
| build | runs | median |
|---|---|---|
| before (5 iframes, HEAD 9fde09f) | 22.1, 25.1, 26.4 % | **25.1 %** |
| after, one canvas (764a1b2) | 19.2, 19.3, 19.4 % | **19.3 %** |
(The earlier "12.0 % calm" was with the demo calm feed, 4 idle sprites; the live cast today is busier, so compare within a row pair.)
A/B on the same live feed, to find where the rest goes (variants under ~/agent-storage/sprites/live/onecanvas/var_*):
| variant | CPU |
|---|---|
| step at 24 Hz, never paint | 2.0-2.3 % |
| rAF + clear, pieces not drawing (nodraw) | 9.4-10.3 % |
| rAF, 4 px dirty rect, no drawing | 8.8 % |
| timer instead of rAF, drawing | 22.4 % (no gain) |
| dpr 1 instead of 2 | 22.8-24.2 % (no gain) |
| willReadFrequently (CPU canvas) | 41.7-43.6 % (worse) |
| CPU scratch + dirty-box copy | 31.7-49.1 % (worse) |
Reading: ~2 % is simulation; ~8 % is the bare cost of ANY painted frame at 24 fps in a full-screen transparent WKWebView
(update + commit + composite, even a 4 px change); the rest (~10 %) is the canvas commands themselves (1 000-1 400 fillRect
plus 100-150 drawImage per species per frame, replayed in the GPU process). One canvas removed the per-layer part. The
target (<= 3 % calm at constant 24 fps) is NOT reachable in WKWebView: the painted-frame floor alone is ~8 %. Next steps:
(a) the v2 native port (one CALayer/Metal view, no WebKit per-frame update), or (b) fewer, batched draw calls per piece
(the draw-call batcher is in stage.html behind ?batch=1, unmeasured; batching fillRect needs one fillStyle per run, so the
pieces' per-dot hsl strings defeat it as written).

Look parity: ~/agent-storage/sprites/live/verify/onecanvas/frames/sheet.png (before | after | diff x8), diff.json. 17 scenes x
2 times, frozen virtual clock, cold start; a before-vs-before control is 0. 26 of 34 frames identical (max <= 7/255, 0 px
> 8); 8 mixed-species frames differ: 4 in 1-5 px, 4 in 431-3 943 px (1.2-5.8 % of lit pixels, max 121/255), all where two species overlap: the old stage composited each
iframe separately, one canvas composites "lighter" glows across species, so overlapping glows add instead of stacking.
Tests: verify/move_test.py 25/25, verify/vpn_truth.py all (42-combination link table), verify/hover_follow_test.py 5/5,
verify/huddle_test.py (now vpndebounce=0 + api failing/network, since a VPN drop alone is only "at risk"): all five within
17-73 px of the beacon by 8 s, same as the before tree. cpu/smooth.py: 24 fps calm and on hover, <= 0.28 px/frame.
verify/stage_test.py: demo, feeds and every scenario render with zero errors, hits for every creature. Old iframe tests run through verify/layerframe.py.

PENDING, gated on load (owner rules): DEMO-mode CPU and any stress run only on a trusted on-site network with the VPN off.
