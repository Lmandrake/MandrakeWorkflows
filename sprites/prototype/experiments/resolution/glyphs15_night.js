/* ARM B EXPERIMENT ONLY -- not a shipped glyph species, not registered in app/stage.html.
 * Three Night Signals redrawn NATIVE at 15x15 for the resolution comparison (docs/SYMBOL_RESOLUTION.md).
 *
 * Why native and not the 9x9 table upscaled: makeGlyph resamples with round(i*(M-1)/(N-1)), i.e. nearest
 * neighbour, so a 9x9 table at N=15 duplicates 6 of its 9 rows and columns. That reads WORSE than the 9x9
 * original (uneven stroke weight, 1-cell rows beside 2-cell rows), and comparing it against a hand-drawn
 * vector arm would have flattered arm C for a reason that has nothing to do with vectors. At M=N=15 the
 * same resample is the identity, so what is typed here is what is drawn.
 *
 * 🔴 ONLY indices 0 (Batman), 4 (TARDIS) and 7 (Cog) are real. The renderer indexes GLYPHS with
 * ((iv % 8) + 8) % 8, so the table must have 8 rows; the other five are deliberate duplicates of a
 * redrawn neighbour and are NEVER rendered by anything in prototype/experiments/resolution/. If arm B is
 * ever adopted, all 48 glyphs across six species get redrawn -- that is the arm's whole cost.
 *
 * Same two invariants as every shipped table (tests/test_sigil_glyphs.py checks the shipped ones): every
 * row reads the same reversed, because the renderer force-mirrors unconditionally, and the centre cell is
 * always lit whatever the table says. Batman and TARDIS are mirror-only; Cog is also top/bottom symmetric,
 * so it keeps the 4-fold mutation orbits the 9x9 Cog has.
 *
 * Drawing notes, since 15x15 buys room the 9x9 did not have:
 *   Batman   the chest emblem. At 9x9 the wings had to be a solid 3-row bar; here they taper to a 2-cell
 *            tip and the scallop notch is a real notch, so the silhouette reads as a bat and not as the
 *            wide V that the 9x9 bat, Autobot face and starbird all collapsed into.
 *   TARDIS   the police box. The one rectilinear glyph, and the one that gains most: at 15x15 the door
 *            panels are 1-cell strokes with 1-cell gaps, which is exactly the detail the 3x pitch blob
 *            destroys at 9x9 and the tightened blob keeps.
 *   Cog      the toothed ring, generated geometrically (8 teeth, thin rim, small hub) so its 4-fold
 *            symmetry is structural rather than hand-checked. The ring is 1-2 cells thick, which is the
 *            thinnest stroke in the set and so the sharpest test of the blob width.
 */
this.SPRITES_GLYPHS15_NIGHT = [
  ["Batman",   ["...............", "...............", "...............", "......###......", "###..#####..###", "###############", ".#############.", ".#############.", "..##.#####.##..", "...#.#####.#...", "......###......", ".......#.......", "...............", "...............", "..............."]],
  ["(not redrawn)", ["...............", "...............", "...............", "......###......", "###..#####..###", "###############", ".#############.", ".#############.", "..##.#####.##..", "...#.#####.#...", "......###......", ".......#.......", "...............", "...............", "..............."]],
  ["(not redrawn)", ["...............", "...............", "...............", "......###......", "###..#####..###", "###############", ".#############.", ".#############.", "..##.#####.##..", "...#.#####.#...", "......###......", ".......#.......", "...............", "...............", "..............."]],
  ["(not redrawn)", ["...............", "...............", "...............", "......###......", "###..#####..###", "###############", ".#############.", ".#############.", "..##.#####.##..", "...#.#####.#...", "......###......", ".......#.......", "...............", "...............", "..............."]],
  ["TARDIS",   [".......#.......", "...............", "...#########...", "..###########..", "..###########..", "..#.........#..", "..#.###.###.#..", "..#.###.###.#..", "..#.###.###.#..", "..#.........#..", "..#.###.###.#..", "..#.........#..", "..#.###.###.#..", "..#.........#..", "..###########.."]],
  ["(not redrawn)", [".......#.......", "...............", "...#########...", "..###########..", "..###########..", "..#.........#..", "..#.###.###.#..", "..#.###.###.#..", "..#.###.###.#..", "..#.........#..", "..#.###.###.#..", "..#.........#..", "..#.###.###.#..", "..#.........#..", "..###########.."]],
  ["(not redrawn)", [".......#.......", "...............", "...#########...", "..###########..", "..###########..", "..#.........#..", "..#.###.###.#..", "..#.###.###.#..", "..#.###.###.#..", "..#.........#..", "..#.###.###.#..", "..#.........#..", "..#.###.###.#..", "..#.........#..", "..###########.."]],
  ["Cog",      ["......###......", "......###......", "..###########..", "..###.....###..", "..##.......##..", "..#.........#..", "###...###...###", "###...###...###", "###...###...###", "..#.........#..", "..##.......##..", "..###.....###..", "..###########..", "......###......", "......###......"]],
];
