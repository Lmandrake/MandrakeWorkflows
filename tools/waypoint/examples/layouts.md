# Window layouts database

Where each focus project's iTerm2 window sat, per machine: its macOS Space
(Mission Control desktop number) and bounds. `waypoint layout save` records the
currently open focus windows here; `waypoint focus launch` reopens a missing
one on its saved Space, at its saved bounds, through the matching
`Claude-SpaceN` iTerm2 profile. A project with no row here opens exactly as
before (default profile, current Space).

Columns:
- **Name** — the launch alias (launches.md).
- **Machine** — machine key (`waypoint machine`). Always set: Spaces and
  screen coordinates mean nothing on another machine.
- **Space** — 1-based desktop number on the window's display.
- **X** / **Y** / **Width** / **Height** — window bounds in points, top-left
  origin (the coordinates iTerm2's AppleScript `bounds` uses).
- **Saved** — when this row was captured.

| Name | Machine | Space | X | Y | Width | Height | Saved |
|------|---------|-------|---|---|-------|--------|-------|
| Notes | work-laptop | 1 | 20 | 40 | 800 | 600 | 2026-01-01 09:00 |
