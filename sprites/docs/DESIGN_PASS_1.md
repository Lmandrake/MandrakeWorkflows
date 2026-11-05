# Visitors (working name) — design pass 1, 2026-10-31

Small, luminous, mostly transparent light-creatures, one per open Claude Code session, that drift
on every Space, keep away from the focused window, play with each other, and encode real load.
Lineage: SidePulse (8 LEDs = sessions), Lodestar Companion (all-Spaces click-through panel), the
MandrakeVisualize/visual-beautiful stack (truth floor, BEAUTIFUL pole, motion lessons).

## Ground rules carried in from MandrakeVisualize
- **Motion must BE the message** (owner, motion study 2026-10-28): motion that carries no state
  change was "just fluff". So every behaviour below is bound to a datum; idle drift is the only
  data-free motion, and it is slow enough to read as "nothing is happening".
- **Model judges cannot proxy a viewer of motion** (same study, ceiling at 95-98%). GPT stills are
  for taste only; behaviour gets judged by the owner watching a live prototype.
- **visual-beautiful truth floor**: a disclosed mapping (a legend/"colophon" on hover-modifier),
  no undeclared glow that reads as load, low end never vanishes into black (an idle Visitor is dim,
  not invisible).
- Rate each concept on clarity 1-7 and beauty 1-7 separately, never summed.

## Data channels (all already collected; poll, never gather)
| Datum | Source | Channel on the creature |
|---|---|---|
| session alive, project, colour | `~/dev/.lodestar/companion/now.json` `plots.agents.segments[]` | existence; hue family = project colour |
| working / needs-you / done | `~/agent-storage/sidepulse/state.json` (hook-driven, freshest) | needs-you = it approaches and "knocks" near the dock/menu bar, gentle |
| CPU cores per session | `host-trace.json` `sessions[].cpu` | pulse rate / internal spin speed |
| footprint (RSS) | `host-trace.json` `sessions[].footprint` | body size / lit-pixel count |
| process tree count `procs` (proxy for bg tasks) | `host-trace.json` | orbiting satellites |
| machine CPU level, stall, thermal, memory pressure | `host-trace.json` `levels`, `status`, `answers.memory` | collective agitation: jitter, speed, colour temperature, flocking tightness |
| network rx/tx, path RTT/loss | `host-trace.json` `answers.network` | sparkle/particle flow between creatures and screen edge |
| VPN / on-site reachability | `lib/netwatch.py` utun detection, `ssid.json` | the "lost mothership" behaviour (below) |

Gaps to fill (small, in Lodestar, not in the pets): per-session subagent/background-task count
(the hook already sees `Task` tool calls), per-session context %/tokens (transcript JSONL), per-session
net bytes (null today), battery %, focused-window rect (new: `CGWindowListCopyWindowInfo` in the app).

## Behaviour grammar (shared by all five concepts)
- **Drift**: curl-noise flow field + Reynolds steering; repulsion field from the focused window rect,
  weaker repulsion from the cursor; soft attraction to screen margins. ~4-10 px/s idle.
- **Bursts**: a tool call or a CPU jump = a short dart (1-2 s) then settle. Sparse, so they read.
- **Play**: two idle Visitors that drift close may "dance" (orbit each other, swap a few motes,
  sync colour). Higher chance when both sessions share a project or a parent.
- **Strain**: machine level light→danger maps the whole flock from serene → restless → frantic:
  faster, jittery, colour heating toward white-orange, lights strobing out of sync.
- **Lost VPN**: unmistakable and distinct from strain: lights drain to cold blue-grey, the flock
  huddles, one red heartbeat blink, a slow searching beam sweeps the sky; on reconnect, a
  joyful bloom and scatter (the only "celebration" in the grammar).
- **Birth / death**: session start = materialise from a twinkle; session end = rise and fade
  upward like a departing craft.
- **Hide**: vanish during screen share / presentation (sharingType .none + DND/presenting check).

## Five concepts (renders in `renders/`)
1. **Mothership Choir** (`c1_choir.png`, mood sheet `s1_states.png`) — each Visitor a ring of
   jewel LEDs round a glass core; lights chase at CPU speed; lit count = memory; satellites = tasks.
   Interaction: call-and-response colour chords (Close Encounters five tones, literally).
2. **Siphonophores** (`c2_jelly.png`, `s2_states.png`) — dot-matrix jelly bells, tentacles of
   pixel beads; bead packets descending = network traffic; tentacle count = tasks; bell pulse = CPU.
   Interaction: tentacles entwine.
3. **Living Sigils** (`c3_sigils.png`) — 7x7 LED glyph per session, a cellular automaton whose rule
   is seeded by the project; generations tick per tool call (the glyph literally evolves as it works);
   orbiting pixels = tasks. Most 8-bit, cheapest to render, most "readable" identity.
4. **Kaleidoscope Seeds** (`c4_mandala.png`) — n-fold mandalas; symmetry order = something stable
   (e.g. project), ring count = memory, rotation = CPU, moire shimmer = network.
   Interaction: rings interlock like gears.
5. **Firefly Murmurations** (`c5_swarm.png`) — a boids swarm per session; mote count = memory,
   swarm speed/cohesion = CPU, comet streams between swarms = shared work. Most "alive", most
   organic, most expensive in particles.
Scene: `c6_vpnloss.png` = the lost-VPN behaviour.

## Names (see the reply for the full list and favourites)
Shortlist: Visitors, Emissaries, Wisps, Lumen, Motes, Envoys, Heralds, Sprites, Glimmers, Kin.
Research: `research/REPORT.md`. Contact sheet: `CONTACT_SHEET.png`.
