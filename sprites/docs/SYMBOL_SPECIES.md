# Six symbol species (owner selection, 2026-11-06)

Six new species of 8 variants each, in the Living Sigils idiom: a 9x9 LED bitmap per variant,
identity only. Requested by the owner; Batman and the Bat Signal came from a collaborator. The roster
below is **selected and closed** — the owner picked all 48 and settled the one duplicate.

Form carries no data. `GRAMMAR_V2.md` is binding: hue + variant form = identity, and the
`must_not_conclude` line forbids reading meaning into the shape. A shield does not mean
protected; a heart does not mean healthy. This species family is where that rule is most
tempting to break, because the symbols all *look* meaningful.

## The roster

| Species | Working name | The eight |
|---|---|---|
| Pop culture | **Night Signals** | Batman · Bat Signal · Star Trek delta · Autobot · TARDIS · Atari Fuji · Rebel starbird · Imperial cog |
| Space missions | **Mission Patches** | Voyager · Golden Record · DSN dish · Juno · ISS · JWST mirror (hex) · Mars rover · Orbit with primary |
| Science + computing | **Instrument Marks** | Bohr atom · integrated chip · light bulb · water molecule · binary tree · bell curve · neural net layers · gear |
| Natural world | **Wild Signs** | Sun · Mountain · Tree · Seed · Water drop · Antlers · Butterfly · Owl |
| Built things | **Made Marks** | Arch · Ladder · Lighthouse · Pyramid · Target · Balance · Bell · Hourglass |
| Heraldic charges | **Old Signs** | Shield · Sword · Skull · Wing pair · Phoenix · Ankh · Heart · Anchor |

Working names are the author's, not the owner's; he has not ruled on them.

### Decisions already taken

- **Drawing style per species (owner, 2026-11-07, from the style samples):** vector for Mission Patches,
  Instrument Marks, Wild Signs and Old Signs; dots for Made Marks. (Night Signals is already vector.)
  The Phoenix is the bird only: the flame band beneath it is removed.

- **Hourglass was picked twice** (science list and an elemental list). Owner, 2026-11-06: it
  goes to the built-things species, and a **gear** fills the science slot. Not an open question.
- **"Wing" means the wing pair.** A single wing is the only asymmetric shape in the roster;
  the pair was what was offered and selected.
- **Anchor sits in Old Signs**, not Made Marks — a heraldic charge before a tool, and it is
  what balances both groups at eight.
- Grouping is by *kind* (natural / built / heraldic). The owner's three elemental lists of
  eight were not thematically coherent, and he invited the rearrangement. Nothing moved out
  of the pop-culture, space or science sets.

## Why no renderer change is needed

The earlier design pass recommended an asymmetry opt-out flag in `makeGlyph`. **That
recommendation is withdrawn: all 48 selected symbols are bilaterally symmetric**, because the
owner did not select the lightning bolt (the one pick that demanded it). Do not add the flag
for this work.

For the record, in case an asymmetric symbol is wanted later:
`prototype/sigils/engine.js:31` force-mirrors every glyph left-to-right, unconditionally (it was
`prototype/c3_sigils.html:46` until the renderer was extracted, 2026-11-06). The
comment says "keep exact symmetry after resampling" — the intent was repairing resampling
damage to glyphs that were *already* symmetric, and since all 8 shipped ones are, the mirror
has always been a no-op. Asymmetric glyphs were never ruled out; it falls out of the code.
Lifting it means a per-glyph flag, skipping that loop, and having `orbit()` (engine.js:37, which
flips mirrored pixel pairs together so CPU mutation preserves symmetry) return the single cell
instead of the pair. ~5 lines across two functions.

## Constraints every glyph must satisfy

- **9x9 bitmap**, resampled to density N (5..15) by `makeGlyph`. Chunky silhouettes read; faces
  and text do not. The NASA meatball and the worm were cut for exactly this.
- **The centre pixel is always lit** — the "pilot light", `prototype/sigils/engine.js:33`. A
  hollow ring therefore gets a dot in its middle. The shipped "Eye" variant already lives with
  this, so it is survivable, not fatal.
- **Exactly 8 variants per species.** `% 8` is hardcoded in `app/stage.html:66` and
  `app/settings.js:108`. Six species of eight fits without touching either.
- **Mirroring is free symmetry, not a cost** for this roster: 4-fold symmetric glyphs
  (rows mirrored top/bottom too) get 4-cell mutation orbits via `vsym`, which is why the Sun,
  Target and Water molecule will mutate differently under CPU than the bilateral-only ones.

## Named execution risks

Three, all of them drawing problems rather than code problems:

1. **Bohr atom vs Orbit-with-primary** are the closest pair in the roster — both are a lit
   centre inside a ring, in different species. The atom needs crossed ellipses to stay
   distinct at 9x9. Check them side by side before accepting either.
2. **Arch fights the pilot light.** The always-lit centre pixel lands inside the arch's
   opening, which is the one place an arch must be empty. Either widen the opening so the dot
   reads as a keystone below the span, or accept it.
3. **JWST hex mirror is the hardest draw of the 48.** Hexagons on a square grid. It is also the
   most distinctive thing in the roster if it lands, so it is worth the attempt rather than a
   substitution.

Minor collisions to name around, not redraw: **Imperial cog vs the new gear** (two toothed
circles, different species), and the gear against the existing **Honeycomb** and **Spirograph**
in Kaleidoscope Seeds. Existing variant names already taken elsewhere, so these species must
not reuse them: Lantern, Trident, Halo, Star, Invader, Ascent, Lattice, Eye, Lotus, Trefoil,
Pentagram, Snowflake, Quatrefoil, Spirograph, Dandelion, Honeycomb, Moon, Saucer, Box, Lyre,
Spire, Pagoda, Corolla, Crown, Comet, Spindle, Gyre, Pinwheel, Twin Deck, Galaxy, Infinity,
Coil, Lissajous, Braid.

Note that **Space Invader already ships** as a Living Sigils variant, which is why Night Signals
does not include it.

## Trademark note

Night Signals and parts of Mission Patches are other people's marks. Private repo, the owner's
own desktop, never distributed — a non-issue as things stand. **Keep each species' glyph table
in its own file** rather than scattered through a shared table, so Night Signals is one
deletion if Sprites is ever published.

## How a glyph species is built (established 2026-11-06, drawing Night Signals)

The Living Sigils renderer was extracted so the eight-glyph tables can be one file each:

| File | What it is |
|---|---|
| `prototype/sigils/engine.js` | the whole Living Sigils renderer, `SpritesSigilsEngine(V, GLYPHS)`. Extracted **verbatim** from `c3_sigils.html`; checked by rendering all 8 shipped variants to PNG before and after (identical bytes). It calls `V.piece()` itself and closes over its own state, so two glyph species on one stage share nothing. |
| `prototype/sigils/glyphs_sigils.js` | the 8 shipped Living Sigils glyphs |
| ~~`prototype/sigils/glyphs_night.js`~~ | the 9x9 Night Signals table; **deleted 2026-11-07** when the species went vector (below) |
| `prototype/c6_night.html` | the piece: a COLOPHON and one line of script |

**Adding a species:** a table file, a piece HTML, then four registrations — `app/stage.html`
(`SPECIES` list **and** a script tag), `app/settings.js` (`SPECIES` + the `NAMES` fallback), the
`.species` grid column count in `app/settings.css`, and the `SPECIES`/`ALL`/`CONCEPTS` lists in
`tests/stage/harness.py`, `tests/js/test_r1_runtime.js`, `tools/render_gallery.py`,
`tools/build_gallery.py`. Add the table to `SPECIES` in `tests/test_sigil_glyphs.py` and it is
checked automatically. **Deleting one** is the table file, the piece, and those same lines.

🔴 **The stage ignores a piece's own `src` tags.** `loadSrc()` (`app/stage.html`) keeps a piece's
LAST inline script and nothing else, so `engine.js` and every table must ALSO be listed in
`app/stage.html`. A missing entry renders perfectly as a standalone page and throws
`SpritesSigilsEngine is not defined` only on the stage. (Also: never write a script tag literally
in a comment there — the loaders are one regex over raw HTML, and a mention in prose eats the next
real tag. Both filed in `LESSONS.md`.)

Two constraints were made mechanical rather than trusted, in `tests/test_sigil_glyphs.py`: every
row equals its own reverse (so the force-mirror provably changes nothing), and the glyph the
renderer builds equals the table (so the pilot light changes nothing either). It parses the `.js`
tables as text — no browser, no node.

**The pilot light turned out to be a non-issue for Night Signals.** The spec flags it as a risk for
the later Arch; all eight of these are drawn with the centre pixel already lit, so it adds nothing.
The test now *requires* that, which is the cheap way to keep the question from recurring per species.

### The vector renderer (2026-11-07): Night Signals moved off the LED grid

Owner, 2026-11-07: *"For the symbol catalog that Batman belongs a part of (Night Signals), I think we must go with
the vector edges to preserve visual identity."* So `c6_night` now runs a second renderer:

| File | What it is |
|---|---|
| `prototype/vector/engine.js` | `SpritesVectorEngine(V, GLYPHS)`: same contract as the sigils engine (calls `V.piece()`, own closed-over state), the same layout/navigation/huddle/knock/play code ported unchanged, glyphs drawn as 1-2 CSS px stroked outlines under `lighter`. Clip-free on purpose: `app/native/canvas.js` has no `clip()`. |
| `prototype/vector/glyphs_night_vector.js` | the 8 outlines, GENERATED — **the trademark-bearing file** (the 9x9 `sigils/glyphs_night.js` is deleted) |
| `tools/build_night_vector.py` | provenance: each glyph drawn as a filled silhouette at 4096 px (Batman: the owner's reference, upsampled and traced), mirror-averaged, marching squares, RDP, two levels of detail; sources land in agent storage |
| `tests/test_vector_glyphs.py` | 8 glyphs, closed loops, unit box, exact mirror symmetry, names = the Settings fallback |

Adding a vector species is the same four registrations as above, with the engine and table script tags in
`app/stage.html` and the table in `tests/test_vector_glyphs.py` instead of `test_sigil_glyphs.py`.

### The five 2026-11-07 species (built, all 8 drawn)

Registered exactly as the recipe above: `c7_patches` Mission Patches, `c8_instruments` Instrument Marks, `c9_wild` Wild
Signs, `c11_old` Old Signs (vector) and `c10_made` Made Marks (dots: `SpritesVectorEngine(V, T, {dots: true})`, the
23/64/256 lattices stored in the table, drawn as hard squares, CPU wedge lights the dots). Tables
`prototype/vector/glyphs_<stem>_vector.js` are GENERATED by `tools/species_glyph_sources.py`; none is trademark-bearing
(generic programmatic marks), so they need no one-file-deletion treatment.
All 40 glyphs are drawn, in roster order (IoU of outline vs source 0.94-0.99). "integrated chip" is named Chip and "neural net
layers" Neural net in the tables. Not yet judged by the owner: the species sheets are the review.

**Stage-verified 2026-11-07 (Laptop):** each of c6..c11 cast to iv 0..7 on `app/stage.html` draws all 8, one layer, 8 hits, no
console errors; nothing was broken on stage. After looking at every glyph at 23/39/64 px three were redrawn: **Neural net**
(doubled edge strokes read as a solid lattice), **Target** (three thin rings broke into a maze on the dot lattice; now two bold
rings), **Balance** (beam, cords and post vanished below 39 px). Named risks as rendered: Bohr atom and Orbit-with-primary are
distinct (crossed ellipses vs one flat ring); **the Arch risk is moot**, since the vector engine has no pilot light; the JWST
mirror holds at 39 px and blurs to a honeycomb at 23 px (left for the owner). Owner review sheet: agent storage
`sprites/species-review/index.html`.

### What judging a glyph actually takes

ASCII `#`/`.` art is **not** a review: it hides collisions the renderer creates. Bat, Autobot face
and starbird are all a wide tapering V, and with the shipped additive glow all three first read as
one blob (a fourth starbird draft read as a trident). Separate glyphs by **overall outline** —
flat, round, tall, bottom-heavy — never interior detail, which the glow erases. Judge from a real
still: `prototype/<piece>.html?tl=g_cast&w=112&h=112&chrome=0&hue=200&iv=N&autostart=0` then
`__renderAt(4.5)`, which is the same path `app/settings.js` uses for its tiles. Also useful: the
shipped eight run **19–38 lit pixels** (median 25), so a 50-pixel glyph is off-family.

**Playwright IS installed on the Desktop** (chromium 151, verified 2026-11-06) — a handoff said it was
absent and that no render could be done here. Stills, the Settings window and the whole browser half of
`tests/run_all.sh` all run locally. The full suite takes ~10 minutes, most of it `test_hover_follow` and
`test_move`, which now loop over six species rather than five.
