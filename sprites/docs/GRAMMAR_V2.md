# Visitors behaviour grammar v2 (after owner gallery round 1, 2026-10-31)

One grammar for all five concepts, so a datum looks "the same kind of thing" whichever creature you
assigned. Source: `GALLERY_FEEDBACK_R1.md`. Each concept realises every row in its own idiom.

| Datum | Universal channel | Never |
|---|---|---|
| Identity (project) | colour (Waypoint hue) + variant form (iv 0..7) | data on form |
| Memory footprint | body size, area-proportional (unchanged; owner liked it everywhere) | |
| CPU (cores) | internal tempo: speed of the shape's own chase/spin/pulse of lights | spin of satellites |
| Background tasks (procs) | count of discrete satellites/appendages (orbiting dots; for Siphonophores the tentacles). Owner reads these as processes by default: count must be readable for 1-10 | |
| Bandwidth IN (rx) | pulses of light travelling INWARD along the shape's own structure (rim -> core), cool white-blue tint. More Mbit/s = more and brighter pulses (log scale) | particles arriving from outside the creature's bounds |
| Bandwidth OUT (tx) | pulses travelling OUTWARD (core -> rim), warm gold tint; same scale | |
| Bandwidth strained (net.strain 0..1: need > available) | the pulses jam: they stall and bunch up at the rim/throat, stutter, pile into a bright clogged band, flow visibly throttled. Distinct from machine strain (no red) | |
| Machine strain (m.level 0..3, thermal, mempress) | REDDISH GLOW behind and inside the shape (ember halo, rising with level) + the shape dis-aligns as if noise were added to its geometry (owner liked this a lot). Agitation of drift grows with it | rings, ripples, approach, flashing halos — anything resembling needs-you |
| Needs you | expanding ripple rings + approach to the focused window's edge and knock (unchanged) | red |
| VPN lost | huddle tightly together, colour drains cold, a searchlight sweeps, a small red beacon blinks (not a heart). Reconnect = one bloom (unchanged; owner loved it) | |
| Idle | calmer than now: slow breathing, very little twinkle | busy sparkle |
| Play | a brief motion between two idle creatures: drift together, one short twirl or orbit, part | beads, bridges, motes, colour exchange, anything that looks like data moving |
| Labels (gallery only) | small, quiet, ABOVE the creature. Deployment shows no labels | |

Scales: rx/tx in Mbit/s per session (0.02 idle .. ~25 heavy); machine-wide `S.net.mbps` is their sum.
`S.net.strain` 0..1 is machine-wide (the link can't keep up); show it on the sessions that are moving data.

## Interaction (owner, 2026-10-31)
"I don't think they even need text names to be honest. Perhaps if the cursor hovers over them then they
mostly-freeze and display their name, and if you click on them it takes you to the Space where that Claude
session is and brings it to the front."
- No names by default. Hover: the creature nearly freezes (motion slows to ~10%) and shows its project name.
- Click: switch to the Space holding that session's terminal window and bring it to front.
- Implication for the native overlay: the panel cannot be fully click-through. It must pass clicks through
  everywhere EXCEPT a creature's hit area (per-creature hit testing, e.g. toggle ignoresMouseEvents on
  mouse-move proximity, or tiny per-creature panels). Session -> window mapping: pid (now.json /
  ~/.claude/sessions/<pid>.json) -> parent iTerm2 tab/window; activating it switches Space.
