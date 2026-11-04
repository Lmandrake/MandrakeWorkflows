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

## Hiding a project at work

Settings gives each project an **On screen** choice: **Show**, **Hide**, or **Hide @ Work** (for an outside
project you would rather not have floating on your screen at the office). Hide @ Work hides the project's sprites
whenever Augur reports `machine.vpn.on_site: true`. If that reading goes missing for a while, the last known value
is kept.

Augur needs to be told once which network counts as work. On the work network, run:

    python3 augur/bin/work_here.py            # saves this network's DHCP domain, e.g. wifi.example.com
    python3 augur/bin/work_here.py --list     # what is saved, and what the current network reports

It writes `$AUGUR_HOME/config/work.json` (`{"dhcp_domains": [...]}`). Augur picks the file up within seconds.
A suffix matches its sub-domains too, so editing the entry to `example.com` covers every building. Wired and
Wi-Fi networks both count, and no Location Services grant is needed.

With Claude Code, open a session in this repo while connected at work and say: *"Mark this network as work for
Augur, then check that Augur reports on_site true."* Claude runs `work_here.py` and reads
`$AUGUR_HOME/live/snapshot.json` back. In Settings, set the project to Hide @ Work.
