# Placard validation record

Placard was folded into MandrakeWorkflows on 2026-10-27 by `git subtree add` (history kept) from
`Lmandrake/Placard` at commit `cd987a2`. The suite was not re-run to prove the move; these are the
records it already had, copied beside the code.

- **Test suite, Docker smoke of the public export** (python:3.12-slim, built tree), measured
  2026-10-26 on Placard `8374ff8`: `246 passed, 14 skipped`, then `256 passed, 4 skipped` with a
  system word list installed; `examples/quickstart.sh`: ok. (The 14 and 4 skips are the
  dictionary-backed cleaner repairs, which need `/usr/share/dict/words`.)
- **Measured result** (README, "The measured result"; data `examples/results.json`, harness
  `examples/eval_qa.py`): on the shipped synthetic example, the map plus digests and the extracted
  bodies alone each passed 14 of 14 questions in 3 of 3 runs, at 7,088 and 3,675 input tokens
  against 37,738 for the originals as native document input.
- **Export scan**: `publish.py scan Placard` passed on 2026-10-28T00:46:57Z (57 files).

After the move, only `contrib/placard_read_guard.py` changed (its default `PLACARD_PY` now points
here); `tests/test_read_guard.py` passed 12 of 12 on 2026-10-27.
