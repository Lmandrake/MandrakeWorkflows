# search-when-words-differ

A Claude Code skill for one failure class: **a corpus that addresses your
question at length and matches none of your words.** Keyword, synonym and
terminology-bridge searches all return the same artifact in that case — an empty
result set — and an empty result set does not look like a failure. It looks like
a finding: *the corpus is silent on this*.

`SKILL.md` gives the six-step prescription and the bounding counterexample (analogy inflation), with the per-hit three-step mapping as its defence: **source mechanism → target situation → why this passage could alter the target risk.**

The sentence at the spine: **retrieval silence is not corpus silence.**

## Install

The skill is a directory; Claude Code finds it through `~/.claude/skills/`.
Clone or check out this repo somewhere permanent and symlink it in:

```bash
mkdir -p ~/.claude/skills
ln -s /path/to/search-when-words-differ ~/.claude/skills/search-when-words-differ
```

Editing the checkout edits the installed skill; there is no build step. It pairs
with `confident-wrong-numbers` (the query's *shape* returns a wrong number, where
this skill is about its *semantics*) and `falsifiable-claims` (how to word the
negative result); it does not depend on either.

## Provenance

Extracted from a coverage-mapping project that ran three
successive recall passes over the same 307 windows of governance text, wrote down
"the corpus has no vocabulary for these risks" after the second, and retracted it for 4
of 5 risks after the third. The recovery that settled it was a passage granting
"the least privilege necessary" and mandating "deny by default, permit by
exception" — found in a document the vocabulary bridge had already scanned and
counted. The governance documents and AI risk categories in the skill are examples; the
failure class is not domain-specific.
