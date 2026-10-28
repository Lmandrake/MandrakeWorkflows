# Ideogram lifecycle: scope cutoff in, ledger out, registry

Both ends are situational: they belong to shapes that get re-run or closed out.

**Scope cutoff (going in).** For re-run shapes (status / report-out), put near the header:
"consider material dated after `<last report-out>`; if none, since project inception." A date
the author edits each cycle, so the same ideogram can be handed to Claude verbatim next quarter
with correct temporal scope. Omit it for one-shot shapes; "N/A" there means the block was
included out of habit.

**The closure ledger (coming out).** When the cycle closes, write the final `§ WHERE I'VE BEEN`
entry: what landed (by path), the per-criterion verdict against the bar, the self-check
receipt, and one lesson for the next cycle. Without it the document states a bar forever and
never learns whether it was met; the ledger is what makes the next version better.

**The block registry** (`block_registry.md`). Rows are invariant → realization → shape →
fingerprint → deployment. **Fingerprint** is the only discriminating column: did this block
leave a visible trace in what came back? `yes` / `no` / `no signal` (nothing came back or no
way to tell; itself a finding). A use-count measures the author's habits, not leverage.
- *On authoring:* a row per block used, fingerprint blank; add the shape if new.
- *On close:* set each fingerprint from what actually arrived.
- *Never gate authoring on it:* an absent fingerprint means "unproven", not "don't use it".
- *Kill condition:* if after two further deployments it has changed no block choice, retire it
  and let the per-ideogram ledgers carry the lessons.
