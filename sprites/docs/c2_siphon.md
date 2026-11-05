# C2 Siphonophores: design case file

Piece: `pieces/c2_siphon.html`. Serves brief c (timeline c3, the strain-only catch trial), brief e (e1),
and the idle-drift-speed pole pair on p1 (drift 0.5 vs 1.8). Taste reference (taste only):
`~/agent-storage/sprites/renders/c2_jelly.png`, `s2_states.png`.

## Intent records (visual-intent)
Brief c:
```
takeaway:         When the jellies writhe, twinkle and throw warm sparks, the machine is busy; only when
                  they go grey, stop pulsing, hang limp, huddle and a beam searches has the network gone.
audience:         the owner, expert, all-day; peripheral vision, glances of seconds
medium:           ambient desktop overlay (no profile fits; nearest dashboard_or_exploratory, glanceable)
data_abstraction: m.level, thermal, mempress quantitative (continuous); net.vpn categorical; mbps, loss quantitative
reader_task:      detect + classify (which kind of event, when), and NOT see the event that did not happen
analytic_relationship: two independent event classes that must never be confused
candidate_families: whole-flock state change (motion.24: the content is change), attention cue (motion.15)
```
Brief e:
```
takeaway:         Two idle jellies circling with tentacles braided and swapping coloured beads are playing;
                  the playing changes nothing about their data, while a third one dimming really did stop.
audience / medium: as above
data_abstraction: play.pair (two categorical ids) + play.amt 0..1; per-session state categorical
reader_task:      locate the pair; separate a data change (worker goes idle) from play
analytic_relationship: a non-data social behaviour beside one real state transition
candidate_families: paired orbit (common fate, motion.10), state = brightness (data channel kept separate)
```

## Art fields (visual-beautiful)
```
aesthetic_intent:  a small shoal of dot-matrix jellyfish made of LEDs, each a session, breathing slowly
                   beside your work
required_readings: busy machine vs lost network, instantly, and that c3 never lost it (c); which two play
                   and which one really changed state (e); which colour is which, always (identity)
must_not_conclude: strain = network trouble (strain keeps colour, pulse and bead traffic); a slower idle
                   drift = less work (drift is data-free); play = state change; position means anything
medium:            interactive web canvas, real-time, 1280x800
```
Poles (dimensions that differ: glow/halo, mark density, motion vocabulary, chrome):
- **BEAUTIFUL pole:** large bells with rainbow bead tint, long free-flowing tentacles in curl flow,
  strong halos, constant shimmer; strain and VPN both "change the mood".
- **CLEAR pole:** small bells, one bead per tentacle tip, no shimmer at idle; strain = warm tint, VPN =
  grey; a plain ring for needs.
- **Combined (shipped):** beautiful bells and beaded tentacles, hue ripple held to +/-14 deg of the
  session hue so identity never drifts; from CLEAR it takes the **categorical separation of failure
  modes**: strain only ADDS energy (writhe, jitter, twinkle, embers, uneven pulse) and never removes
  colour or traffic; VPN only REMOVES life (colour drained to 32 %, pulse stopped, traffic gone, limp
  tentacles, huddle) plus two unique signs (red heartbeat, searching beam). Idle is still and dim.

## Encoding table (visual-encoding)
| datum | visual variable | why (principle ids) |
|---|---|---|
| session id | hue of the whole jelly (fixed, ripple +/-14 deg) | categorical identity; COLOR-04, COLOR-06 |
| mem (GB) | bell radius, area proportional to GB | area for coarse rank only (ENC-03 accepted: no exact read) |
| cpu (cores) | bell pulse rate 0.14 + 0.52*cpu Hz, each beat a small upward thrust | rate is a dynamic channel unused elsewhere (motion.11); motion = the phenomenon (motion.24) |
| procs | tentacle count, each with a brighter countable tip bead | discrete count marks (ENC-07 spirit: whole counts) |
| state idle/working | brightness 0.5 vs 1.0 | luminance for a binary, eased 0.5 s (motion.08, motion.09) |
| state needs | swims to the focused window's outer edge, taps (once per 1.8 s), dotted rings, breathing halo | one target, gentle, peripheral (motion.15, motion.18) |
| m.level | tentacle writhe amplitude + speed, body jitter (~level^2), bead twinkle, irregular pulse | continuous escalation; strain only adds energy (motion.05: unchanged data unchanged) |
| m.thermal | warm ember sparks rising off the bell + rim warming | heat connotation (style.md "palettes carry connotations") |
| m.mempress | tentacles shorten (up to 20 %) | squeeze metaphor; secondary, untested |
| net.mbps | bright beads sliding down tentacles, rate ~ sqrt(Mbit/s) | flow along a path reads as traffic (motion.24) |
| net.loss % | that share of beads fade out mid-tentacle | dropped packets literally drop |
| vpn down | grey (sat x0.32, hue kept), pulse stops, tentacles hang straight, huddle, red lub-dub every 2.4 s, slow beam | categorically different, removes life (CRIT: no confusion with strain) |
| vpn reconnect | one ring of saturated beads flung outward per jelly, 1.4 s | the grammar's one celebration; single event, no flash |
| play | pair orbit a shared centre, inner tentacles braid toward the partner, beads of each colour cross over | social motion, distinct from data channels (motion.10 common fate) |
| idle drift | slow noise wander of the home, 3.7 / 5.1 / 6.9 px/s at drift 0.5 / 1 / 1.8 | the only data-free motion; reads as "nothing happening" (motion.14) |
| glow, halo, hue ripple, apex lantern, manubrium | decoration (declared in COLOPHON) | floor item 7 |

Flash: no full-frame luminance change exists; heartbeat is a 4 px dot; bloom happens once.

## Composition (visual-composition)
- Primary layer: the jellies; context: the desktop and the focused window (never covered).
- Homes are laid out in the wider free strip beside the focused window (1 or 2 columns, staggered),
  re-planned when the window moves; each jelly takes the nearest slot so travel is short. Paths are
  routed round the window's padded corners (shortest path over 4 corners), so a jump never drags a
  jelly across the window; anything caught inside leaves by the nearest edge. Measured (a1, b1, c1): no centre in the
  window 0.8 s after a jump (sampled at 0.5 s steps).
- Margins: y between 40 and H-120 (menu bar 22 px, dock 70 px plus tentacle length), x 30 px from edges.
- Spacing: soft separation of r1+r2+34 px, except the play pair. VPN huddle: a ring of radius 30+11n
  around the flock's centre. Needs: beside the window's top corner, stacked if several.
- Idle lit area 1.9-2.0 % of the screen at default (budget 6 %).

## Skill friction
- visual-intent has no medium profile for an ambient animated overlay; "dashboard_or_exploratory" is the nearest but assumes the reader looks at it.
- INTENT-04 "one takeaway" does not fit a pet that carries ~10 channels all day; I wrote one per brief.
- "Required readings" has no slot for a negative reading (c3: "there was NO drop"); I put it in must_not_conclude, which is about misreadings, not absent events.
- visual-encoding's channel ranking (ENC-01) is static-only; motion rate, writhe, flow direction and huddling have no rank, so channel choice for 6 of 15 rows was invented.
- ENC-03 forbids area for magnitudes but the brief asks for "largest memory"; I accepted area for rank-only and said so.
- Composition's MUST annotations (ANNO-03..06: axes, colour bar, source, caption) are inapplicable to a pet; the COLOPHON stands in, and the skill has no "ambient: legend on demand" exception.
- HIER-01 "one primary" is ambiguous when the primary (which creature needs me) changes over time.
- Nothing in the skills covers placement that moves (avoid a window that jumps, route round it); routing was invented.
- visual-beautiful's Pareto habit asks for three rendered candidates; the brief asks for one shipped piece, so the poles exist only as text here.
- The style rule "no saturation / avoid white cores" conflicts with additive glow on overlapping jellies (play pair); held by keeping per-bead alpha low.

## Individualizer
`s.iv` (0..7) picks one of eight forms, `window.VARIANT_NAMES`: Moon (dome, latitude rings, curtain of
tentacles, manubrium), Lantern (tall ovoid, meridian ribs, tight bundle, glowing wick), Saucer (flat disc,
spiral arms, tentacles ringing the rim, central tuft), Box (square cube-ish wireframe, tentacles from the
four corners), Lyre (flared bell with banded skirt, tentacles from the two sides curling back, oral curls),
Spire (tall cone with starfield dots, corkscrew tentacles), Pagoda (tiered dome with bright tier bands,
zig-zag frill skirt, four ruffled oral arms), Corolla (five-lobed flower rim, spoke dots, tentacles from the
lobes, cauliflower oral cluster). Structure only: bell AREA stays memory, pulse RATE stays CPU, tentacle COUNT
stays processes; no variant spins or resizes. Deterministic from iv (precomputed geometry, no V.rand).
Gallery layout (non-1280x800 stages): creature scale follows stage height and session count, homes on a
centred grid in the free region, bounds computed from each variant's own extent. The 1280x800 trial path is
unchanged (`LEGACY`). Checks: `~/agent-storage/sprites/gallery/check/c2_siphon/`.

## Round 2 (owner gallery feedback, GRAMMAR_V2)
- **Sky, not sea:** jellies became hovering light-craft. Swim thrust cut to a gentle hover bob, tentacles straighter (beam-like) inside a faint tractor-beam cone, a blinking beacon at every tentacle tip (still one per background task, countable), and running hull lights chasing round the rim.
- **CPU = internal tempo:** rim chase-light speed 0.5 + 1.1*cpu rev/s (bell breathing kept).
- **Bandwidth (per session, log scale):** rx = cool blue pulses climbing tip -> core, tx = gold pulses core -> tip, with a core flash where they enter or leave. Link strain: pulses slow and stutter, the throat passes them only at a throttled rate, so they queue and a bright clog band forms at the bell's throat. Old beads removed; nothing enters from outside.
- **Machine strain:** red ember glow behind and inside the bell (rises with level and heat) plus lattice rings slipping out of register (quantised noise) and tentacle beads slipping sideways. Rim warming removed, embers halved; no rings or flashes.
- **VPN:** huddle and searchlight kept; the lub-dub became a small red beacon blink (every 1.6 s).
- **Play:** drift together, ONE twirl, part. Motes and tentacle braiding removed.
- **Idle:** less sway, slower tentacle phase.
