# Augur pilot 1: machine + sessions, write-only, measured

Record of the pilot-1 checks in DESIGN.md section 12, run on the Laptop (mt-AAAAAA) on
2026-10-31 and 2026-11-01. In-session results are below. The 24 h items are pending, each with the
command that settles it.

## What runs

- LaunchAgent `com.mandrake.augur`: `/usr/bin/nice -n 10 ~/agent-storage/python/py
  ~/dev/MandrakeWorkflows/augur/bin/augurd.py`, `ProcessType Standard`, `LowPriorityIO`, bare
  `PATH`, `AUGUR_HOME=~/agent-storage/augur`. Installed with `augur/bin/install.sh` (`--remove`
  undoes it). Logs are `~/Library/Logs/augur.err` and `~/Library/Logs/augur.log`.
- It writes `~/agent-storage/augur/live/snapshot.json` (0644) every 2 s, atomically. It also writes
  `samples/snap-<date>.jsonl` (one snapshot a minute), `audit.jsonl` (0600, the falsifier
  counters) and `cost.jsonl` (10 min and 1 h lines).
- Collectors:
  - fast tier: cpu, memory, net (with vpn), attention.
  - agents tier: sessions; session_net on its own 15 s period.
  - probes tier: thermal, power, strain, path.
  - counts tier: lodestar_burning (pulled forward from pilot 2, ticket
    AUGUR_WIRE_LODESTAR_BURNING_COUNTS).
- Checker: `/usr/bin/python3 augur/bin/pilot1_check.py validate|cost|stale|off|pair|nettop|groundtruth|all`.
  It exits 0 on pass, 1 on fail and 2 when there is not enough data yet.

## In-session results

| Check (DESIGN section 12) | Bar | Result | Verdict |
|---|---|---|---|
| Every written snapshot validates | 0 errors | 40 minute samples + live file over 38 min, 0 errors, 0 privacy hits (`@` outside ids, `/Users/`, IPv4) | pass so far |
| Cost verdict | pass in >= 22 of 24 h | First 10 min window after the fixes: 0.56 % of one core (1 h basis), RSS 28.6 MB, 204 spawns/h, no fast tick late > 1 s; verdict `pass` | pass so far (24 h pending) |
| `kill -STOP` makes the file stale | <= 10 s | 9.42 s; fresh again after SIGCONT | pass |
| Off file gives `off: true` | <= 5 s | 1.79 s; back on 2.29 s after removal | pass |
| Per-session procs and cpu_cores vs hostrec rows | >= 95 % within ±10 % | procs 76 % within ±10 %, cpu 44 % within ±10 % or 0.02 cores (88 pairs, 15 min) | fails against hostrec, **but hostrec is the wrong yardstick**: see "Which CPU number is right" below. Replaced by the ground-truth test. |
| Ground truth instead (controlled busy loops) | ±10 % (±15 % reaped children); procs exact >= 90 % | +1 core: mean +0.988 (4/4 in band). +2 cores: 1.90-2.01 (9/9). Short-lived children: 0.382 against 0.376-0.397 true (4/4, clean run). procs 76/81 exact (94 %), every miss a birth or death inside the tick. mem_gb within 1 MB mean | pass |
| machine.net vs the interface's own counters, 60 s | ±10 % | rx 1.019, tx 1.063 of the en0 byte-counter rate | pass |
| Falsifier: per-session nettop bytes > interface bytes | must not trip | sessions 266.9 MB vs interface 377.1 MB, ratio 0.708 (rx 0.188, tx 0.787) over ~45 min | not tripped |
| Falsifier: cost over 1 % in the at-work day | must not trip | 1.24 % before the fixes, 0.56 % after | pending 24 h |
| Falsifier: tasks heuristic vs hand count of 10 moments | <= 1 in 3 off by more than 1 | needs the owner's hand count | pending (owner) |

Raw files:
- `~/agent-storage/augur/pair-hostrec-2.jsonl`
- `~/agent-storage/augur/scratch/groundtruth/` (`results_run2.json`, `gt.py`)
- `~/agent-storage/augur/scratch/net_truth.py`

### After review R1 (2026-11-01): ground truth re-run pending, load-test gate

Review R1's fixes changed how per-session CPU is attributed (nested sessions, orphans, gone-pid
credits; commits ed1e598..d2a2929). The busy-loop numbers above were measured before those fixes.
**The re-run is pending, and was deliberately not done today:** load testing may only happen
on a trusted on-site network without the VPN. The checker enforces this from Augur's own `machine.vpn`: it runs only when `on_site` is true
and `state` is `down` in a non-stale snapshot, and refuses on anything else, unknown included.

```
/usr/bin/python3 augur/bin/pilot1_check.py groundtruth --root <session root pid>   # refuses off on-site network or with the VPN up
```

Until it can run, what was verified without load instead:
- Synthetic process trees with known CPU per session (`augur/tests/test_session_attribution.py`):
  a nested session's exit reads 0.0 on its parent (truth 0; before the fix 24.0), and an orphaned
  worker's tick reads 0.7 (truth 0.7; before the fix 0.0).
- The live producer, restarted on d2a2929: the live file validates (0 schema errors, 0 privacy
  hits), the last 60 minute samples validate (coverage 0.98), and the cost verdict reads `pass`.

- Restarted again on e5e6c30 (adds `machine.api`), 06:27: 0 schema errors, 0 privacy hits,
  `machine.api` reads `ok`, cost `pass` at 0.61 % of one core (60 s). The probes line now reads
  0.15 %, where it read 0.0075 % before finding 8's fix: the strain burst's CPU is finally on its line.

**Re-run done 2026-11-04 09:17 on campus (run3, root = a live Claude session, nice 19).** The gate
read `on_site` true, VPN `down`, default route en0 at all 33 five-second checks; the VPN never came
up. The 1-min load average was 32 to 42 from other work, against 23 to 36 in the earlier runs.
- +1 core: mean +0.953 (0.946 to 0.958), 4/4 in band. Pass.
- +2 cores: mean +1.984 (1.983 to 1.984), 3/3 in band. Pass.
- 239 short-lived children, true 0.398 cores: 0.364, 0.382, 0.411, 0.519, so 3/4 in ±15 %. The
  0.519 reading (+30 %) is one tick. Marginal.
- procs exact: 23/26 (88 %) against the 90 % bar, off by one in the other 3. Marginal.
- memory: mean difference -0.0001 GB, maximum 0.0011 GB. Pass.
Nested and orphaned attribution is not exercised by this busy loop; the synthetic tests cover it
(`augur/tests/test_session_attribution.py`, 24 pass). Raw: `~/agent-storage/augur/scratch/groundtruth/results_run3.json`.

The 24 h job (`check24h`) runs only `validate`, `cost` and `nettop`. These read files and add no
load, so the gate does not apply to it.

### After reviews R2 and R3 (2026-11-01): the CPU gap is settled, machine.api has a probe

- **The per-session CPU gap against `ps` is settled: it is not phantom.** Review R3 ran an
  independent ledger passively for 123 s on session 89071. It counted own plus reaped-child CPU
  per pid, with dead pids' last totals subtracted at their reap. Result: ledger 12.01 CPU-s,
  Augur 11.92, `ps` (live processes only) 3.91. The mean per-interval difference Augur minus the
  ledger was +0.002 cores, the maximum 0.051, and no tick went negative. The gap to `ps` is the
  CPU of children that have exited, which `ps` cannot see. Limit: the ledger reads the same kernel
  counters, so it checks Augur's transfer arithmetic, not the kernel. An outside scheduler trace
  would add load, so it was not done.
- **machine.api latency.** Claude Code retries a failing call silently for about 3 min (median
  182 s, 49 incidents) before it writes the error line. While a session is busy, Augur therefore
  also TCP-connects to the API host and port from `ANTHROPIC_BASE_URL`, read at call time. It
  probes every 15 s while good calls are flowing, and every tick once the transcript has been
  silent for 6 s. Each probe is bounded at 5 s, DNS included. Two failed probes read `failing`
  (`network`) within about 10 s. A good probe never clears a failure the transcript recorded; only
  a later good call does, at most 10 min later. A missing `ANTHROPIC_BASE_URL` reads
  `unknown: env_missing` and is logged once.

### Fixes the pilot forced

1. **CPU undercount (f6e14f7).** Augur first counted only processes seen in two consecutive
   sweeps. A Claude session's work is mostly short-lived children (git, the Bash tool's commands,
   compilers), which are born and reaped between sweeps. Their CPU lands in the parent's
   "children" time, and Augur now counts that time. During a Swift build the old formula read
   0.01 cores and the new one 0.98.
2. **Cost (d9a21f3, 18b75c0, b8490ce).** Augur first cost 1.24 % of one core against a 1.0 % budget.
   - The cause was `ProcessType Background`: it ran the whole process, and its nettop children, at
     Darwin-BG priority 4. Each nettop exec then cost ~42 ms of CPU, against ~12 ms from a terminal.
     The band is now Standard + nice 10.
   - session_net moved to a 15 s period.
   - The sessions sweep now reads only session trees (90 libproc calls instead of 4,550).
   - `if_indextoname` is cached.
   - The result is 0.56 %.

## Which CPU number is right, in plain words

**Augur's per-session number is right.** It was checked against a known load, not against the
other collectors. A child process told to burn exactly one core raised Augur's reading by 0.99
cores. Two raised it by 1.90 to 2.01. Hundreds of short-lived children, which the other collectors
cannot see, were counted within 4 % of the CPU the parent was billed for them.

The three collectors disagreed in both directions because each one measures something different:

- **hostrec (Companion) reads too low** (0.04 against Augur's 0.13 to 0.17). It counts only the CPU
  of processes alive at both ends of its 10 s tick. The work of every tool command that starts and
  finishes inside the tick is lost.
- **SidePulse Resources reads about half the truth** (0.07 to 0.14 against a true 0.16). It also
  counts only processes it sees, though it catches a few more with a 1 s table.
  - It smooths over 10 s, so it lags and swings.
  - The earlier "0.29 against 0.055" came from comparing it with Augur's old formula, which had the
    same blind spot and an unsmoothed 5 s window.
- **`ps %cpu` (0.05) is lower still.** It is a decaying average of live processes only.

**The machine-wide figure is not 10x too high.** All three old collectors compute it the same
correct way, from the kernel's CPU tick counters. They agree with Augur and `top` to within about
10 %: 2.6 to 2.7 busy cores of 10 at the time measured. What does look 10x high is **load average**
(`sysctl vm.loadavg`: 8 to 10 now, 87 to 115 in normal work, per load_levels' notes). On macOS that
number counts every runnable thread, Electron helpers included. It is not CPU and no collector uses
it as an input. A tile or tool that shows load average as "load" will look 10x off.

## Shadow findings (SidePulse and Companion readers), explained

- **`strain.background_level` absent (81 of 81 rows): by design, not a bug.** load_levels'
  background-QoS probe is a compiled child binary that Augur does not run in pilot 1. DESIGN.md
  section 3 now says so. The comparators should treat it as "not supplied", not as a mismatch.
- **tx differs (33 and 41 rows).** Augur's tx matches the interface's own byte counters
  (1.06x over 60 s). Upload traffic here comes in bursts, and Augur's 2 s window is set against the
  readers' 10 s windows. Not investigated further: the cause could also be hostrec's tx including
  the tunnel interface.
- **cpu level 3 of 6, delay level 11, dly 43 (Companion).** Augur's strain ladder keeps its own
  state, as DESIGN section 10 requires, and fires its own 20 ms burst at a different moment. Levels
  near a threshold may differ by one step, and `dly` medians come from different samples. Expected
  until the old ladder is retired. Then there is only one ladder.
- **procs 3 of 5, 30 rows (Companion).** Against ground truth Augur is exact 94 % of the time, and
  off by one only when a shell starts or ends inside the tick.
- **agents.state 39 of 53 (Companion).** The Companion says `running` where Augur says `stopped`
  or `working`. Augur's states come from the SidePulse hook slots. The mapping is a reader
  decision: stopped = finished a turn, not waiting on him.

## What the consumers read that Augur does not yet supply

From the readers' code and the shadow logs (the reader tickets name no schema gaps):

| Consumer | Field | Status |
|---|---|---|
| hostrec | `levels.background_level` (bg-QoS probe) | not supplied (by design in pilot 1) |
| hostrec | launch-time probe (`launch`, `launches`, `launch_path`) | not supplied: DESIGN keeps it in the Companion (a spawn timer, not a level) |
| hostrec | per-app CPU groups (`now` rows, candidates, watchlist, restrict, actions) | not supplied: Augur measures Claude trees only |
| hostrec | history (`raw`, `roll6h`), `stall_ms`, `thru` | not supplied: Augur holds no history (the readers keep their own ring) |
| SidePulse | net peak / utilisation | computed in the reader from machine.net (fine) |
| both | per-project `tickets_open`, `open`, `waiting` | pilot 2 (absent today) |

**Retiring hostrec's measuring code therefore removes features that no other code supplies:**
per-app attribution, the launch probe and the background probe. Only its session, network, path
and level parts are covered.

## Pending 24 h checks (run after 2026-11-01 23:59)

```
cd ~/dev/MandrakeWorkflows/augur
/usr/bin/python3 bin/pilot1_check.py validate --since-hours 24   # every minute validates, coverage >= 95 %
/usr/bin/python3 bin/pilot1_check.py cost --since-hours 24       # pass in >= 22 of 24 hourly windows
/usr/bin/python3 bin/pilot1_check.py nettop --since-hours 24     # falsifier must stay untripped
/usr/bin/python3 bin/pilot1_check.py all --since-hours 24        # all three, summary block
```

DESIGN asks for 24 h at rest and 24 h at work. The at-work day is the cost falsifier.

**These run by themselves.** The LaunchAgent `com.mandrake.augur.check24h` (installed with
`AUGUR_LABEL=com.mandrake.augur.check24h augur/bin/install.sh`) runs `augur/bin/scheduled_check.sh 24`
every day at 00:15. Each run writes `~/agent-storage/augur/checks/pilot1-<stamp>.txt` and appends one
line to `checks/index.jsonl` (verdict pass, fail or pending). The first full 24 h window closes at
00:15 on 2026-11-02. Once a run reads pass or fail, it writes `checks/pilot1-24h.done` and later runs
do nothing; a pending run leaves it armed. Remove it with
`AUGUR_LABEL=com.mandrake.augur.check24h augur/bin/install.sh --remove`.

### RSS creep after the 18:43 restart (2026-11-02): settling, not a leak

The 10m `rss_mb` went 37.9 (19:03) to 39.1 (19:53), sat at 39.2-39.3 from 20:03 to 23:53, stepped
once to 39.6 at the 00:03 day rollover (first run of the log-retention path), then 39.6-39.7 to
02:34: steps at first-run code paths, flat between them, not a slope. Every per-pid, per-session and
per-path map was read and each is pruned against a live set each collect (sessions.py:572 `_prune`,
:661, :689, :731, :1009-1019; api.py:519, :650-666, :695, :743; tickets.py:105; native.py:259 caps
`_IFNAME`); the deques in core.py:306-315 are cut to the hour. `vmmap --summary` on pid 85902 at
02:4x: physical footprint 20.4 MB (peak 22.9 MB), malloc zone 15.9 MB resident, 44 % fragmented.
The budget reads `ri_resident_size` (core.py:92), which also counts clean shared pages (dylibs,
Python text), so it sits ~19 MB above the dirty footprint. Budget not raised. Risk: 0.3 MB headroom,
so one more first-run step can still print `watch`; the test is a footprint that keeps rising across
two more days, which would reopen this.

## Bandwidth strain: the owner's labelled week (pilot 2, not started)

`machine.bandwidth` stays **absent** until this passes (DESIGN section 5). It needs you, because the
only ground truth is how the network feels.

1. For one working week, whenever the network feels slow, run
   `python3 ~/dev/Lodestar/bin/ticket.py edit AUGUR_BUILD_PRODUCER --note "slow"`. When it has felt
   fine all day, note `fine` once at the end of the day.
2. After the week, an agent builds the strain score from the samples (send queue, retransmits, RTT
   inflation, path loss; DESIGN section 5) and scores it against your notes.
3. **Bar:** strain must be above 0.5 in at least 4 of 5 of your "slow" moments, and under 0.2 in
   95 % of the minutes on the days you called fine.
4. If either part fails, the key stays absent. The scale points are retuned only on a new labelled
   week, never on the same one.
