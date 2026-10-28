# resumable-batch-jobs

A Claude Code skill for one failure class: **a restartable batch job whose resume
logic cannot tell "this item succeeded" from "this item failed and we wrote that
down."** A job asks `if item_id in done_ids: continue`, a transient outage writes
failure records for everything it touched, and every subsequent resume skips
exactly those items forever — turning a temporary network problem into permanent,
invisible missing data while the coverage summary reads clean.

`SKILL.md` gives the state model that fixes it (`pending | in_progress |
succeeded | retryable_failure | terminal_failure`, and resume decisions keyed on
completion state rather than record existence), a table of code shapes to
distrust, a nine-point checklist covering failure classification, server-stated
backoff, crash-safe checkpointing and conservation assertion, and the bounding
counterexample that keeps the skill honest: **the operation may not be
idempotent**, so a recorded failure licenses a retry only once retry safety is
established through an idempotency key, an observable completion state, or a
reconciliation pass. Blindly retrying every failure record double-charges cards.

It also covers why this matters beyond tidiness: a pipeline whose summary cannot
distinguish "we did not look" from "we looked and found nothing" will present an
outage as a finding.

## Install

The skill is a directory; Claude Code finds it through `~/.claude/skills/`.
Clone or check out this repo somewhere permanent and symlink it in:

```bash
mkdir -p ~/.claude/skills
ln -s /path/to/resumable-batch-jobs ~/.claude/skills/resumable-batch-jobs
```

Editing the checkout edits the installed skill; there is no build step. It pairs
with `confident-wrong-numbers` (the general case of an instrument returning a
confident wrong integer) and `grader-validation` (when the thing reporting clean
is a scorer rather than a job summary); it does not depend on either.

## Provenance

Extracted from a batch language-model scan built to be
restartable. A network outage silently poisoned a large share of one run's records; the
resume logic skipped every one of them permanently and no summary showed it,
because the records existed and were counted. Separately, a short retry backoff against a
service whose own error message gave a longer wait lost a fifth of calls to impatience alone
— two independent loss channels, each masking the other's magnitude because the report
carried a single "processed" number. The code examples are generic.
