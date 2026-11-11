# GPT skeptical code review of the Aether (raw reply)

Sent 2026-11-08 17:55 PST, cold thread, locked review profile (no web), consult_id 20261108T175518-MandrakeWorkflows-code_review (Codex transport). Prompt: Aether.swift and AetherHost.swift in full (as of the drift commit), the test file's structure, and a ranked-findings brief. Raw reply below, unedited. Guidance, not authority: each claim is checked against the code in 06-synthesis.md.

---

The largest new performance issue is **`localSigma2()` turning dipole updates into repeated full-capacity scans**. I would fix that before changing numeric precision or moving work to Metal.

There are also concrete correctness gaps: initialization and reservoir injection bypass the ceiling; boost release depends incorrectly on substep timing; repulsion has boundary self-force; and the host can omit the final clearing frame.

I reviewed only the supplied material. I did not execute commands, inspect generated Swift code, or run tests. **All CPU percentages below are unmeasured guesses**, relative reductions in CPU time, not percentage points of a core. Gains overlap and should not be added.

Effort: **S** = hours, **M** = roughly 1–2 days, **L** = several days including validation.

1. **Repeated global temperature scans are a major hidden cost.**

   **Location:** `turnDipoles()` → `localSigma2()`:

   ```swift
   guard n >= 2 else { return meanSigma2() }
   ```

   Every particle in a singleton coarse cell scans all 3,000 slots. At sparse density, mean occupancy is approximately `100e-6 × 48² = 0.2304`; under a roughly uniform distribution, about 79% of particles occupy singleton cells. For 143 particles, that means roughly **340,000 slot visits per step just for these fallbacks**.

   **Change:** Compute the global mean once at entry to `turnDipoles()` and pass it to `localSigma2()`. This preserves the existing timing of the fallback. Separately decide whether local cell moments should describe velocities before or after the thermostat: currently `cSum`/`cSum2` describe the former, while the fallback describes the latter.

   **Gain:** Guess **20–70% of sim CPU** in sparse, chain-enabled scenes; zero when dipole updates are disabled. The complexity problem is definite; its CPU share is unknown.

   **Risk/tests:** Low for caching only. Run temperature variation, chains, and seed determinism; add a counter asserting at most one global fallback scan per dipole pass. Existing pair counters cannot detect this regression.

   **Effort:** S.

2. **Remove dynamic exclusivity from the kernels without disabling unrelated checks.**

   **Location:** Mutable class-array accesses throughout `pair()`, `buildGrid()`, `repel()`, `thermostat()`, and sprite closures:

   ```swift
   vel[i] += ...
   cellStart[c + 1] += 1
   rho[idx(...)] += ...
   ```

   These are source sites requiring accesses to class stored properties. The compiler can eliminate some accesses, but `final` does not establish exclusive ownership of the instance. Your profile confirms that enough remain dynamically checked to matter. Exact surviving call sites require optimized SIL or assembly.

   **Change, in increasing scope:**

   - Use a local particle’s position/velocity while processing it, then write back once.
   - Borrow arrays as buffer pointers and pass those pointers, immutable parameters, and scratch buffers to kernels.
   - Put hot storage in a value-type state and call a static/free kernel taking `inout State`. This can reduce the dynamic class-property access to the outer borrow and make internal accesses statically provable.

   Merely writing `var local = self.vel` usually introduces sharing and a copy on mutation. Merely adding `withUnsafeMutableBufferPointer` around existing methods is also unsafe: calling methods that access the borrowed array through `self` can create overlapping accesses. The kernel must consistently use its supplied buffers.

   `-enforce-exclusivity=unchecked` is the cheapest **benchmark experiment**. It retains ordinary optimized bounds checking, but removes runtime detection of real exclusivity violations. Its scope is the compilation invocation. **Do not use `-Ounchecked` for this purpose**: it removes substantially more safety checking.

   **Gain:** Guess **5–30% of sim CPU**; the profile’s self-time attribution should narrow this considerably.

   **Risk/tests:** Medium for buffer refactoring; higher diagnostic risk for globally disabling enforcement. Run the full suite with normal enforcement enabled, including sprite-grid equivalence and all wall cases. Passing tests does not prove unchecked aliasing safe.

   **Effort:** S for the flag experiment; M–L for scoped kernels.

3. **“No frames” currently does not mean “no simulation work.”**

   **Location:** `AetherHost.tick()`:

   ```swift
   sim.advance(by: dt, typing: typing)
   ...
   schedule(min(next ?? .infinity, max(0.005, nextGeom - now)))
   ```

   When presentation stops, calm geometry still wakes at 2 Hz. Each wake advances approximately 15 fixed steps. A completely settled gas therefore continues doing roughly 30 simulation steps per second, batched into fewer wakeups.

   There is also a resume burst: `.off` and `.still` update `lastTick`, but returning to `.draw` includes the time since the last quiet poll. With `maxCatchUp = 32`, resuming can execute almost a second of simulation immediately. The “2 fps frame” justification for that override is stale relative to the current 30 fps presentation floor.

   **Change:** Track simulation activity and future deadlines explicitly: moving walls, fades, reserve work, boost release, typing expiry/rewarm, sprite motion, and stochastic heating. Skip kernels only when those conditions permit it, while maintaining clock semantics. Reset elapsed-time accounting on quiet-to-running transitions.

   For moving scenes, consider a 30 fps presentation policy during ordinary motion and 60 fps during interactions. With a Maxwellian gas:

   ```text
   v90 ≈ rmsSpeed × sqrt(log(10))
   ```

   At the default temperature, `v90 ≈ 41.7 pt/s`, so the current rule requests about 167 fps before clamping: **it normally selects 60 fps**. Reducing to 30 would halve draw submissions, while retaining the fixed 30 Hz simulation.

   **Gain:** Guess **80–95% of sim CPU during genuinely quiescent periods**. A 60→30 presentation change might save **5–20% of app CPU**, but that estimate is particularly uncertain without drawing attribution.

   **Risk/tests:** Medium. Incorrect sleep eligibility can prevent rewarming, reseeding, or responding to moving windows. Pure clock tests are insufficient; add host scheduling tests for typing expiry, quiet resume, fades, and pending sweeps.

   **Effort:** M–L.

4. **Compute presentation statistics once per state change, and avoid sorting when clamping decides the result.**

   **Location:** `frameInterval()` builds and sorts `speeds` on every host tick.

   At 60 fps, two consecutive calls often observe the same simulation state. It also computes a square root for every active particle.

   **Change:** Cache movement/fading statistics after simulation changes, invalidating them on stirring, settings changes, and activation. Use squared speeds for comparisons and selection.

   At a 30 fps cap, the result is simply 30 fps whenever movement or fading requires presentation. At a 60 fps cap, the upper threshold is only `15 pt/s`; counting how many speeds exceed that threshold can often establish that the percentile is saturated. Use selection or a histogram only for the remaining cases.

   **Gain:** Guess **1–8% of sim CPU**, counting `frameInterval()` as simulation work.

   **Risk/tests:** Low–medium. Incorrect invalidation can suppress frames after stirring or activation. Presentation-clock tests need cache invalidation cases and percentile-boundary cases.

   **Effort:** S–M.

5. **An ordered active list should replace most capacity scans.**

   **Location:** Repeated:

   ```swift
   for i in pos.indices where phase[i] == .active
   ```

   At sparse density, roughly 95% of those slot checks reject dormant entries.

   **Change:** Maintain active and fading indices, or rebuild ordered lists once per step. A single 3,000-slot compaction pass is a reasonable first implementation and can preserve ascending-index traversal.

   Merge compatible passes, such as `sweepMove` followed by `screenEdge` for each particle, while preserving their order. Compute interpolation once per draw. Avoid recomputing active counts already available from a list.

   Do not indiscriminately merge across collisions, validation, thermostat changes, or activation: those boundaries affect semantics.

   **Gain:** Guess **5–25% of sparse sim CPU**, **1–10% dense**, after fixing finding 1.

   **Risk/tests:** Medium. Swap-removal changes collision order and which particle receives each RNG draw. That can change trajectories while still passing a same-seed-repeatability test. Preserve ordering initially; compare old/new seeded trajectories and population transitions.

   **Effort:** M.

6. **Grid construction allocates, and sparse collision traversal visits thousands of empty cells.**

   **Location:** `buildGrid()` and `collide()`:

   ```swift
   var fill = cellStart
   ```

   Mutating `fill` causes a full copy-on-write copy. The default laptop grid has about 10,000 cells for approximately 143 sparse particles.

   **Change:** Allocate a reusable fill-offset buffer. Maintain occupied cells and visit those as collision origins, preserving row-major order initially. A later change can replace dense clearing/prefix construction with stamped sparse structures if profiling warrants it.

   **Important correction:** The supplied production `substep()` has **at most two explicit grid builds**, not three: one for sprites and one after movement. `bondStats()` adds a separate build if called. Neither production build is trivially redundant: movement invalidates the sprite snapshot.

   **Gain:** Guess **3–15% of sim CPU**, particularly sparse scenes and multiple substeps.

   **Risk/tests:** Medium. Reusing an invalid grid misses neighbors. Run sprite-grid equivalence, wall/pile cases, force tests, and work-counter tests.

   **Effort:** S for scratch reuse; M for occupied-cell traversal.

7. **Reuse Metal upload buffers and write vertices directly.**

   **Location:** `AetherHost.draw()` creates `[Float]`, a Metal buffer, and an array of uniforms every draw.

   **Change:** Give each screen reusable shared vertex buffers and a typed uniform struct matching the shader layout. Write `P` records directly into an available buffer. Calculate interpolation and color once per draw.

   Use completion-tracked buffer ownership. Blindly rotating through three buffers is not sufficient if the GPU falls further behind; prefer skipping a presentation over blocking the main thread waiting for storage.

   At these counts the uploaded data is small—24 KB for 1,500 points. The opportunity is primarily allocation, copying, and API overhead.

   **Gain:** Guess **0–5% of app CPU**. GPU and WindowServer costs remain unmeasured.

   **Risk/tests:** Medium. Premature buffer reuse causes intermittent visual corruption. Headless tests will not catch it; validate GPU backlog, screen rebuilds, and vertex/uniform layouts.

   **Effort:** M.

8. **Reuse wall snapshots and previous-position storage.**

   **Location:** `substep()`:

   ```swift
   let A = walls.map { ... }
   let B = walls.map { ... }
   ```

   And `step()`:

   ```swift
   prevPos = pos
   ```

   The position assignment initially shares storage; subsequent position mutation copies the full array.

   **Change:** Keep reusable wall buffers, reuse the previous substep’s endpoint as the next start, and cache expanded rectangles once walls finish moving. Invalidate on geometry/radius changes.

   Keep previous-position storage independently allocated and copy only positions that presentation needs. New activations already initialize both positions.

   **Gain:** Guess **1–5% of sim CPU**; more during frequent substeps.

   **Risk/tests:** Low–medium. Sharing the previous-position buffer with mutable positions breaks interpolation. Existing smooth-presentation and swept-wall tests are appropriate.

   **Effort:** S–M.

9. **Hoist thermostat exponentials; consider paired Gaussian generation separately.**

   **Location:** `thermostat()` computes `decay` and `kick` per particle.

   There are only two possible coefficient sets in a call: ordinary and hot. Their inputs are otherwise global.

   **Change:** Precompute both coefficient sets outside the loop. This is a relatively low-risk optimization.

   `gaussian()` also discards the second Box–Muller result. Producing a pair or caching the spare reduces logarithms, square roots, and RNG calls, although it changes the random stream.

   **Gain:** Guess **5–20% of sim CPU combined**, depending on thermostat/dipole activity. The Gaussian routine needs profiling before assigning much of that estimate to it.

   **Risk/tests:** Low for coefficient hoisting; medium for changing Gaussian consumption. Run temperature, field-energy, force, wall, and determinism tests. Same-seed repeatability alone will not detect changed statistical behavior.

   **Effort:** S for coefficients; M including Gaussian validation.

10. **Float is plausible for some state, but a mechanical conversion is unsafe.**

   **Location:** Position/wall math uses offsets such as:

   ```swift
   p += n * 1e-7
   ```

   Near coordinate 1,500, Float spacing is approximately `0.000122`. Adding `1e-7` does nothing. At larger desktop coordinates it is worse. A conversion would invalidate the reasoning behind contact separation and strict interior tests.

   Double remains appropriate for clocks, accumulators, sweep calculations, and drift phase. The epoch-derived drift phase is already around a million cycles; Float cannot retain per-frame phase increments there.

   **Change:** Retain Double for those quantities initially. Benchmark narrower alpha/charge/orientation/velocity storage separately. A Float position migration needs scale-aware tolerances or representable-neighbor placement such as `nextUp`/`nextDown`, followed by adversarial sweep validation.

   Existing `SIMD2<Double>` arithmetic can already use 128-bit SIMD. `SIMD2<Float>` does not automatically process twice as many particles; that generally needs batching or a different loop layout.

   **Gain:** Guess **0–15% of sim CPU**. These buffers are small enough that a bandwidth bottleneck is not established.

   **Risk/tests:** High for positions; lower for rendering-only state. All invariant tests apply, plus long-duration clock and large-coordinate tests. **I have not reasoned through a complete Float migration sufficiently to recommend one.**

   **Effort:** L.

11. **Avoid doing every host-input operation at presentation frequency.**

   **Location:** Every `tick()` rebuilds per-screen sprite arrays and dictionaries, and potentially evaluates all drift waves. Every screen advances even when its own backdrop is fully occluded.

   **Change:** Separate input, simulation, and presentation deadlines. Reuse dictionary/array capacity and update sprite tracking at the required input cadence. Preserve velocity expiry: skipping identical sprite samples without handling `stirTrack` would leave stale motion active.

   For multiple screens, consider suspending fully occluded simulations independently. Cull sprite *influence* using its full reach, not merely its center, while preserving tracking across screen boundaries. Drift coefficients can be precomputed and settings need not be reassigned on presentation-only ticks.

   **Gain:** Dictionary/drift changes: guess **under 1% of app CPU** at ordinary sprite counts. Suspending one of two similarly loaded screens could save approximately **half the sim CPU**.

   **Risk/tests:** Medium. Sprite re-entry velocity, decay, and resume semantics need host-level coverage. Existing tests cover the simulation’s tracker, not host cadence.

   **Effort:** S–M.

12. **Initialization and reservoir injection violate the ceiling.**

   **Location:** Initial population creation and `injectEdges()` assign Gaussian velocities without clipping. `activate()` correctly clips; these paths do not.

   **Counterexample:** With default temperature, ceiling is `55`, and Gaussian component σ is `27.5 / √2`. Thus:

   ```text
   P(initial speed > 55) = exp(-4) ≈ 1.83%
   ```

   With 143 unobstructed particles, the probability of at least one initial violation is about **93%**.

   Reservoir injection occurs after the step’s final ordinary ceiling enforcement, so a newly injected point can remain above the ceiling until the next step.

   **Change:** Centralize bounded velocity initialization and use it for initialization, reserve activation, and reservoir injection.

   **Gain:** Approximately **0% CPU**; tiny additional work.

   **Risk/tests:** Low. Clipping changes tail statistics, consistently with the declared ceiling. Add ceiling assertions immediately after initialization and after every reservoir step. Existing general ceiling tests may exercise neither path.

   **Effort:** S.

13. **Boost release can reduce a point’s speed during the step that pressed it.**

   **Location:** `releaseBoost()`:

   ```swift
   if time - pressedAt[i] < tuning.dt { continue }
   ```

   **Counterexample:** Start at time zero with one substep. A fast wall contacts a point and sets `pressedAt = 0`, normal speed and boost to `500`. At release, time is exactly `dt`; the condition is false. With the default release constant, boost immediately drops toward roughly `348.6` for a ceiling of `55`, and enforcement clips the velocity—even though this step just established contact.

   With four substeps, a last-substep contact has age `dt/4` and avoids that decay. Behavior therefore depends on substep count.

   **Change:** Record contact during the current step explicitly. Define separately whether `pressHold` governs inelastic pile behavior, boost retention, or both. Do not infer current contact using this strict time comparison.

   **Gain:** Approximately **0% CPU**.

   **Risk/tests:** Medium: this changes push/release dynamics. Add one-substep and four-substep tests with thermostat disabled, asserting face-speed carry immediately after contact and decay after release. Existing push tests may only assert “above ceiling.”

   **Effort:** S–M.

14. **PIC repulsion has boundary self-force; individual acceleration clipping also loses momentum.**

   **Location:** `repel()`, replicated-edge smoothing and central differences.

   **Counterexample:** Use a `96 × 48` domain with 48-point coarse cells, one stationary particle at `(24,24)`, repulsion range `1`, and disable other forces/thermostat. The deposited density is `[1,0]`. Two smoothing passes produce:

   ```text
   [0.625, 0.375]
   ```

   The x-gradient at the occupied cell is:

   ```text
   (0.375 - 0.625) / 96 = -1/384
   ```

   The lone particle accelerates right. With default density, temperature, and repulsion strength, its velocity increases by approximately **0.0712 pt/s in one step**.

   Matching deposit/gather weights alone does not guarantee no self-force at these boundaries. If mirror-boundary pressure is intentional, this is an external boundary force and needs to be described and tested as such.

   Separately:

   ```swift
   if al > cap { a *= cap / al }
   ```

   cannot generally preserve a zero sum. Raw forces proportional to `[-2f, f, f]` cease summing to zero when only the first is clipped.

   **Change:** Specify the boundary force model first. For momentum-preserving internal repulsion, use a consistent antisymmetric interaction operator. If its raw accelerations sum to zero, a common global scale factor preserves both that property and the acceleration limit.

   **Gain:** Approximately **0% CPU**, possibly a small cost.

   **Risk/tests:** High enough to require focused physics validation. Add single-particle tests throughout the domain, asymmetric multi-particle momentum tests, and cases activating the cap. Interior uncapped conservation tests are insufficient.

   **Effort:** M–L.

15. **The CPU bound is a sampled workload result, not an enforced bound. Coincident particles expose it.**

   **Location:** `collide()` enumerates all candidate pairs; `pair()` rejects coincident points:

   ```swift
   guard dist2 < rc * rc, dist2 > 1e-18 else { return }
   ```

   **Counterexample:** Inject 1,500 stationary particles at the same location with other dynamics disabled. One substep performs:

   ```text
   1500 × 1499 / 2 = 1,124,250 pair checks
   ```

   That is **749.5 checks per point**, far beyond either stated budget. The zero-distance guard also leaves coincident particles unresolved.

   Crowding runs afterward, only periodically, and explicitly exempts pressed cells.

   **Change:** Resolve zero-distance pairs using a deterministic, symmetric fallback normal. Separately decide whether the CPU guarantee covers adversarial piles. A hard bound needs an explicit dense-cell fallback or workload policy; capping force magnitude does not bound pair enumeration.

   **Gain:** Approximately **0% in ordinary scenes**; potentially over **90% during pathological piles**, depending on the fallback.

   **Risk/tests:** High for a dense-pile replacement. Add coincident-particle and highly compressed pressed-pile tests. Extend counters to capacity scans, grid builds, sprite candidates, and reserve work. **I have not designed a dense-pile solver here; its gain and physics are not reasoned through.**

   **Effort:** S for zero-distance handling; L for a defensible hard budget.

16. **The final fade or stop can leave stale pixels; unblanking can leave a static gas blank.**

   **Location:** Host drawing condition:

   ```swift
   if next != nil || needsDraw { drawAll(); needsDraw = false }
   ```

   **Counterexample:** The last visible point finishes fading during `advance()`. `frameInterval()` now returns `nil`, and `needsDraw` is false. No clearing frame is submitted, so its previous pixels remain.

   Conversely, `.off` clears the screen, but returning directly to `.draw` clears `blanked` without requesting a redraw. An unmoving gas can remain invisible.

   **Change:** Track presentation dirtiness independently of future animation. Submit the final changed frame, request a draw after unblanking, and retain dirtiness if drawable acquisition fails.

   **Gain:** Approximately **0% CPU**; occasional necessary extra draws.

   **Risk/tests:** Low. Add host tests for last-fade completion, final snap-to-rest, blank/unblank, and failed drawable acquisition. Headless simulation tests cannot catch this.

   **Effort:** S–M.

17. **Drift easing is discontinuous near slider endpoints.**

   **Location:** `AetherDriftKey.value()`:

   ```swift
   let u = min(0.98, max(0.02, ...))
   ```

   Consequently, `value(c, 0) != c` near either bound.

   **Counterexample:** Temperature variation at `1` remains `1` while amplitude is zero. On the first positive amplitude, it becomes approximately `0.98`. Chain forming at zero similarly jumps to approximately `0.02`, enabling a previously disabled pass.

   **Change:** Require the drift mapping to approach the actual base value continuously as amplitude approaches zero. An explicit eased blend can handle endpoints; keep the bounds and intended drift amplitudes documented.

   **Gain:** Approximately **0% CPU**; avoiding unintended pass activation can matter near zero.

   **Risk/tests:** Low–medium. Add amplitude samples `0`, tiny positive, and tiny negative-time-distance from shutoff for every endpoint. Sampled-day smoothness tests may miss mode-switch discontinuities.

   **Effort:** S.

18. **The minimum-temperature guarantee cannot recover from zero.**

   **Location:** `thermostat()`:

   ```swift
   if now > 1e-12 && now < lo { ... }
   ```

   **Counterexample:** Use `.stirAndSettle`, variation `1`, minimum temperature zero, and disable other forces. Let the snap path stop every particle. Then raise minimum temperature to `1.5`.

   Settling supplies no kicks, uniform scaling cannot revive zero velocities, and the floor branch declines to act. The gas remains below its declared floor indefinitely.

   **Change:** Define a deterministic recovery path for zero or negligible energy, followed by normalization and ceiling enforcement. A uniform rescale cannot solve this case.

   **Gain:** Approximately **0% CPU**.

   **Risk/tests:** Medium: recovery must specify momentum and temperature semantics. Add the zero→positive-floor transition. Also test concentrated energy: ceiling clipping after floor rescaling can invalidate the floor again.

   **Effort:** S–M.

19. **Reserve overlap checks use a stale grid and omit newly activated particles.**

   **Location:** `overlapsPoint()` checks `gridBuilt`, although collision correction and wall validation have invalidated positions. `activate()` does not insert into the grid.

   A later seed in the same batch therefore cannot see an earlier seed. Points moved across cells by validation can also be missed.

   **Change:** Establish a current placement-query structure before seeding and include newly activated points immediately. A small list of recent activations plus a fresh baseline grid is a straightforward starting point.

   **Gain:** Approximately **0% CPU**, potentially a small cost during refills.

   **Risk/tests:** Low–medium. Add a seeded batch-placement case checking separation immediately after activation. Population/refill tests alone can pass despite overlaps.

   **Effort:** S–M.

20. **`capacity = 3000` is a minimum allocation, not a maximum.**

   **Location:** Initialization:

   ```swift
   let cap = max(tuning.capacity, ... pop)
   ```

   **Counterexample:** A `3008 × 1692` logical-point screen at Dense density requests **5,090 particles**. Reservoir allocation becomes 10,180 slots.

   **Change:** Either enforce an explicit maximum with a documented density/headroom policy, or describe capacity as an allocation floor and budget for larger screens. The current behavior does not match the stated 150–1,500/3,000 operating envelope.

   **Gain:** No gain within the intended envelope; potentially substantial outside it, at the expense of requested density.

   **Risk/tests:** Product/physics tradeoff. Add large-screen and maximum-density population tests. Existing laptop-only tests will not expose it.

   **Effort:** S implementation, plus deciding the policy.

21. **`bondStats().clusters` has nondeterministic ordering.**

   **Location:**

   ```swift
   cs.values.filter { ... }.map { ... }
   ```

   Dictionary iteration does not provide stable ordering. This does **not** demonstrate nondeterministic simulation evolution: the sprite dictionaries are accessed by key in ordered sprite loops. It does affect the observable QA result.

   **Change:** Produce clusters in sorted component-root order.

   **Gain:** Approximately **0% CPU**, tiny sorting cost.

   **Risk/tests:** Low. Compare multiple-cluster results across calls/processes, or explicitly document unordered output.

   **Effort:** S.

22. **Split by responsibility and ownership before introducing force abstractions.**

   **Location:** Settings/drift, geometry, storage, kernels, and QA currently share one file.

   **Change:** First extract settings/drift and geometry utilities. Then introduce explicit state/parameter/scratch ownership around the hot kernels.

   Use an explicit pass sequence for repulsion, integration, contacts, thermostat, and orientation. They have different cadences and side effects; treating each as interchangeable `applyForce()` hides important ordering.

   A protocol can help high-level composition, but avoid existential dispatch per particle or pair. Static functions, specialized generics, or an outer pass switch are easier to optimize.

   **Gain:** Approximately **0% directly**; it enables finding 2.

   **Risk/tests:** Low for extraction, medium for changing pass organization. Run the full suite and preserve operation/RNG order. Swift extensions in different files cannot simply access the class’s existing private storage.

   **Effort:** M–L.

23. **A shared parameter registry is worthwhile, but should generate metadata rather than add hot-path lookup.**

   **Location:** Parallel definitions in `AetherSettings.from`, `aetherDriftKeys`, and `settings.js`.

   **Change:** Use one canonical schema for defaults, ranges, units, scaling, presets, drift eligibility, off behavior, and rebuild dependencies. Generate typed Swift descriptors and UI metadata. Keep special parsing relationships explicit, such as density presets affecting particle size.

   Give drift parameters stable seed identifiers: currently their array index determines their wave. Inserting or reordering registry entries would change subsequent constants’ walks.

   Retain independent contract tests for important defaults and bounds. Tests generated from the same incorrect table can agree with the bug.

   **Gain:** Approximately **0% runtime CPU**; reduced maintenance risk.

   **Risk/tests:** Medium. Settings compatibility, rebuild triggers, presets, and drift continuity need coverage.

   **Effort:** L.

I would keep Metal compute deferred. The particle count does not justify it before removing repeated scans, access overhead, and unnecessary simulation work. A GPU implementation would also need a deliberate synchronization and ownership design around walls, reserve activation, and rendering. I have not designed that implementation, so I cannot substantiate a speedup estimate.

For finite, parsed settings, I do not see a demonstrated tiny-denominator failure in the attraction branch: the allowed range keeps its well width positive. I cannot audit non-finite settings rejection because `jsonNumber()` was not supplied. Non-finite positions reaching `Int(...)` in grid indexing would trap; input validation belongs before that conversion.

My ranked top 10 implementation priorities, balancing gain, correctness, and risk:

| Rank | Change | Finding | Reason |
|---:|---|---:|---|
| 1 | Cache global temperature for dipole fallback | 1 | Large hidden complexity problem; very small fix |
| 2 | Close initialization/injection ceiling gaps | 12 | Concrete invariant violation; low risk |
| 3 | Fix final draw and unblank dirtiness | 16 | Visible correctness bug; bounded change |
| 4 | Remove dynamic access from scoped kernels | 2 | Profile-supported opportunity |
| 5 | Stop quiescent kernels; revise presentation/resume scheduling | 3 | Largest potential idle and wakeup saving |
| 6 | Introduce ordered active/fading indices | 5 | Broad sparse-workload improvement |
| 7 | Correct boost contact/release accounting | 13 | Substep-dependent push behavior |
| 8 | Resolve PIC boundary and capped-momentum semantics | 14 | Concrete physics mismatch |
| 9 | Cache presentation statistics and remove unnecessary sorting | 4 | Low-risk repeated work |
| 10 | Reuse grid scratch and traverse occupied origins | 6 | Removes allocation and empty-grid work |

Persistent Metal buffers would be next unless a host profile shows drawing allocation above the grid work.
