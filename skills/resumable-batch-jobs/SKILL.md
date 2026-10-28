---
name: resumable-batch-jobs
description: Make a long batch job safe to resume so retries and restart logic cannot silently lose or duplicate work. Use for per-item loops over an API, LLM scans over a corpus, crawls, bulk imports, migrations, any "skip what's already done" check; also when auditing a job's coverage numbers or a clean-looking summary after a network wobble.
---

# Resumable batch jobs

Long jobs get interrupted; build them to resume. The naive resume check, *"is there
already a record for this item?"*, is the bug: it treats *succeeded* and *attempted and
failed* alike as "done, skip". A transient outage then writes failure records that every
later resume skips forever, and the summary still reads clean.

## State model

Not `missing | recorded`, but:

```
pending | in_progress | succeeded | retryable_failure | terminal_failure
```

For operations that may have committed remotely, also `unknown_outcome` (reconcile before
any retry; see "Retry safety").

**Resume decisions depend on semantic completion state, never on record existence.**
`in_progress` left unresolved marks a crash ("started and died" vs "never got to it").

## Identity key must match

If the key is unstable or partly read, finished items look pending and work is
**duplicated**.

1. An identity key is a pure function of the item: content digest (`hashlib`),
   server-assigned id, natural key. Never `hash()` (salted per process), wall-clock,
   iteration order or memory address.
2. Prefer an id recorded inside each record over one derived from the filename.
3. Parse the key to its delimiter or read the whole record; a fixed head read
   (`f.read()[:4000]`) fails on the long records.
4. Test idempotency: run twice against a populated store; the second run creates nothing.

## Shapes to distrust

| code says | actually means | honest version |
|---|---|---|
| `if item_id in done_ids: continue` | any record: success, failure, stub, half-write | skip only on `succeeded`; route `retryable_failure` back to the queue |
| one append-only output, one record per attempt | attempt log read as completion log | explicit outcome field per attempt, resolved per item; or separate stores |
| `except SomeError:` on a network call | misses `RemoteDisconnected`, `ssl.SSLError`, socket timeouts, DNS errors (often not subclasses) | catch broadly at the loop boundary, classify inside, nothing escapes the per-item handler |
| bare `except: pass` | failure becomes success-shaped nothing | record exception type and message; unclassified = `retryable_failure` at worst |
| `sleep(random.uniform(3, 9))` | a guess against a server that published its cooldown | read `Retry-After` / the error body's stated wait; exceed it |
| `processed: 3535` | attempts that produced a record | `succeeded`, `failed_terminal`, `pending` as separate fields, with identity conservation asserted |
| stage 2 starts because stage 1 returned | shell reported last pipeline command, or nothing checked | stage 2 refuses without a completion marker naming the expected item count |
| resume test reruns a finished job | no-op path, always passes | inject a synthetic outage mid-run, resume, assert conservation |

## Retry safety

A failure record does not prove the operation did not happen (response lost after commit).
Blind retry can duplicate side effects (charge, ticket, message, job submit, counter).

> failed record -> establish whether retry is SAFE, then retry or reconcile.

In order of preference:
1. **Idempotency key** derived from the item (not the attempt), sent on every retry.
2. **Observable completion state**: query for what the operation would have created, using a key known before the write.
3. **Reconciliation pass**: enumerate remote state, diff against intent, act on the difference.

Read-only and pure-computation items (LLM scan, parse, fetch into your own store) are
exempt; state that explicitly in code, since the next operation added may not be.

## Reporting contract

A summary that cannot tell "we did not look" from "we looked and found nothing" presents
an outage as a finding.

- Never emit a single "processed" number; success and failure are separate fields.
- **Assert identity conservation, not a count.** `requested == succeeded + terminally_failed + still_pending`
  by count alone is fooled by duplicates: requested {A,B}, completed {A,A} balances while B
  is lost. Required: the set of requested ids equals the set of accounted ids, each id
  accounted exactly once, and the report lists `duplicates`, `missing` and `unexpected`
  ids. Any non-empty list means the run failed.
- Carry the error rate as a first-class output.
- Make "no result for this item" a distinct value from "no finding for this item".

## Checklist

0. Verify the resume key is stable and fully read (section above) before trusting skip logic.
1. Classify every failure retryable or terminal and record which. DNS, reset, 429, 5xx,
   time-outs -> retryable; 400, 401, 404, schema rejection, unparseable input -> terminal;
   unanticipated -> retryable with its type recorded.
2. Record retry count and terminal disposition per item.
3. Honour the server's stated cooldown over your backoff.
4. Back off exponentially with jitter.
5. Establish retry safety before retrying anything with a side effect.
6. Crash-safe writes: temp path then rename, or one complete record per line then flush;
   fsync if guarding against machine loss. A torn record is a record that exists.
7. Report success and failure separately; assert identity conservation.
8. Fail the pipeline, not just the stage: a stage that ends early writes a completion
   marker with its count; the next stage refuses a marker that disagrees with expected input size.
9. Test resume by injecting a synthetic outage mid-run and replaying; assert the final
   state is complete (identity-conserved), not merely that the count balances.

## Neighbours

- `confident-wrong-numbers`: counts that measure records, not completions.
- `grader-validation`: when the thing reporting clean is a scorer, oracle or guard.
- `git-efficiency`: per-item loops that shell out to git.
