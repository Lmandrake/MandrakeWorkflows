"""Executable checks for the 2026-10-15 review findings (confident-wrong-numbers)."""
import json, os, re, shutil, subprocess, tempfile
import pytest

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEXT = open(os.path.join(SKILL, "SKILL.md")).read() + open(os.path.join(SKILL, "references", "instances.md")).read()


def sh(cmd):
    return subprocess.run(["bash", "-c", cmd], capture_output=True, text=True)


def test_grep_if_recipe_text_branches_on_exit_status():
    # The guidance must not present the two-way `if grep -q; then FOUND; else NONE` as honest.
    bad = re.search(r"if grep -q [^\n]*; then echo FOUND; else echo NONE; fi", TEXT)
    assert not bad, "recipe conflates grep exit 1 (not found) with exit 2 (error)"


def test_recipe_as_written_distinguishes_error_from_none():
    d = tempfile.mkdtemp()
    try:
        missing = os.path.join(d, "nope.txt")
        present = os.path.join(d, "a.txt")
        open(present, "w").write("hello\n")
        recipe = ('grep -q %s {f}; rc=$?; case $rc in 0) echo FOUND;; 1) echo NONE;; *) echo ERROR;; esac')
        assert sh(recipe.format(f=missing) % "hello").stdout.strip() == "ERROR"
        assert sh(recipe.format(f=present) % "hello").stdout.strip() == "FOUND"
        assert sh(recipe.format(f=present) % "zzz").stdout.strip() == "NONE"
        # the old shape lies:
        old = sh("if grep -q hello %s; then echo FOUND; else echo NONE; fi" % missing).stdout.strip()
        assert old == "NONE"
    finally:
        shutil.rmtree(d)


VALUES = [("false", False), ("0", 0), ('""', ""), ("null", None), ("[]", []), ("true", True), ("1", 1)]


@pytest.mark.skipif(shutil.which("jq") is None, reason="jq missing")
def test_jq_alternative_truth_table():
    got = {}
    for lit, _ in VALUES:
        out = subprocess.run(["jq", "-c", "(.v // \"D\")"], input='{"v":%s}' % lit, capture_output=True, text=True).stdout.strip()
        got[lit] = out == '"D"'
    # jq falls back on false/null only; keeps 0, "", []
    assert got == {"false": True, "0": False, '""': False, "null": True, "[]": False, "true": False, "1": False}


def test_python_or_truth_table():
    for lit, v in VALUES:
        assert ((v or "D") == "D") == (not v)


@pytest.mark.skipif(shutil.which("node") is None, reason="node missing")
def test_js_or_vs_nullish():
    js = 'for (const v of [false,0,"",null,undefined,[],true,NaN]) console.log(JSON.stringify([ (v||"D")==="D", (v??"D")==="D" ]))'
    out = subprocess.run(["node", "-e", js], capture_output=True, text=True).stdout.split()
    rows = [json.loads(x) for x in out]
    # false,0,"",null,undefined,[],true,NaN -> ||: fallback on falsy; ??: only null/undefined
    assert [r[0] for r in rows] == [True, True, True, True, True, False, False, True]
    assert [r[1] for r in rows] == [False, False, False, True, True, False, False, False]


def test_text_does_not_equate_jq_with_python_or_js():
    assert not re.search(r"`//` in jq, `or` in Python, `\|\|`\s+in JavaScript", TEXT.replace("\n", " ")), \
        "text still lumps jq // with Python or / JS ||"
    assert "keeps `0`" in TEXT and "`??`" in TEXT
