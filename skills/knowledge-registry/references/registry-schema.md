# Registry schema (reference)

The structural detail behind `knowledge-registry`. The SKILL.md is the decision layer —
*when* and *why* to do each thing. This file is the *how*: the field-by-field schema, id
conventions, force semantics, a worked entry, and a checklist for adding or versioning an
entry. The pattern is general (any registry of admitted, citable knowledge). Examples are
drawn from `MandrakeVisualize/principles/principles.yaml`, but nothing here is specific
to visualization.

## Contents

1. [The entry schema, field by field](#1-the-entry-schema-field-by-field)
2. [Id-namespace conventions](#2-id-namespace-conventions)
3. [Force-semantics table](#3-force-semantics-table)
4. [Registry-level (meta) fields](#4-registry-level-meta-fields)
5. [Worked registry-entry template](#5-worked-registry-entry-template)
6. [Companion structures](#6-companion-structures)
7. [Checklist: adding an entry](#7-checklist-adding-an-entry)
8. [Checklist: versioning a snapshot](#8-checklist-versioning-a-snapshot)

---

## 1. The entry schema, field by field

Every entry in the registry carries the same fields. An entry missing a required field is not
ready to publish. Fields marked *required* gate admission; the rest are strongly recommended.

| Field | Required | Purpose | Allowed values | Example |
|---|---|---|---|---|
| `id` | yes | Stable join key that every other artifact cites. Permanent once published. | `<FAMILY>-<NN>`, family prefix from a fixed set, zero-padded number. | `ENC-02` |
| `class` | yes | The family the entry belongs to; groups related entries and scopes the id. | One value from the published family set. | `ENC` |
| `statement` | yes | The rule itself, in one imperative sentence. (Named `principle` in the exemplar registry `principles.yaml` — the field is the same; pick one name and use it consistently.) | Free text, one sentence. | "Bars must start at a zero baseline." |
| `force` | yes | How strongly the entry binds; the contract a downstream gate acts on. | One token from the force vocabulary (§3). | `MUST` |
| `evidence_tier` | recommended | How well-supported the entry is; lets a reader weigh it and lets you reserve hard force for well-backed claims. | An ordered tier label (e.g. A > B > C > D). | `A` |
| `contexts` | recommended | Where the entry applies. | Tags, or `all`. | `[bar, column]` |
| `exceptions` | recommended | Known contexts where the entry is relaxed or overridden; points at the conflict ledger where relevant. | Free text / ids. | "see conflicts.md #3" |
| `sources` | recommended | Provenance: the source ids that back the entry. Governed by `claim-provenance`. | Source ids from a source registry. | `[S02, S15]` |
| `rationale` | recommended | *Why* the entry holds — the mechanism, not a restatement of the rule. | Free text. | "A bar encodes quantity by length from zero." |
| `checks` | yes | The testable operationalization: what a validator or reviewer runs to decide if the entry is honoured. | A list of concrete, evaluable conditions. | ["axis min == 0 for any bar geom"] |

Two fields do the load-bearing work and are therefore *required*: `force` (so the entry is
enforceable) and `checks` (so the entry is runnable). `id` and `class` are required because
they make the entry citable. An entry with a statement but no check is a slogan; an entry with
a statement but no force is an opinion.

## 2. Id-namespace conventions

- **Shape.** `<FAMILY>-<NN>`: an uppercase family prefix from a fixed, published set, a
  hyphen, then a zero-padded sequence number (`SCI-07`, not `sci7`). A fixed width keeps ids
  sortable and greppable with a simple pattern such as `\b[A-Z]+-\d{2}\b`.
- **Family set is closed.** Families are declared once at the registry level (§4). Adding a
  family is a registry-level decision, logged like any other (SKILL rule 5), not an ad-hoc act.
- **Numbers are assigned once and never reused.** When an entry is removed, its number is
  *retired*, not handed to a new entry — reuse would silently repoint old citations.
- **Never renumber to tidy.** Gaps in the sequence are fine and expected. Ids are foreign keys;
  their only job is to be stable.
- **A second registry gets its own id space.** A companion controlled vocabulary uses its own
  keys (e.g. short uppercase names) so its ids never collide with the principle ids. Keep the
  two spaces visibly distinct.
- **Compound citations.** If consumers write slash-lists (`QA-01/03`), make the audit lint
  expand them before matching, or a naive `\bID-\d{2}\b` scan will read only the first id and
  report a false dangling reference. (This exact false positive is logged in
  `MandrakeVisualize/synthesis/DECISIONS.md`.)

## 3. Force-semantics table

The force vocabulary is the contract between the registry and any gate that consumes it. Keep
it small and fixed. The set below is the one this repo uses; adopt it or an equivalent, but
publish the semantics so each token means exactly one thing.

| Force | Class | Meaning | What a gate does with it |
|---|---|---|---|
| `MUST` | hard | Positive hard constraint; violation makes the artifact invalid. | Reject on violation. Never silently override. |
| `AVOID` | hard | Negative hard constraint; the named construction is invalid unless a listed exception fires. | Reject on presence, unless a declared exception matches. |
| `SHOULD` | soft | Strong weighted preference; deviate only for a stated, defensible reason. | Cost points / flag; do not block. |
| `MAY` | soft | Permitted, optional technique. | No penalty either way. |
| `ESCALATE` | surface | A genuinely context-dependent decision the agent must raise, not resolve silently. | Halt and surface the decision to a human or to explicit intent. |

The hard (`MUST`/`AVOID`) vs soft (`SHOULD`/`MAY`) split is what lets *gating* (validity, pass
or fail) be a separate operation from *ranking* (quality, weighted score). `validity-floors`
consumes exactly this distinction. Reserve hard force for well-supported entries (high
evidence tier), so that "this rule is law" always comes with "and here is why it earns that."

## 4. Registry-level (meta) fields

The registry as a whole carries a header block, distinct from any single entry:

| Field | Purpose | Example |
|---|---|---|
| `version` | The snapshot label, so a consumer can cite "built against v0.1". | `"0.1"` |
| `generated` | The date the snapshot was frozen; makes the registry auditable in time. | `"2026-08-28"` |
| `force_semantics` | The published meaning of each force token (§3), inline so the file is self-describing. | (the table above) |
| `families` | The closed set of family prefixes and what each covers; the id namespace. | `{ENC: "encoding choices", ...}` |

## 5. Worked registry-entry template

A blank entry to copy, followed by the field checklist. Format shown as YAML; the pattern is
format-neutral.

```yaml
- id: FAM-NN            # family prefix + zero-padded number; permanent once published
  class: FAM            # the family this belongs to (must be in meta.families)
  statement: >          # one imperative sentence — the rule
    <the rule, stated as an instruction>
  force: MUST           # exactly one of MUST | AVOID | SHOULD | MAY | ESCALATE
  evidence_tier: A      # how well-supported (reserve hard force for high tiers)
  contexts: [ ... ]     # where it applies; "all" for general
  exceptions: >         # known relaxations; cite the conflict ledger if adjudicated there
    <context where it is relaxed, or "none">
  sources: [S02, S15]   # source ids backing it (see claim-provenance before adding)
  rationale: >          # WHY it holds — the mechanism, not a restatement
    <the causal reason a reader could challenge>
  checks:               # the testable operationalization — no check, no entry
    - <a concrete condition a validator or reviewer can evaluate>
    - <another, if the rule has more than one observable consequence>
```

Filled example (abridged, from this repo's registry):

```yaml
- id: ENC-02
  class: ENC
  statement: Bars and columns must start their value axis at zero.
  force: MUST
  evidence_tier: A
  contexts: [bar, column]
  exceptions: "Non-bar encodings (line, dot) escalate the ratio-vs-difference call; see UNC-01 and conflicts.md #3."
  sources: [S02, S05, S15]
  rationale: A bar encodes quantity by length from a zero origin, so truncating the axis makes the length lie.
  checks:
    - "For any bar/column geometry, the value-axis minimum equals zero."
    - "No axis break is present on a bar/column value axis."
```

## 6. Companion structures

A registry is more than its entry list. Four companion structures make it auditable; each is a
first-class file, not a comment:

- **Glossary** — shared definitions so every id and term means one thing across all consumers.
  Prevents two entries from using "baseline" to mean two things.
- **Conflict ledger** — where two well-supported entries disagree, record the tension, state
  which force governs by default, and name the context that flips it. Conflicts are
  *adjudicated, not deleted* — a mature registry does not pretend good sources always agree.
- **Decision log** — each non-obvious call with its rationale and a **reversal condition**
  ("reverses if …"). The reversal condition is what makes the decision testable rather than
  permanent.
- **Open-questions list** — genuine uncertainties, tagged by kind (evidence gap, design
  decision, scope, tooling), recorded so a default resolution never masquerades as a decision.

## 7. Checklist: adding an entry

1. **Provenance first.** Confirm the claim is entitled to be encoded (real source, actually
   read, says what you think) — that is `claim-provenance`, upstream of this step.
2. **Assign the next unused number** in the correct family. Never reuse a retired number.
3. **Write the statement** as one imperative sentence.
4. **Pick exactly one force** from the vocabulary. If you reach for an adjective, stop and
   choose a force token instead.
5. **Justify the force against the evidence tier** — hard force needs strong backing.
6. **Write at least one check.** If you cannot, the entry is not crisp enough to publish yet.
7. **Fill rationale, sources, contexts, exceptions.** Rationale states the mechanism, not a
   restatement.
8. **Check for conflict** with existing entries. If it disagrees with one, add a conflict-ledger
   entry rather than silently overriding.
9. **If the entry embodies a non-obvious call,** log it in the decision log with a reversal
   condition.
10. **Update any consumer** (rubric, taxonomy, orchestrator) to *cite the new id* — never to
    copy its text.

## 8. Checklist: versioning a snapshot

1. **Bump `version` and set `generated`** to today. A snapshot with no date cannot be audited.
2. **Run the citation audit:** every id cited by any consumer resolves to a live entry; report
   zero dangling references (expand slash-lists first — see §2).
3. **Diff against the previous snapshot:** enumerate added, retired, and force-changed entries.
4. **Resolve or re-register open questions:** anything closed since last version moves from the
   open-questions list into the decision log with its rationale.
5. **Confirm no rule is duplicated** across consumers — the registry remains the single source
   of truth; consumers cite, they do not restate.
6. **Freeze the snapshot** as an immutable reference so downstream artifacts can cite "built
   against vN".
