# C4 Kaleidoscope Seeds: design case file (`pieces/c4_kaleido.html`)

Serves brief b (strain escalation, timeline b2), brief e (social play, e2) and the saturation pole
pair on p1 (sat 0.5 vs 1.8). Handles all other timelines generically. Taste reference:
`~/ClaudeWork/sprites/renders/c4_mandala.png`.

## Intent records (visual-intent)
Brief b:
- takeaway: the machine went from calm to danger at one moment, then recovered.
- audience: Mandrake, expert, watching with peripheral vision while working in the front window.
- medium: ambient desktop overlay, glanceable, all day (no profile fits; nearest dashboard_or_exploratory).
- data_abstraction: level (ordinal 0..3, continuous in transit), thermal and mempress (ordinal 0..2), per-session cpu/mem/procs (quantitative), state (categorical).
- reader_task: deviation (from calm), plus locate-in-time (onset) and rank the peak (ordinal).
- analytic_relationship: one shared machine state modulating every creature together.
- candidate_families: whole-flock agitation (common fate) plus a discrete ordinal badge per level.

Brief e:
- takeaway: two idle sessions are playing (no data); separately, one session stopped working.
- reader_task: locate the pair; detect one real state change while decoration runs.
- analytic_relationship: a decoration channel that must never be mistaken for a data channel.
- candidate_families: a play grammar (meeting, orbit, gear-mesh, mote trade) that uses channels data never uses.

## Art fields (visual-beautiful)
- aesthetic_intent: little kaleidoscope seeds of dotted light, each turning its own n-fold flower, that
  stay serene when the machine is calm and lose their symmetry when it struggles.
- required_readings: strain onset to the second; peak level as one of four words; recovery; which
  colour stopped working; which two played.
- must_not_conclude: that play is load; that petal count is a quantity (it is identity); that halo
  brightness is load (glow is decoration); that clustering in VPN loss means sessions merged.
- medium: live real-time canvas, 1280x800, over a blurred desktop.

## Poles and combined (Pareto habit)
- BEAUTIFUL pole: dense rainbow-cycling mandalas (the GPT still), spiral comet trails, heavy glow,
  strain only as faster spin and hotter colour.
- CLEAR pole: one dot ring per seed, petal count = identity, crown badge per level in plain text
  colour, no inner layer, no shimmer, no embers.
- Combined (shipped): the beautiful look restrained to the session hue family (identity must survive),
  plus the one device the clear pole found most useful: the ordinal strain crown (amber dotted ring =
  medium, orange spikes = high, red flickering teeth = danger), since continuous agitation alone does
  not carry the ordinal peak (H-b2).
- Style dimensions that differ between poles: palette (multi-hue vs hue family), mark density, glow,
  chrome (crown badge), motion amplitude.

## Encoding table (visual-encoding)
| Datum | Visual variable | Why |
|---|---|---|
| session identity | hue (fixed) + petal order k (blue 6, amber 5, green 8, pink 7, teal 9) | redundant categorical channel so the hue survives grey-out (COLOR-06, ACCESS-01 spirit) |
| mem | seed radius, area true to GB (r = 38 sqrt(GB)); count of outer dot rings 1-4 | area for magnitude-at-a-glance only (ENC-01 relaxed: rank, not value; ENC-03) |
| cpu | petal spin rate + light chasing outward along petals; idle = nearly still bud | motion rate is the dynamic channel (motion.24: the content is change; motion.11) |
| procs | orbiting plus-shaped pixel seeds, one per process | whole counts as discrete glyphs (ENC-07) |
| state idle/working | petals open + brighter when working, folded and dim when idle; never off | low end stays visible (style: zero is not black) |
| state needs | seed rises to just under the menu bar, breathes at 0.45 Hz, two soft expanding rings | peripheral cue on one target, gentle (motion.15, motion.18) |
| m.level | symmetry breaking (petal angle and length jitter grows as level^1.6), tips heat toward orange, spin faster, position shiver; PLUS ordinal crown badge per level step | continuous agitation for onset, discrete step for the peak (motion.11, H-b2 reading) |
| m.thermal | rising embers (count rate per seed) | separate channel so heat is not confused with load |
| m.mempress | dot rings squeeze inward | small, honest, secondary |
| net.mbps | fine inner moire ring: brightness and beat speed | the GPT concept's "moire = network" kept, low salience |
| vpn down / loss | everything freezes, petals fold, saturation drops to ~45 % (hue kept), outer ring breaks into 3 arcs, flock huddles, a slow grey searching beam, one red pixel heartbeat; reconnect = one bloom ring + mote burst | categorically different from strain: strain is hot + fast + broken symmetry, VPN is cold + still + broken ring (motion.05: different operations look different) |
| play | the pair meets, orbits slowly, gear teeth appear on both rims and mesh, motes trade along an arc | uses channels nothing else uses (teeth, inter-seed motes), so it reads as a separate grammar (motion.14 tested by H-e2) |
| glow | soft halo sprite, decoration, scaled by P.glow | declared in the colophon (floor item 7) |
Colour roles: hue = categorical; heat shift toward orange = sequential on level; crown colours
amber/orange/red = ordinal; grey-blue = VPN state; red heartbeat = alarm highlight.

## Composition plan (visual-composition)
- layers: primary = the seeds (one per session); secondary = crown badges, needs rings, VPN beam;
  context = blurred desktop, focused window (never covered).
- placement: homes by farthest-point sampling over slots at least R + 34 px clear of the focused
  window, 66 px under the menu bar, 74 px above the dock; recomputed when the window jumps; seeds
  glide (eased, capped speed) to new homes; `V.avoid` as the last push; pairwise separation so seeds
  never overlap (except the play pair, which meshes at rim distance).
- needs-you spot: just under the menu bar, nearest x clear of the window.
- VPN huddle: around the most central home; beam clipped out of the focused window.
- idle drift: noise wander of about 80 x 50 px around home at 0.07 noise-units/s x P.drift.
- annotation: the colophon (legend=1) is the only text; no labels on an ambient pet (ANNO-01..10 waived, see friction).

## Self-check (2026-10-31)
`tools/qa_gates.py c4_kaleido`: all PASS on b2, e2, p1 sat 0.5 and 1.8; 120 fps real time (headless);
peak lit 1.96 % (b2), idle 0.58 % (e2); min peak contrast 7.7:1; 0 flash flips. Stills in
`~/ClaudeWork/sprites/trials/qa/c4_kaleido/` and `.../qa/gates_c4/`.
Weak: at idle with small memory the seeds are small (about 25 px); medium crown ring is subtle
against amber; strain shiver plus crown may score annoyance > 4 at danger.

## Skill friction
- visual-intent has no medium profile for an ambient, peripheral, all-day animated overlay; I borrowed dashboard_or_exploratory.
- visual-intent's intent-to-family table has no family for "state of a few live agents"; "deviation" was the closest and fits poorly.
- INTENT-04 "takeaway is a claim" fits a figure, not a continuously changing pet whose takeaway changes every few seconds.
- ENC-01's position channel is unavailable: position is spent on focus avoidance, so every quantity falls to area, rate or count.
- visual-encoding has no row for rate-of-motion (spin speed, pulse rate) as a channel, nor its accuracy rank; I had to cite motion.11/24.
- visual-encoding gives no rule for when a continuous datum needs a discrete visual step at ordinal boundaries (I invented the crown).
- visual-composition's annotation MUSTs (ANNO-03/04/05/06/10: axes, units, colour bar, caption) cannot apply to a label-free pet; there is no ambient exception.
- visual-composition has no notion of avoiding a moving occluder (the focused window) or of layout that changes over time.
- visual-beautiful "a key at the point of use whenever the piece asks for value or order reading": the crown is order reading, yet a key on screen would violate the ambient budget.
- visual-beautiful's Pareto habit asks for three rendered candidates; for live motion that triples build cost, so the poles here are described, not built.
- motion.14 (cut decorative motion) and motion.18 (pause control for >5 s self-starting motion) collide with an ambient pet whose idle drift and play are the product.
- style.md "no saturation" vs the brief's "psychedelic, LED-like": I kept saturation high but on fine marks only.

## Individualizer (2026-10-31)
Channel audit first: symmetry order k already carried session identity (blue 6, amber 5...), never a quantity,
so it is free for the variant; everything else is spent (radius + dot-ring count = memory, spin + chase = CPU,
plus-seeds = tasks, openness = state, symmetry breaking = strain, inner moire = network, crown = level, broken
ring = VPN, teeth = play). Variants change only the petal FIGURE and its order, never size, spin or ring count.
`s.iv` 0..7 -> `VARIANT_NAMES` (window.VARIANT_NAMES), figure family / k:
Lotus (almond petals + inner layer, 8), Trefoil (rose r=cos 3t lobes, 3), Pentagram ({5/2} dotted chords, 5),
Snowflake (spine + branch pairs, 6), Quatrefoil (interlocking dotted circles, 4), Spirograph (hypotrochoid, 7),
Dandelion (forked rays, 12), Honeycomb (hex lattice tile, 6). Each figure is built once in unit space, binned
into arm sectors, cached; drawn arm by arm so CPU spin/chase and strain jitter act identically on all forms.
Trial timelines (named session ids, no `iv` URL param) keep the original Lotus at the original per-colour k.
Gallery layout: no focus -> even grid of homes; seed scale 0.16 H x (3/n)^0.35 when chrome=0 (one factor for
all seeds, so area stays true to memory); all margins scale with V.H/800 and use V.TOP/V.BOT.
Check stills: `~/ClaudeWork/sprites/gallery/check/c4_kaleido/`. Worst frame ~1.8 ms (8 seeds).

## Round 2 (2026-10-31, GRAMMAR_V2)
- Network: inner moire removed. Per-session rx = blue-white beads streaming rim -> core along the arm axes; tx = gold
  beads core -> rim between arms; count, size and brightness grow with log Mbit/s, comet tails show direction.
  Jam (net.strain on sessions moving data) = beads bunch and stall in a bright stuttering band at the rim, tails vanish.
- Machine strain: crown (rings/spikes/teeth) removed. Red ember glow behind and inside the seed rising with level,
  arms knocked off-centre/rotated/stretched (dis-alignment), petal colour warms toward red; heat sparks stay inside.
- VPN: tighter phyllotaxis huddle, separation relaxed; heart replaced by small blinking red beacon; searchlight kept.
- Play: gear teeth and motes removed; pair drifts together, one short twirl, parts. Idle: slow 7 s breath, slower satellites.
- Needs-you rings shortened and knock spot kept a full ring radius from every edge (Granite ran off the 640x400 top).
Check stills: `~/ClaudeWork/sprites/gallery/check2/c4_kaleido/`.
