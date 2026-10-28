"""Checks for the 2026-10-15 GPT review findings on git-efficiency.

Each recipe test executes the SKILL.md guidance literally in a disposable repo.
Run: python3 -m pytest skills/git-efficiency/tests
"""
import json
import pathlib
import subprocess

import pytest

HERE = pathlib.Path(__file__).resolve().parent
GRADER = HERE.parent / "eval" / "git-efficiency-workspace" / "grade.py"


def git(repo, *args, check=True):
    return subprocess.run(["git", "-C", str(repo), *args], check=check,
                          capture_output=True, text=True,
                          env={"GIT_EDITOR": "true", "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin",
                               "HOME": str(repo), "GIT_CONFIG_NOSYSTEM": "1"})


def make_repo(tmp_path):
    repo = tmp_path / "r"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "t@example.com")
    git(repo, "config", "user.name", "t")
    git(repo, "config", "commit.gpgsign", "false")
    return repo


# --- Finding 1: pathspec commit takes the WORKING-TREE content -------------

LINES = [f"line {i}\n" for i in range(20)]


def hunk_fixture(tmp_path):
    repo = make_repo(tmp_path)
    f = repo / "f.txt"
    f.write_text("".join(LINES))
    git(repo, "add", "f.txt")
    git(repo, "commit", "-q", "-m", "base")
    # hunk A: staged deliberately
    a = LINES.copy(); a[1] = "A-approved\n"
    f.write_text("".join(a))
    git(repo, "add", "f.txt")
    # hunk B: unrelated, unstaged edit to the same file
    b = a.copy(); b[18] = "B-unrelated\n"
    f.write_text("".join(b))
    return repo


def test_pathspec_commit_sweeps_unstaged_hunk(tmp_path):
    """Documents the hazard: `commit -m .. -- path` commits hunk B too."""
    repo = hunk_fixture(tmp_path)
    git(repo, "commit", "-q", "-m", "msg", "--", "f.txt")
    assert "B-unrelated" in git(repo, "show", "HEAD:f.txt").stdout


def test_skill_recipe_keeps_hunk_boundary(tmp_path):
    """The SKILL.md recipe: pathspec commit only when `git diff -- <path>` is
    empty; otherwise, with hunks staged on purpose, plain `git commit` after
    `git diff --cached --name-only` lists only your paths."""
    repo = hunk_fixture(tmp_path)
    mine = {"f.txt"}
    if git(repo, "diff", "--name-only", "--", *mine).stdout.strip():
        staged = set(git(repo, "diff", "--cached", "--name-only").stdout.split())
        assert staged == mine
        git(repo, "commit", "-q", "-m", "msg")
    else:
        git(repo, "commit", "-q", "-m", "msg", "--", *mine)
    head = git(repo, "show", "HEAD:f.txt").stdout
    assert "A-approved" in head and "B-unrelated" not in head
    assert "B-unrelated" in (repo / "f.txt").read_text()  # B kept, uncommitted


def test_skill_md_states_the_hunk_rule():
    text = (HERE.parent / "SKILL.md").read_text()
    assert "git diff -- <path>" in text and "git diff --cached --name-only" in text


# --- Finding 2: cherry-pick recovery ordering ------------------------------

def cherry_fixture(tmp_path):
    repo = make_repo(tmp_path)
    cfg = repo / "c.json"
    cfg.write_text(json.dumps({"alpha": 1, "beta": 2, "gamma": 3}, indent=2) + "\n")
    git(repo, "add", "c.json"); git(repo, "commit", "-q", "-m", "base")
    git(repo, "checkout", "-q", "-b", "feat")
    cfg.write_text(json.dumps({"alpha": 1, "beta": 20, "gamma": 3}, indent=2) + "\n")
    git(repo, "commit", "-q", "-am", "beta=20")
    sha = git(repo, "rev-parse", "HEAD").stdout.strip()
    git(repo, "checkout", "-q", "main")
    # another agent reserializes with a different key order and indent
    cfg.write_text(json.dumps({"gamma": 3, "beta": 2, "alpha": 1}, indent=4) + "\n")
    git(repo, "commit", "-q", "-am", "reformat")
    r = git(repo, "cherry-pick", sha, check=False)
    assert r.returncode != 0, "fixture must conflict"
    return repo, cfg, sha


def hand_apply(cfg):
    # the current-format file (ours) with only the semantic change applied
    cfg.write_text(json.dumps({"gamma": 3, "beta": 20, "alpha": 1}, indent=4) + "\n")


def test_old_recipe_loses_hand_applied_change(tmp_path):
    """Documents the defect: hand-apply, THEN checkout --ours, discards it."""
    repo, cfg, _ = cherry_fixture(tmp_path)
    git(repo, "show", "HEAD:c.json")  # current-format file
    hand_apply(cfg)
    git(repo, "checkout", "--ours", "c.json")
    assert json.loads(cfg.read_text())["beta"] == 2  # change gone
    assert git(repo, "cherry-pick", "--continue", check=False).returncode != 0  # unresolved


def test_skill_recipe_cherry_pick_recovery(tmp_path):
    """SKILL.md order: checkout --ours, hand-apply, git add, cherry-pick --continue."""
    repo, cfg, sha = cherry_fixture(tmp_path)
    git(repo, "show", sha, "--", "c.json")  # the small semantic diff
    git(repo, "checkout", "--ours", "c.json")
    hand_apply(cfg)
    git(repo, "add", "c.json")
    git(repo, "cherry-pick", "--continue")
    head = json.loads(git(repo, "show", "HEAD:c.json").stdout)
    assert head["beta"] == 20
    assert list(head) == ["gamma", "beta", "alpha"]


def test_skill_md_cherry_pick_order():
    text = (HERE.parent / "SKILL.md").read_text()
    i = text.index("checkout --ours")
    assert text.index("hand-apply", i) < text.index("git add", i) < text.index("cherry-pick --continue", i)


# --- Finding 3: keyword grader ----------------------------------------------

def load_grader():
    src = GRADER.read_text()
    ns = {"__name__": "grade_under_test", "__file__": str(GRADER)}
    exec(compile(src, str(GRADER), "exec"), ns)
    return ns


PER_FILE_ADD = '''
import os, subprocess
def run(rows):
    for old, new in rows:
        os.replace(old, new)
    for p in paths:
        subprocess.run(["git", "add", p], check=True)
'''

BATCHED_SAFE_COMMIT = '''
import os, subprocess
def run(rows, paths, msg):
    for old, new in rows:
        os.replace(old, new)
    subprocess.run(["git", "add", "--", *paths], check=True)  # one lock cycle
    subprocess.run(["git", "commit", "-m", msg, "--", *paths], check=True)
'''

DENIAL = """Review: this script is fine. There is no per-file add loop and no
per-file log loop; it never uses add -A or an unscoped stage; it does not
suppress stderr; there is no bare commit; no redundant status after commit;
rev-parse is not called in a loop. Nothing to batch, nothing to cache."""


def test_grader_rejects_per_file_add_loop():
    g = load_grader()
    assert g["grade_rename"](PER_FILE_ADD)["one_batched_add"] is False


def test_grader_accepts_safe_pathspec_commit():
    r = load_grader()["grade_rename"](BATCHED_SAFE_COMMIT)
    assert r["one_batched_add"] is True
    assert r["explicit_pathspec_or_no_bare_commit"] is True


@pytest.mark.xfail(strict=True, reason="keyword grading cannot read negation; "
                   "grade_audit verdicts are marked unvalidated in EVAL_RESULTS.md")
def test_grader_audit_rejects_denial_prose():
    assert load_grader()["grade_audit"](DENIAL)["_count"] == 0


def test_grader_has_no_machine_path():
    assert "/mnt/d/" not in GRADER.read_text()
