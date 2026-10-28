#!/usr/bin/env python3
"""RETIRED. This script must not write digests any more.

It was the real body-writing path in v1, and it caused the worst defect in the
corpus. It extracted a whole document, set `body: full`, rewrote `## Full text`
-- and by explicit design preserved the authored prose it had just invalidated,
recording nothing: no provenance stamp, no warning, no non-zero exit. The result
was digests whose Gaps section said "Only the first page / abstract was read"
while holding the entire document, and whose escalation contract told a reader
to open a PDF whose full text was sitting in the same file.

Its job now belongs to `placard digest`, which:

  * stamps body provenance (extractor, version, profile_id, extracted_at),
  * records the summary's basis separately from the body's, so a re-extraction
    cannot silently widen what the summary claims to have been authored from,
  * flags the summary `needs-review` when the new body differs materially,
  * and publishes through the crash-safe protocol.

Spec 7 is explicit that data migration may lag but a writer may not: a program
still permitted to write the old shape defeats every guarantee the new schema
adds. So this refuses rather than being deleted, because a caller that still
invokes it deserves an error naming the replacement instead of silence.
"""
from __future__ import annotations

import sys

MESSAGE = """\
backfill_bodies.py is RETIRED and will not write anything.

It preserved authored prose it had just invalidated, which is what produced the
false coverage claims in a real corpus.

Use the single write path instead:

    .venv/bin/python placard.py --root <project> digest <artifact>

That stamps extraction provenance, keeps the summary's basis separate from the
body's, and flags the summary for review when the body changes materially.
"""


def main() -> int:
    sys.stderr.write(MESSAGE)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
