# What Sprites needs from a data feed (for Augur, 2026-10-31)

Sprites only displays; it gathers nothing. This is the consumer side, so a producer's contract can be mapped
onto it. Today's placeholder shape is in SHIP_PLAN.md ("Data contract"); the conversion lives in ONE adapter
in `app/stage.html`, so any contract with these meanings can replace it there and nowhere else.

## Per Claude session (one sprite each)
| Need | Meaning, unit | Drives | Freshness wanted |
|---|---|---|---|
| id, pid | stable session key; pid lets a click find the terminal | identity, click-to-session | on change |
| project | repo/project name (matches Waypoint names when it can) | species, variant, colour, hover name | on change |
| state | working / idle / needs-you | brightness; needs-you approach + ripples | seconds (hook-driven ideal) |
| cpu | cores in use (0..~4+) | internal tempo | 5-15 s |
| mem | footprint, GB | body size | 15-60 s |
| tasks | Claude background shells + subagents running (OS process count is a fallback) | satellites | seconds-15 s |
| rx, tx | this session's download / upload, Mbit/s | inward / outward pulses | 5-15 s |

## Machine-wide
| Need | Meaning | Drives |
|---|---|---|
| strain level | continuous 0 light .. 3 danger (CPU, scheduling delay) | red glow + disalignment |
| thermal, memory pressure | 0..2 each | adds to strain |
| bandwidth strain | 0..1: the link cannot keep up with what is being asked | pulses jam |
| vpn | VPN up / down | huddle, searchlight, red beacon |
| total rx/tx | Mbit/s | fallback when per-session rx/tx is unknown |

## Per project (pending design, BURNING_CONCEPTS.md)
| Need | Meaning |
|---|---|
| burning | count of Burning items attributed to the project (+ tier red/amber) |
| todos | count of open filed to-dos (tickets) |

## Known gaps today (filed as Lodestar tickets)
- per-session rx/tx is not attributable (NETWATCH_MEASURE_SESSION_TRAFFIC)
- bandwidth strain has no real signal (NETWATCH_MEASURE_BANDWIDTH_STRAIN)
- Claude background tasks are not counted (SIDEPULSE_MEASURE_BACKGROUND_TASKS)
- Burning items carry account codes (A1, B2), not repo names: a code -> project map is needed

## Delivery preferences
A file rewritten atomically (tmp + rename) or a local socket; any cadence; missing fields must be absent,
not zero (Sprites shows "unknown" as calm, never as idle-looking data). Units stated in the contract.
