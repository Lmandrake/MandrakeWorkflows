# The Designer

An agent that argues with you about a design before anything is built. Owner, 2026-11-01: *"It gets really detailed,
dialectic, debating, and works out a thorough understanding of what the mod does and does not do."* It is Socratic: it
asks the questions that make you picture play, attacks its own claims, and coaches you toward a sharper design. It
then writes the result down so precisely that a builder and a separate judge cannot misread it.

The name is provisional (it was "Concept"); the owner is choosing the final one.

First target and proving ground: RimMandrake (`Lmandrake/RimMandrake`), where it runs as the role
`src/RimMandrake/rimflow/roles/designer.md` with the program `rimflow/concept_tree.py`. Its product there is a concept
tree that the [Relentless Pipeline](../relentless/README.md) refuses to start without. First real project: the
GimmeSomeSlack mod. This folder is built as the agent is designed; running code stays in RimMandrake until it is proven.
Reuse is extraction only, as for Relentless: project specifics sit in an adapter, the design is not changed for reuse.

| File | What it holds |
|---|---|
| [`agent/DESIGNER_AGENT.md`](agent/DESIGNER_AGENT.md) | The definition: character, stages, the turn, answer types, product |
| [`DEFECTS.md`](DEFECTS.md) | Known defects, each with evidence and status |
| [`STRENGTHS.md`](STRENGTHS.md) | Known strengths and weaknesses, measured where possible |
| [`CHANGELOG.md`](CHANGELOG.md) | Version history of the agent's growth |
| [`TRUST.md`](TRUST.md) | The numbers that say whether it can be trusted yet |

Rule for this folder: a claim about the agent carries its evidence, or says UNMEASURED.
