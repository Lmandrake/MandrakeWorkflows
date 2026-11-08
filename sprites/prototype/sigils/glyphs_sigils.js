/* Living Sigils: the 8 shipped sigil glyphs (species c3_sigils).
 * One 9x9 LED bitmap per variant, resampled to density N by the renderer. Structure differs, not a parameter:
 * outline vs filled, round vs square vs diamond vs flat, 4-fold vs bilateral symmetry, spiky vs solid vs dotted.
 * Identity only: GRAMMAR_V2.md forbids reading meaning into the shape.
 * Every row MUST read the same left-to-right reversed (the renderer force-mirrors), and the centre pixel is
 * always lit whatever the table says. tests/test_sigil_glyphs.py checks both for every species.
 * Names are taken: never reuse one in another species (docs/SYMBOL_SPECIES.md). */
this.SPRITES_GLYPHS_SIGILS = [
  ["Lantern", ["....#....", "...#.#...", "..#...#..", ".#..#..#.", "#..###..#", ".#..#..#.", "..#...#..", "...#.#...", "....#...."]],
  ["Trident", ["#...#...#", "#..###..#", "#...#...#", ".#..#..#.", "..#####..", "....#....", "....#....", "...###...", "....#...."]],
  ["Halo",    ["...###...", ".##...##.", ".#.....#.", "#.......#", "#...#...#", "#.......#", ".#.....#.", ".##...##.", "...###..."]],
  ["Star",    ["#...#...#", ".#..#..#.", "..#.#.#..", "...###...", "#########", "...###...", "..#.#.#..", ".#..#..#.", "#...#...#"]],
  ["Invader", ["..#...#..", "...#.#...", "..#####..", ".##.#.##.", "#########", "#.#####.#", "#.#...#.#", "...#.#...", "..#...#.."]],
  ["Ascent",  ["....#....", "...###...", "..#.#.#..", ".#..#..#.", "....#....", "....#....", "...###...", "..#.#.#..", ".#..#..#."]],
  ["Lattice", ["#.#.#.#.#", ".........", "#.#.#.#.#", ".........", "#.#.#.#.#", ".........", "#.#.#.#.#", ".........", "#.#.#.#.#"]],
  ["Eye",     [".........", ".........", "..#####..", ".#.....#.", "#..###..#", ".#.....#.", "..#####..", ".........", "........."]],
];
