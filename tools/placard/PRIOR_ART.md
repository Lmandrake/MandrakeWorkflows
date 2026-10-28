# Placard — prior art and where it sits

This is a positioning note, not a literature review. Placard borrows freely from
existing ideas; the point here is to be honest about what is genuinely new versus
what is reassembly of known parts. Citations below were verified against live
sources on 2026-08-26 (via the Fetcher run `2026-08-26_placard_prior_art`), except
where explicitly marked unverified.

## The closest neighbors (verified)

**Open Knowledge Format (OKF)** — Google Cloud, v0.1
published 2026-06-12, v0.2 current. Spec at
<https://github.com/GoogleCloudPlatform/open-knowledge-format>, Apache-2.0; a
byte-identical vendored copy ships in `GoogleCloudPlatform/knowledge-catalog`
under `okf/`. Read from local clones on 2026-10-01. **This is now Placard's
nearest relative, closer than llms.txt.** OKF is "a directory of markdown files
with YAML frontmatter" for agent-consumable knowledge, with a reserved `index.md`
per directory for explicitly-named progressive disclosure, a `log.md`, and v0.2
frontmatter families for provenance (`sources` with credibility signals), trust
(`generated` / `verified` → derived tiers), and lifecycle (`status`,
`stale_after`). The convergence is close enough to be worth saying plainly:
OKF's `index.md` is `PROJECT.placard.md`, its `generated.at` is `digested_on`,
its bundle is a Placard tree. Where it differs, in both directions:

- OKF has **no colocation convention** — concepts are the bundle's own files, not
  sidecars beside a heavy original. It also has no tiers and no escalation
  contract.
- OKF's freshness is `stale_after`, an absolute instant a producer must *predict*.
  Placard's `source_sha256` *measures* staleness instead.
- OKF is **ahead of Placard on trust**, and deliberately so. §5.1 refuses to store
  a credibility score because "a score is subjective, unportable across consumers,
  and goes stale," deriving trust tiers from *who verified* a concept. Placard's
  self-assessed `confidence: high|medium|low` is precisely the stored score OKF
  rejects, and OKF's reasoning is better than Placard's.

Conformance (§11) is permissive — parseable frontmatter, a non-empty `type` per
concept, correct `index.md`/`log.md` structure when present — so Placard is close
to being a conformant producer, with real frictions. Full analysis, field mapping,
and what to offer upstream were written up separately (not shipped).

**llms.txt** — Jeremy Howard / Answer.AI, proposed 2024-09-03; spec now at v2
(<https://llmstxt.org/>, modified 2026-08-10). A curated Markdown index published
at a site's `/llms.txt` so agents get "concise, expert-level information gathered
in a single, accessible location" instead of re-parsing HTML. Adopters include
Stripe, Anthropic, Mintlify, and Cursor. Placard's nearest relative until OKF
appeared, above. The difference: `llms.txt` indexes a *website* for *external* agents, with the
full text living in companion `llms-full.txt` files that are hand- or
tool-authored. Placard indexes a *project's heavy artifacts* for *any* future
LLM, keeps each digest *beside its original file*, and adds machine-checkable
staleness (`source_sha256`) and an escalation contract. `PROJECT.placard.md` is
deliberately close in spirit to an `llms.txt` root index.

**repomix** (github.com/yamadashy/repomix, repomix.com) and the `repo-to-text` /
`files-to-prompt` family — "pack your codebase into AI-friendly formats," i.e.
concatenate a repo into one prompt-ready file. Verified. These *flatten and
concatenate*; they do not summarize, do not track staleness, and re-run wholesale.
Placard is the opposite bet: don't pack the originals, replace them with faithful
digests and only descend when the escalation contract fires. repomix is a good
fallback for the `deep`-tier case where the original genuinely must travel intact.

**Anthropic Contextual Retrieval** (2024-09-19,
<https://www.anthropic.com/news/contextual-retrieval>) — prepends chunk-specific
explanatory context before embedding (Contextual Embeddings + Contextual BM25),
cutting failed retrievals by 49% (67% with reranking). Verified. Shares Placard's
core intuition — *a fragment is more useful when it carries context about its
place in the whole* — but operates inside a RAG pipeline over chunks. Placard
applies the same intuition at the artifact level and in plain files, with no
vector store. Its note that a <200k-token corpus can just go in the prompt
directly is itself an argument for Placard's `skim`/`standard` tiers over RAG for
small projects.

**RAPTOR** (Sarthi et al., arXiv:2401.18059, ICLR 2024) — recursively clusters
and summarizes chunks into a tree, so retrieval can pull from the right level of
abstraction. Verified. This is the academic form of Placard's tiers
(skim/standard/deep) and of the map→digest→original descent — but RAPTOR builds an
automatic multi-level summary *tree* for retrieval, whereas Placard keeps a flat,
human-legible, git-diffable one-hop layer (map → sidecar → original) tuned for a
person or agent reading a project, not for a retriever.

**Progressive disclosure** as an agent-design pattern is well attested for
2025–2026 (Anthropic's Agent Skills framing, plus multiple practitioner writeups).
Verified as an established term. Placard is one concrete instantiation: the map is
the low-detail entry point, the escalation contract is the explicit "load more"
trigger.

## Referenced but NOT verified by this run

**Maximal Marginal Relevance (MMR)** — Carbonell & Goldstein, SIGIR 1998. This is
the classic formalization of "reward relevance, penalize redundancy," which is the
theoretical backing for Placard's *Distinctive contribution* section (what is
unique here versus the rest of the project). The 2026-08-26 Fetcher search for it
returned polluted results (a search-engine failure — a page of unrelated airline
links), so **this citation is from prior knowledge and was not confirmed live.**
It should be re-verified before being cited in any external document. The paper is
real and well known, but treat the exact venue/year as unconfirmed until checked.

## What is actually new in Placard

None of the above combines these four choices at once, which is Placard's niche:

1. **Digest lives beside the original** (`foo.pptx` → `foo.pptx.placard.md`),
   not in a central index or vector store — so it travels with the file, survives
   moves within the project, and is obvious to a human browsing the folder.
2. **A machine-checkable staleness gate** (`source_sha256`) that lets a dumb
   script — not a model — decide when a digest can no longer be trusted.
3. **An escalation contract** ("Open the original if…") that states, per artifact,
   the conditions under which the cheap digest is *insufficient* — the explicit
   anti-re-processing mechanism.
4. **A stdlib-only deterministic CLI** for all the bookkeeping (hashing,
   scaffolding, staleness, map generation), with the LLM confined to the semantic
   fill — so the trustworthy parts never depend on a model behaving.

Everything else Placard does has a well-established ancestor; the contribution is
the assembly and the file-layer, read-safe, no-infrastructure form.

**All four survive OKF v0.2** (2026-10-01 re-check): OKF has none of colocation,
hash-measured staleness, the escalation contract, or tiers, and specifies no
tooling at all. What does *not* survive the comparison is Placard's `confidence`
field, which OKF's trust model supersedes on the merits. Note
also that claim 1's wording ("not a central index") now needs care: OKF's reserved
`index.md` is a per-directory listing, the same two-plane shape as Placard's map
tree, so the contrast is with vector stores and manifests, not with maps.
