# RimWorld calibration and reference implementation

Read when porting the legibility gate or its numbers, or working in the RimMandrake art pipeline.
Numbers are from one art style; re-measure before using them on another.

## Measured results
- Resolution: 35 masters stored at 64/128/256/512, rendered to 96/32/18. 128/256/512 identical
  within 0.1 score points at every tier; only 64 dropped.
- Metric correlation vs human works/borderline/mud grades over 48 sprites (11 metrics): keyline
  contrast at 32 px Spearman +0.83 (boundary-ring darkness vs interior and vs background); RMS
  local contrast about +0.64. SSIM and edge-F1 vs a larger render of itself saturate near 1.0.
  Selection among 11 metrics on 48 sprites is in-sample; validate on a held-out set.
- Lanczos+unsharp lowered keyline scores on mud-grade sprites; DPID gained about +0.02 (noise).
- Approved keyline settings: opacity 1.0, ring 2% of body.
- drawSize: a real 2.4-cell creature moved borderline to pass when judged at its true size.

## Reference implementation
- `src/RimMandrake/Utils/art_legibility.py` (in the RimMandrake repo): score / calibrate / gate /
  resexp (resolution experiment) / zoo (metric zoo x box/unsharp/DPID chains, premultiplied-correct).
- `src/RimMandrake/Utils/art_zoom_sim.py`: tier contact sheets vs a vanilla control.
- Thresholds: `infrastructure/artpipe/legibility_thresholds.json`; daemon wiring in
  `src/RimMandrake/Utils/artpipe/artpiped.py` (`run_legibility_gate`).
- Grading-sheet pattern: the `review-sheets` skill; the measured results above summarise the calibration run.
