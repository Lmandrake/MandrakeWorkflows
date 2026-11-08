# Why the symbol glyphs look blurry, and the three ways out

Owner, 2026-11-06, on the new Night Signals glyphs: *"aren't really great — very blurry and don't
look very good"*, and Kaleidoscope Seeds and Mothership Choir *"have much higher resolution... we
want to aspire to that cleaner, higher res look."* He asked for a comparison before committing to
a fix. This is that comparison's record.

**The images:** `~/agent-storage/sprites/symbol-resolution-comparison/SYMBOL_RESOLUTION_COMPARISON.png`
(all four grids in one), with the individual stills in `stills/` beside it. Rebuild them with the
script named at the bottom. Not in git: large derived artifacts never are.

## The diagnosis

The blur is not a drawing mistake. It is the LED look, working as designed.

- Living Sigils draws each lit cell as a **64 px radial-gradient blob** (`prototype/sigils/engine.js`,
  `sprite()`) scaled to **three times the cell pitch**, with a small hard core under it, plus
  additive halo, ember and two bandwidth layers over the same cell. A cell's light therefore spills
  across its two neighbours in every direction. That overlap IS the LED-panel character, and it is
  also the blur. You cannot have one without the other at that blob width.
- Kaleidoscope Seeds (`prototype/c4_kaleido.html`) and Mothership Choir (`prototype/c1_choir.html`)
  draw with real vector geometry — `arc`, `moveTo`, `lineTo`, bezier — so their edges resolve at
  device resolution. On the owner's screens (1920x1080 at scale 2.0, i.e. 3840x2160 device pixels,
  two of them) that is a 2x advantage the bitmap species cannot reach through the cell grid.
- The grid is **already variable**: `engine.js` computes
  `N = clamp(2*round((9*sqrt(density)-1)/2)+1, 5, 15)`, so 15x15 is a parameter change, not a
  rewrite. Nothing is hardcoded at 9.
- Measured, not assumed: at the default size slider and the real per-session memory in the Augur
  fixture (0.33 GB), the whole glyph is **23 CSS px across — 2.6 px per cell**, and the blob over
  each cell is 7.8 CSS px wide. At the maximum slider and 2 GB it is 115 CSS px, 12.8 px per cell.
  The complaint is loudest in the working state, where the pilot light and the bandwidth runs add
  three more additive layers over the same cells.
- Corroborating the eye with a number (mean absolute luminance gradient per unit lit area, over the
  three symbols): working state **A 4.9, B 11.9, C 14.3**; idle state **A 9.1, B 12.1, C 17.2**.
  Higher is crisper. This is a sanity check on what the stills show, not a verdict — the owner's
  judgment is the verdict.

## The three arms

Symbols chosen to stress different things: **Batman** (the wide-V case the drawing agent found
*"collapsed into one blob"* under the real glow, and had to thin from ~50 lit pixels to 25 — it was
fighting the renderer), **TARDIS** (the only rectilinear form, so it is all 1-cell strokes and
1-cell gaps), and **Cog** (the one 4-fold-symmetric glyph, and the thinnest stroke in the set: a
1-2 cell ring, the sharpest test of blob width). Each is rendered in all three arms at both the
working state with traffic at the maximum size slider and the idle state at the default slider.

### A — current

The shipped renderer, untouched. 9x9, blob at 3x pitch. The baseline he is objecting to.

### B — tightened LED

Same renderer, grid at **15x15**, blob from 3x pitch down to **1.2x**, core from 0.55 of pitch up to
**0.9**, core floor from 2 CSS px to 1. Tuned, not guessed: a sweep of blob 1.0-1.8 against core
0.7-1.0 at both sizes, judged on the stills. 1.2 is the widest blob that still leaves a dark gap
between adjacent lit cells, which is what keeps the grid legible as a grid; core 0.9 fills the cell
almost edge to edge, which is what lets a 1-cell stroke survive the glow.

The three symbols are **redrawn native at 15x15**
(`prototype/experiments/resolution/glyphs15_night.js`). This matters for the comparison's honesty:
`makeGlyph` resamples with `round(i*(M-1)/(N-1))`, i.e. nearest neighbour, so a 9x9 table at N=15
duplicates 6 of its 9 rows and columns and reads *worse* than the 9x9 original — uneven stroke
weight, 1-cell rows beside 2-cell rows. Comparing that against a hand-drawn vector arm would have
flattered arm C for a reason unrelated to vectors. At M=N=15 the same resample is the identity.

**Honest cost:** all **48 glyphs across the six species get redrawn at 15x15**, by hand, each one
checked against the renderer's two silent invariants (force-mirror, pilot light). Three are done
here; forty-five are not. In exchange it **keeps the LED-panel character** — the cells, the mutation
ticks toggling symmetry orbits as CPU rises, the per-pixel bandwidth runs, the rows slipping out of
alignment under thermal strain. Nothing else in the renderer changes, and the data mapping is
untouched.

### C — vector paths

The same three symbols as true geometry — `arc`, `lineTo`, `bezierCurveTo`, stroke and fill — in the
idiom Choir and Kaleido already use, so every edge resolves at device resolution
(`prototype/experiments/resolution/armC_vector.js`). The data mapping is deliberately identical to
`c6_night`, so the only variable a viewer compares is how the symbol is drawn. The LED cell
behaviours get vector stand-ins that carry the same *reading*: the CPU sweep becomes a rotating
gradient wedge clipped to the glyph's own outline, bandwidth becomes round beads running the glyph's
radius, thermal strain becomes a shear transform plus an ember wash clipped inside the figure.

**Honest cost:** a **new renderer plus 48 vector drawings**, and it **loses the LED-panel look
entirely**. There are no cells, so the bitmap character has no literal equivalent — the stand-ins
read the same but they are a different look, and that is the arm's price, not an oversight. The
layout and physics in this arm are also deliberately minimal (spring to home plus curl-noise
wander); the shipped engine's navigation, huddle, knock and play behaviour would all have to be
ported, which the stills do not show because the stills are static.

## What I observed rendering them

- **Arm A is worse in the working state than idle**, and the working state is what he watches. With
  traffic and a lit pilot light there are five additive layers over the same cells; on Batman the
  wash swallows the silhouette's middle, and the glyph stops being a bat.
- **Arm B is a large improvement, and it is not close.** At 15x15 with the tightened blob the cells
  read as individual lit cells again, the TARDIS door panels resolve as 1-cell strokes with visible
  gaps, and the Cog's ring is a ring rather than a halo. The gradient measure goes from 4.9 to 11.9
  in the working state — most of the way to arm C's 14.3.
- **Arm C is crisper still, and cleanest at the small idle size**, where it is the only arm whose
  symbol is unambiguously identifiable at 23 CSS px. That is its real argument: not the big state,
  the small one.
- **The symbol that survives one arm and dies in another is Batman.** It dies in arm A's working
  state (the wash fills the wings). It survives arm B. In arm C it had to be *redrawn twice*: the
  first bezier had a deep head dome and two deep scallops, and at sprite size the wings read as
  spindly claws — the same "collapses into one shape" failure as the 9x9 bat, reached by a different
  route. A low flat head and one shallow scallop per wing fixed it. Vector resolution does not save a
  bad path; it just renders it sharply.
- **Two real drawing faults in arm C's first draft, both worth recording.** The TARDIS door panels
  were drawn as *dark* hairlines and were completely invisible: the stage composites with
  `globalCompositeOperation = "lighter"`, under which a dark stroke adds nothing. They have to be
  additive. And the Cog's teeth started outside the rim's outer edge, so each tooth read as a
  separate spoke floating off the ring; filling the ring as an annulus with the teeth overlapping
  into it makes one continuous silhouette. Either fault alone would have made this arm look
  featureless for a reason that has nothing to do with vectors.
- **TARDIS gains the most from B, Cog gains the most from C.** A rectilinear form is what a cell grid
  is naturally good at, so B nearly closes the gap on the TARDIS; a circular form is what a cell grid
  is naturally worst at, so the Cog's ring and round teeth stay visibly better in C at every size.

## My read

**Arm B is close enough that the vector rewrite is hard to justify on resolution alone.** It gets
most of the way to arm C's crispness, it keeps the LED-panel character the species was designed
around, it is a four-constant change to the renderer plus redrawing, and it cannot regress the other
five species' behaviour because nothing but the grid and the blob changes. Arm C is better, most
clearly at the small idle size, but it buys that by giving up the look — and it costs a second
renderer to maintain beside the first.

The decision that actually matters is therefore not "which is sharper" but **whether the LED panel
is the thing he wants**. If it is, B. If the LED look was never the point and only the symbol
mattered, C is the better object and the cost is honest. That is his call, which is why this doc
stops here.

## Rules these experiments respect

- **The shipped renderer's behaviour is unchanged.** Arm B's knobs are read from one optional global
  (`SPRITES_SIGIL_TUNE`) whose four defaults are the shipped values, so with nothing set the output is
  identical — verified by rendering the arm-A stills before and after the engine edit and comparing
  bytes: all 15 identical. Only the pages under `prototype/experiments/resolution/` set it;
  `app/stage.html` does not, and nothing in `app/` or `tests/` reads it.
- **Neither experiment page is registered in `app/stage.html`'s `SPECIES` list**, so the live app
  never loads them. (The stage keeps only a piece's *last inline* script and ignores `src` tags,
  which is why a new species has to be listed there — and why a `<script>` tag written inside an HTML
  comment in that file is parsed as real by the loader's regex and eats the next real one.)
- Only the three comparison symbols are drawn. The owner ruled: hold all five remaining species until
  the renderer is settled.
- `tests/test_sigil_glyphs.py` still passes (16 glyphs over 2 species), as do the stage tests.

## Rebuilding the images

```
cd ~/dev/MandrakeWorkflows/sprites
python3 -I prototype/experiments/resolution/render_comparison.py
```

It writes to the machine's agent storage root (resolved via `~/dev/Lodestar/bin/lib/agent_storage.py`,
never a hardcoded path) under `sprites/symbol-resolution-comparison/`.

Headless Chromium via playwright (**which works on this machine** — Chromium 151.0.7922.34, launched
and verified; earlier docs and tickets saying it is absent are wrong). It serves the repo, drives each
arm's page in live mode at `dpr=2`, feeds one synthetic live message, advances a fixed number of
steps and screenshots the sprite's reported position, so the stills are deterministic. Arm pages:

| Arm | Page |
|---|---|
| A | `~/dev/MandrakeWorkflows/sprites/prototype/c6_night.html` (shipped) |
| B | `~/dev/MandrakeWorkflows/sprites/prototype/experiments/resolution/armB_led15.html` |
| C | `~/dev/MandrakeWorkflows/sprites/prototype/experiments/resolution/armC_vector.html` |

---

# Round 2 (2026-11-07): edge-only symbols, high density, the fine-pixel jellyfish

Owner, on round 1: *"The one you're making doesn't really look quite right. Even the vector graphic bat
looks poorly. Could you try again, but this time make them just the edges similar to how you made the
circles in the 'choir' species? ... enhance the jellyfish to use smaller pixels that read with less diffuse
edges ... I think you have a lot more resolution to work with than you're currently using."*

**The image:** `~/agent-storage/sprites/symbol-resolution-comparison/SYMBOL_RESOLUTION_COMPARISON_v2.png`,
with every raw still in `v2/stills/` and every crop placed on the sheet in `v2/crops/` beside it.
Rebuild: `python3 tools/trace_symbols.py && python3 tools/build_symbol_comparison.py` (about 20 s).

## What changed

- **The bat is traced, not drawn.** `tools/trace_symbols.py` thresholds the owner's reference
  (`<agent storage>/sprites/refs/batman_reference.png`) on yellow-ness, runs marching squares at level
  0.5 for sub-pixel contours, keeps the ring's outer edge and the edge of the black interior (which IS the
  bat silhouette: ears, scalloped wing tops, three lower lobes and the central point, meeting the ring at the
  wing tips), mirror-averages about the measured axis and simplifies (RDP, 0.6 px). Output:
  `prototype/experiments/resolution/symbols_edge.js`, read by both new arms. TARDIS and Cog are round 1's
  arm-C geometry turned into outlines.
- **Measured fidelity:** IoU of the re-rasterised traced outline against the reference's own yellow mask is
  **0.957** (0.972 before mirror-averaging; the reference itself is not perfectly symmetric). Ring aspect
  as traced: **1.796:1** for the outer edge. (The brief guessed ~1.42; the reference measures 1.8.)
- **Arm B2, edge LED** (`armB_edge.html`): the shipped engine over glyph tables generated at load: a cell
  is lit iff its centre is within half a cell of an outline, so every stroke is exactly 1 cell. Grids 33,
  49 and 65 shown. Engine knobs: blob **1.0x** pitch (shipped 3x, round-1 B 1.2x), core 0.9, floor 0.5 CSS
  px, per-cell glow alpha 0.35, body halo **0**. Neighbouring cells no longer overlap into a smear.
- **Arm C2, vector edges** (`armC_edge.html`, an edge mode in `armC_vector.js`): the same outlines stroked
  as hairlines like Choir's rings (width E/45, floor 1 CSS px), no fill; the CPU sweep lights the outline
  inside a rotating wedge instead of a filled area; body halo at 0.35 of round 1.
- **The jellyfish** is **Siphonophores**, `prototype/c2_siphon.html` (the only species with bell and
  tentacles; variant Moon shown). A shipped-identical hook (`window.SPRITES_JELLY_TUNE`, set only by the
  build script's playwright init script) gives the "fine" look: 2.2x bell rings, 2.2x dots per ring, 1.8x
  tentacle beads, every hard dot 0.6x, per-dot glows 0.2, body halo 0.25.
- **Engine:** two new optional knobs (`led`, `halo`) and the FORCED-N cap raised 15 -> 97. The derived N
  is still clamped 5..15. **Shipped output unchanged, verified:** the 15 shipped stills (12 arm A, 3
  jellyfish) are byte-identical before and after the edits. One jelly still differed on the very first
  run and matched on every re-run, so that was run-to-run noise, not the hook. `tests/test_sigil_glyphs.py`
  passes. Nothing in `app/` changed.

## Sizes, measured not guessed

The script solves the URL size so the glyph extent E is exactly 23, 64 or 256 CSS px, at dpr 2, and shows
device pixels without downsampling. At **23 px** the pitch is 2.56 CSS px at 9x9, 0.70 at 33x33 and
**0.35 at 65x65**: below one device pixel. So at the idle default size a 65 grid is no longer discrete LEDs.
It is an antialiased outline that happens to be built from cells.

## What I saw (honest read)

- **256 px and 64 px:** the bat is recognisably the reference bat in B2 (all three grids) and C2: ring,
  both ears, the scalloped wing tops, three lobes and the point. B2 at 49 and 65 keeps a visible LED
  character with no smear. A (shipped) is still a blob.
- **23 px idle:** B2 and C2 both read as "the bat-signal oval with a bat in it" when magnified, and the
  TARDIS and Cog outlines are clean. At 1:1, though, **only C2 is unambiguous**. B2's dim 1-cell strokes
  at 0.35-0.7 CSS px pitch are thin and low-contrast, and the bat's interior detail (ears, lobes) is a few
  device pixels across. It reads as "bat emblem" mostly because the ring frames it. B2 at 23 px is a big
  improvement on A, not a win over C2. **At 23 px working**, the pilot light and bandwidth beads sit on top
  of the 2-3 device-px interior and compete with it in every arm.
- **The jellyfish:** the fine version holds the same identity (dome, rim, four tentacles, apex mark) with
  hard edges and no wash at 64, 128 and 256 px. The cost: the bandwidth pulses are far less prominent,
  because they shrank with everything else. If adopted, they should keep their shipped size.
- **Not done, by ruling:** the other glyphs, and any change to `app/` runtime behaviour.
