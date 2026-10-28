---
title: "Leak-detection model: what the pilot can and cannot tell us"
subtitle: "Postbrief from the 14 March model-review call (project lead, data scientist, field engineer, analyst). Illustrative example; draft for discussion."
---

**Why this matters.** The utility wants to send repair crews where leaks are likely. The chain runs pressure sensors → the leak model → a ranked list of pipe segments → a crew dispatch. Two questions decide the next quarter: *is the ranking good enough to dispatch on?* and *which fix improves it most: more sensors, better pipe records, or a better model?*

## 1. Words we use, and when to ask for each

| Term | Plain meaning | Ask for it when… |
|---|---|---|
| **Sensitivity** (feature importance, local or global) | How much the model's score moves when one input moves. Says nothing about how wrong that input is. | "Does the model even react to pipe age?" If not, better age records can never help. |
| **Uncertainty** (predictive uncertainty, calibrated intervals) | How sure the model is about each segment's score. | "Can we tell a crew chief this segment is 80% likely to be leaking?" |
| **Accuracy** (validation: precision and recall against confirmed leaks) | How often the ranking matches what crews actually found. Needs field outcomes. | "Of last month's top 50 segments, how many really leaked?" |
| **Error attribution** (ablation, data-swap tests) | Which input or assumption causes the misses. | "We missed the Elm St. leak. Was it a sensor gap or a wrong pipe material?" |
| **Value of new data** (information gain, data-acquisition experiment) | How much accuracy improves if we add a data source. | "Are 40 more sensors worth $200K, or would cleaner pipe records do more?" |
| **Label noise** (unreliable ground truth) | Confirmed-leak records that are themselves wrong or late. Inflates or hides errors. | "Before we trust the recall number, how often are work orders mis-coded?" |

**Rules of thumb.** Importance ≠ value: a feature the model leans on can already be well measured. Confidence ≠ accuracy: a sure model can still be wrong, and only field outcomes show it. The lead's question, "what would most improve the dispatch list?", is **value of new data**, which needs accuracy first.

## 2. The proposed plan

**Does:** retrains the model on 18 months of sensor data and ranks features by importance (SHAP values), about two weeks.
**Will measure:** which inputs the model leans on; a cleaner, faster pipeline.
**Will not measure:** accuracy against confirmed leaks; the effect of new sensors; label noise.
**Against the need:** about a quarter of the way. It shows what the model uses, not what would make the list better, which is the lead's real question: "if we buy sensors and nothing changes, I've spent the budget."

## 3. Quick ways forward

| Add-on (technique) | What it gives | Workdays |
|---|---|---|
| **A. Score last quarter's list** (retrospective validation: precision@50 against work orders) | The first honest accuracy number | 2 |
| **B. Audit 100 work orders** (label-noise estimate) | Tells us how far to trust A | 2–3 |
| **C. Hold out sensors** (data-denial experiment: drop 20% of sensors, re-score) | Previews what adding sensors would buy, before buying them | 3 |
| **D. Swap in corrected pipe records for one district** (data-swap ablation) | Compares the records fix against the sensors fix | 3–4 |

**Shortest useful path:** A, then C and D side by side, in about two weeks. That turns "buy sensors?" into a measured comparison.
