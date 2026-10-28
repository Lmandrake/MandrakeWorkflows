---
name: search-when-words-differ
description: Find source passages relevant to a question when the question and the sources use different words (domain, era, organisation, abstraction level). Use before reporting "nothing found" on a topic the corpus plausibly addresses. Restate the query as concrete situations, not synonyms.
---

# Search when the words differ

A corpus can address your question at length and match none of your words. Every
word-matching instrument (keyword, synonym expansion, surface-form embeddings, a
hand-built terminology bridge) then returns nothing, and an empty result looks like
a finding ("the corpus is silent") rather than a failure.

Example: asked whether governance addresses excessive machine permissions, a
lexical pass finds no "agent", "autonomy" or "permission scope", because the text
says "the least privilege necessary" and "deny by default, permit by exception".
A carefully built, corpus-verified vocabulary bridge missed it too. Restating the
risk as concrete situations and asking each passage whether it bears on them found it.

## The prescription

1. **Restate the query as concrete situations or mechanisms, not as synonyms.**
   Not "other words for X" — "what would this look like happening, in two or
   three specific scenarios?" A synonym list stays inside the query's own
   vocabulary; a situation can be recognised in any vocabulary.

2. **Ask whether the source text bears on that situation, regardless of
   vocabulary overlap.** The question put to each passage is *would this
   provision change what happens in that scenario*, not *does this passage
   contain my terms*.

3. **Treat vocabulary terms as navigation aids, not proof of relevance.** A term
   hit tells you where to look. It does not establish that the passage is
   relevant, and its absence does not establish that the passage is not.

4. **Require a concrete cited source passage for every positive.** Mechanism
   reasoning is generative; without a quoted, located passage behind each hit you
   have produced an argument, not a finding.

5. **Union the mechanism-oriented search with lexical retrieval. Do not replace
   it.** Each finds material the other misses — the mechanism pass's matches are
   *additions*; the lexical hits are not invalidated. Replacement trades one blind spot for another.

6. **Report "nothing found" as a limit of the search, not a property of the
   corpus**, unless completeness has been established separately by some other
   means.

> **Retrieval silence is not corpus silence.**

## The bounding counterexample: analogy inflation

**Mechanism restatement can be pitched so abstractly that everything looks
relevant.** Transform "excessive software permissions" into "one entity has more
authority than appropriate", and passages about budget authority, personnel
delegation, signing authority and general management responsibility all become
candidates. They are all, at that altitude, about the same thing.

The method's own strength is what does this. Vocabulary independence is precisely
the property that stops a lexical mismatch from blocking a hit — and it is
precisely the property that stops an unrelated topic from being blocked either.
Loosen the words and you loosen the gate.

So the two failure directions are symmetric, and a reader who guards one will
fail the other way:

| direction | what it produces | what it looks like |
|---|---|---|
| **vocabulary dependence** | relevant passages missed because the words differ | a clean empty result: "the corpus does not address this" |
| **analogy inflation** | irrelevant passages admitted because the restatement is too abstract | a large plausible candidate set that collapses under review |

Both feel like success at the moment they are produced. The first feels like
diligence — the search ran, the documents are listed. The second feels like
recall — look how much was found.

### The defence: a three-step mapping, per hit

Every mechanism-oriented candidate must carry an explicit chain:

    source mechanism → target situation → why this passage could alter the target risk

Written out, per candidate, in words. Then a downstream relevance check reads
the chain rather than the hit.

**If a candidate cannot fill in all three steps, it is analogy inflation, not a
finding.** "Both are about authority" fills the first two and fails the third —
it never says what would be different in the target situation if this provision
applied. That third step is where budget-approval authority stops looking like
software privilege scope.

Two practical consequences:

- **The chain is the unit of review, not the passage.** A human arbitrating
  hundreds of candidates reads mappings; a raw hit list with no chains cannot be
  reviewed at a sane rate, and a bad chain is faster to reject than a bad
  passage.
- **The chain makes the inflation visible to its own author.** Writing step three
  is what forces you to notice you have nothing to say.

## False friends must be excluded deliberately

Vocabulary independence does not exempt you from the ordinary polysemy problem —
it makes it worse, because a mechanism pass is already predisposed to say yes.

Examples: "permission" in most documents, "agent" in a chemical sense, "opaque"
as a property of packaging. A keyword pass built on them re-flags nearly the whole
corpus for the wrong reason, and the volume of hits reads as coverage.

So: enumerate the false friends for your query's terms *before* running, exclude
them by name, and record which ones you excluded — a term you quietly dropped is
indistinguishable later from a term you never thought of.

## Where the trigger applies

The trigger is the *shape*: a query and a corpus describing the same situation in
different words. Untested instances:

- **Modern security concepts against older standards.** Supply-chain integrity,
  zero trust, SBOM — against standards written when the same mechanisms were
  called configuration management, access control and parts provenance.
- **Lay medical language against clinical literature.** A patient's description
  of a symptom against the literature's diagnostic terminology.
- **A legal question in plain language against statutory terminology.** The
  statute's words are chosen for legal precision, not for matching how the
  question would be asked.
- **Product language against customer complaint text.** Your feature names
  against what customers actually write when that feature fails them.

## Neighbours

- **`confident-wrong-numbers`** — a query whose shape returns a confident wrong
  number, including a zero. That skill is about the construction of the query;
  this one is about the *semantics* of the match, where the query is correctly
  built and still asks the wrong question of the text. Its rule that **presence
  is cheaper to trust than absence** is the same asymmetry driving this skill.
- **`falsifiable-claims`** — how to word the negative result once you have it, so
  "our search found nothing" cannot be read as "the corpus contains nothing".
- **`validity-floors`** — the three-step mapping is a validity floor on a
  candidate: gate on admissibility before ranking, so a vividly-argued analogy
  cannot outscore a plainly relevant provision.
- **`claim-provenance`** — prescription step 4, the demand for a concrete cited
  passage behind every positive, is that skill's discipline applied to retrieval
  output.
