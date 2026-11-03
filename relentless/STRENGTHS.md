# Strengths and weaknesses

Measured where possible. UNMEASURED means nobody has the number yet.

## Strengths

- Survives restarts and lost workers: state is on disk. Design claim; failure rate UNMEASURED.
- Forces a change of approach after 3 failures of one class. Benefit UNMEASURED.

## Weaknesses

- Inherits the Ralph weakness: each generation starts ignorant unless the disk tells it otherwise.
- Bad memory compounds: a worker that misreads a failure passes it on with confidence.
- Fails silently under resource limits unless an outside watcher reads it (RA-001 to RA-003).
- Fan-out defect rate UNMEASURED: the trial arms ran serial.
