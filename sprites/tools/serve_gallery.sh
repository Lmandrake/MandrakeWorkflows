#!/bin/sh
# Serve the Sprites gallery; ratings, notes and the project cast write to feedback/gallery.decisions.json.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec python3 "$HOME/.claude/skills/review-sheets/assets/serve_sheet.py" \
  --sheet "$HOME/agent-storage/sprites/gallery/index.html" \
  --decisions "$ROOT/feedback/gallery.decisions.json" "$@"
