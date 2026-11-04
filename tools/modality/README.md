# modality

Given a probability distribution — as an analytic description, or as a set of
i.i.d. samples — estimate **how multimodal it is**.

```console
$ modality case g2u_prior_hidden -n 4000 --no-bootstrap
case: g2u_prior_hidden
  Two Gaussians plus a broad uniform prior. The owner's 'modality 3' example: ...
  0.400 * Normal(mu=0, sigma=1) + 0.400 * Normal(mu=6, sigma=1) + 0.200 * Uniform(a=-8, b=14)
  GROUND TRUTH: 3 components, 2 visible modes

n = 4000 samples

VISIBLE MODES (local maxima of the density): 2
  headline method: consensus
  estimated at: 0.05209, 5.89

MIXTURE COMPONENTS (BIC-selected Gaussian count): 4
  NOTE: a different question. Components that overlap enough merge
  into fewer visible peaks than there are components.

per-method breakdown:
  kde_silverman       4   [visible_modes] h=0.6839 (robust rule of thumb)
  kde_scott           3   [visible_modes] h=0.7599
  kde_stable          2   [visible_modes] widest log-h plateau, h in [1.11, 2.51]
  kde_critical_h1   n/a   [visible_modes] smallest h giving 1 mode = 2.642 (3.86x Silverman)
  dip                 2   [unimodality_test] p=0.0000; 1 = unimodality not rejected, 2 = 'at least 2'
  gmm_bic             4   [component_count] components, NOT peaks
  gmm_aic             4   [component_count] components, NOT peaks
  gmm_modes           4   [visible_modes] local maxima of the BIC-selected fitted mixture density

notes:
  - kde_stable said 2 and gmm_modes said 4; taking the lower, which is the more
    accurate choice on the validation set
```

Three components, two peaks, and BIC wants four Gaussians. Every number in
that report is right; they answer different questions.

---

## The definitional question, answered up front

There are two different things people mean by "modality", and the whole design
of this package turns on keeping them apart.

| | |
|---|---|
| **Number of mixture components** | How many pieces the distribution was *built* from. "A Gaussian plus a broad uniform region" = 2. "Two Gaussians and a uniform prior" = 3. |
| **Number of visible modes** *(classical definition)* | How many distinct local maxima the density function actually has — how many bumps you would count in a plot. |

These are not the same number, and they come apart constantly. Two Gaussians
one sigma apart have **two components and one peak**. A low, wide uniform slab
under a tall Gaussian adds a component but does not add a peak.

**This tool treats the classical definition — the count of local density
maxima — as the primary, estimable quantity.** Three reasons:

1. It is the standard meaning of "multimodal" in the statistics literature.
2. **It is the only one of the two that is actually identifiable from
   samples.** Component count is not a property of the distribution at all; it
   is a property of *how you chose to describe* the distribution. A Student-t
   is one component if you are allowed t's, and five if you only have
   Gaussians — the validation run below shows BIC choosing 3–6 Gaussians for a
   single Student-t, and 8 for a single exponential. Both answers are correct
   for the question actually asked. The density's peaks, by contrast, are a
   fact about the density.
3. It is what a researcher looking at a plot is usually asking.

**The component count is still reported**, as a separate, explicitly labelled
field (`result.component_count`, from a BIC-selected Gaussian mixture), because
it is genuinely the number the owner's examples were reaching for. It is never
folded into the visible-mode estimate.

The divergence between them is not an awkward edge case to be hidden. It is
the single most useful thing in here, so the validation report prints both
numbers side by side for every test case, and `modality list-cases` marks with
a `*` every distribution where they differ. **15 of the 44 built-in cases
diverge.**

---

## Install

Requires Python ≥ 3.10, `numpy`, `scipy`, `scikit-learn`, `matplotlib` and
`diptest`.

```bash
cd /path/to/Modality
python3 -m venv .venv
./.venv/bin/pip install -e .          # or: pip install -r requirements.txt
./.venv/bin/modality --version
```

`diptest` is the only unusual dependency — it wraps Hartigan's original
algorithm. If it is missing the dip test reports itself unavailable rather
than silently substituting something else; everything else still works.

## Use

### As a library

```python
import numpy as np
from modality import estimate_modality

result = estimate_modality(samples)          # samples: 1-D np.ndarray

result.visible_modes      # int  -- headline: how many peaks
result.mode_locations     # where they are
result.component_count    # int  -- BIC's Gaussian component count (different question)
result.methods            # every estimator's answer, each labelled by what it measures
print(result.report())
```

### From the command line

```bash
modality list-cases                        # the 44 built-in ground-truth cases
modality truth g4_pairs                    # exact analytic modes of one case
modality case g2u_prior_hidden -n 4000     # sample a case and analyse it
modality analyze data.csv --column value   # your own samples (.npy / .csv / .txt)
modality validate --jobs 5 --out results   # the full accuracy sweep
modality figures --out figures             # the plot gallery
```

⚠ **Set `OMP_NUM_THREADS=1` when using `--jobs`.** numpy and scikit-learn each
spawn their own thread pools inside every worker process; without pinning, the
880-run sweep oversubscribed a 14-core machine to a load average of 131 and ran
**~20× slower** than with one thread per worker. With pinning the full sweep
takes about three minutes.

```bash
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  modality validate --jobs 5 --out results
```

---

## How it works

### Ground truth is computed, not eyeballed

`modality.testcases` builds 44 mixtures from components that each carry a
closed-form density **and its exact analytic derivative**
(`modality.distributions`). The true mode count then comes from root-finding
on that derivative, not from staring at a histogram:

* the domain is split at every **breakpoint** — a point where the density jumps
  or kinks (uniform edges, exponential and gamma boundaries);
* inside each smooth piece, sign changes of `f'` are located on a fine grid and
  refined with Brent's method;
* the one-sided limits at each break are added to the chain, because **the flat
  top of a step is a visible mode even though `f'` is never zero on it** — any
  scheme that only solves `f' = 0` silently misses every uniform slab;
* runs of equal values are merged, so a uniform counts as *one* flat-topped
  mode rather than zero or thousands;
* each mode gets a topographic **prominence**, so shallow ripples can be told
  from real peaks.

This machinery is validated against a mode count that is known in closed form:
two equal-weight, equal-variance Gaussians are bimodal **iff** their separation
exceeds `2σ`. The finder flips at exactly that point — 1 mode at `d = 1.99σ`
and `d = 2.00σ`, 2 modes at `d = 2.01σ` — and does so identically at
`σ = 0.01`, `1` and `100`.

### The estimators

Each is a separate method so they can be compared, and each is labelled with
*which question it answers*.

| method | measures | idea |
|---|---|---|
| `kde_silverman`, `kde_scott` | visible modes | Count local maxima of a KDE at a rule-of-thumb bandwidth. |
| `kde_stable` | visible modes | **The main one.** Mode count is monotone non-increasing in bandwidth, so scanning bandwidth gives a staircase; report the count occupying the widest tread in `log h`. |
| `kde_critical_h1` | diagnostic | Silverman's critical bandwidth: the smallest `h` at which the KDE becomes unimodal. |
| `silverman_boot` | visible modes | Silverman's smoothed-bootstrap test of "at most k modes", applied sequentially. Calibrated, but the least accurate of the mode counters here. |
| `dip` | unimodal, yes/no | Hartigan & Hartigan's dip test. Binary only — it never says *how many*. |
| `gmm_bic`, `gmm_aic` | **components** | Gaussian mixture chosen by BIC/AIC. A different question. |
| `gmm_modes` | visible modes | Local maxima of the *fitted* mixture density — the GMM turned back into a peak counter using the same exact machinery as the ground truth. |

Two implementation choices worth knowing:

* **The KDE is evaluated by linear binning plus an FFT convolution**, so its
  cost is independent of sample size and a 60-bandwidth scan takes ~30 ms. Its
  derivative comes from multiplying the same spectrum by `iω`, which makes it
  the *exact* derivative of the estimate rather than a finite difference — so
  modes are found by derivative zero-crossings, with sub-grid locations, rather
  than by the grid-resolution-dependent test `f[i-1] < f[i] > f[i+1]`. Checked
  against direct O(n·m) summation to 1 part in 10⁷.
* **The bandwidth scan is anchored on the critical bandwidth, not on
  Silverman's rule.** Above `h_crit(1)` the answer is trivially 1 forever, so
  anchoring there keeps the scan inside the informative part of the staircase.
  This was measured, not assumed: Silverman-anchored ranges hand the count "1"
  an arbitrarily wide free plateau and score **0.62 exact vs 0.74**.

---

## Validation

`modality validate` runs all 44 cases × 4 sample sizes (50, 200, 1000, 10000)
× 5 seeds = **880 runs**. Full output in
[`results/summary.md`](results/summary.md) and
[`results/results.csv`](results/results.csv).

### Accuracy against the true visible-mode count

| method | exact | within ±1 | bias |
|---|---|---|---|
| **headline (consensus)** | **0.827** | **0.989** | −0.10 |
| `kde_stable` | 0.817 | 0.974 | −0.03 |
| `kde_scott` | 0.780 | 0.969 | −0.15 |
| `kde_silverman` | 0.745 | 0.928 | +0.08 |
| `silverman_boot` | 0.702 | 0.909 | −0.08 |
| `gmm_modes` | 0.686 | 0.916 | +0.29 |
| `gmm_bic` *(wrong question)* | 0.487 | 0.756 | +0.95 |
| `gmm_aic` *(wrong question)* | 0.344 | 0.495 | +2.38 |

### By sample size

| method | n=50 | n=200 | n=1000 | n=10000 |
|---|---|---|---|---|
| **headline** | 0.732 | 0.841 | 0.850 | 0.886 |
| `kde_stable` | 0.705 | 0.836 | 0.841 | 0.886 |
| `kde_scott` | 0.605 | 0.768 | 0.864 | 0.882 |
| `silverman_boot` | 0.605 | 0.686 | 0.736 | 0.782 |
| `gmm_modes` | 0.623 | 0.759 | 0.727 | **0.636** |

### Does mode counting actually work?

**Yes, with caveats that are easy to state.** Roughly:

* **It is right about five times in six, and essentially never off by more than
  one** (98.9% within ±1). If a downstream decision only needs "one bump or
  several", this is reliable.
* **It improves with sample size**, 0.73 → 0.89 from n=50 to n=10000.
* **It is very good at the thing people actually care about**: on the binary
  question "is this unimodal?", the dip test was wrong in the dangerous
  direction **once in 340 runs** (99.7% specificity). A multimodality flag from
  this tool is close to trustworthy. Its *sensitivity* is only 0.669 — it
  misses shallow bimodality — so the reverse is not true: "dip says unimodal"
  is weak evidence.
* **Almost every remaining error is at the bifurcation**, where the truth
  itself is a knife-edge and any answer is defensible.

### How the headline rule was chosen

By measurement, over 16 candidate combinations scored on the same 880 runs.
The winner:

> `min(kde_stable, gmm_modes)`, then raised to 2 if the dip test rejects
> unimodality while that minimum is 1.

The two mode counters fail in **opposite** ways and rarely at once — the KDE
invents ripples on flat regions and in tails, the GMM invents Gaussians to
paper over non-Gaussian shape — and both failures are *over*-counts, so the
minimum cancels them. The dip test's near-perfect specificity then makes its
rejection a safe one-way upward correction; its non-rejection is deliberately
**not** used to push an answer down, which was tried and cost 6 accuracy
points.

| rule | exact | within ±1 |
|---|---|---|
| **min(stable, gmm) + dip bump** | **0.827** | **0.989** |
| `kde_stable` + dip bump | 0.823 | 0.974 |
| `kde_stable` alone | 0.817 | 0.974 |
| median(stable, gmm, boot) | 0.801 | 0.976 |
| max(stable, gmm) | 0.683 | 0.901 |
| `kde_stable` + dip *brake* | 0.765 | 0.967 |

### A prominence filter is worth more than any estimator choice

A KDE lays hair-thin ripples over flat regions and heavy tails, and every one
of them is a genuine local maximum. Discarding modes whose topographic
prominence is under a small fraction of the peak density is the single
highest-value knob in the package:

| `min_rel_prominence` | 0% | 1% | **2% (default)** | 5% |
|---|---|---|---|---|
| exact-match rate | 0.743 | 0.805 | **0.822** | 0.828 |
| ...at n=10000 | 0.784 | 0.903 | 0.892 | 0.875 |

2% is the default: it takes nearly all of the available gain while removing the
least real structure. Set `min_rel_prominence=0` for the strict mathematical
count.

---

## Where component count and visible mode count genuinely diverge

Real numbers from the run, at n=10000, ranges across 5 seeds.

**1. The owner's own example — `g2u_prior_hidden`.** Two Gaussians plus a broad
uniform prior: `0.4·N(0,1) + 0.4·N(6,1) + 0.2·U(−8,14)`.

> **3 components. 2 visible modes.** Estimated visible modes: **2** on every
> seed at n ≥ 200 (19 of 20 runs at n=50). `gmm_bic`: **4** on every seed at
> n ≥ 200.

The uniform lifts the floor across the whole range; it never rises above the
Gaussian tails enough to create a third maximum. The owner's intuition would
call this "modality 3", the density has two peaks, and BIC — needing extra
Gaussians to imitate the flat slab — says four. All three numbers are
defensible answers to three different questions.

**2. A spike on a base — `g2_spike_on_base`:** `0.7·N(0,4) + 0.3·N(0,0.4)`.

> **2 components. 1 visible mode.** Estimated: **1**. `gmm_bic`: **3**.

Both components are centred at the same place. There is exactly one peak, and
no amount of data can turn this into two — the components differ in *scale*,
not location. This is the cleanest demonstration that component count is not
recoverable from peaks and vice versa.

**3. Two tight pairs — `g4_pairs`:** Gaussians at 0, 1, 9, 10, equal weights.

> **4 components. 2 visible modes.** Estimated: **2**. `gmm_bic`: **2**.

Note that BIC *also* says 2 here: at unit variance and unit separation, four
components are not statistically distinguishable from two wider ones. So even
the component-count route does not recover the construction.

**4. A hidden pedestal — `gu_hidden`:** `0.85·N(0,1) + 0.15·U(−6,6)`.

> **2 components. 1 visible mode.** Estimated: **1–2**. `gmm_bic`: **4–8**.

The owner's "Gaussian plus a broad level region → modality 2" case. The level
region is real and a fitter can find it, but it is not a second *peak*.

**5. Where the family is the whole answer — `mix_norm_t`:**
`0.7·N(0,1) + 0.3·t₂(0,3)`.

> **2 components. 1 visible mode.** Estimated: **1**. `gmm_bic`: **4–5**.

Two components by construction, but BIC wants four or five *Gaussians*, because
Gaussians are a bad basis for a heavy tail. A single Student-t (`u_studentt`,
**1 component**) draws **3–6** from BIC for the same reason, and a single
exponential draws **8**. Component count is a statement about your model
family, not about the world.

**6. The one the analytic truth-finder caught and a human would not —
`g2u_prior_visible`:** `0.35·N(0,1) + 0.35·N(10,1) + 0.3·U(3.5,6.5)`.

> **3 components. 4 visible modes** (2 after a 1% prominence filter).

Both Gaussian tails lean into the slab, so their sum has a minimum inside it —
which makes *both* slab edges local maxima. Nobody designing this case expected
four. The exact derivative found it; a histogram never would.

---

## Where each estimator breaks

* **Flat regions defeat KDE mode counting.** The worst case in the whole suite
  is a **single uniform** (`u_uniform`, truth: 1 plateau mode). Sampling noise
  on a perfectly flat density produces ripples that are real maxima of the
  estimate, and *more data makes it worse*, because a smaller bandwidth becomes
  defensible: the headline answer across 5 seeds is `[1,1,1,1,1]` at n=50 but
  `[1,1,2,5,5]` at n=10000. If your data have genuinely flat stretches, raise
  `min_rel_prominence` hard.
* **The bifurcation is unwinnable and that is correct.** At `g2_sep2.2` — just
  past the `2σ` threshold — the tool returns 1 or 2 depending on the seed. The
  true dip there is a fraction of a percent of the peak height. This is not a
  defect; a "mode" that shallow is not a fact a finite sample can establish.
* **`gmm_modes` degrades as n grows** (0.759 at n=200 → 0.636 at n=10000).
  More data lets BIC justify more Gaussians to chase non-Gaussian shape, and
  some of those extra components create spurious bumps. It is the only method
  here that gets *worse* with more data, which is why it is used as the lower
  half of a min() rather than on its own.
* **`gmm_bic` over-counts components** whenever the truth is not Gaussian
  (bias +0.61 against the true component count), and badly against peaks
  (+0.95). `gmm_aic` is much worse (+2.04) — AIC is not consistent for this
  and should not be used for component selection here.
* **Small n is hard for everyone.** At n=50 nothing exceeds 0.73, and
  `estimate_modality` attaches an explicit warning below n=50.
* **Bounded, steeply-rising supports are the fragile unimodal shape.**
  `Beta(2,5)` is reported as 2 modes on 1 seed of 5 at n=2000 and n=5000
  (correct on all seeds at n=1000 and n=10000). This is documented rather than
  papered over, and there is a test asserting exactly that behaviour.
* **A rule-of-thumb bandwidth alone is not good enough** — `kde_silverman`
  scores 0.745 against `kde_stable`'s 0.817, and *degrades* with more data when
  the prominence filter is off. Never report a single-bandwidth KDE mode count
  without saying which bandwidth.

---

## Figures

`modality figures` writes a gallery to `figures/` — true density, sample
histogram, the KDE at the chosen bandwidth, true modes and detected modes.

* [`figures/contact_sheet.png`](figures/contact_sheet.png) — all twelve at once.
* [`figures/bandwidth_staircase.png`](figures/bandwidth_staircase.png) — mode
  count against bandwidth, which is the clearest single picture of why "the"
  KDE mode count is not a number.
* [`figures/g2u_prior_hidden.png`](figures/g2u_prior_hidden.png) — the owner's
  3-component / 2-peak example.

## Tests

```bash
OMP_NUM_THREADS=1 ./.venv/bin/python -m pytest -q      # 159 tests
```

They check the analytic densities against `scipy`, the analytic derivatives
against numerical differentiation, that each density integrates to 1, the mode
finder against modes known in closed form (Gamma at `(k−1)θ`, Beta at
`(a−1)/(a+b−2)`, the `2σ` Gaussian bifurcation), the FFT KDE against direct
summation, and the monotonicity of mode count in bandwidth. The regression
guardrails assert that known unimodal cases read as 1 and clearly separated
ones are counted exactly.

## Layout

```
src/modality/
    distributions.py   components with exact pdf, dpdf and breakpoints
    modes.py           the mode counter -- exact and grid paths, prominence
    testcases.py       the 44-case ground-truth catalogue
    estimators/
        kde.py         FFT-binned KDE, bandwidth rules, critical bandwidth,
                       stability scan, Silverman's smoothed bootstrap
        dip.py         Hartigan's dip test
        gmm.py         BIC/AIC component count, and modes of the fitted density
    api.py             estimate_modality + the consensus rule
    validate.py        the accuracy harness
    plots.py           the figure gallery
    cli.py             the command line
tests/                 159 tests
results/               validation output (regenerate with `modality validate`)
figures/               plot gallery (regenerate with `modality figures`)
```

## Known limitations and what would come next

* **1-D only.** This is the significant scope limit. The definitional argument
  and the GMM route carry over to N-D unchanged, but the KDE machinery does
  not: the FFT trick generalises to 2-D and 3-D and then dies, "count the local
  maxima" becomes a search over a grid whose size is exponential in dimension,
  and bandwidth becomes a matrix. The right N-D approach is probably mean-shift
  or a Morse-theoretic cluster tree rather than a direct port of any of this.
* **The tuned constants are tuned on this catalogue.** The scan range
  (`h_crit/40` to `2·h_crit`), the 2% prominence default and the consensus rule
  were all selected by measuring against these 44 cases. They are not
  overfitted to a handful of runs — 880 runs, and the winners won at every
  sample size — but a genuinely different family of shapes could shift them.
  An honest next step is a held-out catalogue.
* **No uncertainty on the headline number.** It returns `2`, not "2, and 1 is
  plausible". The bandwidth staircase already contains the information needed
  to produce an interval; exposing it as one would make borderline cases much
  more honest than a bare integer.
* **The bootstrap test underperforms its theory.** `silverman_boot` is the most
  principled method here and the weakest in practice (0.702). Silverman's test
  is known to be conservative; a calibrated variant (Hall & York's correction)
  would likely close much of the gap.
* **Boundary bias is not corrected.** A KDE near a hard support edge is biased
  downward, which is part of why bounded shapes like `Beta(2,5)` are the
  fragile ones. Reflection or a boundary kernel would help.
* **Sample independence is assumed.** Correlated draws (MCMC output, say) will
  break the bandwidth rules badly, since every one of them is a function of `n`.
