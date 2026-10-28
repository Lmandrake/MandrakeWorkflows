---
name: visual-beautiful
description: >
  The BEAUTIFUL family of the visual-reasoning stack: data visuals that maximize
  communication plus beauty, the sibling pole to the CLEAR family's communication
  plus clarity. Use when the user asks for something beautiful, striking, data art, a
  poster, a wall or lobby display, an exhibition piece, a screensaver, a hero image, a
  glowing network, a LiDAR city, a wind or flow animation, or "make it gorgeous"; and
  when the user wants options, to make both poles plus a combined candidate and rate
  them (the default when a request names neither pole). Keeps the truth floor (real
  data, disclosed mapping) while relaxing style rules.
---

# Visual Beautiful

## Purpose
CLEAR and BEAUTIFUL are two poles of one design space. CLEAR maximizes communication and
clarity and tends toward sparsity. BEAUTIFUL maximizes communication and beauty and tends
toward aesthetics. **Communication is the shared floor and is never traded away.** The win
is a piece that is high on communication, clarity and beauty at once, so this skill always
looks for the front between the poles, not just its own pole.

Beauty here is not decoration on top of data. The strongest pieces are beautiful *because*
the data is legible in them: colour breaks where the physics changes, marks that look like
samples, motion that is the phenomenon.

## When to use
- `visual-intent` handed off here. That is the default: a request that names neither
  pole gets a CLEAR version, a BEAUTIFUL version and one combined candidate. A request
  for beauty, art, display or exhibition narrows to this pole alone.
- A CLEAR figure exists and the user wants a striking companion of the same data.

**Not alone** when the reader must read exact values or the output feeds a decision. Then
CLEAR is required and a BEAUTIFUL piece may be a companion, never the sole output. Say so.

**Not at all** when no renderer can draw the data shape honestly (step 3 finds nothing
primary): make the CLEAR figure and say why.

## Inputs
The intent record from `visual-intent` (audience, data abstraction, reader task,
medium, `modes`), plus four art fields you write before any styling:
```
aesthetic_intent:   <one sentence of feeling that does not misstate the data
                     ("an airline route network", not "air traffic")>
required_readings:  <what a viewer must be able to get right, e.g. "tallest areas",
                     "where the wind is strongest, and when">
must_not_conclude:  <readings the look invites but the data does not support>
medium:             <interactive web | high-res still | video loop | wall display>
```

## Modes
Read `~/dev/MandrakeWorkflows/visualize/principles/modes.md` once per task. With no `modes`, the
default (office, technical meetings, workshops) gives the full colour bandwidth: rainbow
and turbo are allowed, and there is **no colour-blind or grayscale requirement**.
- `colorblind_safe` is opt-in, never by habit. It costs most of the hue space this
  family lives in, so add it only for journals or audiences you cannot vouch for.
- `journal` = `colorblind_safe` + `archival` + print resolution and sizing. It does not
  require grayscale; that is `print_grayscale`, invoked on its own.
- `projector`, `accessible_web`, `lay_audience`, `archival` as the table says.

## The communication floor (always on, every mode)
Breaking any of these lets a viewer believe something false about the data, or not know
what is data. They cost almost nothing in colour or composition.
1. **Real data.** Simulated, modelled, interpolated and derived layers are labelled as
   such on the piece (UNC-03, SCI-03).
2. **The mapping is disclosed** in a short caption and a colophon (sources, encodings,
   transforms, omissions, decoration), and the drawn colours really follow it.
3. **A key at the point of use** whenever the piece asks for value or order reading. A
   colophon one click away is not a key.
4. **Colour maps:** never jet; the map class fits the data (COLOR-04); no silent clamp
   (out-of-range values are either absent or keyed as "≥ max"); a lifted or trimmed map
   is recorded. A rainbow on a quantity is declared, spans the full data range, and comes
   with a key or readout that gives the order.
5. **Magnitude honesty (G1):** area ∝ value, no 3-D height to compare non-spatial amounts,
   exaggeration and non-scale sizing disclosed, the map projection's scale stated.
6. **Unsupported derived values** (heights with no ground nearby, interpolated wind
   outside the stations' reach) get their own declared appearance, never a real value
   such as zero.
7. **Effects are declared.** Glow, depth shading, bloom and trails are either
   data-derived transforms or independent decoration, and the colophon says which.
   Every hidden renderer default is bound or switched off (step 3).
8. **Network and embedding groups say what they mean**: a source attribute, an algorithm
   result, or only the layout (NET-03). Layout distance between clusters means nothing.
9. **Time:** state data time against playback time and any interpolation ("hourly
   fields, interpolated"); mark a loop seam on non-periodic data; at most 3 flashes a
   second.
10. **Claims and aggregation:** any number in a title or caption is checkable against the
    encoding (SCI-06); KDE, hexbin, bundling, LOD and smoothing disclosed with their
    parameters (SCI-07).
11. **Look at the render at final size** in its real medium, and keep it reproducible
    from its scene file.

## Style rules
Read `~/dev/MandrakeWorkflows/visualize/principles/style.md`: the style rules shared by both
families (anchored extremes, colour breaks at real thresholds, fine crisp marks, no
saturation, near-black floor, clarity as revealed structure, time devices, minimal
readable text). This pole pushes them to full strength and adds:
- **A rainbow body between the anchors** is the strongest default for an ordered field
  on a dark ground (declared, full range, keyed: floor item 4).
- **Fine dots floating in space:** prefer visible gaps between samples over filled,
  surface-like splats, even if scan-line gaps show.
- **Density against sparsity is the beauty** of network and point art: small sparse
  constellations set against dense cores.
- **Glow** stays soft, declared and background-subtracted so the floor stays put.
- **Motion adds beauty** even to static subjects: a slow turntable for a 3-D scene.
- **Artistic hierarchy is free**, and keys sit inside the composition, not stuck on;
  keys, units and essential caveats stay visible and near what they qualify.

## Procedure
1. **Take the intent record** and write the four art fields. If you cannot name a
   required reading, the piece is decoration; ask one focused question.
2. **Fix modes** from the stated destination only. None means the default.
3. **Choose a renderer by capability, never by name.** Ask for data shape, primitive,
   dimensionality and output mode with
   `python3 ~/dev/MandrakeWorkflows/visualize/tools/route_renderer.py --shape <shape> --output <mode>`
   (registry: `~/dev/MandrakeWorkflows/visualize/registry/renderers.yaml`). Bind or switch off
   every hidden default it lists, and declare the ones you keep. No primary match →
   CLEAR only.
   Time streams: add `--task` (live, drill-down, distribution over time); a dark dashboard
   tops out at handsome, so see `~/dev/MandrakeWorkflows/visualize/principles/time-series-and-dashboards.md`.
4. **Write a scene file** (data sources, transforms, bindings, effects, camera, modes)
   so the piece regenerates from it. Never accept a renderer's defaults (ENC-09).
5. **Make the candidates** (next section) and render each at final size.
6. **Run the floor** on each render: key present, no clamp, low end not vanished into
   black, units, validity mask, text not clipped, plus whatever the modes add.
7. **Read each render back** against the required readings and `must_not_conclude`.
8. **Hand the candidates to the user to rate**, with the short caption and colophon.

## The Pareto habit: both poles plus one combined
Unless the request names one pole, every piece produces three candidates from the same
data and scene:
- **CLEAR pole:** reveals the structure (fronts, peaks, extremes, the comparison), on a
  sparse ground. Not a dimmed copy of the beautiful one.
- **BEAUTIFUL pole:** the style rules above at full strength.
- **Combined:** the beautiful look plus the one structural device the clear pole found
  most useful (for example a rainbow body with anchored extremes plus a timeline).

Vary only a few declared style dimensions between them: palette, mark size and density,
glow and depth shading, chrome and labels, camera, motion. Then ask the user to rate each
candidate on **clarity** and **beauty** separately, 1 to 7, with a one-line note on what
would make it a 7. Communication is the floor each candidate must pass first, not a
third score to trade.
- **Never add the scores.** Show positions on the two axes and keep every candidate
  nothing else beats on both.
- **Iterate on the notes.** The next round moves the combined candidate toward the front;
  a combined candidate that rates at or above both poles is the target.
- **Record ratings and notes** in a FEEDBACK file beside the study, and fold any lesson
  that holds across studies back into this skill as a rule.
- These ratings are formative. They place candidates for this user; they are not
  evidence that the family works for other readers.

## Output contract
- One scene file per candidate, rendered at final size in its real medium.
- A short caption on the piece (what it is, that it is real data, the mapping, the time
  basis) and a colophon (sources with licences, encoding table, transforms, omissions,
  effects and decoration, renderer and hidden defaults handled, modes).
- A ratings table (candidate, clarity, beauty, note) once the user has rated.

## Failure modes
- Beauty bought with truth: an undeclared glow, a clamp, a layout gap read as real.
- A "clear" candidate that is merely sparse, so clarity loses and beauty loses too.
- Colour-blind or grayscale constraints applied by habit in the default mode, throwing
  away the bandwidth the piece needs.
- Big soft marks, a navy floor, a dim palette, tiny text, cores burned to white.
- A time piece with no arc device, so the story needs scrubbing.
- A skill or note that names a toolkit instead of a capability (D6).

## Source basis
Truth floor and gate table: `~/dev/MandrakeWorkflows/visualize/principles/modes.md`. Gates:
`~/dev/MandrakeWorkflows/visualize/evaluation/RUBRIC.md`. Principle IDs:
`~/dev/MandrakeWorkflows/visualize/principles/principles.yaml`. The style rules are distilled from
rated rounds of several data-art studies.
