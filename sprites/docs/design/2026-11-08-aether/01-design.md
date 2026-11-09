# The Aether: pass 1 (deep design)

Deep-Design-3x2, pass 1. Written 2026-11-08, about 02:00 PST, on the Work Laptop (`mt-AAAAAA`, M1 Max, 3456 x 2234
Retina, macOS 26.7.2), on AC power with the VPN up and off site. That last fact matters: **no load or stress run was
made.** Every measurement below is a single light run of a few seconds (a 100-step timing loop, a 5-second toy
window, single API calls). Scratch code for all of them: `~/agent-storage/scratch/aether/`.

Problem statement: `~/dev/MandrakeWorkflows/sprites/docs/design/2026-11-08-aether/PROBLEM.md`.

> **Three findings from the survey change the design before any idea is had.**
> 1. **SpriteKit's built-in electric and magnetic fields are the obvious tool, and measured, they are far too costly:**
>    13.3-13.7 % of a core for 1 000 bodies at 12 fps, 38-58 % for 3 000. A hand-written sim plus one instanced Metal
>    draw does 1 500 dots at 12 fps for **1.0 %** (app side). The physics is not the cost: a spatial-hash hard-disc step
>    for 1 500 dots takes **0.04 ms** in Swift and in JavaScript alike.
> 2. **Sprites already has nearly every input the Aether needs.** Window rects (shared 50 ms cache, 2 Hz focus read,
>    full read on change), a global mouse-drag monitor (so a window drag is detectable at no new cost), every sprite's
>    position and radius at ~10 Hz in Swift (the `hits` messages), the menu-bar status items as windows with rects (18
>    of them, no Accessibility grant), the Dock area (`visibleFrame`), and an opaque black Metal window at desktop+1
>    with pause-on-occlusion, lock, sleep, hide and Reduce Motion. The Aether is a new tenant of `BackdropWindow`, not
>    a new subsystem.
> 3. **A naive "every window is a wall" reading is wrong on this machine:** the window list has a **full-screen,
>    fully opaque-alpha layer-20 window (the Dock's)** and a full-screen layer-3 window (Sprites' own stage). Taken as
>    walls they leave a free fraction of 0.00. Walls must come from layer-0 windows plus explicit menu-bar, status-item
>    and Dock geometry.

---

## 1. The problem, restated

The owner saw a concert backdrop of green glowing dots that bounced, collided, sometimes merged into something
larger, sometimes formed small linear structures that floated and rotated and then fell apart. He wants that as the
environment the Sprites live in, replacing the moving backdrops with **pure black** plus these dots, named **the
Aether**. The elements, each of which this design must honour:

| # | element (owner's words, condensed) | where it is answered |
|---|---|---|
| 1 | dots live only outside windows of any kind, focused or not | §4.2 walls |
| 2 | they bounce off the boundaries | §4.2, §3 physics core |
| 3 | pushed out of the way as windows move | §3 physics core, moving walls |
| 4 | hotter or colder as they are compressed or expand, ideal gas through particle kinetics | §3, adiabatic section |
| 5 | complex things near Sprites, as if in electric and magnetic fields | §3 fields, §4.4 |
| 6 | the background becomes utterly black; the dots are the visual interest | §4.1 |
| 7 | Setting: entry temperature (hot and fast, or cool and still unless struck) | §4.1 |
| 8 | Setting: reservoir (enter and freely leave) or reflecting boundaries | §4.1, §3 boundaries |
| 9 | Setting: density | §4.1 |
| 10 | Setting: how often they build small temporary vector structures | §3 structures, §4.1 |
| 11 | Setting: particle size | §4.1 |
| 12 | interactions with desktop icons, the menu-bar tray, shortcuts | §4.3 |
| 13 | not obtrusive during normal work, a whimsical note | §1 success, §4.5, every idea's risk tag |
| 14 | low CPU; it runs all day on battery | §1 budget, §3 cost per solution |
| 15 | look at the repos for similar ideas and for how to keep CPU low | §2 |

### Constraints (inherited)
- Sprites is a native Swift app; the sprites' simulation is JS in an in-process JavaScriptCore context, drawn by
  Metal (`~/dev/MandrakeWorkflows/sprites/docs/NATIVE_PORT.md`). Its standing CPU target is
  **<= 3 % of one core calm** and it is not yet met: 7.0-7.7 % measured passive after the port, and **9.7-13.3 %**
  right now (`top -l 2 -pid`, `ps`, this session, live cast, current backdrop b04 at speed 4 and 2 fps). **The
  Aether may not make that gap wider than the backdrop it replaces does.**
- Owner's no-duplicates rule: the Aether replaces the moving backdrops' role; it does not run beside them.
- Perception rules already written for this desktop
  (`~/dev/MandrakeWorkflows/visualize/docs/MACHINE_BACKGROUNDS.md`): coherent motion far below
  1 deg/s (about 60 px/s at 60 cm on this screen), no radial expansion or whole-field rotation (vection), mean
  luminance <= ~0.5 %, 99.9th percentile <= ~2 %, single-pixel-scale points may reach ~5 %; moving points must never
  read as sprites (the b09 Marine Snow caution).
- Existing sprite grammar the Aether must not collide with: **VPN lost = colour drains to cold blue-grey and motion
  stops**; **strain = more motion and heat**; **needs-you = a ring and two ripples near the menu bar**; red is the VPN
  heartbeat. So: cold Aether must not go blue-grey, a hot Aether must not read as strain, and expanding rings are
  reserved.
- Load testing only on Lab Wi-Fi with the VPN off. Passive CPU measurement of the running app is not load testing.

### What success looks like, and how it is measured
| criterion | bar | how measured |
|---|---|---|
| CPU, calm (no window moving, no sprite near dots) | Aether adds **<= 1.0 % of one core** over Aether-off | existing `~/agent-storage/sprites/live/native/cpu/passive.sh`, 60 s x 3, median, on battery, live cast |
| CPU, disturbed (window dragged continuously) | <= 2.5 % added while dragging, back to calm within 10 s of release | same, with a scripted drag; **Lab Wi-Fi, VPN off only** (it is a load run) |
| WindowServer | Aether adds <= 1 % to WindowServer | `ps -o time` on WindowServer, A/B interleaved, quiet machine; not resolvable tonight (see claims) |
| Covered or full screen | **0 %** added (no frames) | `SPRITES_NATIVE_STATS`-style frame counter reads 0 |
| Energy | Activity Monitor Energy Impact no worse than b04 today | read it, 60 s, both settings |
| Not noticed while working | after the first week, **<= 1 "that distracted me" log per 2 working hours**, and he keeps it on | a one-key "distracted" log (idea §4.6) records time plus Aether state |
| Never misread | no dot or structure is ever taken for a sprite, a needs-you ripple, VPN loss or strain | owner's eye in week one; a review sheet of 12 stills plus 4 clips |
| Whimsy | he shows it to someone | the honest test |

---

## 2. Survey: what already exists

### 2.1 Sprites itself (`~/dev/MandrakeWorkflows/sprites/app/macos/`)
- **`Backdrop.swift`**: `BackdropWindow`, one per screen, borderless, **opaque black**, at desktop window level + 1
  (above the wallpaper, below desktop icons at desktop-icon level and the DimLayer at desktop-icon + 1),
  `canJoinAllSpaces`, click-through, its own `CAMetalLayer` (bgra8, sRGB, 2 drawables, full backing resolution). A
  `Timer` at the concept's fps (1-10 clamped, tolerance 20 %). Draws only windows whose `occlusionState` is visible;
  paused while locked, asleep, hidden (meeting mode and user-hide via `visibilityPlan`) or under Reduce Motion. The
  live mode **does not touch the wallpaper store**, so black-plus-dots needs no wallpaper write. This is the Aether's
  host, nearly as is.
  - **Finding:** `BackdropWindow` does **not** set `sharingType = .none`; the stage panels and the DimLayer do
    (`Stage.swift` lines 20 and 316). So today a moving backdrop shows in screen shares and screenshots while the
    sprites do not. Open decision `MANDRAKEWORKFLOWS_DECIDE_AETHER_VISIBLE_IN_SCREEN_SHARES` (§6).
- **`Focus.swift`**: `windowList()` (CGWindowListCopyWindowInfo, on-screen, desktop elements excluded, cached 50 ms
  and shared), `allWindows()` with layer and alpha, `windowBounds(id)` for one window (the comment says ~0.11 ms),
  `tickNeedsFullRead` (2 Hz focused-window read, full list every 4th tick or on change), `stageRect` and
  `cgFrame` coordinate conversion, `isFullScreen`.
- **`App.swift`**: one 10 Hz host tick; window and focus push every 0.5 s; app-activation and Space-change
  notifications push at once (and again 0.4 s later); **a global `NSEvent` monitor on `.mouseMoved` and
  `.leftMouseDragged`** (no TCC grant) that already fires on every drag; `secondsSince(.keyDown/.scrollWheel)` gives
  "typing" (keys or scroll in the last 1.5 s); hotkey ⌃⌥⌘S for meeting mode; screens-did-sleep, session-resign,
  occlusion observers.
- **`Stage.swift`**: `handle(body)` receives `hits` from the JS stage at ~10 Hz: every sprite's `id, x, y, r,
  project, pid` in world px. **The Aether's field sources are already in Swift.** `DimLayer` is the precedent for
  per-screen click-through windows that re-fit without flashing; a static layer was measured to cost nothing
  (`docs/SHIP_PLAN.md`: 0.51 s vs 0.49 s CPU per 30 s).
- **`Native.swift`**: the Metal renderer for the sprites (instanced quads, analytic coverage, "lighter" blending). The
  Aether's renderer is the same idea, much smaller.
- **`Decide.swift`**: `spanLayout` (multi-monitor world, each screen's `visibleFrame` = menu bar and Dock excluded),
  `currentSpace` and SkyLight `CGSGetActiveSpace` (per-Space identity already exists for the wallpaper book),
  `backdropPaused`, `visibilityPlan`.
- **Backdrops** (`app/backdrops/catalog.json`, `backdrops.sl`, `bd.js`, Settings → Backdrop tab in
  `app/settings.html`): 12 shader concepts, 0-4 fps, speed multiplier; owner's live setting is **b04 Caustic Floor at
  speed 4**. b09 Marine Snow is the only particle concept, rendered by shader, not simulated.
- **The sprites' own particles**: c5 Firefly Murmurations is a boids swarm per session (motes = memory); the runtime
  `visitors_runtime.js` steers creatures round the focus with a cost grid and moves them to the screen edge while
  typing (`edgeWhileTyping`). Nothing there simulates collisions, a gas, or fields. Nothing to reuse but conventions.
- **CPU history** (`docs/LIVE_MODE.md`, `docs/NATIVE_PORT.md`, `docs/NATIVE_PORT_HANDOFF.md`): per-frame cost, not
  simulation, dominated every measurement; full-screen transparent WebViews cost 2.6 % static and 5.9 % per animated
  layer; JS in JSC runs **about 2x slower live than in a tight loop** (cold, efficiency cores: c5 step 0.34 ms live vs
  0.18 ms in a loop); a JSContext without `allow-jit` runs ~10x slower (the entitlement is present); the host's own
  polling costs ~1.5-2 %.
- **Design-run precedent:** `~/dev/MandrakeWorkflows/sprites/docs/design/2026-11-06-foreign-work/`
  (same 3x2 shape).

### 2.2 Elsewhere in `~/dev`
A grep for boids, flocking, spatial hash, particle system, SKFieldNode, Lennard-Jones and ideal gas across `~/dev`
(js, py, swift, md, html) finds only papers, the c5 design case file, and unrelated game design notes in RimMandrake.
`~/dev/MandrakeWorkflows/visualize/docs/MACHINE_BACKGROUNDS.md` is the one directly relevant document:
its perception rules and luminance budget are adopted above, and its estimate "particles at 2-5 fps: under 1 %" is
consistent with the measurement below. Lodestar's board has no animation code worth borrowing. **Nothing to reuse;
nothing to collide with.**

### 2.3 Platform and open source
- **SpriteKit** (`SKPhysicsBody.charge`, `SKFieldNode.electricField / magneticField / vortexField / noiseField /
  turbulenceField / dragField / springField`, `SKRegion`): literally the owner's vocabulary, built in. **Measured
  here** (toy app, offscreen window, 12 fps): 1 000 charged circle bodies with one electric and one magnetic field:
  **13.3 %** (`SKShapeNode`) and **13.7 %** (`SKSpriteNode`); 3 000: **57.8 %** and **38.0 %**. Box2D-style rigid
  solving per body is the cost; the fields also apply to every body every step. Rejected for production (§3 D).
- **Metal**: instanced quads (what Sprites already does); compute kernels for GPU particle sims (Apple's "Metal
  particle" samples, the classic counting-sort grid in a compute pass). Measured below.
- **Frame drivers**: `Timer` with tolerance (Sprites' choice, kept); `CADisplayLink` on macOS 14+ via
  `NSView.displayLink(target:selector:)` with `preferredFrameRateRange`; either is fine at 2-24 fps.
- **Power APIs**: `ProcessInfo.isLowPowerModeEnabled` and `NSProcessInfoPowerStateDidChange`;
  `ProcessInfo.thermalState` (`nominal / fair / serious / critical`) and its notification; Augur already publishes
  `machine.power.on_battery`, `battery_pct`, `machine.thermal.state` and `low_power` in its snapshot
  (`~/agent-storage/augur/live/snapshot.json`, read tonight). `NSWindow.occlusionState` (used).
- **Window geometry**: CGWindowList (used; no Screen Recording grant needed for bounds). Accessibility could give
  window move events (`AXObserver` `kAXMovedNotification`) but needs the AX grant per watched app; the existing drag
  monitor plus a faster poll while dragging is enough.
- **Desktop icon positions**: Finder AppleScript `desktop position of every item of desktop` worked here
  (**0.21 s wall** for 6 items via `osascript`, process spawn included) but needs an **Automation (Finder) grant** for
  the Sprites app. The Finder icon window in CGWindowList is one full-screen window (layer -2147483603): no per-icon
  rects there.
- **Menu-bar tray**: status items are layer-25 windows with bounds (18 measured, each ~31-38 x 33 px) in the plain
  window list: no AX grant.
- **Physics literature used** (standard, not novel): hard-disc molecular dynamics with a cell list; reflection off a
  moving wall `v' = 2u - v` (normal component; the kinetic origin of adiabatic heating and of Fermi acceleration);
  2D monatomic gas `gamma = 2`, so a quasi-static adiabat is `T * A = const`; ideal-gas free expansion leaves `T`
  unchanged; effusion flux through an open edge in 2D is `n * sqrt(kT / 2 pi m)` per unit length; the **Boris
  pusher** (plasma particle-in-cell) rotates velocity in a magnetic field exactly, so magnetic fields do no work;
  Arrhenius bond lifetimes `tau = tau0 * exp(Eb / kT)`.

### 2.4 Measured tonight (single light runs; scratch in `~/agent-storage/scratch/aether/`)
| what | result | how |
|---|---|---|
| Sprites CPU now | 12.0 % (`ps`), 9.7 % and 13.3 % (`top -l 2`, POWER 9.7 / 13.3) | live cast, b04 backdrop, AC |
| Full window list, raw call | 0.37-0.55 ms (first call in a process 1.4-2.3 ms) | `br.swift`, `one.swift`, 50-100 calls |
| One window's bounds | **0.158 ms** | `one.swift`, 200 calls |
| Windows on screen | 24: layer 0 x2, layer 3 (Sprites stage, full screen), layer 20 (Dock, **full screen**, alpha 1), layer 24 (menu bar 1728 x 33), layer 25 x18 (status items) | `free2.swift` |
| Free desktop fraction now | **0.28** of the main display (two app windows) | rect arithmetic on the live list |
| Hard-disc gas step, spatial hash, Swift `-Ounchecked` | 1 500: **0.038 ms**; 4 000: 0.133 ms; 10 000: 0.507 ms | `sim.swift`, 100 steps |
| Same step, JavaScript (node 26) | 1 500: **0.042 ms**; 4 000: 0.122 ms; 10 000: 0.453 ms | `sim.js`, 100 steps |
| SpriteKit, charged bodies + E and B fields, 12 fps | 1 000: 13.3-13.7 %; 3 000: 38.0-57.8 % | `sk.swift`, `sk2.swift`, 4 s |
| Metal instanced dots, full-res 3456 x 2234 drawable, CPU move + draw | 1 500 @ 12 fps: **1.01 %**; @ 24 fps: 1.76 %; 4 000 @ 4 fps: 0.31 % | `mt.swift`, 5 s, app process only |
| WindowServer delta of that window | not resolvable: 46.7 % idle vs 45.0-46.7 % with it | `ps` time over 6 s, machine load 6-18 |
| Finder icon positions | 0.21 s for 6 icons via `osascript` | one call |

---

## 3. Solutions

All share one **physics core** (below) and one **frame policy** (below); they differ in where the sim runs and what
draws it. Five were considered; three are real contenders, two are recorded because they are the obvious ideas and
the measurement or the brief kills them.

### The shared physics core (units: px, s; mass 1; `k = 1`; temperature `T` = mean kinetic energy per dot)

**Dots.** Position, velocity, charge `q in {-1, +1}` (half each, invisible), and a *visual* radius (Settings) distinct
from the *collision* radius. This split is a design finding: at 1 500 dots in half a 14-inch screen the mean free
path `1 / (sqrt 2 * n * d)` is **~150 px at d = 3 px** and **~76 px at d = 6 px**; at a calm 8 px/s that is one
collision every 10-20 s per dot. Visible collisions need a collision diameter of ~6-8 px under 1.5-2 px dots, which
reads exactly like the Asteroids look (vector dots that clearly "hit" before they touch).

**Collisions.** Uniform grid hash (cell = collision diameter x 2), elastic hard discs, impulse along the line of
centres, no friction, no rotation of single dots. One pass per step; overlapping pairs are separated by half the
overlap each. Cost measured above (0.04 ms at 1 500).

**Walls.** Axis-aligned rectangles: every on-screen **layer-0** window of another process with alpha > 0 and size >
50 px (the filter `onScreenWindowsWithID` already applies), plus the menu bar strip, plus each status item's rect as a
bump hanging from it, plus the Dock band (from `frame` minus `visibleFrame`), plus notification banners and open menus
(windows of any layer that are neither full-screen nor ours). Each wall carries a velocity estimated from successive
reads. A dot that ends a step inside a wall is reflected off the face it crossed (decided from its previous position),
with the normal component `v_n' = 2 u_n - v_n`. That one line is the **ideal-gas heating and cooling, from kinetics**:
an approaching wall adds speed, a receding wall removes it; nothing is faked.
- **Teleports** (a window appears, un-minimises, is snapped, Mission Control, an app switch reorders): a rect that is
  new or jumped more than 40 px between reads has no meaningful wall velocity. Dots found inside are **expelled** to
  the nearest free face over 0.3 s with an outward velocity of (distance / 0.3 s), a small shock front that heats
  them. That is work done on the gas, so heating is correct.
- **Revealed space** (a window closes or moves away suddenly): the gas streams into the vacuum **without cooling**, as
  an ideal gas does in free expansion. Only a wall that *recedes while touching* the gas cools it. This is the honest
  physics, and it reads well: a slowly dragged-away window leaves a cold dim wake; a closed window just fills in.
- **Rounded window corners and shadows** are ignored (the dots are below the window, so a 10 px error is hidden by the
  window itself).

**Screen boundaries** (Setting).
- *Reflecting*: closed box, `N` conserved; specular reflection at screen edges and walls.
- *Reservoir*: screen edges are open to an imaginary reservoir at the entry temperature and target density. A dot
  crossing an edge is removed; dots are injected along each edge at the effusion rate `n0 * sqrt(T0 / 2 pi)` per px,
  with velocities drawn from the 2D Maxwell flux distribution. So a compressed, hot gas empties out of the screen
  edges and a cold one refills: the reservoir is the thermostat, and density and temperature relax to the Settings by
  themselves.
- *(added) Thermal walls*: closed box, but a dot hitting a screen edge leaves at the reservoir temperature (diffuse
  reflection). N conserved, T relaxes; the middle option.

**Thermostat and the Fermi trap.** A wall that oscillates (a window dragged back and forth, a Dock that bounces)
pumps energy into a closed gas without limit: Fermi acceleration, a real effect that would end in a frantic desktop.
So in every mode: a weak Berendsen thermostat relaxes `T` toward the entry temperature with a time constant of 60 s
(reflecting) or 20 s (thermal walls; reservoir needs none), and a hard per-dot speed cap of 40 px/s that decays any
excess with a 3 s time constant. 40 px/s is under the 60 px/s (1 deg/s) vection line, and only transiently.

**Compression limit.** With a fixed `N` and most of the screen covered (free fraction 0.28 tonight; near 0 with a
maximised window), density can rise 10x. Below a free fraction of 0.15, dots above the target density **condense**:
they fade to a dormant pool (not drawn, not simulated) and re-evaporate as space opens, entering at the gas's current
temperature. Physically a phase change; practically a CPU cap and a guard against a crowded sliver.

**Fields near Sprites.** Sources: each sprite from `hits` (x, y, r at ~10 Hz, interpolated to the step), with a
per-species field signature from a small JSON table (no JS). For a dot at offset `d` from a sprite of radius `r`,
softening `a = r`, cutoff `R = 4 r` (about 120-200 px):
- electric: `E = Q * d / (|d|^2 + a^2)^(3/2)`, a softened point charge; energy-conserving because it is a potential.
- magnetic (out of the screen, scalar in 2D): `Bz = M / (|d|^2 + a^2)^(3/2)`; force `q v x B` integrated with the
  **Boris rotation**, so it does no work and turns dots into **cyclotron arcs of radius `v / (q Bz)`**: hot dots swing
  wide, cool ones curl tight, and `+` and `-` dots curl in opposite senses, so a sprite passing through the gas leaves
  two counter-rotating spiral wakes. Moving sources add the motional field `E' = -v_s x B` (computed in the sprite's
  frame), which is what makes a wake rather than a static whirl.
- species signatures (proposal, all subtle): Choir a slowly precessing dipole; Siphonophores a pure vortex (B only:
  the gas swirls but never gains energy); Sigils a quadrupole (four lobes); Kaleidoscope a slowly rotating hexapole;
  Fireflies a weak attracting charge (dots gather like midges); vector species a dipole aligned with their heading;
  ghosts none. Strength is a Setting.
- only dots within `R` of a source are touched (grid query), so the cost is `O(dots near sprites)`.

**Structures (the "small temporary vector structures").** The owner described two things: dots merging into
something larger, and short linear structures that float, rotate and dissolve. The rule produces both:
1. *Bonding.* Two dots that collide with relative speed below `v_b` (about 0.6 x the thermal speed at the entry
   temperature) bond with probability `p_bond` (the "structure frequency" Setting), if each has a free valence. Valence
   is 2 (chains: the linear rods he saw), and 3 with probability 0.1 (a kink or a triangle).
2. *Rigid bodies.* A bonded group becomes one rigid body: centre of mass, angle, angular velocity, member offsets. A
   free dot hitting a member applies its impulse to the body, linear and angular, so rods spin up when struck off
   centre, which is exactly "floated and rotated". Groups carry the sum of their members' charges and dipole, so **near
   a sprite a rod turns like a compass needle along the field**: iron filings that reveal the field without any field
   line being drawn.
3. *Rocks.* A group of 5 or more folds into a closed outline: drawn as a jagged vector polygon round its members, the
   Asteroids rock. That is "merging into something larger".
4. *Breakup.* Each bond has an Arrhenius lifetime `tau = tau0 * exp(Eb / T_local)` (so a hot gas holds few structures
   and a cold one many), a hard cap of 20-60 s (they are temporary by rule), and an impulse threshold. A rock struck
   above threshold **splits along a random chord into two smaller rocks or rods**, as in the game; fragments under 2
   members evaporate to free dots with the bond energy shared as heat.
5. *Budget.* At most 12 structures alive per screen, so the effect stays an event, not a texture.

### The shared frame policy: the frame rate follows the motion
Each step the sim knows the fastest on-screen dot. The next frame comes after `max(1 px / v_max, 1/24 s)`, clamped to
2-24 fps: a cold, undisturbed Aether drops to 2-4 fps (each dot moves under 1 px per frame, so it looks continuous); a
drag or a sprite passage lifts it to 12-24 fps and it decays back within seconds. While every `BackdropWindow` is
occluded (covered, full screen) the sim **holds time** and nothing is drawn, as the backdrop does today; a static black
window with its last frame costs nothing. Window reads: the existing 2 Hz path when calm; while the drag monitor sees
`leftMouseDragged`, the dragged window's bounds alone (0.158 ms) at the frame rate, for wall velocities.

### A · `MANDRAKEWORKFLOWS_SIMULATE_AETHER_NATIVE_SWIFT_UNDER_THE_ICONS`
**How.** A new `Aether.swift` beside `Backdrop.swift`: the physics core in plain Swift on `SIMD2<Float>` arrays,
stepped on the main run loop by the existing timer pattern (or a utility QoS queue if a step ever exceeds 1 ms).
Rendering reuses `BackdropWindow` (opaque black clear) with one instanced draw: dots as soft analytic discs with a
velocity-aligned streak (a cheap stand-in for phosphor persistence; no full-screen feedback pass), bonds and rock
outlines as 1 px line quads. Inputs: `windowList()`, `windowBounds()`, the drag monitor, `hits` (already in
`Stage.handle`), `visibleFrame`. Settings land in `behaviors.json` (keys under `"aether"`), which the app already
watches every 2 s; **the desktop itself is the preview** (changes apply live).
**Cost.** Sim: 0.04 ms per step at 1 500 measured, x2 for the live cold-run penalty seen in the native port, x2 again
for fields, walls and structures: ~0.15 ms; at an average 6 fps (mostly 2-4 calm, bursts of 24) that is ~0.1 % of a
core. Render: 1.0 % at 12 fps and 1.76 % at 24 fps measured for a toy that also moved the dots, so ~0.3-0.5 % at the
calm 2-4 fps. **Estimate: 0.4-0.8 % calm, 1.5-2 % while dragging, 0 covered.** GPU: one small instanced pass per
frame. WindowServer: unmeasured (starred). Memory: < 1 MB.
**Build.** ~2 agent-days for core, walls and render; ~1-2 for fields and structures; ~1 for Settings and the tuning
sheet. Swift unit tests under `tests/swift/` for wall reflection, adiabatic `T*A`, free expansion, Boris energy,
bond lifetimes (deterministic, seeded).
**Risks.** No in-Settings preview animation (the tab can show a still and say "live on your desktop"). Physics tuning
happens in Swift, slower to iterate than JS in a browser. Window-list quirks (the full-screen Dock and stage windows)
must be filtered by rule, and future macOS chrome may add more.
**Dominates when** the CPU budget is the binding constraint (it is: Sprites is 3-4x over its own target already) and
the live desktop is an acceptable preview.

### B · `MANDRAKEWORKFLOWS_COMPUTE_AETHER_ON_GPU_FOR_DENSE_DUST`
**How.** The same core as Metal compute kernels: integrate, counting-sort into a grid, collide per cell, walls from a
small uniform buffer of rects, fields from a buffer of sources; render straight from the GPU buffer. Structures stay on
the CPU (a few hundred bonded dots), reading back a compacted list of slow collisions each frame.
**Cost.** CPU ~0.2-0.3 % (encode only); GPU time per frame trivially small at 1 500-10 000 dots; but the GPU is woken
at the same frame rate as A, so energy is roughly A's at low N. Beats A only where A's CPU sim grows: 10 000 dots is
0.5 ms per step on the CPU (measured), 100 000 would be ~5 ms.
**Build.** ~5-8 agent-days: GPU collision with atomics or sorting is fiddly; rigid structures split across CPU and GPU
is the hard part; debugging needs GPU frame capture.
**Risks.** Determinism (atomic ordering) makes tests weaker; a CPU-GPU readback each frame adds latency; most of the
effort buys density the brief does not ask for.
**Dominates when** the owner wants "dust": 20 000+ dots, a nebula rather than Asteroids.

### C · `MANDRAKEWORKFLOWS_SHARE_AETHER_JS_CORE_DRAWN_BELOW_THE_ICONS`
**How.** The physics core as `app/aether/aether.js`, one source run three ways: in a second in-process JSContext
(like the stage) producing a Float32Array of instances each frame, which Swift renders into `BackdropWindow` exactly as
in A; in Settings' WebView as a live animated preview on a canvas; and in node for headless tests, as the stage's
tests run today.
**Cost.** JS step measured equal to Swift in a tight loop (0.042 vs 0.038 ms); the native port measured ~2x worse live
in JSC; a second JSContext adds GC and JIT threads and its own timer wakeups. **Estimate: A plus 0.3-0.5 %**, i.e.
0.7-1.3 % calm.
**Build.** ~3 agent-days plus the bridge (~1): the shim and the typed-array handoff exist already.
**Risks.** The JSC overhead that has kept Sprites above 3 % is exactly the thing this adds more of. Two JSContexts on
one main thread compete for frame slots.
**Dominates when** a live Settings preview, or fast physics iteration by agents in node and the browser, is worth
~0.4 % of a core all day.

### D · `MANDRAKEWORKFLOWS_BORROW_SPRITEKIT_FIELDS_MEASURED_TOO_HUNGRY` (rejected by measurement)
`SKView` in the backdrop window, one `SKPhysicsBody` per dot with `charge`, an `SKFieldNode` electric plus magnetic
pair per sprite, `SKPhysicsJointFixed` for structures. It would be running in a day and look right. Measured 13-58 % of
a core at 1 000-3 000 bodies and 12 fps: 15-50x the budget. Useful only as a one-day look prototype to show the owner
before A is built, and even then A's toy is nearly as fast to write.

### E · `MANDRAKEWORKFLOWS_FAKE_AETHER_IN_A_STATELESS_SHADER_NO_PHYSICS` (rejected by the brief)
A fragment shader computes dot positions as a function of time and samples a window-mask texture. ~0.3 % and no state,
but dots cannot be pushed, cannot heat, cannot collide or bond: it fails elements 3, 4, 5 and 10. Recorded so nobody
proposes it later.

### Comparison
| | A native Swift | B GPU compute | C shared JS | D SpriteKit | E shader fake |
|---|---|---|---|---|---|
| calm CPU (est.) | **0.4-0.8 %** | 0.3-0.6 % | 0.7-1.3 % | 13 %+ (measured) | ~0.3 % |
| dense (10 k) | 0.5 ms/step, OK at low fps | best | 0.45 ms/step | impossible | n/a |
| every brief element | yes | yes | yes | yes | **no** |
| Settings live preview | no (desktop is the preview) | no | **yes** | no | yes |
| build | ~4-5 d | ~6-9 d | ~4-5 d | ~1 d | ~1 d |
| testability | Swift tests, seeded | weaker | **node tests** | poor | n/a |

---

## 4. Experience design (applies to A, B and C alike)

### 4.1 The look and the Settings
**The look.** Pure black (the backdrop window is opaque black; the wallpaper is never touched). Dots are one hue,
default a dim **P1 phosphor green** (the concert, the vector-monitor era), tiny, with a soft core and a
velocity-aligned streak 1-3 px long. Temperature shows as brightness and a slight shift toward white-green for hot
dots; **cold never goes blue-grey** (VPN lost owns that). Bonds and rocks are 1 px vector lines at half the dots'
brightness. No glow halos (halos belong to sprites; this is what keeps a dot from ever reading as a sprite). Default
brightness inside the luminance budget: dots at sRGB code ~40-70 on single-pixel-scale points, mean luminance well
under 0.5 % (1 500 dots of ~4 lit px each are 0.15 % of the pixels). The concert was brighter than this; see §6.

**Settings → a new "Aether" tab replacing "Backdrop"** (or Aether as the first choice in it; §6):
| knob | values | default | maps to |
|---|---|---|---|
| Aether | on / off | on | the backdrop window carries it, or "none" |
| Temperature (entry) | Frozen / Cool / Mild / Warm / Hot (shown as px/s: 0.5 / 3 / 8 / 16 / 28) | **Cool** | reservoir `T0`; thermostat target |
| Boundaries | Reservoir (enter and leave) / Thermal walls / Reflecting | **Reservoir** | §3 boundaries |
| Density | Sparse / Light / Medium / Dense (per megapixel of **free** desktop: 300 / 800 / 1 500 / 3 000) | **Light** | `n0`; dot budget scales with free area |
| Structures | Never / Rare / Sometimes / Often | **Rare** | `p_bond` 0 / 0.02 / 0.08 / 0.25, and `Eb` |
| Particle size | 1 / 1.5 / 2 / 3 px | **1.5 px** | visual radius (collision radius held at ~6 px) |
| Sprite fields | Off / Subtle / Vivid | **Subtle** | `Q`, `M` scale |
| *(added)* Colour | Phosphor green / Amber / Vector white / Session hues | green | single hue; "session hues" tints dots that a sprite has captured |
| *(added)* Brightness | 3 steps | middle | code ceiling |
| *(added)* Desktop icons | Ignore / Obstacles / Obstacles + halos | Obstacles | §4.3 (needs the Finder grant) |
| *(added)* Hold still while typing | on / off | on | §4.5 |

Frozen temperature is the owner's "cool, barely moving unless struck" taken to its end: dots sit still, the window
policy drops to no frames at all, and only a disturbance wakes them (the cheapest mode; it is solution E's CPU with A's
physics).

### 4.2 Windows, Dock, menu bar, full screen, Spaces
- **Windows** are walls whether focused or not (layer 0, other apps, alpha > 0). Dragging pushes the gas with a bow
  wave; compressed gas in a narrow channel between two windows brightens (hotter); slowly pulling a window away leaves a
  cold, dim wake that warms back over a minute. Resizes push and pull the same way.
- **Our own windows** (stage, dim, Settings) are never walls.
- **Dock**: a wall band from `visibleFrame`, never the Dock's full-screen layer-20 window. Auto-hide sliding is a
  moving wall. Magnification is ignored (too fast, too frequent: distraction).
- **Menu bar**: a ceiling. Each status item is a small bump hanging from it, so dots ricochet among the tray icons.
- **Full screen** and **covered desktop**: zero frames, time held (existing occlusion pause).
- **Spaces**: a Space change swaps the whole wall set at once. Without care every dot is "inside a new window" and a
  storm follows. So the default keeps **one gas per Space** (state keyed by the Space id the wallpaper book already
  computes; at most 8 kept), each frozen while away and resumed as left. §6.
- **Multiple monitors**: one world (`spanLayout`), so a dot can cross a shared screen edge; gaps and non-shared edges
  are walls.

### 4.3 Icons, tray, shortcuts, notifications
- **Desktop icons** (needs Automation → Finder for Sprites; the owner has authorised granting permissions): each icon
  is a circular obstacle of the icon's size, refreshed when `~/Desktop` changes (FSEvents), after a drag that ends on
  bare desktop, and every 60 s while the desktop is exposed; 0.21 s per refresh, off the main thread. With "halos",
  icons carry a faint attracting charge only after 5 minutes of no input, so an idle desktop's gas slowly settles into
  rings round the icons like filings round magnets, and scatters the moment work resumes. *Distraction: low (only when
  idle).* Without the grant: "Ignore" (dots pass under the icons; the DimLayer already shades them).
- **Dragging an icon** (drag monitor, no window under the cursor) sweeps a path through the gas, a moving obstacle at
  the cursor. *Low.*
- **Menu-bar tray**: opening any menu (a status item's or an app's) drops a menu window, a wall falling into the gas:
  a puff downward that the user caused. *Low.* Sprites' own status item is the **vent**: in reservoir mode, a third of
  the injected dots enter from under it, so new aether "comes from Sprites". *Low.*
- **Notifications**: a banner sliding in at top right is a moving wall: a small compression puff at the corner, cooling
  as it leaves. *Low-medium* (it adds motion next to something already asking for attention; it never adds a second
  attention cue, and it can be switched off with the tray item).
- **Shortcuts**: keyboard shortcuts already reshape the windows (⌘Tab reorders, ⌘M minimises, ⌘W closes, Mission
  Control, tiling), and the walls physics answers every one honestly with no special code. Added hotkeys, both
  user-initiated, both zero risk: **Exhale** (sweep the gas to the screen edges, for a screenshot or a share; it
  drifts back) and **Stir** (one gentle heat pulse, for the fun of it). Whether these get global hotkeys is §6.
  Desktop *alias* shortcuts are icons and behave as icons.
- **Cursor**: no interaction by default (it would be constant motion under the eye). Optional: over bare desktop and
  still for 2 s, the cursor becomes a weak charge. *Medium if on; off by default.*

### 4.4 How the Sprites' fields look
No field lines, ever (lines are drawing, and drawing is attention). The field is shown only by what the gas does:
cyclotron arcs, two counter-rotating spiral wakes behind a moving sprite, rods turning like compass needles in a
dipole, four-lobed eddies round a Sigil. Near a hovered sprite (labels already appear on hover) the field strength
rises for 2 s, so hovering "lights up its magnetosphere": a reward for curiosity, never unprompted. A sprite at rest in
calm gas leaves a slowly turning disc of captured dots, a small planetary system. Sprites inside the focused-window
avoidance zone are in front of windows, where there is no gas: the effect only happens where the desktop shows, which
is also where it cannot distract.

### 4.5 Quiet behaviour
| condition | Aether does | why |
|---|---|---|
| typing (keys or scroll in the last 1.5 s) and "hold still" on | fps capped at 4, fields at 30 %, no new bonds | the periphery goes still while he works; physics continues, slower |
| idle 5 min+ | cools 30 %, structures form more (cold), icon halos | the desktop "sleeps" visibly and it costs less |
| away / locked / display asleep | stopped (existing) | |
| meeting mode, hidden | stopped (existing `visibilityPlan`) | |
| Reduce Motion | static last frame (existing) | |
| Low Power Mode | fps cap 6, density x0.5 | `isLowPowerModeEnabled` |
| on battery < 20 % | static last frame | MACHINE_BACKGROUNDS rule |
| thermal serious / critical | fps cap 4 / static | `thermalState` |
| full screen / covered | no frames (existing) | |
| sprite in needs-you | gas within 300 px of it cools and dims | the one cue that matters is never competed with |

### 4.6 "Impress us" ideas, each with its distraction risk
1. **Asteroids, literally.** Rocks are jagged vector outlines; a hard hit splits a rock in two along a chord, fragments
   tumble apart, small ones evaporate to dots. *Risk: low* (rare by rule, slow, peripheral).
2. **Honest thermodynamics.** Squeeze the gas between two windows and the channel glows; drag a window away slowly and
   the wake goes dim and cold; close a window and the gas floods in at the same temperature (free expansion). The
   physics is right, which is the joke for anyone who knows it. *Risk: low* (only during his own window moves).
3. **Magnetospheres.** Counter-rotating spiral wakes behind travelling sprites; rods aligning as compass needles near
   them; a resting sprite's tiny planetary system. *Risk: low-medium*; "Subtle" default, 120-200 px reach.
4. **Species signatures.** Each species bends the gas its own way (dipole, vortex, quadrupole, hexapole, midge cloud),
   so a glance at the gas near a sprite says which kind it is. *Risk: low.*
5. **A finished session's exhale.** On `celebrateDone`, the sprite's field flips once, flinging a few nearby dots
   outward: a puff, not a ring (rings are reserved for needs-you). *Risk: medium*; it piggybacks on an existing cue
   rather than adding one, and is off under strain like the cue itself.
6. **Night crystal.** After long idle the gas cools until structures dominate: a slow, sparse lattice of rods and
   triangles. The first keystroke warms it and it melts over 10 s. *Risk: none* (he is away).
7. **The vent.** New aether enters from under Sprites' own menu-bar icon, so the app is visibly the source. *Low.*
8. **Exhale and Stir hotkeys.** *None* (user-initiated).
9. **One gas per Space.** Every desktop keeps its own weather. *None.*
10. **Rare guest, off by default.** Once a day at most, while idle, a tiny vector saucer crosses and is "shot" to dots
    by a fast particle. *Medium*; strictly an easter egg; §6.
11. **Maxwell's demon, off by default.** A rare one-minute event where a tiny gate on a window edge lets only fast dots
    through, so one side glows and the other dims, then it gives up. *Medium*; §6.
12. **The distracted key.** A hotkey that logs "that distracted me" with the Aether's state (fps, T, structures,
    nearest sprite, what moved) to `~/agent-storage/sprites/aether/distractions.jsonl`. It is the success metric and the
    tuning loop at once. *None.*
13. **The machine's own heat (decision, off by default).** Entry temperature follows the CPU package temperature from
    Augur. Delightful and true, but it double-encodes strain, which the sprites already carry. *Medium.*

---

## 5. Recommendation

**Build A (`MANDRAKEWORKFLOWS_SIMULATE_AETHER_NATIVE_SWIFT_UNDER_THE_ICONS`)**, with the shared physics core and the
motion-following frame policy, hosted in the existing `BackdropWindow`, and retire the twelve moving backdrops'
live mode once the owner accepts it (no duplicates). Defaults: Cool, Reservoir, Light density, Rare structures,
1.5 px, Subtle fields, phosphor green, hold still while typing.

Why:
1. **CPU is the binding constraint and Sprites is already 3-4x over its own target.** A is the cheapest design that
   meets every element of the brief: physics measured at 0.04 ms per step and render at 1.0 % at 12 fps on the very
   window type it will use, so the estimate of 0.4-0.8 % calm at 2-4 fps rests on measurements, not hope. C costs
   about half as much again for a preview; B costs a week for density nobody asked for; D is measured 15-50x over.
2. **Almost nothing new is plumbed.** Window rects, drag detection, sprite positions, Dock and menu-bar geometry,
   status-item rects, Space identity, pause conditions and the black Metal window all exist. The new code is the sim
   and one shader.
3. **The frame policy is the real CPU win, whichever engine.** A cold, undisturbed gas costs 2-4 frames a second, a
   covered desktop none; motion only costs frames when he made it or a sprite did.
4. **The desktop is the preview.** Settings already applies live within 2 s; a still in the tab plus "look at your
   desktop" is honest and cheap.

What would change my mind:
- **WindowServer charges a full-screen opaque Metal window much more than its app-side 1 %** (unmeasured tonight; the
  same cost lands on A, B and C, but if it is large, the fix is a lower drawable scale or a sparse-tile layer, and the
  calm fps floor must drop to 1-2).
- **The owner wants a live animated preview in Settings**, or wants to tune the physics himself in a browser: then C,
  accepting ~0.4 %.
- **He wants dust, not Asteroids** (density "Dense" too thin at 3 000 per free megapixel): then B.
- **The A toy, rebuilt with walls and fields, measures over 1.5 % calm on battery**: then B's CPU path or a lower
  density default.
- **"Noticed while working" logs stay above 1 per 2 hours after a week** at the defaults: the answer is not another
  engine but Frozen as the default temperature (no frames unless disturbed).

First build steps (for the merge pass to keep or cut): the toy in `~/agent-storage/scratch/aether/mt.swift`
grows into `Aether.swift` with walls and the frame policy (day 1); measure calm CPU passive on battery, and WindowServer
on Lab Wi-Fi with the VPN off (`MANDRAKEWORKFLOWS_MEASURE_AETHER_WINDOWSERVER_COST_ON_Lab_WIFI`); then fields, then
structures, then Settings; a review sheet of 12 stills and 4 clips for the owner's eye, checked on the mini-LED panel
at minimum brightness (`MANDRAKEWORKFLOWS_CHECK_AETHER_BLOOM_ON_MINILED_BLACK`: dim points on pure black can bloom
or crush).

---

## 6. Open decisions for the owner

1. `MANDRAKEWORKFLOWS_DECIDE_AETHER_RETIRES_OR_JOINS_BACKDROPS`: **(a)** the Aether replaces the moving backdrops (the
   12 stay only as static wallpaper stills), or **(b)** it becomes one more choice in the Backdrop tab, or **(c)** it
   replaces all 12 entirely. Recommendation (a): no duplicates, but the stills cost nothing.
2. `MANDRAKEWORKFLOWS_CHOOSE_AETHER_COLOUR_PHOSPHOR_OR_VECTOR_WHITE`: phosphor green (the concert) / amber / vector
   white / session hues. Recommendation: green.
3. `MANDRAKEWORKFLOWS_DECIDE_AETHER_BRIGHTNESS_ABOVE_THE_OLD_BUDGET`: keep the backdrop luminance budget (mean
   <= 0.5 %), or allow the concert's brighter dots (single points up to ~8 %, still a tiny mean). Recommendation: keep,
   with the Brightness knob going one step above.
4. `MANDRAKEWORKFLOWS_DECIDE_AETHER_ICONS_COST_A_FINDER_GRANT`: grant Sprites Automation → Finder so icons are
   obstacles (and halos), or let the gas ignore icons. Recommendation: grant.
5. `MANDRAKEWORKFLOWS_DECIDE_SPRITE_FIELDS_CARRY_NO_DATA`: fields are decorative (species signature, constant
   strength), or strength follows the session's state (working stronger, idle weaker). Recommendation: decorative; the
   sprites already carry the data and a second encoding invites misreading.
6. `MANDRAKEWORKFLOWS_DECIDE_AETHER_VISIBLE_IN_SCREEN_SHARES`: today's backdrop window shows in shares and screenshots
   while the sprites do not. Hide the Aether from shares too (black shows instead), or show it. Recommendation: hide,
   matching the stage and dim layer.
7. `MANDRAKEWORKFLOWS_DECIDE_AETHER_HOLDS_BREATH_WHILE_TYPING`: on (fps cap 4, fields damped while typing) or off.
   Recommendation: on.
8. `MANDRAKEWORKFLOWS_DECIDE_AETHER_KEEPS_ONE_UNIVERSE_PER_SPACE`: one gas per Space, or one shared gas that reflows
   on every switch. Recommendation: per Space.
9. `MANDRAKEWORKFLOWS_DECIDE_AETHER_GETS_ITS_OWN_STIR_HOTKEY`: global hotkeys for Exhale and Stir, tray-menu items
   only, or neither. Recommendation: tray items, plus Exhale on a hotkey.
10. `MANDRAKEWORKFLOWS_DECIDE_AETHER_EASTER_EGGS_DEFAULT`: the saucer and Maxwell's demon off, rare, or cut.
    Recommendation: off by default, present in Settings.
11. `MANDRAKEWORKFLOWS_DECIDE_AETHER_FEELS_THE_MACHINE_HEAT`: entry temperature follows the CPU temperature, or stays
    a Setting. Recommendation: stays a Setting.
12. `MANDRAKEWORKFLOWS_DECIDE_AETHER_FRAME_CAP_ON_BATTERY`: on battery, cap at 12 fps (calm unchanged), or at 6.
    Recommendation: 12, measured before shipping.

---

## 7. Claims table

`*` = the recommendation would change if this were wrong.

| # | claim | status | how |
|---|---|---|---|
| 1* | Hand-written hard-disc step with a grid hash: 0.038 ms (1 500), 0.133 ms (4 000), 0.507 ms (10 000) in Swift | **measured** | `sim.swift`, 100 steps after 5 warm-up, M1 Max, load 6-18 |
| 2 | The same in JS (node 26): 0.042 / 0.122 / 0.453 ms | **measured** | `sim.js`, 100 steps after 20 warm-up |
| 3* | Metal instanced dots in a full-res 3456 x 2234 opaque window: 1.01 % of a core at 12 fps, 1.76 % at 24, 0.31 % at 4 fps (4 000 dots), app side | **measured** | `mt.swift`, getrusage over 5 s, one run each |
| 4* | SpriteKit with charged bodies and E/B fields: 13.3-13.7 % at 1 000 bodies, 38.0-57.8 % at 3 000, 12 fps | **measured** | `sk.swift`, `sk2.swift`, getrusage over 4 s |
| 5* | WindowServer's added cost for the Aether window is small (<= 1 %) | **unmeasured** | 6 s `ps` deltas were within noise (45.0-46.7 % vs 46.7 %); needs a quiet machine |
| 6* | A's calm total is 0.4-0.8 % of a core, 1.5-2 % while dragging | **estimated** | from 1 and 3, x2 live JSC-style cold penalty (by analogy, Swift may not suffer it), x2 for walls/fields/structures, 2-4 fps calm |
| 7 | C costs ~0.3-0.5 % more than A | **estimated** | from the native port's measured live-vs-loop JSC penalty (0.34 vs 0.18 ms) and a second context |
| 8 | B's build is ~6-9 agent days, A's ~4-5 | **estimated** | judgement |
| 9 | Sprites uses 9.7-13.3 % of a core right now | **measured** | `ps`, `top -l 2 -pid`, this session |
| 10 | Sprites' standing calm target is <= 3 %; post-port passive was 7.0-7.7 % | **measured (by others)** | `docs/NATIVE_PORT.md`, `docs/NATIVE_PORT_HANDOFF.md` |
| 11* | `BackdropWindow` is an opaque black Metal window at desktop+1, below icons, paused when occluded/locked/asleep/hidden/Reduce Motion, and does not write the wallpaper in live mode | **read in code** | `Backdrop.swift` |
| 12* | Sprite positions and radii already reach Swift at ~10 Hz | **read in code** | `Stage.swift` `handle`, `stage.html` hits forwarder (100 ms) |
| 13 | A global mouse-drag monitor already exists, no TCC grant | **read in code** | `App.swift` `addGlobalMonitorForEvents([.mouseMoved, .leftMouseDragged])` |
| 14 | Full window list costs 0.37-0.55 ms per call warm, 1.4-2.3 ms first call; one window's bounds 0.158 ms | **measured** | `br.swift`, `one.swift`, `wl.swift` |
| 15* | The window list contains a full-screen layer-20 (Dock) window with alpha 1 and Sprites' full-screen layer-3 stage, so walls must be layer-0 plus explicit chrome | **measured** | `free2.swift` listing |
| 16 | Status items are 18 layer-25 windows with rects, readable without AX | **measured** | `free2.swift`, `one.swift` |
| 17 | Free desktop fraction tonight 0.28 (two windows) | **measured** | rect arithmetic, one sample |
| 18 | Finder icon positions: 0.21 s for 6 icons; needs an Automation grant for the Sprites app | **measured** (time) / **assumed** (the app needs its own grant; the terminal had one) | one `osascript` call |
| 19 | Mean free path ~150 px (d 3) and ~76 px (d 6) at 1 500 dots in half the screen | **calculated** | `1 / (sqrt 2 n d)` |
| 20 | Moving-wall reflection `v' = 2u - v` reproduces adiabatic heating; 2D gamma = 2; free expansion leaves T unchanged; Boris rotation conserves speed | **standard physics** | textbook kinetics and PIC |
| 21 | Without a thermostat, an oscillating wall heats a closed gas without bound (Fermi acceleration) | **standard physics** | |
| 22 | Coherent motion should stay far below ~60 px/s (1 deg/s) to avoid vection; luminance budget mean <= 0.5 % | **cited by others** | `visualize/docs/MACHINE_BACKGROUNDS.md` |
| 23* | The live desktop is an acceptable Settings preview | **assumed** | owner's call (§5 "change my mind") |
| 24 | A static layer costs nothing | **measured (by others)** | `docs/SHIP_PLAN.md`, DimLayer test |
| 25 | Bonds at 0.6 x thermal speed with p 0.02-0.25 give "rare to often" structures; 12 alive per screen is "an event, not a texture" | **assumed** | to tune on the review sheet |
| 26 | `BackdropWindow` lacks `sharingType = .none` while the stage and dim layer have it | **read in code** | `grep sharingType` |
| 27* | No more than ~1 distraction log per 2 hours is reachable at the defaults | **unmeasured** | week-one test |

Starred claims: **10** (1, 3, 4, 5, 6, 11, 12, 15, 23, 27).
