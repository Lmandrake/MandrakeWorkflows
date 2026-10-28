# Row content — what goes on each row, and how to measure it honestly

Read this when writing the generator that fills `ITEMS`: mining effect lines, measuring sizes,
choosing a sort criterion, or adding a marker/badge to rows.

## Mining the consequence out of the data

A label is not a decision aid. Read the fields that change behaviour. RimWorld's
`TileMutatorDef` carries `animalDensityFactor`, `plantDensityFactor`, `junkDensityFactor`,
`extraGenSteps`, `blacklistedRaidStrategies`, so the line becomes *"Halves plants, doubles junk,
blocks siege raids"*. *"A headwater is where a river begins"* is not decidable.

- 🔴 **Text-matching a tag in raw XML truncates on nested tags of the same name.** A regex for
  `<ThingDef>…</ThingDef>` stops at the first closing tag, which can be a nested one (e.g.
  `<descriptionHyperlinks><ThingDef>…</ThingDef></descriptionHyperlinks>` before the field you
  want). The field then reads as ABSENT and the fallback gets recorded as a measurement. Parse the
  XML properly, and **resolve through your own mod's patches**: the game reads the patched value,
  not the donor's shipped one.
- An inference from a name (fields empty) is prefixed as one and gets its own filter.

## Sizes are measurements

A size panel is worth exactly as much as the resolver behind it. A resolver that silently falls
back to a default ("inherited") draws a plant several times too small while looking measured.
**Verify one donor row's number against the raw def before serving a batch, and print the SOURCE
of every measured value on the row.**

## The criterion: quality is not worth

A metric (resolution, contrast, fill, saturation) can rank quality; it cannot rank worth. A
sprite ranked fine at 2,850 px / contrast 0.30 was ruled *redraw* because it was "too odd
to discard"; good art was cut for looking terrestrial; weak art kept for its
outline. So:

- Name the criterion in one line next to the counts (`CONFIG.criterion`), including what it
  cannot rank.
- Read overrides as a GROUP (`serve_sheet.py --decisions f.json --overrides`) before acting on
  any one. Scattered disagreements read together are usually one unwritten rule.
- Zero overrides looks identical whether you nailed the criterion or disagreeing was too hard.
  Compare against other sheets before calling it success.

## Count a marker against the real data before you add it

A badge, glyph or chip is worth adding only if it is **rare**. Measured on a 137-item board:

| candidate | rows | verdict |
|---|---|---|
| a draft is ready | 1 | ship it |
| an offer exists | 12 (9%) | ship it |
| material on disk | 29 (21%) | ship it |
| message body present | 33 (24%) | ship it |
| who/what this involves | 105 (77%) | cut it, wallpaper |

A marker on most rows teaches the eye to skip that position and drowns the markers sharing it.

- **Never mark a field that is never populated.** Four schema fields were filled on 0 of 137
  rows; their absence reads as "no problem here" when it means "nobody recorded one".
- **A FLAG is not a CATEGORY.** A flag (absence normal) must be sparse; a category (every row has
  exactly one) is correctly at 100%. Give them separate positions on the row.
