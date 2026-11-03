# Universal channels for Visitors (design study, 2026-10-31)

Answers the owner R1 ask; extends `GRAMMAR_V2.md`.

## What is measurable, and at what scope
From `~/dev/.lodestar/companion/host-trace.json` (19:12).

| Datum | Per session | Machine-wide | Caveat |
|---|---|---|---|
| Memory | yes: `claude.rows[].fp`, footprint of the Claude tree | `memory.three.available` (45%), kernel pressure 1..4, swap-out | |
| CPU | yes: CPU-s/s per tree | busy cores, scheduling delay `dly` | |
| Background tasks | only process count `n` per tree (2-6 now) | | `n` counts MCP servers and helpers, not Claude's background shells or subagents |
| rx / tx | weak: nettop top-5 with `claude_project`, sampled only while the link is busy | `rx_bps`, `tx_bps` | all 5 talkers `claude_project: null`; on VPN the VPN client carries the bytes, hiding sessions. Absent is not zero |
| Bandwidth strain | no | partial | `available` is a lower bound on delivered rate, so need/available is 1 by construction (10.38 vs 10.38 Mbit/s). Real evidence: send-queue backlog (129 KB), path RTT/loss; throughput probe UNMEASURED on VPN |
| Machine strain | no | yes: cpu/delay levels, pressure, swap-out, `thermal` (0), low power | |

So per-session data differ between creatures; machine-wide data move all creatures alike (common fate,
motion.10), reading as weather. Net strain cannot honestly be pinned to sessions "moving data" yet.

## Options per datum
Peripheral = preattentive strength off-fovea; Calm = all-day tolerance; H/M/L.

| Datum | Option (creature-agnostic idiom) | Peripheral | Calm | Owner fit | |
|---|---|---|---|---|---|
| Memory | M1 body area, area-proportional | M | H | H | Rec |
| | M2 density of lit elements | M | M | M | |
| | M3 halo radius | M | H | L | |
| CPU | C1 tempo of the shape's own rotation/chase | M | M | H | Rec |
| | C2 twinkle rate of internal lights | H | L | M | |
| | C3 number of internal lights lit | L | H | M | |
| Background tasks | T1 count of discrete satellites, slow constant orbit | M | H | H (read as processes) | Rec |
| | T2 count of appendages (tentacles, petals, rays) | M | H | H for Siphon only | alt |
| | T3 ring beads | L | H | M | |
| Bandwidth in | B1 pulses rim to core, rate/brightness log scale | H | M | H | Rec |
| | B2 core fill brightness breathing | L | H | M | |
| | B3 contraction wave along the contour | M | M | M | |
| Bandwidth out | B1-B3 mirrored, core to rim | | | | Rec |
| Bandwidth strain | S1 jam: pulses stall, bunch into a bright band | H | M | H | Rec |
| | S2 stutter: irregular pulse rhythm | H | L | M | |
| | S3 throat narrows | M | H | M | Rec, with S1 |
| Machine strain | X1 red ember glow behind/inside + geometric noise | H | M | H (both likes) | Rec |
| | X2 heat shimmer, desaturation | M | M | L | |
| | X3 tremor of drift | H | L | M | |

## Separability of the recommended set
`watch` = separable only under the rules below.

| | M1 area | C1 tempo | T1 satellites | B1 in | B1 out | S1+S3 jam | X1 red+noise |
|---|---|---|---|---|---|---|---|
| M1 area | | ok | ok | ok | ok | ok | watch: noise keeps area |
| C1 tempo | | | watch: fixed orbit | watch: angular vs radial | watch | watch: jam irregular, tempo regular | watch: spatial vs temporal |
| T1 satellites | | | | ok | ok | ok | ok |
| B1 in | | | | | watch: direction, not tint | ok | ok |
| B1 out | | | | | | ok | clash if gold: gold, amber identity and red share a ramp (COLOR-06) |
| S1+S3 jam | | | | | | | ok: no red |
| X1 red+noise | | | | | | | |

Rules: CPU is angular, bandwidth radial, so they never share a motion axis (motion.11). Satellite orbit
speed is fixed. Out-pulses are pale neutral, never gold; direction carries in/out, tint is redundant
(ACCESS-01). Red belongs to machine strain alone.

## Principles behind the ranking
- ENC-01 relaxes (`magnitude_reading_not_required`): readings are ordinal; ENC-03, no exact GB from area.
- ENC-07: satellites are whole things, so they suit counts; past about 4, cluster them (motion.10).
- motion.15, motion.14: motion grabs the periphery; idle near-still, every motion a datum (why C2, X3 rank low).
- motion.18: pulses stay under 3/s at 25 Mbit/s; the log scale caps.
- MEDIA-05: seven data exceed the three-property guide; defensible because both strains are shared and rare.
- COLOR-06: hue is identity, red is machine strain, nothing else.

## Recommended set
M1 area; C1 rotational tempo; T1 satellites (T2 for Siphon); B1 radial pulses, direction-coded, neutral
tint; S1 jam plus S3 narrowing and X1 red glow plus geometric noise, both on all creatures alike. Data gaps
first: per-session rx/tx attribution, and net strain from send-queue backlog and path loss.

## Questions for the owner
1. "Background processes": OS processes in the tree (measured, includes MCP servers), or Claude's background
   shells and subagents (unmeasured)?
2. Bandwidth strain is machine-wide: on every creature, only on ones with attributed traffic, or as shared haze?
3. Machine-strain red: identical everywhere, or weighted by each session's CPU/memory share (`who` supports it)?
4. Give up gold out-pulses, carrying in/out by direction alone?
5. Satellites past 4: exact count, or "few vs many" clustered?
