#!/usr/bin/env python3
"""Objective grader for the git-efficiency skill eval. Checks each arm's output
against anti-pattern assertions. Run after all 6 runs complete.

Source-keyword heuristics, not execution: grade_audit cannot read negation (a
review denying every defect still scores), so its verdicts are unvalidated."""
import re, pathlib, json

WS = pathlib.Path(__file__).resolve().parent / "iteration-1"

ADD_IN_LOOP = re.compile(r"^([ \t]*)for\s[^\n]*:[ \t]*\n(?:\1[ \t]+[^\n]*\n)*?\1[ \t]+[^\n]*['\"]add['\"]", re.M)
BARE_COMMIT = re.compile(r"commit['\"]\s*,\s*['\"]-m(?![^\n]*(--|paths))")

def read(p):
    try: return pathlib.Path(p).read_text(encoding="utf-8", errors="replace")
    except Exception: return None

def grade_rename(src):
    if src is None: return {"_missing": True}
    return {
        "no_per_row_git_mv": not re.search(r"for\s+.*:\s*(\n|.)*?git['\"],?\s*['\"]mv", src) and "\"mv\"" not in src.replace(" ", ""),
        "uses_fs_rename": bool(re.search(r"os\.replace|os\.rename|Path\([^)]*\)\.rename|shutil\.move|\.rename\(", src)),
        "one_batched_add": not ADD_IN_LOOP.search(src) and (bool(re.search(r"""add['"][^\n]*(\*|paths)""", src)) or src.count('"add"') + src.count("'add'") <= 2),
        "explicit_pathspec_or_no_bare_commit": not BARE_COMMIT.search(src),
        "concurrency_aware": bool(re.search(r"index\.lock|lock|worktree|concurren", src, re.I)),
    }

def grade_status(src):
    if src is None: return {"_missing": True}
    log_calls = len(re.findall(r'["\']log["\']', src))
    return {
        "no_per_file_log_loop": not bool(re.search(r"for\s+\w+\s+in[^\n]*:(\n[^\n]*){0,6}?['\"]log['\"]", src)),
        "batched_history_walk": bool(re.search(r"--name-status|--name-only|cat-file[^\n]*--batch|--format=[^\n]*%H[^\n]*--name", src)),
        "single_status_for_staged": bool(re.search(r"--porcelain|diff['\"]?\s*,\s*['\"]--cached|diff-index", src)),
    }

DEFECTS = ["per-file add", "per-file log", "add -A / unscoped", "stderr suppress",
           "bare commit / whole-index", "redundant status / self-verify", "rev-parse in loop"]
def grade_audit(src):
    if src is None: return {"_missing": True, "caught": 0}
    s = src.lower()
    caught = {
        "per_file_add_loop": ("add" in s and ("loop" in s or "per file" in s or "per-file" in s or "batch" in s)),
        "per_file_log_loop": ("log" in s and ("loop" in s or "per file" in s or "per-file" in s or "batch" in s)),
        "add_dash_A": ("-a" in s and "add" in s) or "whole tree" in s or "whole-tree" in s or "unscoped" in s,
        "stderr_suppress": "stderr" in s or "devnull" in s or "2>/dev/null" in s or "suppress" in s,
        "bare_commit": ("bare commit" in s) or ("whole index" in s) or ("whole-index" in s) or ("pathspec" in s),
        "redundant_status": ("status" in s and ("redundant" in s or "verify" in s or "unnecessary" in s or "no-op" in s or "after" in s)),
        "rev_parse_loop": "rev-parse" in s and ("loop" in s or "once" in s or "constant" in s or "cache" in s),
    }
    caught["_count"] = sum(1 for k,v in caught.items() if k!="_count" and v)
    return caught

def main():
    out = {}
    for name, grader, fname in [("eval-rename", grade_rename, "rename_mods.py"),
                                 ("eval-status", grade_status, "file_git_info.py"),
                                 ("eval-audit", grade_audit, "review.md")]:
        out[name] = {}
        for arm in ("with_skill", "without_skill"):
            src = read(WS/name/arm/"outputs"/fname)
            out[name][arm] = grader(src)
    print(json.dumps(out, indent=2))
    # summary
    print("\n=== SUMMARY ===")
    for name in out:
        for arm in ("with_skill","without_skill"):
            r = out[name][arm]
            if name=="eval-audit":
                print(f"{name:12} {arm:14} caught {r.get('_count','?')}/7")
            else:
                passed = sum(1 for k,v in r.items() if v is True)
                total = sum(1 for k,v in r.items() if isinstance(v,bool))
                print(f"{name:12} {arm:14} {passed}/{total} assertions pass")


if __name__ == "__main__":
    main()
