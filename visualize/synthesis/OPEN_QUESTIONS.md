# Open questions

Genuine uncertainties surfaced during v0.1 synthesis. Recorded so they are not
silently resolved by default. Tagged by kind: [evidence gap], [design decision],
[scope], [tooling].

## Evidence and sources
- [evidence gap] The channel-accuracy ordering places area vs. angle order-adjacent;
  our accessible sources (S02 summary, Heer&Bostock abstract) do not pin the exact
  rank, and Cleveland&McGill 1984 is paywalled (reference_only). ENC-01 states the
  robust part (position/length highest; area/intensity low) and flags the rest as
  order-adjacent. Resolving needs the full C&M ordering or a replication table.
- [evidence gap] Soft-rubric weights (RUBRIC.md Layer 2) are currently the brief's
  §11 defaults, not learned from perceptual data. QA-04 asks for evidence-grounded
  weights; Draco's learned weights (S10) are the intended source but not yet imported.
- [evidence gap] S14 (Jambor checklist) is reference_only — only its abstract was
  accessible. Its concrete checklist items are not encoded. If lawfully obtained,
  it may add or sharpen ANNO/QA principles.
- [scope] Canonical books (Tufte, Few, Munzner's textbook) were not acquired (no
  lawful in-sandbox full text). Their well-known ideas are cross-checked against
  accessible Tier-A/B sources; some nuance is therefore secondhand.

## Design decisions to revisit
- [design decision] Zero-baseline is split: hard for bars (ENC-02), escalated for
  non-bars (UNC-01). Confirm this split holds up on real cases rather than collapsing
  to one rule.
- [design decision] WCAG numeric thresholds (ACCESS-03) are web-UI norms. We kept
  the *principle* of a measured floor but leave the exact number medium-dependent.
  Needs a small table of recommended floors per medium (slide/print/poster).
- [design decision] "Remove non-data ink" vs. scaffolding (conflicts.md #1) is
  resolved by "reader-serving purpose", which is judgment-heavy. A sharper operational
  test would reduce variance.
- [design decision] Annotation is folded into `visual-composition` for v0.1. Decide
  in v0.2 whether it earns a standalone skill as the annotation rule set grows.

## Scope and packaging
- [scope] Standalone `technical-diagram` skill deferred to v0.2; diagram rules
  currently live inside `scientific-visualization`. Revisit if diagram work grows.
- [scope] Packaging decision (one umbrella skill vs. six installable skills) is
  deliberately deferred until after v0.1 review, per the project decision.
- [scope] Relationship to the exemplar decks: exemplars are a validation set, not an
  input. When/if to feed validated designer judgments back as context exceptions is
  an open cross-track question.

## Tooling
- [tooling] How much of the render-QA collision/contrast scan can be automated vs.
  requires a vision check of the rendered image. v0.1 assumes a rendered-image
  inspection step exists.
- [tooling] A machine-readable defect-list output from critique mode (for downstream
  automation) is proposed but unbuilt.
