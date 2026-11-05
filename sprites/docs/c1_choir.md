# C1 Mothership Choir: design case file

Piece `pieces/c1_choir.html`. Serves brief b (timeline b1), brief d (timeline d2) and the glow pole
pair on p1. It also runs every other brief. GPT taste references: `c1_choir.png`, `s1_states.png`.

## Intent records (visual-intent)
Brief b:
```
takeaway:   the machine is straining now, this badly, and it has (or has not) recovered
audience:   the owner, expert, glancing out of the corner of his eye while working
medium:     ambient desktop overlay: glanceable, peripheral, all day (not in the medium list)
data:       m.level quantitative 0..3 (ordinal bands light/medium/high/danger), thermal 0-2, mempress 0-2
reader_task: deviation from calm, plus trend (onset, peak, recovery)
relationship: one scalar for the whole machine, carried by every creature at once
families:   a "collective mood" of the flock (no chart family fits; nearest is a status lamp)
```
Brief d:
```
takeaway:   one particular session (the colour) is waiting for me, starting now
audience / medium: as above, attention on the front window
data:       state categorical idle|working|needs per session; cpu as decoy
reader_task: locate (which one) + detect onset
relationship: one singleton against a stable background (pop-out)
families:   a highlighted mark: one dynamic channel nobody else uses (motion.11)
```

## Art fields (visual-beautiful)
- aesthetic_intent: a small choir of jewel-lit saucers that hum along with each session's work, and
  grow hot together when the whole machine strains.
- required_readings: which colour is which session; when strain began, how bad it got, whether it
  passed; which colour needs me and when it started; VPN loss as a different kind of event from strain.
- must_not_conclude: that a session is at fault for machine strain (the heat is collective, every craft
  heats alike); that play, embers or bloom are load; that a dim idle craft has ended.
- medium: live animation in a click-through overlay, 1280x800 test frame.

## Poles and the combined candidate
- BEAUTIFUL pole: dense rings (40+ LEDs), heavy additive bloom, rainbow chords between neighbours,
  per-LED hue cycling, constant shimmer. Gorgeous, but heat and needs drown in the shimmer.
- CLEAR pole: each craft a plain ring in its session hue; strain = one shared ring colour step per level
  band (amber/orange/red) with a plain size jitter; needs = the ring brightens and steps beside the
  front window. No halo, no particles.
- Combined (shipped): the beautiful saucers (jewel diamonds, glass core, spire, soft additive halos),
  plus the CLEAR pole's two structural devices: (1) strain recolours every craft's ring together along a
  single ordered heat ramp, so "how bad" is one shared colour, and (2) needs-you is the only craft that
  MOVES to a fixed knock spot by the front window and the only one that breathes.
- Style dimensions that differ between poles: LED density, glow/bloom, palette (per-LED hue variation
  vs pure session hue), particles (embers, motes), and motion vocabulary.

## Encoding table (visual-encoding)
| Datum | Visual variable | Why (principle ids) |
|---|---|---|
| session identity | hue of glass heart, spire, satellites, unlit ring baseline; never removed | categorical hue (COLOR-04, COLOR-06); kept under strain/VPN so "which colour" survives |
| cpu (cores) | angular speed of a bright chase head round the ring (0.3 + 1.9*cpu rad/s) | rate reads in periphery; motion is the datum (motion.24, motion.14) |
| mem (GB) | ring radius (36..70 px) and the fraction of ring slots lit | size for a gestalt "bigger"; ENC-03 accepted: no precise magnitude asked |
| procs | count of orbiting satellite diamonds on a tilted outer orbit | whole-number count as discrete marks (ENC-07 spirit) |
| state idle/working | brightness of the whole craft (dim, never off) | low end never vanishes (style: "zero is black only when truly zero") |
| state needs | moves to a knock spot beside the front window, 1.6 s breath, ripples, a soft beam | a dynamic channel no other datum uses, one target (motion.11, motion.15); slow so not a strobe (motion.18) |
| m.level + thermal | shared heat ramp hue -> amber -> orange -> red on ring LEDs, out-of-sync flicker, wobble, jitter, embers, faster wander | one ordered ramp, anchored top in red (COLOR-04, style "anchor extremes"); fire connotation fits heat |
| m.mempress | ring LEDs randomly dropping out | a second, independent cue; MEDIA-05 risk noted |
| net.mbps | rate of small rising hue motes from each spire | flow as particle rate |
| vpn down / loss | grey-blue drain of LEDs, craft huddle mid-free-space, chase slows, one red heartbeat (1.5 s), sweeping searchlight | categorically different motion (gathering, slowing, cold) from strain (scatter, heating) |
| reconnect | one rainbow bloom ring + scatter of session-hued sparks, once | the only celebration in the grammar |
| play (pair, amt) | the pair orbit a shared centre, rings turn rainbow, a bead arc carries notes between them | decoration declared as permission, not data (floor item 7) |
| glow/density/drift/sat/size | halo radius+alpha / LED, satellite and particle counts / wander rate / V.hsl sat / all radii | the five contract multipliers |

## Composition (visual-composition)
- Primary layer: the crafts in the largest free rectangle beside the focused window (right, left, above
  or below, whichever has most area), laid out in a 1-2 column zigzag; secondary: particles; context:
  the desktop. One primary signal at a time: a needing craft is the only thing that leaves its slot.
- Focus avoidance: free-rect anchors plus `V.avoid`; when the window jumps onto a craft it makes a swift
  eased dash out (measured 0 centres inside after 1.5 s on a1, b1, b2, c1, c3).
- Menu bar 22 px + 50 px margin; dock: free rect ends 120 px above the bottom.
- Needs knock spot: just outside the front window's top corner on the free side, where the eye already
  is; the other crafts shift 190 px outward to keep that spot clear.
- VPN huddle sits at the free rect's centre; the beam sweeps upward from it.
- Annotation: no on-screen text (an ambient pet); the COLOPHON is the disclosed mapping (legend=1).

## Measurements (self-check)
Idle lit area 0.5-0.8 % (budget 6 %); strain peak 3.4 %. Real-time 120 fps headless; 108 fps at
density=1.8 glow=1.8. No JS errors on any timeline.

## Skill friction
- visual-intent has no medium profile for an ambient, peripheral, all-day animated overlay; I invented one.
- visual-intent's intent->family table has no entry for "collective mood" or "status pop-out"; nothing maps.
- INTENT-04 "takeaway is a claim" fits a figure, not a continuous monitor whose takeaway changes minute to minute.
- visual-composition's MUST annotations (ANNO-03/04/05: caption, colour bar, axis units) cannot apply to a pet with no text; I substituted the COLOPHON.
- HIER-01 assumes one static hierarchy; here the hierarchy must change live (needs-you promotes one craft).
- visual-encoding ranks static channels only; motion channels (rate, rhythm, dash, breath) have no accuracy ranking.
- COLOR-06 "default to grey" conflicts with session hue as permanent identity plus a "beauty" mandate.
- motion.01/motion.16 (static first, final frame a complete chart) do not fit a never-ending live piece.
- motion.18 sets a flash ceiling but nothing in the skills says how slow a summons can be and still be noticed in ~2 s.
- visual-beautiful's "key at point of use" conflicts with a glanceable pet that must carry no labels.
- The skills give no rule for a datum that must be shared (machine strain) versus owned (per session) on the same marks.

## Individualizer
`s.iv` (0..7) picks a saucer FORM (`FORMS`, `window.VARIANT_NAMES`), the same in every scenario. Forms vary
structure only: ring tiers, crossing hoops, LED clustering, spokes, view elevation, bank and beacon spire.
None of them touches a data channel. Ring radius stays memory, chase speed stays CPU, satellite count stays
processes and hue stays session. A form may set the chase's head count, direction and step rhythm, but never its speed.
Faint glass hairlines trace every ring so a form still reads when memory lights only a few slots.
- 0 Halo: the original single ring, mast of two beads, one pendant.
- 1 Twin Deck: two stacked rings counter-chasing, twin antennae.
- 2 Gyre: a horizontal ring crossed by a tilted vertical hoop, beads at the hoop's poles.
- 3 Crown: six 3-LED jewel clusters, chase steps cluster to cluster, a five-ray crown fan, no hairline.
- 4 Lantern: three tiers narrowing upward (a pagoda), a tall four-bead mast.
- 5 Pinwheel: seen from above (elevation 0.62) with five lit spokes from the glass core, no spire.
- 6 Comet: banked about 20 degrees, a short-tailed chase, a long trailing pendant below.
- 7 Spindle: three tiers narrowing downward (a top), two chase heads per tier alternating direction, a keel bead.
Gallery layout: free rect and all margins now derive from V.W/V.H/V.TOP/V.BOT (1280x800 reproduces the old
numbers). Crafts sit on a fitted grid (two columns keep the old zigzag) and scale `G.sc` with stage and count.
With focus null every craft keeps its slot, and the HUD band is kept clear. Checks:
`~/agent-storage/sprites/gallery/check/c1_choir/` (no errors, at most 0.8 ms/frame with 8 sessions).

## Round 2 (owner gallery feedback, GRAMMAR_V2)
- Bandwidth now lives inside the saucer: 8 radial lanes in the main deck. Download = cool white-blue pulses rim -> core (core takes a cool tint), upload = gold pulses core -> rim; pulse count/brightness on a log Mbit/s scale. Link strain (net.strain, weighted by the session's own traffic) = pulses compress and stall at the rim, stutter, and pile into a bright clogged band. The rising uplink motes are gone (no particle enters or leaves the creature).
- Machine strain: embers removed; a red ember glow behind and inside the saucer, LEDs heat amber > red, and each ring slips out of register (offset + twist) with per-LED geometric noise. The body shake is softer and slower. No ring, ripple or flash.
- Play: bead arc and rainbow LEDs removed; the pair drifts together, makes one eased half-orbit twirl and parts.
- Idle: slower base chase, slow breathing brightness, smaller wander.
- Satellites = background tasks (count); their drift is now constant, so CPU shows only in the ring's chase tempo.
- VPN huddle, searchlight and small red blinking beacon kept as is. Headless check: ~/agent-storage/sprites/gallery/check2/c1_choir/ (no errors, all scenarios and the a1/b1/d2 1280x800 trials).
