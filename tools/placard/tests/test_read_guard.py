"""Tests for contrib/placard_read_guard.py — the PreToolUse Read guard.

Tested on BOTH sides deliberately. A syntactic guard fails CLOSED, so its cost
lands on legitimate work rather than showing up as a miss; the false-block cases
below are therefore the more important half of this file."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
GUARD = REPO / "contrib" / "placard_read_guard.py"
PLACARD = REPO / "placard.py"

ALLOW, BLOCK = 0, 2


def run(payload, env=None):
    e = dict(os.environ)
    e["PLACARD_PY"] = str(PLACARD)
    if env:
        e.update(env)
    p = subprocess.run(
        [sys.executable, str(GUARD)],
        input=json.dumps(payload) if not isinstance(payload, str) else payload,
        capture_output=True, text=True, env=e, timeout=60,
    )
    return p.returncode, p.stderr


def read_payload(path):
    return {"tool_name": "Read", "tool_input": {"file_path": str(path)}}


# --- helpers to build a tree with a real, usable digest -------------------

def _digested(tmp: Path, body="hello body text"):
    """An artifact plus a sidecar whose source hash MATCHES -> usable."""
    art = tmp / "deck.pdf"
    art.write_bytes(b"%PDF-1.4 pretend")
    sha = hashlib.sha256(art.read_bytes()).hexdigest()
    side = tmp / "deck.pdf.placard.md"
    side.write_text(
        "---\n"
        "placard_version: 1\n"
        f"source_sha256: {sha}\n"
        "---\n\n"
        "## Full text\n\n"
        f"{body}\n",
        encoding="utf-8",
    )
    return art, side


# --- TRUE BLOCKS ---------------------------------------------------------

def test_blocks_heavy_file_with_usable_digest():
    with tempfile.TemporaryDirectory() as d:
        art, side = _digested(Path(d))
        code, err = run(read_payload(art))
        assert code == BLOCK, f"expected block, got {code}: {err}"
        assert "read the digest, not the original" in err
        assert str(side) in err, "the refusal must name the digest path"
        assert "--allow-once" in err, "the refusal must name the override"


def test_blocks_the_shipped_example_pdf():
    """Against the real digested example that ships in examples/."""
    art = REPO / "examples" / "quarterly-review" / "field-trial-report.pdf"
    if not art.is_file() or not art.with_name(art.name + ".placard.md").is_file():
        return  # the example is not part of this checkout
    code, err = run(read_payload(art))
    assert code == BLOCK, f"expected block on the example PDF, got {code}: {err}"


# --- FALSE-BLOCK GUARDS (the important half) ------------------------------

def test_allows_when_no_sidecar():
    with tempfile.TemporaryDirectory() as d:
        art = Path(d) / "lonely.pdf"
        art.write_bytes(b"%PDF-1.4 x")
        code, err = run(read_payload(art))
        assert code == ALLOW, err


def test_allows_non_heavy_extension():
    with tempfile.TemporaryDirectory() as d:
        # Even with a sidecar beside it, a .md is not a heavy artifact.
        f = Path(d) / "notes.md"
        f.write_text("x")
        (Path(d) / "notes.md.placard.md").write_text("---\n---\n")
        code, err = run(read_payload(f))
        assert code == ALLOW, err


def test_allows_when_source_is_stale():
    """A hash mismatch means the digest describes a different file. The original
    is authorized; regeneration is the remedy, not a block."""
    with tempfile.TemporaryDirectory() as d:
        art, _ = _digested(Path(d))
        art.write_bytes(b"%PDF-1.4 CHANGED SINCE DIGEST")   # hash no longer matches
        code, err = run(read_payload(art))
        assert code == ALLOW, f"stale digest must not block: {err}"


def test_allows_image_reads():
    """Images are out of scope: a Read of an image is a visual read a text body
    cannot serve."""
    with tempfile.TemporaryDirectory() as d:
        img = Path(d) / "figure.png"
        img.write_bytes(b"\x89PNG\r\n")
        (Path(d) / "figure.png.placard.md").write_text("---\n---\n")
        code, err = run(read_payload(img))
        assert code == ALLOW, err


def test_allows_nonexistent_file():
    code, err = run(read_payload("/nope/missing.pdf"))
    assert code == ALLOW, err


def test_allows_other_tools():
    with tempfile.TemporaryDirectory() as d:
        art, _ = _digested(Path(d))
        code, err = run({"tool_name": "Bash",
                         "tool_input": {"command": f"cat {art}"}})
        assert code == ALLOW, err


def test_allows_on_garbage_payload():
    for bad in ["", "not json", "{}", '{"tool_input": null}']:
        code, err = run(bad)
        assert code == ALLOW, f"payload {bad!r} -> {code}: {err}"


def test_fails_open_when_placard_missing():
    with tempfile.TemporaryDirectory() as d:
        art, _ = _digested(Path(d))
        code, err = run(read_payload(art),
                        env={"PLACARD_PY": "/nonexistent/placard.py"})
        assert code == ALLOW, f"must fail open without placard.py: {err}"


# --- the override --------------------------------------------------------

def test_allow_once_is_single_use():
    with tempfile.TemporaryDirectory() as d:
        art, _ = _digested(Path(d))
        assert run(read_payload(art))[0] == BLOCK      # blocked first

        arm = subprocess.run(
            [sys.executable, str(GUARD), "--allow-once", str(art)],
            capture_output=True, text=True, timeout=30,
        )
        assert arm.returncode == 0, arm.stderr

        assert run(read_payload(art))[0] == ALLOW, "token must permit one read"
        assert run(read_payload(art))[0] == BLOCK, "token must be consumed"


def test_allow_once_does_not_leak_to_other_files():
    with tempfile.TemporaryDirectory() as d:
        art, _ = _digested(Path(d))
        other = Path(d) / "other.pdf"
        other.write_bytes(art.read_bytes())
        (Path(d) / "other.pdf.placard.md").write_text(
            (Path(d) / "deck.pdf.placard.md").read_text()
        )
        subprocess.run([sys.executable, str(GUARD), "--allow-once", str(art)],
                       capture_output=True, timeout=30)
        assert run(read_payload(other))[0] == BLOCK, "override is per-file"
