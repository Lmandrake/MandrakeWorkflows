---
name: defeat-recitation
description: >
  Rule out RECITATION before crediting a model's correct answer about material it may have
  memorised (public standards, statutes, famous codebases, datasets). Use whenever a model reasons
  over supplied evidence from a possibly public source; when treating a model's agreement with a
  citation as proof it read it; when an ablation removes evidence but leaves a name, id or section
  number; or when a "second reader" check returns suspiciously clean agreement. Not blinding
  (blind-evaluation), build/judge separation (evaluation-independence) or wording
  (falsifiable-claims).
---

# Defeat Recitation

A model that has seen a document during training does not need the copy you hand it. Ask it
about ISO 26262 part 6 clause 9, or the GPL, or the Sherman Antitrust Act, or a well-known
open-source function, and it can answer correctly from parametric memory alone — quoting the
text, naming the neighbouring clauses, reconstructing structure it was never shown in this
conversation. That answer looks exactly like a careful read of the evidence you supplied. It
is not. The two are observationally identical from the outside, which is precisely why
agreement between a model's answer and ground truth proves nothing about whether the model
used your evidence, until you have specifically ruled recitation out.

This is not a defect in the model. It is a property of testing anything public with a model
trained on public text, and it defeats the ordinary intuition that a correct answer is the end
of the question.

## When this fires

Any time a model is asked to reason from evidence you supplied, and the underlying source is
public, famous, or otherwise plausibly present in a training corpus: a named standard, a
statute, an RFC, a well-known repository, a canonical benchmark, a widely reproduced dataset.
It fires hardest exactly where the check matters most — using a model as a "second reader" or
independent judge of your own extraction, precisely because a second reader's whole value is
that it is reading independently.

It also fires on ablations: any experiment that removes evidence to see whether the model's
answer degrades. If the model's answer does not degrade, the naive conclusion is "the evidence
didn't matter, our structural claim holds without it." The real conclusion may be "the model
never needed the evidence in the first place."

## The protocol

**1. Assume recitation until you have evidence against it.** Do not start from "the model
answered correctly, so it read the material." Start from "the model may have recited this,"
and require a specific finding before crediting the read.

*Why:* the burden has to sit on the harder claim. A read and a recitation cost nothing to
confuse, and only one of them tells you anything about the evidence you supplied.

**2. Hiding the document's NAME is not enough.** Blinding the label — replacing every
identifier token for a standard or statute name — is the obvious first move, and it was
tested twice: with every document-identifier token replaced, the model still answered
"recognised: yes" on all four probes run. It identified the material from its CONTENT, not
its label. If your defense against recitation is a name swap, you have not defended against
anything.

**3. Perturb the STRUCTURE, isomorphically, and verify the perturbed form comes back.** The
technique that actually works: find a relation the question is really about — which items sit
under which, which clauses reference which, the order of events in a timeline — and perturb
its surface identifiers while preserving that relation exactly. Shift every section reference
by a constant offset; rename variables; relabel taxonomy categories; shift every date in a
timeline by the same delta. The perturbed material is isomorphic to the original — same
structure, same membership, same order — but its exact strings now exist in no copy of the
source anywhere. Then check that the answer USES the perturbed form. In the case this rule is
drawn from, shifting every section reference by +6 left families, ordering, and membership
untouched while making every reference string undeducible from memory; every reply returned
the synthetic references, which is the only thing that makes the check mean something.
Verification is the whole point of this step — without checking that the perturbed form came
back, you have only hoped the model was reading.

**4. A citation left in place is a leak channel, even with the evidence text removed.** A
three-arm ablation stripped the text under test but left the citation — document id plus a
section number — and the model still asserted a requirement stem it had never been shown, one
of the three replies quoting it verbatim. The id and locator alone were enough to recall a
public document. Only when the citation was stripped too did recall stop and the model
visibly reason from what little text remained, at markedly lower confidence (0.82, then 0.81,
then 0.67) — and that run carried the arm's only "needs human review" flag. An ablation that
strips evidence but keeps a citation has not removed the evidence at all.

**5. Perturb everything, or the unperturbed remainder leaks.** A first-pass reference
substitution can leave sentence-final and compound references unshifted, so the payload carries
real references beside synthetic ones — weakening any claim of undeducibility. Also perturb the JOINED text, not each
line independently: an identifier split across a line break is invisible to a per-line
substitution while remaining perfectly readable to the model reading the reassembled page.

**6. Make the perturbation fail loudly when it changes nothing.** A perturbation that maps
zero identifiers and silently reports success is worse than no perturbation, because it
invalidates the entire arm's claim while looking like it ran. Build the check so it raises
when it maps nothing — single-component section numbers, for example, can match none of a
substitution's patterns while the tool reports success regardless.

**7. Run the probe in a fresh context, not the thread that already holds your answer.**
Conversational context is a leak channel as surely as a citation. Moving a check to a fresh
chat, away from the thread already carrying the project's own analysis, changed answers: two
of five probes then reported "recognised: no," where an earlier round run inside the
contaminated thread had reported "yes" on four consecutive probes.

## What this does and does not buy

Perturbation defeats recitation of the ANSWER. It does not defeat recognition of the SOURCE —
a model can correctly say "I recognise this document" from content alone and still be reasoning
about the perturbed copy in front of it rather than the memorised original, which is exactly why
step 3's verification step matters more than the recognition question. Nor does agreement
between two readers under this protocol prove correctness: both readers can share a blind spot,
so a clean result is corroboration, not proof. Treat the result as guidance for where to look
next, never as a grading key. Runs against this protocol have gone from initial rounds of zero
disagreement to later rounds surfacing real refutations of prior conclusions — the refutations,
not the agreements, were the valuable output.

## Good behaviours to require of the reader

A reader worth trusting under this protocol reports its own limits rather than guessing past
them: naming its own truncation when the supplied text was genuinely cut, rather than filling
the gap from memory; refusing to name a structure whose parent identifier is absent from the
supplied text instead of inventing one; and, unprompted, flagging duplicated content that is a
defect in YOUR extraction rather than staying silent about it. All three were observed in
practice and are worth writing into a probe's instructions explicitly rather than hoping for
them.

## Rejected approaches

**Blinding the document name and calling it sufficient.** Tested twice, failed twice — content
alone re-identifies the document. Superseded by rule 2 and rule 3.

**Leaving the citation in place while removing the evidence text.** Looks like a clean ablation
and is not one; the citation alone reintroduces memorised content. Superseded by rule 4.

**Partial perturbation of "the obvious" identifiers.** Sentence-final and compound references
are easy to miss and leave real strings inside a supposedly synthetic payload, understating how
undeducible the material actually is. Superseded by rule 5.

**Trusting a perturbation tool's own "success" report.** A silent no-op — mapping zero
identifiers — is indistinguishable from a working perturbation unless the tool is built to
raise on it. Superseded by rule 6.

**Reusing the analysis thread as the probe thread.** Convenient, and it manufactures agreement
that a fresh context does not reproduce. Superseded by rule 7.

## Rationalizations that mean stop

| Thought | What is actually true |
|---|---|
| "It got the right answer, so it must have read the evidence" | A recited answer and a read answer look identical. Right is not the same as read. |
| "I blinded the document name, that's enough" | Content alone re-identifies public material. Measured twice; name-blinding is not source-blinding. |
| "I removed the text, the citation is harmless context" | The citation is enough on its own to recall a public document. Strip both or you have removed neither. |
| "It didn't map every reference, close enough" | An unmapped identifier is a real string sitting next to your synthetic ones, and it is exactly what recitation would use. |
| "Same thread, shouldn't matter, it's just for continuity" | Conversational context is a leak channel. Measured: answers changed when the probe moved to a fresh chat. |
| "Two readers agreed, so it's confirmed" | Agreement is corroboration, not proof — both readers can share the same blind spot. |

## Worked example

This protocol was built and repeatedly stress-tested inside one evaluation of a model reading
public documents as a "third reader" check on an extraction. That project's files are not part
of this repository; the arc, in order, was:

- **A three-arm ablation** (full text, text without its citation, citation alone) showing that a
  citation alone is a leak channel (rule 4), with a falling-confidence tell (0.82 -> 0.81 -> 0.67)
  as the recitation stopped and real reasoning began.
- **An isomorphic-perturbation probe**: name-blinding tested and found insufficient, then
  section-reference renumbering built and verified by checking that replies used the synthetic
  numbers (rules 2, 3, 6).
- **The probe's results across rounds**, including the change in recognition answers once the
  probe moved to a fresh context (rule 7), and the refutations that later rounds surfaced against
  earlier "zero disagreement" claims.

## Boundaries with neighbouring skills

- **`blind-evaluation`** — blinds which ARM produced an output, at judging time, in a single
  comparison. This skill blinds the MATERIAL itself from a model's own memory, across any
  single evaluation, comparative or not. A blind protocol on memorised material is still
  contaminated even with the arm identity perfectly hidden.
- **`evaluation-independence`** — keeps build material and judge material apart for the whole
  life of a project, so the judge never learned from the same inputs the builder used. This
  skill is about a different leak: the judge learned the material from a training run that
  predates the project entirely, and no amount of project-level firewalling touches that.
- **`falsifiable-claims`** — words the resulting claim once evidence is in. This skill decides
  whether the evidence is real evidence at all before any claim gets written.

## Provenance of this skill

These practices come from one project's repeated attempts to use a model as an independent
second reader of public documents — public standards a training run could plausibly
have seen. Every rule above was learned by a defense failing first: name-blinding was tried and
measured to fail before renumbering was tried; partial perturbation shipped before its gaps
were found; a citation was kept "for context" before the leak it caused was measured. This is
engineering practice that survived that project's own scrutiny, not an established empirical
finding, and it generalizes to any evaluation of a model against material it might already
know.
