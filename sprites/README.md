# Sprites

Small, luminous, mostly transparent light-creatures — **sprites** — one per open Claude Code session, drifting
on every Space of the laptop. They keep away from the focused window, play briefly with each other, and
encode real load: memory as size, CPU as internal tempo, background tasks as satellites, bandwidth in/out as
pulses inside the shape, machine strain as a red glow and geometric disalignment, a lost VPN as a
huddled, searching flock. Hover a sprite to slow it and see its project; click to jump to that session.

Five concepts are in development side by side, each with 8 colour-independent variants:
Mothership Choir, Siphonophores, Living Sigils, Kaleidoscope Seeds, Firefly Murmurations.

    prototype/    HTML canvas prototypes (one file per concept) on a shared runtime; data from scripted timelines
    tools/        make_scenarios.py (gallery timelines), render_gallery.py (videos), build_gallery.py + serve_gallery.sh (review sheet)
    docs/         GRAMMAR_V2.md (the spec every concept follows), design notes, research, feedback rounds
    feedback/     the owner's gallery decisions (written by the review sheet)

Spec: `docs/GRAMMAR_V2.md`. Data will come from the sampler being built in MandrakeWorkflows; until then the
prototypes run on scripted timelines. The judged design study (blind trials, pre-registration, skill lessons) is
`../visualize/evaluation/runs/2026-10-31-visitors/` (working name then: Visitors).
Large artifacts (videos, screenshots) live in agent storage, `~/ClaudeWork/sprites/`, never in git.
The product will be a native macOS overlay (SpriteKit or Metal), reading Lodestar's collector files.

Gallery: `python3 tools/build_gallery.py && tools/serve_gallery.sh` (videos: `nice -n 10 python3 tools/render_gallery.py`).
