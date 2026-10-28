#!/usr/bin/env python3
"""test_review_2026_10_15.py — reproductions of the GPT deep-review findings, on fake data.

    python3 -m pytest assets/test_review_2026_10_15.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import check_sheet                                          # noqa: E402
import serve_sheet                                          # noqa: E402

MERGE = os.path.join(HERE, "merge_artifact_db.py")
DEMO = os.path.join(HERE, "..", "demo", "sheet.html")


def _write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh)


def _merge(dump, decisions, *extra):
    return subprocess.run([sys.executable, MERGE, "--dump", dump, "--decisions", decisions, *extra],
                          capture_output=True, text=True)


# ── 1. merge_artifact_db.py ──────────────────────────────────────────────────

def test_merge_apply_refuses_frozen_file_and_leaves_it_byte_identical(tmp_path):
    dec = str(tmp_path / "decisions.json")
    _write(dec, {"frozen": True, "frozenOn": "2026-10-01", "decisions": {"a": {"decision": "keep"}}})
    before = open(dec, "rb").read()
    _write(str(tmp_path / "dump" / "a.json"), {"rowId": "a", "rec": {"decision": "cut"}})
    r = _merge(str(tmp_path / "dump"), dec, "--apply")
    assert r.returncode != 0, r.stdout
    assert "frozen" in (r.stdout + r.stderr).lower()
    assert open(dec, "rb").read() == before


def test_merge_refuses_duplicate_row_documents(tmp_path):
    dec = str(tmp_path / "decisions.json")
    _write(dec, {"decisions": {}})
    before = open(dec, "rb").read()
    _write(str(tmp_path / "dump" / "doc1.json"), {"rowId": "a", "rec": {"decision": "keep"}})
    _write(str(tmp_path / "dump" / "doc2.json"), {"rowId": "a", "rec": {"decision": "cut"}})
    r = _merge(str(tmp_path / "dump"), dec, "--apply")
    assert r.returncode != 0, r.stdout
    assert "duplicate" in (r.stdout + r.stderr).lower()
    assert open(dec, "rb").read() == before


# ── 2. two writers on one decisions file ─────────────────────────────────────

_SECOND_WRITER = """
import sys; sys.path.insert(0, {here!r})
import serve_sheet
serve_sheet.DecisionsFile({path!r}).write_ops({{"b": {{"decision": "cut"}}}})
"""


def test_two_writers_do_not_lose_an_update(tmp_path):
    """Writer A reads, a second PROCESS writes row b, then A writes row a. Both must survive."""
    path = str(tmp_path / "decisions.json")
    _write(path, {"decisions": {}})
    a = serve_sheet.DecisionsFile(path)
    real_read = a.read
    state = {}

    def read_then_let_b_in():
        doc = real_read()
        if "proc" not in state:
            state["proc"] = subprocess.Popen(
                [sys.executable, "-c", _SECOND_WRITER.format(here=HERE, path=path)])
            time.sleep(1.0)          # unfixed: B finishes its whole write inside this window
        return doc

    a.read = read_then_let_b_in
    a.write_ops({"a": {"decision": "keep"}})
    assert state["proc"].wait(timeout=20) == 0
    got = json.load(open(path))["decisions"]
    assert got.get("a", {}).get("decision") == "keep"
    assert got.get("b", {}).get("decision") == "cut", f"row b lost: {got}"


def test_sidecar_and_merger_do_not_lose_an_update(tmp_path):
    path = str(tmp_path / "decisions.json")
    _write(path, {"decisions": {}})
    dump = str(tmp_path / "dump")
    _write(os.path.join(dump, "b.json"), {"rowId": "b", "rec": {"decision": "cut"}})
    a = serve_sheet.DecisionsFile(path)
    real_read = a.read
    state = {}

    def read_then_let_merger_in():
        doc = real_read()
        if "proc" not in state:
            state["proc"] = subprocess.Popen(
                [sys.executable, MERGE, "--dump", dump, "--decisions", path, "--apply"],
                stdout=subprocess.DEVNULL)
            time.sleep(1.0)
        return doc

    a.read = read_then_let_merger_in
    a.write_ops({"a": {"decision": "keep"}})
    assert state["proc"].wait(timeout=20) == 0
    got = json.load(open(path))["decisions"]
    assert got.get("a", {}).get("decision") == "keep"
    assert got.get("b", {}).get("decision") == "cut", f"row b lost: {got}"


# ── 3. check_sheet.py: an empty sheet ────────────────────────────────────────

def test_empty_items_fails_the_gate(tmp_path):
    import re
    if not os.path.exists(DEMO):    # generated and gitignored: a fresh clone builds it first
        subprocess.run([sys.executable, os.path.join(os.path.dirname(DEMO), "make_demo.py")],
                       check=True, capture_output=True)
    html = open(DEMO, encoding="utf-8").read()
    html = re.sub(r'(<script id="ITEMS" type="application/json">)(.*?)(</script>)',
                  r"\1[]\3", html, flags=re.S)
    # beside the demo, so everything else about the sheet still checks out
    p = os.path.join(os.path.dirname(DEMO), ".empty_items_test_sheet.html")
    try:
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(html)
        fails = [lab for sev, lab, _ in check_sheet.check(p, None) if sev == check_sheet.FAIL]
    finally:
        os.unlink(p)
    assert fails, "ITEMS=[] passed every handover check"


# ── 4. serve_sheet.py: static serving and symlinks ───────────────────────────

def _serve(root):
    serve_sheet.Ctx.root = root
    serve_sheet.Ctx.sheet = os.path.join(root, "sheet.html")
    serve_sheet.Ctx.token = ""
    serve_sheet.Ctx.quiet = True
    serve_sheet.Ctx.store = serve_sheet.DecisionsFile(os.path.join(root, "decisions.json"))
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), serve_sheet.Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def _get(httpd, path):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{httpd.server_address[1]}{path}") as r:
            return r.status, r.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def test_static_refuses_symlink_out_of_root(tmp_path):
    root = tmp_path / "sheetdir"
    root.mkdir()
    (root / "sheet.html").write_text("<html></html>")
    (root / "ok.txt").write_text("inside")
    secret = tmp_path / "secret.txt"
    secret.write_text("TOP SECRET")
    os.symlink(secret, root / "leak.txt")
    httpd = _serve(str(root))
    try:
        assert _get(httpd, "/ok.txt") == (200, b"inside")
        code, body = _get(httpd, "/leak.txt")
        assert b"TOP SECRET" not in body and code in (403, 404), (code, body)
    finally:
        httpd.shutdown()
