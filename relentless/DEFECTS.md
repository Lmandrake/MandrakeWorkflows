# Known defects

Newest first. Judge mode reads this as a list of what to hunt. Status: open, fixed (sha), or watching.

| ID | Date | Defect | Evidence | Status |
|---|---|---|---|---|
| RA-014 | 2026-11-01 | `./sync` could never level a clone holding a replayed commit, and read `relentless.py` as the blocker while the true refusals were the shard blob compare (RA-013) and a commit replayed after a 3-way merge | seat_sync.py | Fixed: a494b1755f, f3c1bdb8fa |
| RA-013 | 2026-11-01 | seat_sync refuses a landed ledger commit once origin's shard has grown: it compares blobs, so a commit whose every line is upstream reads as unpublished and the clone stays diverged | infrastructure/state/lessons/20261101T180249Z-BENCH-seat-sync-refuses-landed-ledger-commit.md | Open; land.sh -m works around it |
| RA-012 | 2026-11-01 | First wall profile left all of /mnt/d/owner/dev but one repo, ~/.ssh (a clone of origin), ~/.claude history and session stores, and most scratch readable | relentless_rules.json walls.marker; proof D:\ClaudeWork\rimmandrake\relentless_agent\wallproof\probe2.out | Fixed 06fd8dece7 |
| RA-011 | 2026-11-01 | Parallel appends to census.jsonl on /mnt/d tore rows | census.jsonl 2 torn rows of 1088 | Fixed: LOG_LOCK, reader tolerates torn rows, resume refills |
| RA-010 | 2026-11-01 | Census v1 read an exit status: a proof written as prose gave a shell error that read as red | relentless_seeds.py proof verdict is now its own PASS/FAIL/CRASH lines | Fixed before any Marker saw a seed |
| RA-009 | 2026-11-01 | Every contract so far was written by the worker that built the work: 48 of 48 | RimMandrake live store, measured | open: tree intake in build |
| RA-008 | 2026-11-01 | Judge blindness was prompt prose: the store is readable and the clean clone carries `.git` and conversations | `relentless.py` read | open: wall in build |
| RA-007 | 2026-11-01 | `learned[-8000:]` feeds workers an unbounded, uncited diary | `relentless.py` read | open: memory in build |
| RA-006 | 2026-11-01 | A fresh worker has no memory of what was already tested, so it can repeat checks forever | Owner's account of v2; three helpers queued on one 6-minute selftest | open: result cache in build |
| RA-005 | 2026-11-01 | Repeats are counted by failure class only, so circling through different failures goes unseen | `same_failure_limit` reads class alone | open |
| RA-004 | 2026-11-01 | Enrolling an item before publishing it let a tick retire it | RimMandrake `RELENTLESS_ENROL_FIX_UNPUBLISHED_RETIRED` | fixed `54f435ea82` |
| RA-003 | 2026-11-01 | Blind checkers drew on the same clone cap as builders, so full pools starved the checks that free them | RimMandrake `relentless_pool_jam`: no finishes for about 6 hours | fixed `bbcff75f26`, review open |
| RA-002 | 2026-11-01 | A resource failure was charged as a launch failure and backed the whole engine off for hours | same | fixed `bbcff75f26` |
| RA-001 | 2026-11-01 | "Running" counted waiting candidates, so a dead engine read as staffed | same | fixed `bbcff75f26` |
