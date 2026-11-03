# Launch aliases database

This file is the **authoritative source of truth** for `waypoint`'s launch
aliases — the second managed block in your shell file, which defines a
`launch <name>` function that cds into a directory and runs a command (for
example, starting a Claude session in a project root). Edit here (or via
`waypoint launch add` / `waypoint launch remove`) then run `waypoint sync`.

Default launch template: claude -n {NAME}

Columns:
- **Name** — the alias; becomes `launch name`. Also substituted for `{NAME}`
  in the command template (verbatim casing). Must be a valid shell identifier.
- **Waypoint** — name of a waypoint to cd into (preferred; follows that
  waypoint's per-machine resolution). Leave blank to use Path instead.
- **Path** — an explicit absolute directory, used only when Waypoint is blank.
- **Command** — the command to run; blank means use the default template above.
  `{NAME}` and `{DIR}` are substituted. Colour markers: the text colour is
  `printf '\033]10;#RRGGBB\007'` (iTerm2 foreground; Lodestar colorboard.py
  reads it); an optional `: led=#RRGGBB;` right after it is the project's
  SidePulse LED colour (a shell no-op; absent means the LED uses the text hex).
- **Added** / **Status** / **Notes** — as in waypoints.md.
- **Machine** — optional; blank = universal fallback (same rule as waypoints).
- **Focus** — `yes` marks a current-focus project: `waypoint focus launch`
  opens an iTerm2 window for it if none is open. Blank = not in focus. Purely a
  launcher marker; it has no effect on Lodestar's background sync.

| Name | Waypoint | Path | Command | Added | Status | Notes | Machine | Focus |
|------|----------|------|---------|-------|--------|-------|---------|-------|
| Notes | NOTES |  |  | 2026-01-01 | active | default template |  | yes |
| Thesis | THESIS |  | printf '\033]10;#00B5B5\007'; claude -n {NAME} | 2026-01-01 | active | cyan text |  |  |
| Lab | | /home/you/lab | jupyter lab --notebook-dir {DIR} | 2026-01-01 | active | explicit path, own command | work-laptop |  |
