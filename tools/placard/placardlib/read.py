"""The canonical read: resolve one entry file to one identified generation.

`<original>.placard.md` is always the authoritative entry point. An external
body is selected BY it; a body file's mere presence on disk never makes it
authoritative, and a similarly-named body is never substituted for the one the
entry names.

All I/O is injected so the state machine is testable without a filesystem.
"""
from __future__ import annotations

from . import schema

STATES = (
    "ok",
    "legacy",
    "source-stale",
    "extraction-stale",
    "body-missing",
    "unavailable",
    "needs-source-inspection",
)

_ERROR_MARKER = "[extraction error:"


def authorizes_original(state: str) -> bool:
    """Owner decision D5. These two states -- and only these -- permit a reader
    to open the original. Without this, a filename-guess image digest blocks the
    very inspection needed to answer what the image shows."""
    return state in ("unavailable", "needs-source-inspection")


class ReadResult:
    __slots__ = ("state", "body", "view", "detail")

    def __init__(self, state: str, body=None, view=None, detail: str = ""):
        self.state = state
        self.body = body
        self.view = view
        self.detail = detail

    def __repr__(self) -> str:
        return f"ReadResult(state={self.state!r}, detail={self.detail!r})"


RETRY_ATTEMPTS = 3
RETRY_DELAY_S = 0.4


def resolve_with_retry(entry_text: str, *, source_sha256, current_profile_id,
                       load_body, sha256_of_text, reread_entry=None,
                       attempts: int = RETRY_ATTEMPTS, sleep=None) -> ReadResult:
    """`resolve`, retrying the one state that is genuinely transient.

    On a synchronising mount the entry file can become visible before the body
    it names (race S7): locally-correct write ordering cannot prevent that,
    because the ordering that matters is the mount's delivery order, not ours.
    `body-missing` is therefore retryable — and ONLY it. A `source-stale` or
    `unavailable` result is a fact about the files and retrying it just wastes
    time.

    `reread_entry` is re-read between attempts when supplied, because the entry
    may itself be mid-publish; without it the same stale pointer is retried.
    Sleep is injected so the retry is testable without real delay.
    """
    import time

    sleeper = sleep or time.sleep
    text = entry_text
    result = None
    for attempt in range(1, max(1, attempts) + 1):
        result = resolve(text, source_sha256=source_sha256,
                         current_profile_id=current_profile_id,
                         load_body=load_body, sha256_of_text=sha256_of_text)
        if result.state != "body-missing":
            return result
        if attempt < attempts:
            sleeper(RETRY_DELAY_S * attempt)
            if reread_entry is not None:
                fresher = reread_entry()
                if fresher:
                    text = fresher
    # Still missing after bounded retry: report it as unavailable, which is the
    # state that authorizes opening the original.
    return ReadResult("unavailable", view=result.view if result else None,
                      detail=(f"declared body still missing after {attempts} "
                              f"attempts — {result.detail if result else ''}"))


def resolve(entry_text: str, *, source_sha256, current_profile_id,
            load_body, sha256_of_text) -> ReadResult:
    view = schema.load_digest(entry_text)

    if view.body_layout == "external":
        if not view.body_path:
            return ReadResult("unavailable", view=view,
                              detail="body_layout is external but body_path is absent")
        raw = load_body(view.body_path)
        if raw is None:
            return ReadResult("body-missing", view=view,
                              detail=f"declared body {view.body_path} not found")
        if not view.body_sha256 or sha256_of_text(raw) != view.body_sha256:
            return ReadResult("body-missing", view=view,
                              detail="body hash does not match the entry's body_sha256")
        body = raw
    else:
        body = schema.inline_body(view.markdown)
        if not body or body.startswith("_("):
            return ReadResult("unavailable", view=view,
                              detail="no usable inline body")

    if _ERROR_MARKER in body:
        return ReadResult("unavailable", view=view,
                          detail="body records an extraction error")

    # Source staleness outranks extraction staleness: if the bytes changed, the
    # profile question is moot.
    if view.source_sha256 and source_sha256 and view.source_sha256 != source_sha256:
        return ReadResult("source-stale", body=body, view=view,
                          detail="source_sha256 differs from the artifact")

    if view.is_legacy:
        return ReadResult("legacy", body=body, view=view,
                          detail="placard_version 1 — upgrade on access")

    if view.profile_id and current_profile_id and view.profile_id != current_profile_id:
        return ReadResult("extraction-stale", body=body, view=view,
                          detail=f"extracted with {view.profile_id}")

    return ReadResult("ok", body=body, view=view)
