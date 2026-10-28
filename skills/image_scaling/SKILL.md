---
name: image_scaling
description: Downscale sprites and small images so they stay recognizable, and measure legibility against a calibrated human eye. Use when generating, resizing or validating game art that renders small, choosing texture source resolution, when a downscale "turns to mud", or building an art-quality gate.
---

# Image scaling that survives being looked at

Numbers here come from RimWorld art-pipeline work (one art style, measured); re-measure before
porting them. Details and the reference implementation: `references/rimworld-calibration.md`.
Unmeasured items are marked as such.

## Viewing model: measure at on-screen size, never at source size

Establish the real on-screen pixel ladder first (RimWorld ~1-cell creature: 96 px zoomed in, 27-36
normal, ~18 far out), then judge at the requested 1:1 plus two zoom-outs (96/32/18). Render like the
engine: trim transparent margin, BOX/area-average downscale (approximates GPU mipmaps; conservative,
shows mud honestly where Lanczos hides it), composite over the game's actual terrain color, then
measure the composite. A metric on the transparent image alone, or at the wrong size, lies. Verify
the real engine's filtering, mip generation, color space and camera geometry rather than assuming BOX matches.

The 96 px top tier is VANILLA max zoom. With enhanced-zoom mods
the ceiling does not hold: review near native resolution (128-256 px per cell) and treat law 1's knee as vanilla-only.

## Laws

1. **Resolution above the 1:1 tier buys nothing** (one experiment: 128/256/512 identical, only 64
   dropped). Knee = max on-screen px, next power of two (~128 for a 1-cell creature). Legibility at
   zoom is design: outline, few bold shapes, value contrast. Not tested for thin geometry or text.
2. **The dark keyline is what a human eye grades.** Best metric: keyline contrast at 32 px (boundary
   ring darkness vs interior and vs background), Spearman +0.83; RMS local contrast ~+0.64. Reference-based
   metrics (SSIM, edge-F1 vs a bigger render of itself) saturate near 1.0 and only compare resampling chains.
3. **Resample chains cannot rescue art with no drawn outline.** Lanczos+unsharp lowers keyline scores
   on mud-grade sprites (halos); DPID gains ~noise. Fix the art or inject an outline, not the filter.

## Alpha handling

Any blur/sharpen/resample of straight RGBA bleeds background into edges and draws halos. Always: zero
RGB of fully-transparent texels, premultiply, process, unpremultiply, composite. Each halving of a mip
chain happens in premultiplied space.

## Building a legibility gate

1. Render path first: reproduce the engine's downscale and background exactly.
2. Metric zoo, not one metric: keyline ring contrast, outline-coverage survival vs the 1:1 render, RMS
   local contrast, silhouette IoU, HF-energy retention, edge-F1, SSIM.
3. Calibrate on shipping art: score a few hundred known-shipping sprites; thresholds are percentiles
   of that distribution, never invented numbers.
4. Calibrate the calibration against a human: graded review sheet (works/borderline/mud) over a
   stratified sample plus unlabeled known-good probes interleaved. Spearman every metric against the
   grades; promote the winner. The human's bar sits ABOVE shipping-corpus p10 (corpora have a mud
   tail). All-one-way overrides mean the line is shifted, not noisy. Use a held-out set before trusting a threshold.
5. Verdicts inspectable: diagnostic overlay (counted outline green / missing red) and a contact sheet
   at true sizes + 4x nearest zoom.
6. Deterministic wiring: subprocess with documented exit codes (0 pass / 1 reject naming the weakest
   metric / skip-is-never-pass), thresholds in a JSON the gate reads, env override for tests.

## Improving a downscale (ranked by measured promise)

1. **Synthetic keyline reinforcement, OUTSIDE stroke only.** Paint a black ring in the dilated region
   and composite the ORIGINAL over it: solid pixels stay byte-identical, the fringe blends over black,
   the silhouette grows by the ring. Settings: opacity 1.0, ring 2% of body. Darkening solid ring
   pixels only is invisible (the fringe dominates the blend); an inward stroke that recolors art
   pixels is rejected. Needs ~2-3% canvas margin: check ring-clip fraction deterministically and
   fail distinct ("insufficient margin"). A fitted quality model needs FLOORS for degenerate inputs
   (a flat featureless block passed a ridge model): require nonzero structure/contrast for any pass,
   and an outline for a top band.
2. DPID-style weighted resample: small consistent gain, cheap, no halos.
3. Unsharp after Lanczos: only for art already graded "works"; harmful on weak art. Never on straight alpha.
4. PixelOE-style outline expansion before downsample: promising for pixel-art targets, UNMEASURED.

## Red flags

| Thought | Reality |
|---|---|
| "512 source will look better zoomed out" | Identical to 128 at play zooms. Design, not pixels. |
| "SSIM says it's fine" | Self-referential SSIM saturates; it ranks filters, not art. |
| "Sharpen will crisp it up" | Unsharp made mud-grade sprites worse. |
| "p10 of shipping art is a safe pass line" | A p10-passing sprite was graded mud. |
| "The metric threshold seems reasonable" | Calibrate on a corpus, then against a human pass, or it is a guess. |
| "Alpha will be fine" | Straight-alpha processing bakes halos. Premultiply. |

## drawSize scaling

The tier ladder is per-CELL. A drawSize-3 creature shows 3x the pixels at every zoom, so the gate's
effective tiers and the source canvas budget scale by drawSize (canvas = drawSize x 128, next power of
two). Judging a big creature at vermin tiers is too harsh; the reverse too lenient. Jobs must carry
drawsize as data. A model fitted at 1-cell transfers only approximately (size-stratified regrade not yet done).
