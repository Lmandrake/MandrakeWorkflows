"""Vendored-code drift (DESIGN.md section 9): every `# from Lodestar <file>@<sha> <name>` block is
compared with that name's source at that sha. A difference WARNS; it never fails the suite."""
import ast
import glob
import os
import re
import subprocess
import warnings

import pytest

AUGUR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LODESTAR = os.path.expanduser("~/dev/Lodestar")
MARK = re.compile(r"^(\s*)# from Lodestar (\S+?)@([0-9a-f]+) (\S+)\s*$")


def _named(text, name):
    """Source of a top-level def/class/assignment `name`, or `Class.method`; None if absent."""
    tree = ast.parse(text)
    cls, _, meth = name.rpartition(".")
    body = tree.body
    if cls:
        body = next((n.body for n in tree.body if isinstance(n, ast.ClassDef) and n.name == cls), [])
    for n in body:
        if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name == meth:
            return n
        if isinstance(n, (ast.Assign, ast.AnnAssign)):
            tg = n.targets if isinstance(n, ast.Assign) else [n.target]
            for t in tg:
                if any(isinstance(e, ast.Name) and e.id == meth for e in (t.elts if isinstance(t, ast.Tuple) else [t])):
                    return n
    return None


def _seg(text, node):
    lines = text.splitlines()[node.lineno - 1:node.end_lineno]
    return "\n".join(l.rstrip() for l in __import__("textwrap").dedent("\n".join(lines)).splitlines())


def _marks():
    files = glob.glob(os.path.join(AUGUR, "augur", "darwin", "*.py")) + \
        glob.glob(os.path.join(AUGUR, "augur", "collectors", "*.py")) + \
        glob.glob(os.path.join(AUGUR, "augur", "lodestar", "*.py"))
    for f in sorted(files):
        lines = open(f).read().splitlines()
        for i, line in enumerate(lines):
            m = MARK.match(line)
            if m:
                modified = any(l.strip().startswith("# modified") for l in lines[max(0, i - 3):i + 2])
                yield f, i, m.group(2), m.group(3), m.group(4), modified


def test_vendored_marks_exist():
    assert len(list(_marks())) >= 40


def test_vendored_drift():
    if not os.path.isdir(os.path.join(LODESTAR, ".git")):
        pytest.skip("Lodestar checkout absent")
    cache, checked, drift = {}, 0, []
    for f, i, rel, sha, name, modified in _marks():
        if modified:
            continue
        key = (rel, sha)
        if key not in cache:
            r = subprocess.run(["git", "-C", LODESTAR, "show", "%s:%s" % (sha, rel)], capture_output=True, text=True)
            cache[key] = r.stdout if r.returncode == 0 else None
        upstream = cache[key]
        if upstream is None:
            drift.append("%s@%s: not in Lodestar history" % (rel, sha))
            continue
        un = _named(upstream, name)
        mine_text = open(f).read()
        # the vendored node is the first statement starting after the mark line
        mn = None
        for node in ast.walk(ast.parse(mine_text)):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Assign, ast.AnnAssign)) and node.lineno == i + 2:
                mn = node
                break
        if un is None or mn is None:
            drift.append("%s %s: not found (%s)" % (os.path.basename(f), name, "upstream" if un is None else "vendored"))
            continue
        checked += 1
        if _seg(upstream, un) != _seg(mine_text, mn):
            drift.append("%s %s differs from %s@%s" % (os.path.basename(f), name, rel, sha))
    for d in drift:
        warnings.warn("vendored drift: " + d)
    assert checked > 0
