---
name: incomplete-ground-truth
description: >
  Score a system against reference data that asserts some correct answers and denies none
  (published index, partial gold set, labelled sample, compliance matrix) without reading silence
  as a negative. Use whenever reporting recall, precision or "0 defects found" against an
  incomplete answer key; when references may share a source; when a reference seems to omit
  something your system emitted; when combining scores across references; or before publishing a
  "no losses" headline. Not grader-validation, evaluation-independence or claim wording
  (falsifiable-claims).
---

# Incomplete Ground Truth

Most "gold standards" are not gold standards. They are lists of things known to be correct,
built by someone who was not trying to enumerate everything that is correct, and silence
about an item is not a claim that the item is wrong. Treating that silence as a negative is
the single most common way a scoring number becomes confidently false — and it is invisible
in the write-up, because "0 defects found" reads the same whether the reference could see
the defect class or not.

The material below comes from one project's experience scoring a document-structure
extractor against nine reference indexes. Two of those
nine were later found to be the same underlying source republished; three "publisher
omissions" the project reported were retracted when the raw source, not the project's own
parse of it, was checked. Generalize the rules; the numbers are real and are kept as
worked examples, not as a target to hit.

## When this fires

Any time you are about to compute recall, precision, agreement, or "zero defects" against
something less than an exhaustive, adversarially-built answer key. It fires for an external
published table, a sample a human hand-labelled for other purposes, a spec's own compliance
matrix, a prior tool's output kept as a reference, or a subset of cases someone reviewed
carefully. It fires **backwards** too: handed a scoring report that claims full recall or a
clean pass, ask what the reference underneath it could not have spoken to.

## The core asymmetry

**Given a reference asserting {a, b} and a system emitting {a, b, c}, the worlds "c is real
and the reference omits it" and "c is fabricated by the system" are observationally
identical.** Nothing in the data distinguishes them. So a positive-only reference can answer
recall — did the system reproduce what the reference asserts — and nothing else. It cannot
measure fabrication, no matter how many differently-incomplete positive lists you stack. Nine
of them are still nine samples of the same kind of data: assert-only.

*Why this is the root of every rule below:* every other rule here is a way of not
accidentally treating that asymmetry as resolved when it is not.

## The rules

**1. Model the reference as assert / rule-out / unknown, and never collapse unknown into
clean.** A reference speaks only where it asserts something exists or, rarely, explicitly
rules something out. Everything else is unknown, and "no defects found" over the unknown
region is not a pass — it is silence read aloud. *Why:* a scorer that reports one number for
"confirmed correct" and "never checked" produces a false sense of coverage that nobody
decided to create.

**2. Report the unscoreable items as a required field, not a footnote.** If a reference
asserts 10 items and the system emits 900, the other 890 must be reported, or "10/10
recalled" misleads by omission. In the source project this figure was 158 emitted edges at
first, then 266 once more references were added, neither confirmed nor refuted by anything on
hand. *Why:* the reader of a recall number assumes it describes the whole output unless told
otherwise; a required field forces the disclosure the summary sentence will not carry on its
own.

**3. Never aggregate over reference count when references share provenance.** Four of nine
references in the source project republished the same underlying document. Counting four
agreements as four independent votes turns provenance correlation into false confidence.
Aggregate over unique upstream assertions, and deliberately publish no single combined score
across a reference set of mixed independence. One reference was initially logged as a tenth
independent source and was in fact the same instrument in a later revision — 54 of 54 rows
identical and in the same order, still carrying the other document's page footer. *Why:*
"nine references agree" and "one reference agrees, copied four times" are different claims,
and only the count of unique sources tells you which one you have.

**4. Check which direction the incompleteness runs — it is rarely random.** In the source
project, every one of nine references was incomplete in the dangerous direction: each
asserted fewer items than genuinely existed. One indexed only children carrying their own
modal verb — 5 of 59 real children. A reference asserting fewer items than exist will score a
correct system as fabricating the ones it omitted. *Why:* an incompleteness that is uniform
in direction is a systematic bias, not noise, and treating it as noise inverts a true positive
into a false one. **Consequence: score recall only over items the reference actually asserts,
and do not score fabrication against a reference known to be incomplete in this direction at
all.**

**5. Know what remains honestly scoreable against any reference, however incomplete:
cardinality and contradiction.** An item emitted twice by the system is wrong regardless of
what the reference says about it. An item claimed under two mutually exclusive parents is a
proven negative — both cannot be true. These two checks need no completeness assumption, and
they are the only negatives you get for free. Use them; do not invent others.

**6. Conserve every disagreement between reference and source — never quietly exclude one.**
Require every raw assertion to be matched, lost, adjudicated, or explicitly left open; keep
the reason codes a closed enumeration; require a locator for any claimed discrepancy; and
print the exclusion fraction (1 of 243 assertions, in the source project) so a rising
exclusion rate cannot hide behind a "0 defects found" headline. *Why:* an excluded assertion
is a place the scorer chose not to look, and if that choice is silent the exclusion rate can
grow without anyone noticing the ground under the score eroding.

**7. An "omission" claim is a claim about your own ability to see — evidence it against the
raw source, never against your own parse of it.** An extractor that cannot represent one
spelling variant of an identifier makes every query over the already-parsed rows return
absent while the raw bytes contain the item. A defect in the reader gets
written down as a defect in the publisher — the worse of the two possible directions to be
wrong in. **Fix: record the probe method, the exact needle, every spelling tried, and the hit
count; refuse to publish an absence claim whose probe finds the text, or whose probe ran over
the parse rather than the source.** Run these probes live at build time, not once and
transcribed, so a claim cannot outlive its evidence — if a later fix makes the allegedly-
missing item visible, the build must raise rather than silently keep republishing a claim
about the publisher that has quietly become a claim about you.

**8. Two "independent" cross-checks that share a defect are one check.** An adjudication's
regex and a hand tally of the same field agreed exactly in the source project, because both
assumed the same wrong spelling of an identifier. Agreement between two checks is only
evidence if the checks could plausibly have disagreed.

**9. Never join records by a formatted reference string.** Across five documents, the same
containment relationship was spelled three different ways within a single column; 3 of 50
references did not resolve to anything at all; one document named the wrong parent in 29 of
70 rows — 41%. **Prefer a stable, publisher-assigned tag; failing that, join structurally on
separate fields, and report a non-resolving reference rather than dropping it.** *Why:* a
formatted string is a rendering choice, not an identity, and two renderings of one identity
fail a string-equality join every time they differ by punctuation.

**10. Count the denominators and refuse to state a rate.** Report disagreements discovered,
assertion pairs compared (403 here), and how many sources were fully versus partially
compared, with an explicit line that this is not a rate. *Why:* discovery scales with how
hard you looked, not with corpus health, so a trend claim needs a frozen corpus and a fixed
detector version — usually you have neither.

**11. Write adversarial tests for the scorer before the next reference arrives.** The source
project specified 14 of them — known-wrong answers driven through the scoring machinery —
before scoring newly-added references, so the scorer's own defects could not be discovered
only through their effect on a headline number.

## The honest headline shape

The source project's headline result was "399/399 edges reproduced" across seven
references. The qualifiers that make it true rather than misleading, carried in the same
breath as the number: fabrication is unmeasured (all seven references are assert-only; rules
1 and 4); the result covers a small fraction of the documents in scope; no combined score is published
(provenance overlap made one illegitimate, rule 3); and the unscoreable extras are named as
their own count. A headline with none of those sentences attached is not lying by content,
only by omission — and omission is exactly the failure mode this skill exists to catch.

## Rejected alternatives

- **Treat every reference-absent item as a false positive.** Rejected: this collapses the
  core asymmetry (rule 1) on purpose, producing a confident, wrong fabrication rate every
  time the reference is incomplete — which measured incompleteness always is.
- **Average the per-reference recall scores into one number.** Rejected by rule 3: shared
  provenance turns the average into a count of how many times one source was republished,
  not independent agreement.
- **Drop a non-resolving reference row rather than report it.** Rejected by rules 6 and 9: a
  dropped row is an unconserved disagreement, exactly what a rising-defect scorer needs kept
  visible.
- **Trust the absence of a hit in your own extraction as proof of publisher omission.**
  Rejected by rule 7: unverified against the raw source, that is a claim about your reader.

## Rationalizations that mean stop

| Thought | What is actually true |
|---|---|
| "The reference doesn't mention it, so it's a false positive" | Silence is not a negative. That is the core asymmetry; check whether the reference could have asserted it at all. |
| "We have nine sources agreeing, that's strong" | Count unique upstream assertions first. Four of nine may be one document photocopied. |
| "Zero defects found, we're clean" | Clean against what the reference can see. State the unscoreable fraction in the same sentence. |
| "Our parser doesn't find it, so the publisher must have omitted it" | That is a claim about your reader until the raw source is probed directly, with the spellings tried recorded. |
| "Close enough, join on the formatted reference string" | Formatted strings are rendering choices. A structural join, or a stable tag, survives spelling drift; a string match does not. |
| "It's basically a rate, let's just say X% pass" | Discovery scales with scrutiny, not with corpus health. State the denominators and refuse the rate. |

## Boundaries with neighbouring skills

- **`grader-validation`** — validates the scoring machinery itself: adversarial tests against
  known-wrong answers, guard-firing checks, the scorer's own correctness. This skill decides
  what the reference data can and cannot license the scorer to conclude in the first place.
  Use this skill to frame the reference; use that one to prove the scorer honours the frame.
- **`evaluation-independence`** — keeps the people and material that build a system away from
  the material that grades it. That is about who sees the answer key. This skill is about what
  the answer key itself can and cannot assert, even when independence is perfect.
- **`falsifiable-claims`** — words the eventual claim and its refutation bar. This skill
  supplies the qualifiers ("fabrication unmeasured," "covers a fraction of the documents in scope") that a wording pass
  must then not drop; it does not itself decide how to phrase the sentence.
- **`validity-floors`** — separates hard gates from soft ranking criteria for a set of options.
  Different problem: this skill is about what a single reference's silence licenses you to
  conclude, not about admissibility among alternatives.

## Provenance of this skill

This comes from one project's experience scoring a document-structure extractor against nine
reference indexes. It is engineering practice that held up under
that project's own scrutiny — including three retracted omission claims that turned out to be
the project's own reading defect, and one reference that was briefly counted as a tenth
independent source before being recognized as the same instrument republished — not an
established empirical finding. The rules above are the corrections made after each of those
mistakes was caught, not a plan followed from the start.
