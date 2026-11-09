# The Aether: merged design (Deep-Design-3x2, step 5)

Run: `~/dev/MandrakeWorkflows/sprites/docs/design/2026-11-08-aether/`. Inputs: `PROBLEM.md` (the owner's
words), `01-design.md` (pass 1), `02a-gpt-blind.md` (GPT blind), `02-gpt.md` (GPT critique of pass 1, authorship
hidden), `02m-remeasure.md` (starred claims re-measured). All passes ran in full; no optional second Opus pass (GPT
was available and the decision is cheap to reverse: nothing is built yet). Provenance tags: **[P1]** pass 1,
**[GB]** GPT blind, **[GC]** GPT critique, **[RM]** re-measure, **[M]** this merge.

## What the Aether is (the experience, after review)

Pure black where the desktop shows. On it, a thin luminous gas of small phosphor-green points **[P1][GB]**, living
only outside every window, focused or not **[owner]**. Most points drift so slowly you notice their movement only
after a few seconds **[GB]**. Drag a window and its leading edge pushes a soft pressure front through the gas; the
squeezed channel between two windows glows a little hotter; space a window leaves behind refills gently rather than
sitting empty for minutes **[P1][GC]**. A Sprite passing through bends the gas into two faint counter-curling wakes,
and the occasional short chain near it turns like a compass needle **[P1]**, the field shown only by what the gas
does, never by drawn lines **[P1]**. Now and then a few points meet slowly, lock into a tiny rotating needle, drift,
and come apart again **[owner][P1][GB]**. Larger "Asteroids rocks" that fold and split come later, if the chains are
quiet and convincing first **[GC]**.

The governing rule is **bounded surprise** **[GB]**: something interesting may happen locally, never a desktop-wide
spectacle, and never a second attention cue next to one that is already asking for him **[P1]**.

## The options (final set)

Every pass converged on the same engine. All three agree that a native CPU simulation drawn by Metal is the right
first build: pass 1 calls it A, GPT blind calls it C and picks it, GPT critique agrees ("best first implementation").
The real choices are therefore less about the engine than about how alive the gas is and how much of it there is.

| option | how | calm CPU (one core) | buys | costs | dominates when | from |
|---|---|---|---|---|---|---|
| **A · Native Swift sim + Metal draw** in the existing black `BackdropWindow`, under the icons | Swift arrays + grid hash, swept walls, three clocks; one instanced draw | **0.4-1.2 %** est. (re-measured upper bound 1.2 % **[RM]**); ~2.5 % while dragging **[GC]** | cheapest that meets the whole brief; almost all plumbing exists | no animated preview in Settings unless built separately; tuning in Swift | CPU is the binding constraint (it is) | P1, GB, GC |
| **A′ · A with "stir and settle"** as the default motion style | same engine; gas cools to stillness 8-15 s after a disturbance and the frame is held | **~0.1-0.3 %** est. (frames only after a window move or a sprite passage) | near-zero cost; the owner's "cool, barely moving unless struck" | the desktop is mostly still; whimsy only when something moves | battery or distraction turns out to bind | owner, GB, P1 ("Frozen") |
| **C · Shared JS core**, drawn natively, also run live in Settings and in node tests | the stage's JSContext steps the gas; typed buffer to Swift | A + **0.03 % compute** (GC arithmetic) + an **unmeasured** second-context/GC overhead; P1 guessed +0.3-0.5 % | live Settings preview; agents iterate physics in a browser; node tests | the JSC runtime is exactly what keeps Sprites over budget today | the owner wants to tune it live in Settings | P1, GC (cost corrected) |
| **B · Metal compute dust** | integrate, sort, collide on the GPU | CPU ~0.2-0.3 %; GPU woken at the same rate, so energy ≈ A at low N | 10 000-100 000 points: a nebula | 6-9 agent-days; weaker tests; readback | he wants dust, not Asteroids | P1, GB |

Rejected, recorded so nobody re-proposes them: SpriteKit physics bodies + fields, **measured 12-58 % of a core**
(**[P1]**, reproduced by **[RM]**: 11.9-51.2 %); a stateless shader fake that cannot push, heat or bond **[P1]** (GC
notes a procedural ambient layer could complement a small stateful population; not needed at these counts).

**Compositions.** A and A′ are one engine with two motion styles, so the owner gets both: A′ is simply A's coldest
setting with the frame held. C's preview can be added later on top of A by running the same rules in the Settings
WebView only while the tab is open (cost only while it is open). B is a later swap of the step function, not a fork.

## Recommendation [M]

**Build A, with stir-and-settle available as the "Still" temperature, and ship a deliberately small first release**
**[GC]**: particles, robust exclusion from every window, bounded window push, both boundary modes, one subtle sprite
interaction, particle size and the thermodynamic controls he asked for. Add short chains in release 2 once release 1
meets the CPU and distraction budgets; rocks, fragmentation and decorative extras after that.

Why: every pass picked this engine; the physics step is cheap and was reproduced **[RM]**; the expensive unknowns are
the same for every engine (window tracking and the compositor), so they are measured first, not designed around.

One sobering fact sits behind the budget: **Sprites already uses 9.7-13.3 % of a core** (measured by pass 1 in this
run) against its own ≤ 3 % target. The Aether's ~1 % is small next to that, but it is additive to an app already over
budget. The Aether build should not be blamed for, or block on, that existing overrun, which already has its own work.

## Corrections the review forced (all adopted)

1. **Swept collisions against the union of obstacles [GB][GC].** Pass 1 tested "ended the step inside a window". That
   misses a narrow window crossing a point between samples, thin obstacles, overlapping windows ejecting into each
   other, resizes, and gaps closing below the collision diameter. Walls become the union of window rectangles expanded
   by the collision radius; edges are swept between geometry samples; a point that has no valid place fades and
   re-enters later instead of being thrown.
2. **Three clocks, not one [GC].** Geometry (2 Hz calm, ~12 Hz while the drag monitor sees a drag, plus immediate
   reconcile on app activation and Space change **[GB]**), simulation (fixed step with bounded substeps), and
   presentation (its own budget). The frame rate is **not** set by the fastest point: with 1 500 points at Cool the
   Maxwell tail is ~2.7x RMS, so "one pixel per frame for the fastest" forces ~8 fps, not the 2-4 pass 1 budgeted
   (**[GC]**; confirmed by **[M]**: the expected maximum of 1 500 2-D Maxwell speeds is σ√(2 ln N) ≈ 3.8σ = 2.7 x RMS).
   Presentation follows the 90th-percentile displacement and an explicit cap; outliers are speed-limited instead.
3. **Speed limits that are real [GC].** Pass 1's "40 px/s cap that decays excess over 3 s" allowed bursts of 400-1000
   px/s on window impacts and teleports. Now: a strict displayed-speed ceiling, bounded wall impulses, slow temperature
   relaxation, and geometry recovery by fading, never by expulsion at speed.
4. **Revealed space refills on purpose [GC].** At Cool (3 pt/s) an 800 pt opening takes ~4.5 minutes to refill by
   physics alone, and a receding window cannot cool points that never catch it, so pass 1's "cold dim wake" would
   rarely appear. Adopted: a small **revealed-space reserve** that seeds newly exposed desktop gently at the gas's
   temperature, and an optional bounded "entrainment" behind a moving window, both declared as visual physics, not
   kinetics.
5. **The thermostat is an artistic control [GB][GC].** "Fermi acceleration without bound" is not universal, and a weak
   Berendsen thermostat does not guarantee a ceiling under continuous forcing. Kept as: thermal screen edges as the heat
   bath, reservoir exchange only where a region actually connects to an open edge (a pocket enclosed by windows
   cannot), and a separate damping policy for persistent forcing and trapped pockets. Temperature is measured relative
   to local flow, so a whole drifting cloud is not "hot" **[GB][GC]**.
6. **Density is defined once, in logical points [GB][GC].** Pass 1's "per megapixel of free desktop" was ambiguous by
   4x (432 vs 1 729 points at Light, logical vs backing pixels) and contradicted reflecting mode's conserved N.
   Now: simulation geometry in points; density = initial population (reflecting) or reservoir density (open), per
   million logical square points; suspension into a dormant pool is an explicit capacity policy for crowded pockets.
   Particle size is stated as a **diameter**, with the collision diameter separate from the drawn core.
7. **Mean free path was off by 2x [GC].** In 2-D the hard-disc cross-section is 2d, so λ ≈ 1/(2√2 n d): ~76 pt at
   d = 3 and ~38 pt at d = 6, not pass 1's 150 / 76 (**[M]** checked: n = 1 500 / 965 000 pt² gives 75.8 pt at d = 3).
   Collisions are twice as frequent as pass 1 thought, so a collision diameter of 3-4 pt under a ~2 pt core is enough
   for visible "Asteroids hits"; pass 1's 6-8 pt would be too sticky.
8. **Fields are tunable behaviours, not eleven EM recipes [GB][GC].** A static magnetic field cannot start a
   stationary point moving or capture it into a "planetary system"; a charged rod does not align like a compass
   without a dipole or alignment term. Kept: softened attraction/repulsion, sideways (Boris) deflection, wake
   entrainment and rod alignment as separate knobs, fading out within ~80-200 pt **[GB][P1]**; a few field families
   shared across species rather than one per species, prototyped one at a time.
9. **Structures are a second physics system [GC].** Release 2 does chains of 2-5 with a straightening constraint, a
   stochastic lifetime that updates with local temperature (4-12 s typical, hard cap) **[GB][GC]**, momentum conserved
   at bonding, and a small bounded release on breakup, at most ~2 chains per display and roughly one formation chance
   every 20-60 s in work hours **[GB]**. Rocks, chord fracture and folding come only after.
10. **macOS facts corrected [GC][RM].**
    - `NSWindow.sharingType = .none` is documented by Apple as a legacy constant macOS no longer honours; hiding the
      Aether from screen shares cannot be promised. Meeting mode (which already hides Sprites) hides the Aether too.
      *(Unverified here beyond GC's citation; it changes a promise, not the build, so the safe behaviour is adopted.)*
    - `visibleFrame` is a safe content rectangle, not a Dock-animation stream: the Dock is a stable exclusion band;
      auto-hide sliding is optional polish.
    - Window alpha is not an opacity mask; layer numbers are observations, not an API. The classifier is conservative,
      with explicit exclusions, and is tested against sheets, palettes, menus, Spotlight and notification banners.
    - Sprites' own **Settings window is a window** under the owner's rule and must be a wall; only the stage, dim
      layer and backdrop are exempt. Pass 1 exempted all of Sprites' windows.
    - A full-width layer-24 menu-bar window exists and counts as chrome **[RM]**. Status-item "bumps" only exist if
      deliberately drawn to protrude below the menu bar.
    - Display-link frame-rate ranges are best effort; occlusion `.visible` means "at least part visible", so a tiny
      exposed strip keeps the backdrop drawing.
11. **Memory is ~59 MiB, not < 1 MB [GC].** Two 3456 x 2234 BGRA drawables are 58.9 MiB; "< 1 MB" was the simulation
    state only. A lower drawable scale is the obvious lever if the compositor cost turns out to dominate.

## Claims after the re-measure

| # | claim | pass 1 | now | trust |
|---|---|---|---|---|
| 1* | hard-disc step, 1 500 points | 0.038 ms | 0.050 ms (fresh C re-implementation; old Swift binary within 3 %) | RM, same scaling |
| 3* | Metal instanced dots, app side, 12 / 24 / 4 fps | 1.01 / 1.76 / 0.31 % | 0.81 / 1.85 / 0.28 % | within noise (load 9-13, ±0.2 pt) |
| 4* | SpriteKit at 1 000 / 3 000 bodies | 13-14 / 38-58 % | 12-17 / 39-51 % | rejection stands |
| 5* | WindowServer cost of the Aether window ≤ 1 % | unmeasured | **deferred: needs Lab Wi-Fi, VPN off, quiet machine** | open; the biggest unknown |
| 6* | A's calm total | 0.4-0.8 % | **0.4-1.2 %**; dragging ~2.5 % by GC's arithmetic | estimate; never measured in the app |
| 7 | C's extra cost over A | +0.3-0.5 % | compute +0.03 % (GC arithmetic, checked); second-context overhead unmeasured | unverified |
| 11*, 12*, 15* | backdrop host, sprite positions, window-list filtering | read in code | confirmed, with caveats: live mode only; 10 Hz is a ceiling (nothing posts when sprites are still); layer-24 menu-bar window **[RM]** | RM |
| 19 | mean free path | 150 / 76 pt | **76 / 38 pt** | GC, checked by M |
| new | max-speed frame rule at Cool | 2-4 fps | ~8 fps | GC, checked by M |
| 23*, 27* | desktop as preview acceptable; ≤ 1 distraction per 2 h | assumed / unmeasured | owner's call / week-one test | open |

## Reviewer findings and their status

| finding | status |
|---|---|
| Mean free path factor of 2 | **confirmed** (arithmetic, M) |
| Fastest-point frame rule gives ~8 fps, not 2-4 | **confirmed** (order-statistic arithmetic, M) |
| C's compute delta ≈ 0.03 %, not 0.3-0.5 % | **confirmed for compute**; the context/GC overhead behind P1's figure is unmeasured |
| Drawable memory 58.9 MiB | **confirmed** (arithmetic) |
| Luminance share 0.078 %, not 0.15 % | **confirmed** (6 000 / 7.72 M px); minor |
| Endpoint-inside wall test misses sweeps and overlaps | **confirmed by construction** (the listed cases follow from the rule as written) |
| Receding window cannot cool at Cool; refill takes minutes | **confirmed** (800 pt / 3 pt/s) |
| `sharingType = .none` is legacy and unreliable | **unverified** (GC cites Apple docs); adopted as the safe behaviour |
| `visibleFrame` does not track Dock animation | **unverified**; adopted conservatively |
| Settings window must be a wall | **confirmed** against the owner's words ("windows of any kind") |
| Berendsen distorts translation/rotation partition | **unverified**; moot once the thermostat is an artistic control |
| Window polling may dominate the budget **[GB]** | **open**: window-list calls measured at 0.37-0.55 ms warm (P1 claim 14), so 2 Hz is ~0.1 %; the WindowServer side is unmeasured |

## Where the passes disagree (stated, not smoothed)

1. **How many points.** GPT blind starts at ~150 on a laptop screen (100 per million logical pt², cap 400) with a
   2.5 pt core; pass 1's "Light" is ~430-1 700 depending on units, with a 1.5 px core. A 3-10x gap. GPT's view: the
   interesting physics comes from interaction radius and rare directed bonding, not from filling the desktop. Pass 1's
   view: collisions and the Asteroids look need density. The concert memory ("tiny dots bouncing and interacting and
   colliding") sits between. **[M]**: default ~400 on the laptop screen, tuned on the review sheet; this is a card.
2. **Default boundary.** Pass 1: open reservoir (self-regulates temperature and density). GPT blind: reflecting
   chamber with emergency pressure relief (compression stays visible). GPT critique: the reservoir's self-regulation
   fails in pockets enclosed by windows. This is a card.
3. **Continuous life or stir-and-settle.** GPT blind lists both as honest product modes and recommends continuous very
   cool drift; pass 1 recommends continuous Cool with a "hold still while typing" damping; GPT critique says reducing
   frame rate alone can make motion *more* conspicuous, so "hold still" must actually settle the motion, not step it.
   This is a card.
4. **Icons.** Pass 1: obstacles with the Finder grant, plus idle "filings" halos. GPT critique: halos contradict "rings
   are reserved for needs-you" and crowd labels; start quiet. This is a card.

## Experience decisions made in the merge (no card needed)

- **Replaces the moving backdrops**, as the owner said ("take the place of the slowly moving background"); the 12
  backdrops stay only as static stills in the same tab, at no cost.
- **Colour: phosphor green** (the concert), with amber and vector white as choices; cold never turns blue-grey (that
  colour belongs to "VPN lost") **[P1]**.
- **Fields carry no data**: species signature and a strength setting only; the sprites already carry the data **[P1]**.
- **One gas per Space**, frozen while away **[P1]**; Space and Mission Control transitions reconcile quietly, never as
  a storm **[GB][GC]**.
- **Quiet behaviour** **[P1][GB]**: needs-you dims the gas within ~300 pt of that sprite; Reduce Motion holds a still
  frame; Low Power Mode and battery under 20 % hold still; thermal Serious or Critical stops; covered, full screen,
  locked and meeting mode draw nothing.
- **Controls**: tray items Pause, Hide and Stir; a temporary **quiet period** that expires by itself after focused work
  or a presentation **[GC]**; Hide is instant (no "Exhale" sweep animation) **[GC]**. No new global hotkeys in release 1.
- **Cut from release 1** **[GC]**: notification puffs, completion exhale, icon halos, the hover "magnetosphere" (needs
  a deliberate dwell if ever added), the saucer, Maxwell's demon, machine-heat temperature. The night crystal stays a
  later idea, and only if it melts without motion on return (it may not "melt over 10 s" as work resumes).
- **The distraction key** stays **[P1]**, plus an occasional one-line check in Sprites' own Settings rather than relying
  on him to log every lapse **[GC]**.
- **Menu-bar vent**: new aether enters under Sprites' own status item in reservoir mode **[P1]**, declared as an
  artistic source with its share of injection balanced **[GC]**.

## Build plan and gates [M]

1. **Measure the open unknown first** (load test, so **only on Lab Wi-Fi with the VPN off**): WindowServer and GPU cost
   of a full-screen opaque Metal window under sustained low-rate animation, against both Aether-off and today's backdrop;
   process CPU, WindowServer CPU, GPU activity and energy kept separate **[GC]**. Ticket
   `MANDRAKEWORKFLOWS_MEASURE_AETHER_WINDOWSERVER_COST_ON_Lab_WIFI`.
2. **Release 1** (~3-4 agent-days): `Aether.swift` beside `Backdrop.swift`; swept walls on the obstacle union; three
   clocks; both boundary modes; revealed-space reserve; one sprite field family; Settings tab (temperature, boundary,
   density, particle size, field strength, colour, brightness); seeded Swift tests for wall reflection, adiabatic
   behaviour, free expansion, speed limits and the seven acceptance cases below.
3. **Review sheet** for his eye: stills and short clips at real scale on the mini-LED panel at low brightness (dim
   points on pure black can bloom or crush) **[P1]**.
4. **Release 2**: short chains; species field families; icons per the card.
5. **Later**: rocks and fracture, night crystal, a live Settings preview (C's rules in the WebView), dust (B).

Acceptance cases, all ordinary actions **[GC]**:
1. Drag a window fast across the whole screen: no missed sweep, no fast-point burst.
2. Close an 800 pt window at Cool: the exposed desktop refills on purpose, not in five minutes.
3. Trap points between two windows, then close the gap: no jitter, no density explosion, no invalid placement.
4. Open Sprites' Settings and a translucent floating panel: points respect both.
5. Cover one display and leave another exposed: drawing suspends per display.
6. Leave one fast point alive: it cannot drive the whole system to a high frame rate.
7. Turn on Reduce Motion, and start a screen share in meeting mode: behaviour matches what the UI promises.

## Decisions for the owner (question cards, ready for the morning)

1. **How alive while you work?** Living gas (continuous, very cool drift; ~0.4-1.2 % of a core) / Stir and settle
   (still until a window or sprite moves it; ~0.1-0.3 %) / Living, but settles fully while you type.
   Recommendation: **living, settles fully while typing**: it keeps the concert feel and removes motion exactly when he
   is working.
2. **Screen edges by default?** Open reservoir (enter and leave; self-regulating) / Reflecting chamber (sealed;
   squeezing stays visible) / Thermal walls (sealed, but edges reset temperature). Recommendation: **thermal walls**:
   compression stays visible as GPT wants, temperature still relaxes as pass 1 wants, and it has no pocket problem.
3. **How many, how big?** Sparse (~150, 2.5 pt) / Medium (~400, 2 pt) / Dense (~1 500, 1.5 pt).
   Recommendation: **Medium**, tuned on the review sheet.
4. **Desktop icons?** Quiet obstacles (gas flows round icons and labels; needs Sprites' Finder automation grant) /
   Ignore (gas passes under them) / Obstacles that gather idle "filings". Recommendation: **quiet obstacles**: the
   owner asked how they interact, and this answers without adding a ring cue.
5. **First release scope?** Small (gas, windows, one sprite field; chains in release 2) / Full (chains, rocks and all
   species fields at once). Recommendation: **small**: every reviewer warned the second physics system is where it
   goes wrong.

## Rulings

Owner, 2026-11-08 ~08:10 PST, question cards (verbatim):

1. **How alive:** "These are mod settings, but we should support always living as an option". All three motion
   styles ship as settings; always-living must be one of them. Default not ruled; build keeps "living, settles while
   typing" as the default until he sees it.
2. **Screen edges:** "Thermal walls (Recommended)". Default boundary = thermal walls.
3. **How many, how big:** "Again, tunable in settings, so we need to spec for (3) even if we usually use (1). Need to
   see it to know." The engine and budgets are specified for Dense (~1 500, 1.5 pt, ~8 fps tail rule) even if Sparse
   (~150) is the usual setting; the default is settled on the review sheet.
4. **Desktop icons:** "Ignore icons". No Finder automation grant, no icon polling; gas passes under icons.
5. **First release scope:** "Gas plus short chains". Release 1 includes chains of 2-5 (correction 9's rules); rocks
   and fracture stay later. This overrides the merge's "small first release" recommendation and moves build plan
   step 4's chains into step 2.

Owner, 2026-11-08 3:15 PM PST, question card (verbatim):

6. **Windows push the gas:** "Push, replace wipe". Before the card he called the wipe-and-fade-back "strange and the
   wrong mechanic" and said the dots "should have been bumped out of the way". A moving window face carries the dots
   it meets at its own normal speed (above the ceiling only while in contact, relaxing once free), a pile spills
   round the window's corners, and every plausible move is swept, calm reads included. The absorb-above-ceiling rule
   (correction 3's "absorbs the point") is removed. Only a window that appears on top of dots, with no motion, sends
   them dormant; the revealed-space reserve stays.

Owner, 2026-11-08 ~4:00 PM PST (verbatim):

7. **Temperature varies:** "Let's not relax particles to the 'correct' temperature. Let it vary more." The per-point
   relaxation toward the target is scaled by a new "Temperature variation" setting (0 = the old uniform gas, 1 =
   free; default 0.85). Energy leaves through Cooling (drag) and comes in from windows, sprite stirring, the tray
   Stir and the screen edges, now a weak, slow source (thermal edges re-emit at the Temperature on a fraction of hits,
   else reflect). The Minimum temperature stays as a global floor (a uniform rescale of the mean), and the hot-pocket
   damping stays only as a ceiling against runaway. The same message: "Yes, sprite grid" (the sprite passes read
   only the collision-grid cells under each sprite's reach).

Owner, 2026-11-08 ~4:10 PM PST (verbatim):

8. **Bonding by forces:** "with the removal of forced equilibrium I would like to add a short-range attraction and a
   long range repulsion. Both of these should be adjustable for fun. Make sure I'm not driving your CPU usage crazy
   though. See if we can reproduce the bonding through actual forces rather than constraints. Relax those
   constraints." The chain constraints (bond length, straightening, stochastic lifetimes, caps, formation windows,
   the "chains" setting) are deleted. Attraction is a tapered pair well in the collision grid; repulsion is
   particle-in-cell on the coarse grid; needles come from an optional dipole term ("Chain forming"). Five sliders:
   Attraction strength and range, Repulsion strength and range, Chain forming. Cost is bounded by deterministic work
   counters in the tests, not a benchmark.


Owner, 2026-11-08 ~5:00 PM PST (verbatim):

9. **Drifting constants:** "Please have a mode where the Universal Constants slowly vary over the course of tens of
   minutes so that the behavior of the dots is surprising and interesting over the course of a day." Built as "Drift:
   off / gentle / wild" (default off) with a period (10-120 min, default 30). Attraction strength and range, repulsion
   strength and range, chain forming, cooling, temperature variation, edge temperature, field strength and stirring
   each follow their own seeded sum of three sines at jittered, incommensurate period multiples, added in logit space
   around the owner's slider value, so drift never leaves a slider's range and never turns on a constant he set to
   off. Density and collision size do not drift (the population and the grid are fixed per sim). The amplitude eases
   in and out over ~3 minutes. Settings shows the drifted values faintly beside the sliders; "Hold this universe"
   writes them into the sliders and turns drift off. The same message asked for two GPT passes (creative expansion,
   then a skeptical code review) and question cards on the result: `04-gpt-creative.md`, `05-gpt-code-review.md`,
   `06-synthesis.md`.

Owner card 2026-11-08 18:30 PST (the question cards in `06-synthesis.md`; the choices as relayed to the build):

10. **Gas ideas:** build **Weather fronts** (drift varies by region; the borders wander over about an hour), **Needle
    memory and knots** (broken needles leave their direction behind for the next ones; a small knot sometimes forms
    where two sprites' wakes cross) and **Window dew** (dots bead along a window edge that has not moved for about 10
    minutes and shake off when it moves). Owner card 2026-11-08 18:30 PST.
11. **Sprite ideas:** build **Species wakes** (each species shapes the gas its own way: a Siphonophore combs it into
    strands, the Mothership parts it like a bow; never tied to work or status), **Handedness by project** (each project
    always curls the gas the same way, so two wakes braid or cancel) and **Wake reader** (an idle sprite at play
    sometimes follows another sprite's leftover current a little; rare and subtle, so it never reads as one project
    following another). Owner card 2026-11-08 18:30 PST.
12. **Drift shape:** **Couple the risky pairs** (attraction and repulsion drift together), plus a test that samples a
    simulated day and fails on desktop-wide clumping. Owner card 2026-11-08 18:30 PST.
13. **Speed-ups:** not built now; filed as tickets `MANDRAKEWORKFLOWS_FIX_AETHER_SLOT_SCAN_AND_SIX_RULE_BREAKS`,
    `MANDRAKEWORKFLOWS_TRIM_AETHER_LOOPS_TO_LIVE_DOTS_ONLY`, `MANDRAKEWORKFLOWS_TRY_AETHER_LOOPS_WITHOUT_ACCESS_CHECKS`
    and `MANDRAKEWORKFLOWS_SPLIT_AETHER_FILE_AROUND_ONE_SETTINGS_TABLE`. Owner card 2026-11-08 18:30 PST.
14. **Frame rate:** "30 calm, 60 when pushed" (owner card 2026-11-08 ~6:35 PM PST). A calm, drifting gas presents
    at 30 fps; it goes to 60 only while a window face pushes the gas or a moving sprite stirs it, plus about 1 s of
    hold-off, then returns to 30. Positions stay blended between sim steps; the host's thermal cap still wins.

Rules for every feature in 10-12 (same message): bounded surprise (local, never desktop-wide, never an attention
cue); each gets a Settings control with a subtle default; each stays inside the work-counter budget (Dense under 15
pair checks per point per step at default, under 45 at max), over a sampled drift day too; each test fails on a
deliberately broken version.
