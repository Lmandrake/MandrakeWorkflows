# C5 Firefly Murmurations: design case file

Piece: `pieces/c5_fireflies.html`. Briefs served: **a** (timeline a2), **c** (timeline c1), and the
**density** pole pair on p1. Taste reference: `renders/c5_swarm.png`, `renders/c6_vpnloss.png`.

## 1. Intent records (visual-intent)
Brief a:
```
takeaway:        "Amber is the one burning CPU; green is the heavy one; pink is running lots of tasks."
audience:        the owner; expert, all-day, peripheral attention, no reading time
medium:          ambient desktop overlay, glanceable, animated, peripheral vision, all-day (no profile fits; nearest is dashboard_or_exploratory)
data_abstraction: session id (categorical, 5) x cpu (quant 0-4) x mem (quant 0.2-2.5 GB) x procs (count 1-12) x state (categorical)
reader_task:     locate + rank (which one has the most X), live
analytic_relationship: per-entity magnitude on three measures, compared across 3-5 entities
candidate_families: proportional symbol (one glyph per entity, three channels); small multiples rejected (ambient, no frame)
```
Brief c:
```
takeaway:        "The machine got busy first, then the network dropped; those looked nothing alike."
data_abstraction: machine level (quant 0-3, continuous) + thermal/mempress (ordinal 0-2); vpn (binary); loss (%)
reader_task:     detect + discriminate two event classes in time (mark the moment)
analytic_relationship: two categorical regimes over a shared population, plus onset/offset times
candidate_families: whole-population state change (all glyphs share a regime); one categorical regime per event class
```

## 2. Art fields (visual-beautiful)
```
aesthetic_intent:  a night meadow of firefly swarms, one per Claude session, that spin when it works
required_readings: which colour spins fastest (CPU); which is the largest swarm (memory); which wears the
                   most diamonds (tasks); "the machine is hot" vs "we lost the mothership", at a glance
must_not_conclude: that swarm position or distance between swarms means anything (layout only); that
                   halo brightness is load (halo is decoration); that the network sparks are per-session traffic
                   (they are machine-wide Mbit/s split by activity)
medium:            interactive web canvas, 1280x800, real time, additive light
```
BEAUTIFUL pole: dense galaxy spirals (density 1.8), long comet streaks, full additive halos, embers, heavy
curl drift; reads as fireworks; magnitudes blur together. CLEAR pole: sparse (density 0.5) separated
points, no halo, no streaks, swarm area and diamond count only; legible but reads as a scatterplot.
**Combined (shipped, density 1.0):** fine crisp 2-px cores with soft small halos, the two-arm spiral that
only spins when working, plus the clear pole's structural device: discrete countable 8-bit diamonds for
tasks and a fixed-hue pixel-cross "queen" for identity. Dimensions that differ between poles: mark
density, halo strength, streak length, drift amplitude. The p1 pair varies density alone (0.5 vs 1.8).

## 3. Encoding table (visual-encoding)
| Datum | Visual variable | Why (principle IDs) |
|---|---|---|
| session identity | hue of every mote, diamond and queen cross; the queen cross keeps >=60 % sat even in VPN grey | categorical colour for nominal (COLOR-04, SEM-04); identity channel never reused for magnitude (COLOR-06) |
| mem (GB) | firefly count (38/GB x density) and swarm radius ∝ sqrt(mem), so lit area ∝ memory | area-true magnitude (SCI-02, G1); area is a coarse channel, fine for "largest" (ENC-03 exception: ranking, not reading) |
| cpu (cores) | spiral angular speed + blink rate + streak length (motion trails) | motion is the phenomenon: activity rate as rate (motion.24); mark length carries magnitude (style.md) |
| procs | count of orbiting 4-pixel diamonds, one per process | countable discrete units for whole counts (ENC-07); a second shape class separates it from motes (DIAG-02) |
| state idle | dim (42 %), loose noise-cloud, near-still spin | idle drift is the only data-free motion, slow so it reads "nothing happening" (motion.14) |
| state working | full brightness, tight spinning arms | brightness + order rise together; one change, two redundant cues (ACCESS-01 spirit) |
| state needs | swarm rises toward the menu bar edge, motes form a ring, a slow "knock" bob (0.55 Hz) and two expanding ripples in its hue | peripheral attention with one target at a time (motion.15); well under 3 Hz (motion.18) |
| machine level 0..3 | continuous strain: per-mote jitter amplitude, desynchronised blink, swarm shake, faster spin | escalation mapped to agitation, a magnitude channel (SEM-04); never categorical, so no false threshold |
| thermal, mempress | add to strain; strain also lights white-hot flicker on 1 in 7 motes and releases rising orange embers | heat connotation fits (style.md palettes carry connotations) |
| network mbps | fine sparks falling from the top edge into swarms; rate ∝ Mbit/s | flow as particles (SCI-05: make invisible visible) |
| loss % | that fraction of sparks die mid-fall | same marks, failure visible as interruption |
| vpn down | categorical regime: all colour drains to cold grey (hue kept in the queen), swarms huddle bottom-centre on the free side, motion stops, one red heartbeat cross every 1.7 s, a slow searching beam; reconnect = one ring bloom with confetti in every session hue | must differ in kind from strain: strain = MORE motion and heat; VPN = LESS motion and cold (HIER-04 separation, motion.11 unused channel) |
| play pair, amt | the two swarms orbit a shared centre, blink in unison, trade hue-coloured comets on alternating arcs | sync and exchange are behaviours no datum uses, so play cannot be misread as load (motion.11) |
| glow/density/drift/sat/size | halo alpha+diameter / motes per GB / noise-drift rate / V.hsl / radius and pixel size | contract multipliers |
Colour roles: hue = categorical (identity); grey + red = highlight for VPN regime; orange embers = strain
(decorative-but-declared). Halo is declared decoration (beautiful floor item 7).

## 4. Composition plan (visual-composition)
```
layers:     primary = the swarms (identity + activity) ; secondary = [needs ripples, VPN beam/heart, strain embers] ; context = [network sparks]
hierarchy:  swarms carry the brightest cores; sparks are 1.6 px at <=0.8 alpha; beam is 13 % alpha
annotation: COLOPHON (5 lines) via ?legend=1; no on-canvas text (ambient medium; ANNO rules relaxed, see friction)
layout:     swarms live in the free half of the screen beside the focused window (freeRect), stacked in
            two zig-zag columns; V.avoid() + spring keep reported centres out of the window, menu bar, dock
```
When the focus window jumps sides, homes move to the other half and the flock streams across in about
1.5 s (spring with damping, speed cap). Separation keeps swarms from merging except a play pair. VPN
huddle sits low (y 610) in the free half, above the dock.

## 5. Self-check
Timelines rendered: a2 (3, 12, 22, 30 s), c1 (4, 12, 20, 27, 32.6, 36 s), p1 at density 0.5 / 1 / 1.8,
plus d2, e1 spot frames; every timeline a1..p1 renders with no errors and reports every session.
Idle lit area (bg=0, >20/255): 0.2-0.6 %, peak 0.84 % (reconnect bloom). fps 120 headless (rAF cap).
QA stills: `~/ClaudeWork/sprites/trials/qa/c5_fireflies/`.
Weak: CPU in a2 reads mainly from spin and streaks, which a still cannot show; tasks (diamonds) and the
fireflies can overlap at large mem; network sparks are subtle at 0.8 Mbit/s by design.

## 6. Skill friction
- visual-intent has no medium profile for an ambient, animated, peripheral, all-day overlay; I had to borrow dashboard_or_exploratory.
- INTENT-04's single takeaway does not fit a pet that has no message most of the time; "nothing is happening" had to become the takeaway for idle.
- visual-composition ANNO-03/04/05/10 are MUST, but an ambient overlay can carry no axes, units, caption or colour bar; I relied on the colophon and have no rule saying that is allowed here.
- visual-beautiful floor item 3 ("key at the point of use whenever the piece asks for value or order reading") conflicts with brief a, which asks for rank reading with no on-screen key.
- ENC-01's channel ranking assumes static marks; there is no ranking for motion channels (spin rate, blink rate, streak length) versus area, so the CPU choice had no principled tie-break.
- motion.01 (default to static) and motion.12/19 (viewer advances, can scrub) do not fit a live data stream that is itself the motion; I treated motion.24 as overriding.
- motion.18's "pause/stop/hide control" for motion over 5 s has no place in a click-through overlay.
- motion.10 (follow about four things) is exceeded by design with 5 sessions; no guidance for an ambient field where nobody follows anything until it changes.
- No skill addresses categorical regime discrimination (VPN vs strain): I invented "opposite on every axis" (motion, temperature, spread) as the rule.
- style.md "avoid saturation / cores burned to white" collides with the brief's request for white-hot strain; I kept hue and lit only 1 in 7 motes white.
- No rule for identity persistence under global desaturation; I invented the fixed-saturation "queen" glyph.
- Ambient lit-area budget and luminance flip counting live only in the study PLAN, not in visual-render-qa's vocabulary for animation.

## Individualizer
Each session's `iv` (0..7) picks the flight figure its fireflies stream along plus the pixel shape of each
firefly core; a faint ghost line of the figure (7-14 % alpha) makes the path readable in one still frame.
`window.VARIANT_NAMES` = Galaxy (the original two-arm spiral, square pixels), Halo (circle, square),
Infinity (lemniscate, cross), Coil (helix seen side-on, open, diamond), Lissajous (3:2 knot, round),
Trefoil (torus-knot projection, diamond), Comet (bright head with a fraying tail on a circular track, cross),
Braid (three interleaved vertical strands, open, square). Channels untouched: figure size still = sqrt(memory),
mote count = memory, speed along the figure = CPU (same spin law as the galaxy), diamonds = tasks.
Fireflies are spaced along the figure by the golden ratio, so any memory-lit prefix covers the whole figure.
Gallery layout (chrome=0 or H<700): swarms sit on the roomiest grid in the free rect; unit radius is fixed
per run from stage size and session count (never per datum); pixel sizes scale with it (KS). With a focus
window, a "needs" swarm flies to the window's edge and knocks on it. The 1280x800 trial path is unchanged.

## Round 2
Per GRAMMAR_V2 and the owner's notes. Bandwidth now lives on the swarm's own flight figure: download packets
(cool white-blue, bigger halo + square core, short trail) ride the figure rim -> heart, upload packets (warm gold)
heart -> rim; rate and brightness log-scale with per-session rx/tx (falls back to splitting S.net.mbps in the
trial timelines, which carry no rx/tx). Link strain (S.net.strain, weighted by how much the session moves)
stalls packets into bright clots at the rim/heart ends and makes the whole stream stop-and-go. The falling
sparks, play comets and in-unison play blinking are gone. Machine strain: steady red ember glow behind and
inside each swarm, band-wise horizontal misregistration of the figure (noise-in-geometry), slower shake, fewer
embers; the white-hot flicker is removed. VPN: the heart is now a small red square beacon (on 0.25 s per 1.7 s)
under the searchlight. Idle: slower drift, twinkle amplitude 30 %. Lanterns (tasks) are evenly spaced so the
count reads. Play: drift together, one slow circle, part. Checks: ~/ClaudeWork/sprites/gallery/check2/c5_fireflies/.
