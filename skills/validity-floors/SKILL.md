---
name: validity-floors
description: >
  Separate the hard constraints that decide whether an option is admissible at all from the
  soft criteria that rank the admissible ones — then gate before you rank, so a beautiful
  invalid choice cannot outscore a plain valid one. Use this whenever you are about to pick,
  shortlist, or recommend from a set: choosing a library or vendor, triaging bugs to fix,
  screening candidates, selecting a design, or scoring alternatives against a rubric. Also
  use it when a scoring scheme deducts points for a violation that should have been
  disqualifying, when someone asks for N options and only two clear the bar, or when you
  notice a favourite you are about to justify. Not for running the head-to-head comparison
  once the admissible set exists (that is blind-evaluation), not for wording the final claim
  (falsifiable-claims), and not for checking your own work is finished
  (superpowers:verification-before-completion).
---

# Validity Floors

Identify the binding requirements, verify that each selected option satisfies them, and rank only
the eligible options; return fewer than requested when necessary.

## Why this skill is one sentence

The full-length version (in MandrakeVisualize's git history, where this skill began) was measured on 120 independent tasks
against no skill and against this sentence alone. It solved 111, against 113 for each of the
others, at about 30% more cost per task (`evals/behavior/v2/CONFIRM_RESULTS.md` in MandrakeVisualize). The sentence is
what the evidence supports. The one failure every arm shared, missing an input file that changed
silently mid-task, is not addressed by this skill.
