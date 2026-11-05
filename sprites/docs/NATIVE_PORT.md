# Sprites native port: design (2026-11-01)

Owner, 2026-11-01 08:47: port the drawing from the WebKit canvas to native macOS graphics, constant 24 fps, <= 3 % of one
core calm (passive, live feed), look unchanged. Evidence for why: docs/LIVE_MODE.md "One canvas": ~2 % is simulation, ~8 %
is the bare cost of any painted frame in a full-screen transparent WKWebView, ~10 % is the canvas commands replayed in the
WebKit GPU process. Baseline for this port, same day, live feed (1 session + 3 ghosts), passive ps over 60 s:
**21.4, 21.4, 19.8 % (median 21.4 %)**, ~/agent-storage/sprites/live/native/cpu/passive.txt.

## Shape
1. **The simulation stays in JS, unchanged.** stage.html's script, visitors_runtime.js, the five pieces and labels.js run in
   a JavaScriptCore `JSContext` inside the app process (no WebView, no WebContent/GPU processes, no compositing of a web
   layer). The same files keep running in WKWebView for the fallback and in headless Chromium for every existing test, so
   the movement, VPN/WiFi/API, huddle and hover tests keep testing the code the native build runs.
   A thin shim (app/native/shim.js) supplies what JSC lacks: window, document.createElement("canvas"), location.search,
   URLSearchParams, setTimeout/setInterval (Swift timers), performance.now, XMLHttpRequest (reads the piece file), and
   `webkit.messageHandlers.sprites.postMessage` (hits and clicks to Swift). stage.html changes only where it must: a
   native frame driver hook in schedule() and layer markers around each species and the labels (no-ops in WebKit).
2. **A recording 2D context replaces the canvas** (app/native/canvas.js). It is a `CanvasRenderingContext2D` class with the
   same accessors (the runtime's per-creature globalAlpha trick reads the prototype descriptor, so it must be one), and it
   turns calls into GPU instances written straight into a Float32Array: no per-call bridge into Swift (that would cost
   more than WebKit). Swift reads the array's bytes once per frame (JSObjectGetTypedArrayBytesPtr).
   Primitive kinds: rect, disc (a full-circle arc), convex polygon (diamonds, wedges, trapezoids; points in a side
   buffer), stroke segment (polylines, arcs and ellipses flattened), each with a solid colour or a gradient (radial or
   linear, up to 6 stops, side buffer), globalAlpha folded in, the current transform applied in JS.
   **Offscreen canvases** (every piece caches its glow sprites in a small canvas holding ONE gradient fill) are recorded,
   not rasterized: drawImage(sprite) replays that one fill under the destination transform, so a glow is an analytic
   gradient quad on the GPU (no texture atlas, no upload). An offscreen canvas with anything else in it (text: the
   labels' glyph canvases) is rasterized once by the Core Graphics interpreter below and drawn as a texture.
3. **Metal renderer** (app/macos/Render.swift): a CAMetalLayer per screen in the existing transparent, click-through
   StagePanel. One render pass per frame; each kind is expanded to a quad in the vertex shader and shaded with analytic
   coverage (box-filter AA for rects, distance AA for discs, polygons and segments), so 1-2 px motes keep their weight.
   Blending is the canvas's: "lighter" = one/one, "source-over" = one/one-minus-source-alpha, premultiplied, 8-bit,
   in sRGB gamma space (bgra8Unorm, layer tagged sRGB), as the WebKit canvas does.
   **Per-species layers (the approved look):** each species accumulates into a memoryless tile attachment and is then
   composited source-over onto the frame (framebuffer fetch), as the five iframes were composited by Core Animation.
   That is the reference look, not the one-canvas regression where glows of two species add.
   Full circles and ellipses (fills and strokes: rings, ripples, bloom) are one analytic ellipse instance each; polylines
   are butt-capped segment quads. A canvas stroke is a union per path, so where two segments of one path meet, the small
   joint wedge is drawn twice here; at the 1-1.5 px strokes the pieces use this is expected to stay under the parity bar,
   and the diff sheets will show it if not.
   Per-instance layout, shader and blending: app/macos/Render.swift; recorder: app/native/canvas.js.
4. **Labels** (all five styles, labels.js unchanged): while a label is showing, its calls go to a recording canvas bounded
   by the label's box; the Core Graphics interpreter (app/macos/CGCanvas.swift: paths, gradients, text via CoreText,
   shadows, clip, transforms, getImageData for the Constellation glyph sampling) rasterizes that box and it is drawn as one
   texture, composited like a layer. Labels draw only on hover, so their CPU is not in the calm budget.
5. **Frame driver** (**not built as written:** the native host drives frames with main-runloop Timers on the stage's wall-clock
   grid (Native.swift `arm`), no CADisplayLink; R1-SPEC S10. The design below stands if the timers miss 24 under load): a CADisplayLink on the panel's screen with preferredFrameRateRange 24...24 (24 divides the 120 Hz
   ProMotion rate, so frames land on a fixed 5-vsync grid), resumed only when the stage asks for a frame. Off when there are
   no creatures, when paused (hidden, meeting, locked, full-screen fade) or when the stage is all faded (then the stage's
   own 2 Hz sim-only timer runs and nothing is presented). An empty frame after a painted one presents one clear drawable.
6. **Clicks:** the panel is click-through except over a hit (unchanged); a mouseDown on the native view is handed to the
   stage's own mousedown listener (same pick, same `{click}` message).

## Fallback, then removal
`SPRITES_RENDERER=webkit` (env) or the `renderer` default (`defaults write com.mandrake.sprites renderer webkit`, also
`-renderer webkit` on the command line) selects the old WKWebView stage until the native one is verified. When parity holds,
the WebKit stage is removed (owner's no-duplicates rule): the shim then becomes the only host of stage.html's script, and
stage.html stays only as the headless test harness and Settings previews (those run in Settings' own WebView).

## Evidence plan (pre-registered)
- **Spike gate:** c5 fireflies only, rendered natively, everything else in the live feed cast to c5 for both builds
  (`SPRITES_CAST` points at a test cast; the owner's cast.json is not touched). Passive CPU of the running app, ps time over
  60 s, 3 runs, median, live feed. Pass = well under the WebKit number on the same cast (target <= 5 % at the spike, <= 3 %
  after the full port). Fail = stop and report before porting the rest.
- **Parity:** a `--render-frames` mode renders fixed-seed frames (frozen clock, seeded Math.random, cold start,
  renderAt(t)) offscreen through the same Metal path; the reference is the per-layer (five iframe) tree rendered by
  ~/agent-storage/sprites/live/onecanvas/tools/parity.py's scenes. Every species x calm/busy, plus the mixed scenes (needs,
  strain, vpn_down, ghosts, unmanaged), t = 3 s and 9 s. Diff sheets and diff.json in
  ~/agent-storage/sprites/live/verify/native/. The reference rasterizer (Skia) and Metal differ in antialiasing, so the bar is
  the one-canvas bar: no frame with structure missing or added, >= 99 % of lit pixels within 8/255, and the mixed-species
  overlap frames must match the per-layer reference (not the one-canvas additive look).
- Existing tests: move_test 25/25, vpn_truth (42-combination table), huddle_test, hover_follow_test, stage_test on
  stage.html after the hook edits.
- Machine rules: renders one process at a time under `nice -n 19` while the 1-min load is < 8; no load or stress testing
  (demo-mode CPU) unless on the on-site network with the VPN off (Augur machine.vpn).

## Spike result (c5 fireflies, 2026-11-01 ~10:00)
Passive, live feed (1 session + 3 ghosts, every project cast to c5 by a test cast), ps over 60 s, interleaved, load 4-7.5
(~/agent-storage/sprites/live/native/cpu/ab_run2.txt):
| build | runs | median |
|---|---|---|
| WebKit (one canvas) | 17.2, 19.0, 18.6 % | **18.6 %** |
| native (JSC + Metal) | 7.3, 6.8, 7.0 % | **7.0 %** |
That is well under WebKit (owner's gate) but **misses this doc's own spike target (<= 5 %)**; the target is not moved.
Where the 7 % goes (SPRITES_NATIVE_STATS=1, main thread, per second): JS 3.1-3.9 % (c5 step 0.34 ms + draw 0.37 ms per
frame live, against 0.18 + 0.06 ms in a tight loop: at 24 short bursts a second the work runs cold and on efficiency
cores), Metal encode + present 0.5 %, the host's own polling (focus, windows, cursor) ~1.5-2 % (the WebKit build's app
process alone shows 1.7-2.4 %), JIT and Metal helper threads the rest.
Trap found: a JSContext in an app without the `com.apple.security.cs.allow-jit` entitlement runs interpreted (~10x
slower; first native run measured 19.9 %). app/macos/Sprites.entitlements; the Makefile signs with it.
Look: the simulation is bit-identical under JSC (reported positions equal the Chromium reference to the last digit).
Pixels vs the per-layer reference (t = 3 and 9 s, calm and busy): max 27-62/255, 2.2-3.5 % of lit pixels > 8/255
(~/agent-storage/sprites/live/verify/native/cmp/sheet.png); the parity bar (>= 99 % within 8/255) is not met yet.
