# Waypoints — navigational shortcuts database

This file is the **authoritative source of truth** for the `waypoint` tool.
Every environment variable and `wp` jump target in your shell is rendered from
the table below. Edit here (or via `waypoint add` / `waypoint remove`) and then
run `waypoint sync` to push changes into your shell login file.

If your shell login file is ever damaged, `waypoint sync` rebuilds it from this
table. If *this* file is ever lost, `waypoint import` rebuilds it from the
managed block in your shell login file.

Columns:
- **Name** — the shortcut name; becomes `$NAME` and `wp name`. Must be a valid
  shell identifier (letters, digits, underscore; not starting with a digit).
- **Path** — absolute directory path (no `~`).
- **Added** — date the waypoint was first recorded.
- **Status** — `active` normally; free-form otherwise (e.g. `stale`).
- **Notes** — optional human note.
- **Machine** — optional. Blank = universal fallback, used on any machine with
  no more specific row for this Name. A Name may have several rows as long as
  each has a distinct Machine (see `waypoint machine` to find this machine's
  key, and the README for the full resolution rule).

| Name | Path | Added | Status | Notes | Machine |
|------|------|-------|--------|-------|---------|
| NOTES | /home/you/dev/Notes | 2026-01-01 | active | personal notes repo |  |
| THESIS | /home/you/Drive/Projects/Thesis | 2026-01-01 | active | universal row: same path on every machine |  |
| THESIS | /home/you/Library/CloudStorage/Drive/Projects/Thesis | 2026-01-01 | active | this machine mounts the drive elsewhere | work-laptop |
| SCRATCH | /home/you/scratch | 2026-01-01 | blocked | deliberately not exported |  |
