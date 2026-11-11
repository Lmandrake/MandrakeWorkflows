"""Fleet mode: digest several repos, OPT-IN only, from an allowlist file.

Owner-approved scope is the only scope. The 2026-11 fleet run was scoped as
"all of ~/dev minus exclusions" and swept in household, health and company
repos nobody approved (LESSONS: "A multi-repo run is opt-in"). So there is no
"all" mode and no glob: every repo root is named, one per line, in a file the
owner approved. The guard (git-crypt, `.placard-skip`) and SKIP_DIRS still hold
inside each repo; they are the second fence, not the scope.

The default is a dry-run plan; `--go` digests, one process and one Docling
load for the whole run (`digest_many`). A file whose digest is current
(`digest_current`: same sha, profile and figures) is skipped, unless `--force`.
"""
from __future__ import annotations

from pathlib import Path

EXIT_REFUSED = 7
UNTRACKED_MARKER = ".lodestar-untracked"
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".tiff", ".bmp", ".svg"}
REASONS = ("git-crypt", ".placard-skip", ".lodestar-untracked", "collection")


class Refused(Exception):
    """The run must not start; the message is the reason."""


def load_allowlist(path) -> list:
    """Repo roots from FILE: one per line, `#` comments and blanks ignored,
    `~` expanded. Raises Refused on a missing file, an empty list, a glob, or
    a root that does not exist or is not a git repo."""
    if not path:
        raise Refused("no --allowlist given. A fleet run is opt-in: list the "
                      "repo roots the owner approved, one per line, in a file.")
    f = Path(path).expanduser()
    if not f.is_file():
        raise Refused(f"allowlist {f} does not exist")
    roots, bad = [], []
    for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        if any(c in line for c in "*?["):
            bad.append(f"line {n}: {line}: globs are not allowed, name each repo")
            continue
        p = Path(line).expanduser().resolve()
        if not p.is_dir():
            bad.append(f"line {n}: {p}: does not exist")
        elif not (p / ".git").exists():
            bad.append(f"line {n}: {p}: not a git repo root")
        elif p not in roots:
            roots.append(p)
    if bad:
        raise Refused("allowlist rejected:\n  " + "\n  ".join(bad))
    if not roots:
        raise Refused(f"allowlist {f} names no repos")
    return roots


def _reason_key(why: str) -> str:
    return "git-crypt" if "git-crypt" in why else ".placard-skip"


def plan_repo(root: Path, placard, force: bool = False,
              describe_figures: bool = True, profile: str | None = None) -> dict:
    """What a run would do in one repo. `placard` is the CLI module, passed in
    so this reuses its walk, guard partition and digest_current exactly."""
    from . import collection as _collection

    rep = {"root": root, "todo": [], "missing": 0, "stale": 0, "unchanged": 0,
           "images": 0, "refused": {k: 0 for k in REASONS}}
    every = list(placard._iter_all(root))
    if (root / UNTRACKED_MARKER).exists():
        rep["refused"][".lodestar-untracked"] = len(every)
        return rep
    from . import guard as _guard
    allowed, excluded = _guard.partition(every)
    for _p, why in excluded:
        rep["refused"][_reason_key(why)] += 1
    for a in sorted(allowed):
        if a.suffix.lower() in IMAGE_EXTS:
            member, _v = _collection.member_of_collection(a)
            if member:
                rep["refused"]["collection"] += 1
                continue
        st = placard.status_of(a)
        if not force and placard.digest_current(
                a, describe_figures=describe_figures,
                current_profile=profile)[0]:
            rep["unchanged"] += 1
            continue
        rep["missing" if st == "missing" else "stale"] += 1
        rep["todo"].append(a)
        if a.suffix.lower() in IMAGE_EXTS:
            rep["images"] += 1
    return rep


def format_plan(rep: dict) -> list:
    r = rep["refused"]
    return [f"REPO {rep['root']}",
            f"  to digest {len(rep['todo'])} (missing {rep['missing']}, "
            f"stale {rep['stale']}); unchanged {rep['unchanged']}; "
            f"images among them {rep['images']}",
            "  refused: " + ", ".join(f"{k} {r[k]}" for k in REASONS)]


def run(allowlist, placard, *, go: bool, force: bool, describe_figures: bool,
        option_profile: str = "text-v1", out=print, err=print) -> int:
    try:
        roots = load_allowlist(allowlist)
    except Refused as exc:
        err(f"refusing: {exc}")
        return EXIT_REFUSED
    from . import extract as _extract
    profile = _extract.current_profile_id(option_profile)
    reps = [plan_repo(r, placard, force=force,
                      describe_figures=describe_figures, profile=profile)
            for r in roots]
    out(("fleet run" if go else "fleet plan (dry run; pass --go to digest)")
        + f": {len(roots)} allowlisted repo(s)")
    for rep in reps:
        for line in format_plan(rep):
            out(line)
    total = sum(len(r["todo"]) for r in reps)
    if not go:
        out(f"TOTAL to digest {total}")
        return 0
    done = failed = 0
    for rep in reps:
        if not rep["todo"]:
            continue
        # The plan already chose; force so the check is not paid twice.
        _rc, counts = placard.digest_many(
            rep["root"], rep["todo"], option_profile,
            describe_figures=describe_figures, force=True, err=err)
        done += counts["digested"]
        failed += counts["failed"]
    out(f"TOTAL digested {done}, failed {failed}, unchanged "
        f"{sum(r['unchanged'] for r in reps)}")
    return 0 if failed == 0 else 1
