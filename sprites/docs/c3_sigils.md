# C3 Living Sigils: design case file

Piece: `pieces/c3_sigils.html`. Serves brief a (timeline a1), brief d (d1), and the size pole pair on p1
(size 0.5 vs 1.8). Taste reference: `~/agent-storage/sprites/renders/c3_sigils.png`.

## Intent records (visual-intent)
Brief a:
```
takeaway:         Each sigil is one session; its colour and glyph say which, its size says memory,
                  its inner spinning light says CPU, its orbiting pixels say background tasks.
audience:         the owner, expert, all-day; reads in peripheral vision, glances for seconds
medium:           ambient desktop overlay (no profile fits; nearest dashboard_or_exploratory, glanceable)
data_abstraction: session id categorical; cpu, mem quantitative; procs count; state categorical
reader_task:      locate (which colour) + rank (largest/busiest/most) across 3-5 items
analytic_relationship: per-item magnitude on three independent channels
candidate_families: proportional symbol (size = mem), glyph with count marks (procs), animated rate (cpu)
```
Brief d:
```
takeaway:         One sigil comes to the edge of your window and knocks: that session needs you.
audience / medium: as above; the owner is working in the focused window
data_abstraction: state categorical (idle | working | needs), one transition to 'needs'
reader_task:      detect + locate (who, when) while attending elsewhere; ignore a CPU decoy
analytic_relationship: one categorical change against a background of quantitative churn
candidate_families: attention cue on one mark (motion.15, motion.11), approach toward the focus
```

## Art fields (visual-beautiful)
```
aesthetic_intent:  a small company of 8-bit alien emblems made of LEDs, each its session's crest, that
                   mutate softly while they work
required_readings: which colour is busiest / largest / has most tasks (a); which colour needs me and
                   roughly when (d); strain vs VPN loss categorically different (generic)
must_not_conclude: glyph shape or mutation pattern means anything beyond "CPU is ticking it" (the
                   shape is identity only); position on screen means anything (it is free space);
                   play means the pair changed state
medium:            interactive web canvas, real-time, 1280x800
```
Poles (the dimensions that differ: mark density, glow, chrome/marks, motion):
- **BEAUTIFUL pole:** large 9x9 sigils, strong additive halos, continuous CA mutation at every state,
  packet rain and embers everywhere, no ring/reticle chrome; identity by glyph and hue only.
- **CLEAR pole:** small fixed 5x5 glyph, no mutation, size = mem, a numeric-like row of task pixels
  under the glyph, a solid ring for needs, plain colour shift for strain.
- **Combined (shipped):** beautiful sigils and halos, but mutation is bound to CPU only (still glyph =
  idle; that is the one structural device taken from CLEAR: stillness at idle is readable), the CPU
  sweep light is a separate, faster channel than mutation, satellites are discrete countable pixels, and
  needs-you borrows CLEAR's explicit chrome (reticle corners + dotted ripples) plus an approach.

## Encoding table (visual-encoding)
| datum | visual variable | why (principle ids) |
|---|---|---|
| session id | hue (V.sessions hue) + a hash-seeded mirrored glyph; centre pilot pixel keeps full hue under any state | categorical, two redundant cues so identity survives desaturation (ACCESS-01, COLOR-06) |
| mem GB | glyph extent, area proportional to mem (side ∝ sqrt mem) | ranking magnitude on area; precise reading not required (ENC-01 relaxes, ENC-03 accepted for rank) |
| cpu cores | twin sweep light rotating at 0.85 rev/s per core + mutation ticks at 2.2/s per core | rate is the native channel of activity; stillness = idle (motion.24, motion.01 job: show a process) |
| procs | orbiting satellite pixels, one per process, discrete and countable; orbit only while working | count -> discrete marks (ENC-07 pictogram for whole counts) |
| state idle/working | brightness 0.5 / 0.85, satellites still vs orbiting | idle dim, never gone (style: zero is not black) |
| state needs | approach to nearest focus edge, 2-tap knock every 2.6 s, dotted ripple rings 1.5 s apart, reticle corners pulsing at 0.7 Hz | one target, peripheral-salient, below 3 flashes/s (motion.15, motion.11, motion.18) |
| m.level 0..3 | continuous: halo heats to orange, cell jitter ∝ level^2, desynchronised twinkle, wander speed x(1+2.2 level^2) | strain is "the same creatures getting restless" (motion.24) |
| m.thermal | embers rising from each sigil, rate ∝ thermal; jitter gain | heat connotation (style: palettes carry connotations) |
| m.mempress | satellite orbit tightens and speeds up | secondary, low-salience (MEDIA-05: kept off primary channels) |
| net.mbps | tiny packets falling from the menu bar into sigils, rate ∝ mbps | flow from "outside" (motion.24) |
| net.loss | that fraction of packets fizzle grey mid-fall | redundant on the same flow mark |
| vpn down | categorical: colour drains to ~40% sat (hue kept), flock huddles still, slow searching beam, one red double heartbeat every 2.6 s; reconnect = one radial bloom of hue sparks | a different KIND of change from strain: stillness+cold vs restless+hot (COLOR-06, motion.22) |
| play | pair orbits a shared midpoint, a bead bridge arcs between them, outer cells take the partner's hue | data-free, so it uses channels no datum uses (bridge, hue swap) (motion.11) |
Multipliers: size scales glyph and satellites; density sets the grid N (5..15) and particle rates; glow
scales halos; drift scales wander; sat passes through V.hsl everywhere.

## Composition (visual-composition)
- Primary: the sigil that changed (needs or busiest); secondary: other sigils; context: packets, embers.
- Homes: farthest-point sampling over a 24 px grid of free space, excluding the focused window plus
  one radius, the menu bar (22 px) and dock (bottom 70 px); recomputed when focus moves, assigned by
  least travel; the path detours via the window's clear horizontal edge so sigils never cross the window.
- Wander: curl noise around home (only data-free motion), capped radius 45 px x drift; spring with
  critical damping so arrivals ease (motion.08).
- Needs: the sigil leaves the flock for the focused window's nearer side edge (outside it), so it sits
  in near-peripheral vision of the work.
- Annotation: the COLOPHON (5 lines) is the key; no on-screen labels (ambient medium).

## Self-check (headless Chromium)
Timelines rendered: a1, d1, p1 (size 0.5/1.8), b1, b2, c1, c2, e1, e2, plus all multipliers at 1.8/0.5.
No errors; 120 fps headless; idle lit area 0.3-0.9 % (bg=0, >10 % luminance), 2.1 % at size 1.8 under
strain. Focus centre-inside time <= 0.5 s after a jump.

## Skill friction
- visual-intent has no medium profile for an ambient, peripheral, all-day overlay; I used dashboard as nearest.
- intent -> family table has no entry for "detect a categorical change while attending elsewhere".
- visual-intent's single takeaway does not fit a piece that answers several standing questions over time.
- ENC-01 ranking assumes static reading; rate (spin/pulse frequency) is not on the channel ladder at all.
- ANNO-01/04/05 (direct labels, axes, colour bar) are MUST-ish but text on a desktop pet is wrong; the colophon is the only key.
- Floor item 3 "key at the point of use" conflicts with an unlabelled ambient medium; no rule for a hover/modifier key.
- motion.18 asks for a pause control; for an always-on pet that is an app setting, not in-piece.
- motion.14 "cut decorative motion" vs the brief's required data-free idle drift: no rule for permitted idle motion and its max speed.
- motion.10 (follow about 4 things) vs 5 sessions in brief a: no guidance for ambient multi-object monitoring.
- No principle covers focus avoidance, occlusion of the user's work, or screen-area budget; I invented them.
- visual-beautiful's Pareto habit wants three rendered candidates; the contract ships one file, so poles exist only on paper.
- "Glow is declared decoration" but glow here also encodes state (needs brightness); the skill has no mixed category.

## Individualizer
Identity no longer comes from a hash of the session id: `s.iv` (0..7) picks one of 8 hand-drawn 9x9 LED
bitmaps (`GLYPHS`, exposed as `window.VARIANT_NAMES`): Lantern (outlined diamond, 4-fold), Trident (fork
on a stem, bilateral), Halo (open ring with a pilot dot), Star (8-ray burst), Invader (dense 8-bit
creature), Ascent (stacked chevrons, an upward arrow), Lattice (sparse dot grid), Eye (flat lens). They
differ in silhouette (round/square/diamond/flat/tall), symmetry (4-fold vs left-right only), and texture
(outline, solid, rays, dotted), so they read without colour at a glance. Size stays memory; nothing about
a variant moves or scales. Mutation (CPU) now toggles whole symmetry orbits and is capped at one or two
orbits off the base, so a busy sigil shimmers but keeps its name. Bitmaps resample to the density grid N.
Old trial timelines (no iv, runtime sets 0) fall back to session order so their 5 sigils stay distinct.
Gallery layout: stages under 1000x700 scale sigils to the stage (crowd-shrunk for 4+), place them on a
centred grid when no window is focused, and use V.TOP/V.BOT throughout. Checks:
`~/agent-storage/sprites/gallery/check/c3_sigils/`.

## Round 2
Applied GRAMMAR_V2 after owner gallery round 1 ("pulling random pixels in from beyond is odd but glyphs themselves are amazing"; idle "still a bit busy"; strain "tinge more red glow behind pixels"; rotating lights kept as is).
- Bandwidth now lives inside the glyph. Falling packets are removed. Each Mbit/s run is an arc of light along the glyph's own pixels: download is pale blue-white, running rim to core; upload is gold, running core to rim (log rate and brightness). Base pixels dim slightly while data flows, so the runs stand out. A strained link (net.strain) stalls the runs at the rim and makes the outer ring flicker as a clogged band in both tints, with no red.
- Machine strain: a red ember halo behind the glyph, a per-pixel ember glow behind each LED, rows that slip out of line (shear noise) on top of the existing jitter, and fewer, redder embers. No rings.
- Play: the bead bridge and partner-tint exchange are removed. The pair drift together, do one eased half-turn twirl, then part.
- Idle: mutation runs at 1/4 rate, drift range is 0.55x, and the glyph breathes slowly (7 s period).
- VPN: the red heartbeat is replaced by a small red blinking beacon. Huddle and searchlight are unchanged.
Verified headless: __errors empty for all 12 gallery scenarios plus a1/d1 at 1280x800. Screens: ~/agent-storage/sprites/gallery/check2/c3_sigils/ (g_net_strip.png = download/upload/jam over time).
