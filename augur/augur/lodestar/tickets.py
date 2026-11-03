"""Per-project ticket and to-do counts from Lodestar (DESIGN.md section 3, pilot 2). Read-only.

Sources, all optional (absent, never zero, when unreadable):
- Ticket directories: Lodestar's own resolved list of ticket homes,
  <home>/dev/.lodestar/tickets/homes-cache.json ({stamp, at, homes: [[name, repo_id, code, kind,
  dir, top, repo, public], ...]}), which `ticket` and the Companion refresh at least hourly.
  Augur does not re-derive placements (overlay rules need Lodestar's private-store logic).
  Each home's repo_id is Augur's project key (the registry Id, as for a session); the Lodestar
  checkout is key `lodestar`.
- Each ticket file's front matter `status`: open/active -> tickets_open, blocked -> waiting.
  Files are re-read only when (mtime, size) changes; directories are listed every call.
- `open` = tickets_open + the live items in <home>/dev/.lodestar/whatnow.json whose project maps
  to this key, minus items that ARE tickets (ref path under a tickets/ dir: already counted).
  whatnow project keys map through whatnow.json's own projects[].repo path to the registry Id.
  Items with no project, or filed to private-store or Hestia, count on the Lodestar entry.

basis: "waiting=tickets-only" (Reckoning's waiting_on_others is one global count, not per
project), plus "open=no-whatnow" when whatnow.json is unreadable (then `open` is absent).
"""

import json
import os
import re

STALE_HOMES_S = 6 * 3600.0     # a homes list older than this (Lodestar not running) is not trusted
STALE_WHATNOW_S = 6 * 3600.0   # the same rule for whatnow.json's built_at (R1 finding 11)
NAME_RE = re.compile(r"^(?:[A-Z][A-Z0-9]{1,5}-(?:\d+|x[a-z2-7]{5})|[A-Z0-9]+(?:_[A-Z0-9]+){2,6})\.md$")
OPEN = ("open", "active")
#: DESIGN section 3: the Lodestar entry carries all work that belongs to no project, private-store
#: and Hestia included (the same rule Lodestar's burning attribution applies).
FOLD_TO_LODESTAR = ("private-store", "hestia")


def _status(path):
    """The front-matter status of one ticket file, '' when it has none."""
    with open(path, encoding="utf-8") as fh:
        first = fh.readline()
        if first.strip() != "---":
            return ""
        for _ in range(60):
            line = fh.readline()
            if not line or line.strip() == "---":
                return ""
            if line.startswith("status:"):
                return line.split(":", 1)[1].strip().strip("\"'").lower()
    return ""


class TicketReader(object):
    def __init__(self):
        self.files = {}          # path -> ((mtime, size), status)

    def homes(self, home, now):
        p = os.path.join(home, "dev", ".lodestar", "tickets", "homes-cache.json")
        with open(p, encoding="utf-8") as fh:
            d = json.load(fh)
        if now - float(d.get("at") or 0) > STALE_HOMES_S:
            raise ValueError("homes list stale")
        return d["homes"]

    def counts(self, home, lodestar, now):
        """{key: {"tickets_open": n, "waiting": n}} for every key with a ticket home; a key with a
        home that exists but cannot be listed is left out (unmeasured, never 0). A home whose
        directory does not exist yet is a real 0. Hestia and private-store fold into the Lodestar
        entry (DESIGN section 3; R1 findings 9, 10)."""
        out = {}
        live = set()
        bad = set()
        lod_real = os.path.realpath(lodestar) if lodestar else None
        for h in self.homes(home, now):
            name, repo_id, _code, _kind, d, _top, repo = h[:7]
            key = "lodestar" if lod_real and os.path.realpath(repo) == lod_real else (repo_id or name.lower())
            if key in FOLD_TO_LODESTAR:
                key = "lodestar"
            row = out.setdefault(key, {"tickets_open": 0, "waiting": 0})
            try:
                names = os.listdir(d)
            except FileNotFoundError:
                continue
            except OSError:
                bad.add(key)
                continue
            for n in names:
                if not NAME_RE.match(n):
                    continue
                p = os.path.join(d, n)
                live.add(p)
                try:
                    st = os.stat(p)
                except OSError:
                    continue
                sig = (st.st_mtime, st.st_size)
                hit = self.files.get(p)
                if hit is None or hit[0] != sig:
                    try:
                        hit = (sig, _status(p))
                    except (OSError, UnicodeDecodeError):
                        continue
                    self.files[p] = hit
                s = hit[1]
                if s in OPEN:
                    row["tickets_open"] += 1
                elif s == "blocked":
                    row["waiting"] += 1
        for p in [p for p in self.files if p not in live]:
            del self.files[p]
        for k in bad:
            out.pop(k, None)
        return out


def _epoch(iso):
    from datetime import datetime
    try:
        return datetime.fromisoformat(str(iso)).timestamp()
    except (TypeError, ValueError):
        return None


def whatnow_open(home, lodestar, key_of_repo, now=None):
    """{key: n} of live whatnow items that are not tickets, or None when unreadable, or when its
    built_at is missing or older than STALE_WHATNOW_S (Lodestar stopped: not current)."""
    p = os.path.join(home, "dev", ".lodestar", "whatnow.json")
    try:
        with open(p, encoding="utf-8") as fh:
            d = json.load(fh)
        items = d["items"]
    except (OSError, ValueError, KeyError, TypeError):
        return None
    if now is not None:
        b = _epoch(d.get("built_at"))
        if b is None or now - b > STALE_WHATNOW_S:
            return None
    proj_repo = {}
    for pr in d.get("projects") or []:
        if isinstance(pr, dict) and pr.get("key"):
            proj_repo[pr["key"]] = pr.get("repo") or ""
    out = {}
    for it in items:
        if not isinstance(it, dict):
            continue
        ref = it.get("ref")
        rp = ref.get("path") if isinstance(ref, dict) else (ref if isinstance(ref, str) else "")
        if rp and "/tickets/" in rp:
            continue
        repo = it.get("repo") or proj_repo.get(it.get("project") or "") or ""
        key = key_of_repo(repo) if repo else None
        if not key or key in FOLD_TO_LODESTAR:
            key = "lodestar"
        out[key] = out.get(key, 0) + 1
    return out


def registry_ids(lodestar, home):
    """realpath(checkout) -> registry Id, from sync/registry.md (mtime-cached by the caller)."""
    from augur.lodestar.burning import _expand, _table_rows
    out = {}
    try:
        for r in _table_rows(os.path.join(lodestar, "sync", "registry.md")):
            p = r.get("path", "").strip("`")
            i = r.get("id", "").strip("`")
            if p and i:
                out[_expand(p, home)] = i
    except OSError:
        pass
    return out
