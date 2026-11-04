# Where 'component count' and 'visible mode count' diverge

| case | components | visible modes | why |
|---|---|---|---|
| g2_sep1 | 2 | 1 | Two equal unit Gaussians 1 sigma apart. Equal-weight equal-variance Gaussians are bimodal iff the separation exceeds 2 sigma. |
| g2_sep1.5 | 2 | 1 | Two equal unit Gaussians 1.5 sigma apart. Equal-weight equal-variance Gaussians are bimodal iff the separation exceeds 2 sigma. |
| g2_sep2 | 2 | 1 | Two equal unit Gaussians 2 sigma apart. Equal-weight equal-variance Gaussians are bimodal iff the separation exceeds 2 sigma. |
| g2_w10_sep3 | 2 | 1 | A dominant Gaussian with a 10% companion 3 sigma away. |
| g2_var_sep3 | 2 | 1 | A narrow and a broad Gaussian, centres 3 apart. |
| g2_spike_on_base | 2 | 1 | A narrow spike sitting exactly on top of a broad base: two components, one peak, and nothing about the sample can separate them by position. |
| gu_hidden | 2 | 1 | A Gaussian over a broad low uniform slab. Two components; the slab is too low to make a second peak, so the density has ONE maximum. |
| gu_wide_low | 2 | 1 | The same idea pushed further: a 5% uniform pedestal, invisible as a mode. |
| gu_tall_slab | 2 | 1 | A narrow tall uniform inside a broad Gaussian: one plateau mode. |
| g3_tight | 3 | 1 | Three equal Gaussians 1.5 sigma apart: fully merged into one hump. |
| g3_two_merge | 3 | 2 | Two Gaussians merge into a single wide hump; a third sits far away. Three components, two visible modes. |
| g2u_prior_hidden | 3 | 2 | Two Gaussians plus a broad uniform prior. The owner's 'modality 3' example: three components, but the uniform only lifts the floor, so the density has TWO maxima. |
| g2u_prior_visible | 3 | 4 | Two Gaussians with a uniform slab between them. A surprise the analytic truth-finder caught and a histogram would not: the two Gaussian tails sum to a shape with a minimum inside the slab, so BOTH slab edges are local maxima and the density has FOUR of them from three components -- though only two clear a 1%-prominence filter. |
| mix_norm_t | 2 | 1 | A Gaussian core with a heavy-tailed Student-t halo: one mode, two components, and a shape no single Gaussian fits. |
| g4_pairs | 4 | 2 | Two tight pairs far apart: four components, two visible modes. |