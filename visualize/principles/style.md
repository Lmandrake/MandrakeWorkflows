# Style rules shared by both families

CLEAR and BEAUTIFUL are poles of one design space, and these rules hold at both poles. They come
from rated candidate rounds; the ratings and notes are the evidence, in the study feedback
notes. Each is a default: break one when a candidate rates better without it. The truth
floor (`principles/modes.md`) is never a style choice. Pole-specific rules stay in the pole's
skill (`visual-beautiful` for BEAUTIFUL; `visual-encoding` and `visual-composition` for CLEAR).

## Colour
- **Anchor both extremes.** The top of an ordered ramp is an unmistakable extreme (a saturated
  red that reaches beyond the highest marks); on a dark piece the floor is nearly black, just
  distinguishable from the background. Both ends then read as extrema.
- **Ramp ends never loop back** toward a middle hue. Check the top and bottom of the rendered key,
  not only the LUT.
- **Put the colour break where a real concept changes** (gale force, freezing, sea level, a policy
  threshold). The break does a contour's job; arbitrary contour lines on top add little.
- **Palettes carry connotations.** Fire ramps say "heat". Pick one whose connotation fits the
  subject, or deliberately avoid the misleading one.
- **A pale, desaturated "neutral" ramp** costs much beauty and buys no clarity.
- **Colour manipulations must not invent connections.** A stretch or blend that produces a hue
  linking unrelated regions creates false structure; check blended edge colours for this.
- **Never strip colour that carries meaning.** Neutral grey marks that inform nothing (edges that
  leave dots without context) are worse than no marks; an edge coloured by its endpoints is
  information. Grey-first (COLOR-06) applies to colour with no meaning, not to this.

## Marks
- **Fine, crisp, separated marks.** Small sharp points with space between them read as
  high-resolution samples; big soft discs merge into blur and read as low quality.
- **Fix moiré by sampling, not by enlarging marks** (sub-pixel jitter, supersampling). Moiré is
  unphysical structure laid over real structure.
- **Mark length can carry magnitude too.** Slow flow gets short marks and fast flow long ones,
  redundant with colour; make the short ones short enough that the contrast is obvious.
- **Meaningful transparency reads well.** Opacity that encodes something beats decorative fade.

## Ground, light and density
- **Sink the ground plane.** On dark pieces, streets, sea floor and background context recede to
  nearly black, so they never read as structures and over/under is unambiguous.
- **Zero is black only when the data is truly zero.** The lowest real values sit visibly
  above the floor; dim is fine, black is not.
- **Not too dim.** On a near-black floor the data marks still need enough luminance to glow.
- **Avoid saturation; it costs clarity and beauty at once.** Blending that burns dense regions to
  white or yellow loses information. Prefer blending that saturates toward the hue.
- **Density against sparsity is valuable.** Protect small sparse structures beside dense cores
  from being washed out or culled.
- **Dense cores need internal structure.** Aggregate, bundle, tone-map, or colour by a
  sub-attribute so a cluster's interior is not a saturated blob.

- **Inner structure comes from crisp means, not blur.** Fading or blurring a dense core to
  thin it reads as worse, not clearer.

- **Spend space where the structure is.** Compress sparse periphery; give the dense interior room.
- **Group what belongs together.** When the data has a hierarchy, keep siblings near each other.

## Structure: clarity means revealing, not removing
- **Sparser is not clearer.** A clearer version surfaces something the other hides (a front, a
  peak, where the strongest value is, a shift). Replacing streaming flow with an arrow grid
  simplifies without clarifying; keep the flow and add the structure on top.
- **A comparison that is claimed must be visible at a glance**: observed against modelled, before
  against after, with the difference drawn.

## Time
- **Motion must mean something:** animate data time or a meaningful transition, never an
  algorithm settling (a layout solver's motion is an artefact, not data).
- **A movie needs an interesting question, not just a true one.** Choose the time axis for the
  question it answers (when things began, how a project grew), not the nearest timestamp.
- **Appearances ease in:** fade, grow or bloom new elements over several frames; never pop.
- **Never map a resetting quantity (a sawtooth) to geometry**; it makes shapes slam for unseen
  reasons. Use colour or brightness, or mark the resets.
- **Anchor time streams with events the viewer recognises**, and give unfamiliar polar or spiral
  forms a reading aid or a familiar companion view.
- **Show the real events, then let them decay.** Drawing each logged event with a short
  afterglow is more contentful and more interesting than a summary of it.
- **Every pole must answer the piece's question at a glance.** If the question is "do the days
  repeat?", repetition must be visible without deep thought; beauty that hides the answer loses
  on both scores.
- **Motion is the native medium for time-varying fields.**
- **Give time a narrative device** so the viewer never has to scrub: a small timeline with "now"
  marked, phase labels, or a trace of where the extreme is. Time-trace panels under the main view
  work as story.
- **Stills of moving fields need compensation:** length contrast, an arc panel, a peak marker.
- **Tone down overlays that animate dramatically** (isosurfaces, contours) so they do not upstage
  the data.

## Text and keys
- **Minimal text:** a short title and a compact key on the canvas; the rest in the caption or
  colophon.
- **Readable type at viewing size** in every panel and key. Tiny text costs clarity and beauty.
- **Labels never move or flicker in motion pieces.** Pin them (fixed anchor, gentle fade) or
  drop them; label the key threshold region in large readable type.
- **When centred labels collide, drop the lesser one, never shift it.** Rank by the stated
  importance, keep the larger mark's label, and word the subtitle as "the largest" rather than a
  fixed count.
- **Every colour on the canvas is in the legend**, with an explicit "other" where needed.
- **State the labelling rule on the canvas** ("divisions with ≥ 3 units", "top 8 hubs by links");
  unexplained single labels read as strange.
- **One colour metaphor per picture.** Never mix, say, colour = community with colour = type for
  the remainder.
- **Label a coherent set** (all of one kind, or the top N of a stated kind) so viewers do not
  wonder about the rest; make the remainder discoverable on hover where interactive.
- **Labels are anchored and self-explaining.** Centre each label on its mark, size it by a stated
  importance, and say what the labelled set is ("largest hubs"). Off-centre labels of unclear
  importance cost clarity and beauty.

- **Never superimpose alarm outlines** (red boxes, white step lines) on a beautiful ground; mark
  outliers in the piece's own palette with restraint, and show a reference pattern once, in its own
  place, rather than over every row.
- **Every actor gets its macroscale pattern** (human and agent alike), so their rhythms compare.

- **One colour, one meaning across all panels** of a piece; never reuse a hue pair for a second
  distinction (actor in one panel, above/below typical in another).
- **Never compare two aggregates by interleaving bars**; give the second series another channel (a
  line, ridge or glow) on the same axis.
- **Protect a winner:** add to a top-rated piece only through a channel it does not already use.

- **A combined piece succeeds when the viewer draws a conclusion of their own** from it.
- **In a movie, flash context briefly as it happens** (name an unusual event for a moment as the
  sweep passes) rather than leaving it to a static note.

## Knowing when to stop
- **A piece is done** when context marks are present but not intrusive and it shows the
  information the data holds. Stop adding there.
