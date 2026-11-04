# Augur: one shared machine-state snapshot (design, 2026-10-31)

Augur is one small macOS background producer. It measures the Mac once and writes one versioned
snapshot file. Three consumers read that file instead of each measuring on its own:

- **Lodestar Companion**: `~/dev/Lodestar/bin/companion.py` writes `now.json`, and its HOST recorder
  (`bin/lib/hostrec.py`) writes `host-trace.json`.
- **The SidePulse LED card**: `~/dev/SidePulse`, driven by the runners `~/dev/Lodestar/bin/sidepulse_*.py`.
- **Sprites**, the desktop creatures (the Visitors study, renamed Sprites):
  `~/dev/MandrakeWorkflows/sprites/`.

Owner decisions are in `~/dev/Lodestar/tickets/WATCH_BUILD_SHARED_MACHINE_STATE_PRODUCER.md`. Every
decision below either carries one of them out or is marked as a proposal.

Built and live as LaunchAgent `com.mandrake.augur` (pilot 1 since 2026-11-01). Schema:
`augur/schema/snapshot.schema.json` (version **1.1**; 1.1 added `sessions_at`,
`sessions[].tasks.background` and `projects[].counts.as_of`, and named the keys 1.0 builds already
wrote: `machine.api`, `tasks.bg_shells`, `tasks.other`, `load.method`). Worked example: `augur/schema/example.json`, which validates against the schema.

## 0. What this replaces, and the cost today

Three LaunchAgents measure the same machine at once. Their CPU since boot was read with `ps` on
mt-AAAAAA at 2026-10-31 21:5x, over 2 d 06 h of uptime:

| Process | CPU time | Share of one core |
|---|---|---|
| `sidepulse_sparkle.py --intensity` | 21 min 49 s | ~0.67 % |
| `companion.py collect` (incl. hostrec, 4 h 42 min run) | 6 min 27 s | ~2.3 % |
| `sidepulse_resources.py` (idle: mode is `sparkle`) | 52 s | ~0.03 % |
| `sidepulse_clarity.py` (idle) | 51 s | ~0.03 % |
| `sidepulsed.py serve` (card driver, stays) | 2 min 57 s | ~0.09 % |

`load_levels.current()` already shares one load timeline across these processes through a file and
a lock. Process trees, network counters and session state are still read separately by each one.
Augur measures each thing once. The Companion keeps everything that is not a measurement: Burning,
Orders, drafts, Bearing tiles and spend.

## 1. Rules (settled)

1. **A field with no source is absent, never zero.** The owner settled this on 2026-10-31. Zero
   reads as "nothing there", and a creature or LED drawn from a false zero looks calm and idle when
   the truth is "we cannot see". The rule covers:
   - Lodestar-derived project counts when Lodestar is missing or unreadable. This replaces the
     ticket's earlier "zero/unknown": they are now absent.
   - Per-session rx/tx when flow accounting is off or failed.
   - Bandwidth strain until it is validated.
   - Any key with no source on this platform or machine, for example battery on the Desktop.
2. **Failed is not the same as absent.** Each measured group is a *Signal* object stamped with
   `observed_at` and `valid_until`.
   - If the source exists but this reading failed, the Signal carries `unknown: "<reason>"` and no
     value keys.
   - Past `valid_until`, a reader treats the whole Signal as unknown. It never shows the last value.
   - `valid_until` = `observed_at` + 2.5 x that tier's cadence (5 s for fast, 12.5 s for agents,
     37.5 s for probes, 150 s for counts).
   - The file has its own top-level `valid_until` = `written_at` + 5 x the fast cadence. If the
     producer is dead or asleep, everything reads unknown within ~10 s.
3. **Levels and counts only.** The shared file never holds titles, senders, subjects, session
   names, command lines, remote addresses or SSIDs.
   - A project name is a repo or registry name, which the Companion's `now.json` already carries.
   - A burning item becomes a count per project and tier. Its own `project` field is never copied.
4. **Augur works without Lodestar.** Every Lodestar input is optional and read-only. Augur imports
   no Lodestar module at runtime: it vendors the few pure readers it needs (section 4). Without
   Lodestar it still writes machine and session data. The `lodestar` project entry is still present,
   with its `counts` absent.
5. **Measure once, then cut.** No collector ships on by default until its own cost has been
   measured and passes the budget in section 6.

## 2. Cadence tiers

| Tier | Period | What it reads | Why this period |
|---|---|---|---|
| fast | 2 s | CPU ticks, VM counters + pressure, interface bytes, default routes (VPN), attention state from hook files | Each read costs microseconds to under 0.5 ms (measured). The SidePulse display ticks at 2 s today. |
| agents | 5 s | One libproc sweep: every pid's BSD info, parent, path. Claude roots, trees, rusage (CPU, footprint, runnable time), shells/subagents, per-session flows (one `nettop` exec) | The sweep took 2.4 ms + 2.9 ms over ~920 pids, measured. The nettop exec is the cost here (section 5). |
| probes | 15 s | Scheduling-delay burst (20 ms at UTILITY QoS, median of 5), thermal + low power + battery, TCP send-queue (one `netstat`, pilot 2 only) | The burst costs 20 ms of CPU by design. Path echoes keep netwatch's own 10 s worker cadence. |
| counts | 60 s | Lodestar feeds (registry, `whatnow.json`, `now.json` burning block, ticket headers), with mtime caching | They change over minutes to days. The ticket headers are the one costly read (63 ms for 377 files, measured cold), so they are cached by mtime. |

Every Sprites signal arrives within ~15 s, as the ticket requires. Attention, CPU, memory, rx/tx and
VPN arrive within 2 s. Per-session values arrive within 5 s, strain and path within 15 s, counts
within 60 s.

**Battery rule (Laptop):**
- On battery: fast becomes 5 s, agents 15 s, probes 30 s.
- In Low Power Mode: probes stop. Strain then reads unknown `disabled`, not light.

## 3. The snapshot, field by field

The full contract is the schema. This is a summary.

- **machine.**
  - `cpu`: busy_pct, cores_busy, ncpu.
  - `memory`: pressure 0..2, available_pct, swap_out_per_s.
  - `thermal`: state 0..3, low_power.
  - `strain`: the five load levels, a continuous `score` 0..4, sched_delay_x, agent_wait_s_per_s.
  - `net`: rx/tx Mbit/s of the physical default-route interface.
  - `vpn`: up or down, on_site, changed_at.
  - `path`: ok/degraded/bad, rtt, loss.
  - `bandwidth`: strain 0..1, absent for now.
  - `power`: Laptop only.
  - `api`: ok / failing with `error_kind`, from the session transcripts plus a reachability probe
    (section 3 machine table).
- **sessions[]**: one entry per live Claude Code session.
  - Identity: `id` = `pid@start` (a reused pid never inherits a session), pid, project,
    project_key, managed.
  - Signals: `attention`, `load` (cpu_cores, mem_gb, procs, wait_s_per_s, starved), `tasks` and
    `net`. `tasks` keys: `shells` (every live Bash-tool shell), `bg_shells` (those whose stdout
    is a harness task file, i.e. `run_in_background`), `subagents`, `other` (orphaned workers the
    session launched), `total` = shells + subagents (the 1.0 meaning, kept), and `background`
    (1.1) = bg_shells + subagents + other, the dot count. `background` is absent when any part
    is unmeasured; readers never fall back to `total` or `load.procs`.
- **sessions_at** (1.1): the list's own stamp. When it carries `unknown` (the sweep raised, was
  switched off or cut, or is warming up) or is past `valid_until`, `sessions` is unmeasured, not
  empty: the producer then publishes `[]`, never the previous rows (C3, R5 RB2), and readers must
  not read it as "no sessions" or "0 Claude CPU".
- **projects[]**: the `lodestar` entry, always present. Plus every project with a live session.
  Plus every managed project with a non-zero count. `counts` holds burning (and per tier),
  tickets_open, open, waiting and unmapped_burning, with a `basis` string. Its `observed_at` is
  when Augur read the sources; `as_of` (1.1) is the oldest input's own time (the burning view's
  `built_at`, the homes-cache time, whatnow's `built_at`), which can be hours older (C4).
- **cost**: Augur's own meter (section 6). It is published so that consumers and tests can hold
  Augur to its budget.

### Per agent (each Claude Code session)

How a session is found:
1. A process whose `proc_pidpath` contains `/claude/versions/` is a root.
2. The root is matched to `~/.claude/sessions/<pid>.json` by procStart, within ±2 s. This is the
   rule hostrec already uses.

| Field | Definition | Cost | Status |
|---|---|---|---|
| project, project_key | git toplevel of the root's cwd (`proc_pidinfo` VNODEPATHINFO, 0.035 ms/pid measured), named by the registry row when it is managed, else by basename | ~0 (cached per pid@start) | measured |
| managed | toplevel is an *active* row of `~/dev/Lodestar/sync/registry.md` (the registry is the authority). `.lodestar/managed.json` lists only the 52 enrolled checkouts and misses 20 active repos (SidePulse, MandrakeWorkflows, Atlas... measured), so it is not used. Lodestar absent = everything false. Registry unreadable = absent. | one parse per mtime | measured (rule), unbuilt |
| cpu_cores | d(user+system) / dt over the tree, `proc_pid_rusage` V4 | inside the 5 s sweep | measured (sidepulse_resources, hostrec) |
| mem_gb | sum of `ri_phys_footprint` over the tree | same | measured |
| procs | every OS process in the tree, root included | same | measured: 5 and 7 on the two sessions at 21:28 |
| tasks.shells | children of the tree whose command is `/bin/zsh -c source ~/.claude/shell-snapshots/...`. This is how the Bash tool runs, foreground and `run_in_background` alike. MCP servers (`.venv/bin/python ...`) and `caffeinate` are not counted. | `proc_pidinfo` cmdline per new pid@start only (0.3 ms for 7 pids, measured) | **heuristic, unvalidated**. It cannot tell a foreground Bash call from a background one: both are live shells. |
| tasks.subagents | transcripts under `~/.claude/projects/<slug>/<sessionId>/subagents/agent-*.jsonl` (any depth) whose last complete line is not a terminal assistant line (`end_turn` or an API error), written within 24 h; a mid-stream assistant line older than 5 min reads as cut off. Only the tail is read (at most 1 MiB). Replaced the 30 s mtime window (owner bug 2026-11-01: it dropped agents blocked on long tool calls). | one scandir per session plus a tail read per changed file | provisional; checked against the transcripts in PILOT1.md |
| tasks (exact) | `SIDEPULSE_MEASURE_BACKGROUND_TASKS`: the session hook already sees Task / `run_in_background` calls and their completions. It would publish a live count beside the attention state. Augur prefers it (`method: hook`) whenever it is present and fresh. | ~0 for Augur | **unmeasured**: needs a hook change in Lodestar |
| wait_s_per_s, starved | load_levels' runnable-wait idea per tree: max(0, d `ri_runnable_time` - d CPU) / dt. "Asking for more than it is getting" = `starved` when wait >= 0.5 s/s, held for 10 s (two agents ticks). | inside the sweep | the signal is measured (rest median 0.02 s/s, under 12 spinners ~3). **The 0.5 / 10 s threshold is a proposal.** |
| attention | `~/ClaudeWork/sidepulse/state.json` slots (hook-driven: working, needs-you, done), joined by pid. Fallback: `~/.claude/sessions/<pid>.json` `status` (busy/idle/waiting). needs_you = Notification, or a turn that ended on a question. stopped = a `done` within the last 10 min. idle = everything older. | 1 file read per fast tick (0.64 ms, measured) | measured. Without SidePulse hooks only the fallback remains, and it cannot show `stopped`. |
| net (per session) | section 5 | one `nettop` exec per 5 s | **measured as possible tonight, not yet validated** |

### Per project (from Lodestar when present)

| Count | Source | Rule |
|---|---|---|
| burning (+ red/amber/verify) | **Lodestar's own per-project burning count** (Lodestar ticket BURNING_WIRE_TO_PROJECTS, owner ruling 2026-10-31). Attributing a burning item (mail tagged with account codes such as `A1` or `B2`) to a project is Lodestar's job, not Augur's. | Augur copies the per-project count Lodestar publishes; every item Lodestar leaves unattributed is counted on the Lodestar entry as `unmapped_burning`. Augur never reads an item's `project` field and keeps no code map of its own. (Superseded 2026-10-31: the earlier rule chain of Bearing filing, then an Augur code map, then the Lodestar entry, measured 29 of 46 attributable; that work now lives in BURNING_WIRE_TO_PROJECTS.) |
| tickets_open | each project's ticket home (`sync/ticket-homes.md` via Lodestar's tickets reader), status `open` or `active` | headers cached by mtime |
| open | `~/dev/.lodestar/whatnow.json` items (Reckoning + project lists + meetings) by their `repo` / `project` key, plus `tickets_open` | |
| waiting | blocked tickets. Reckoning `waiting_on_others` is one global count today, not per project, so it goes to the Lodestar entry. `basis: "waiting=tickets-only"` says so. | |

**The Lodestar entry** (`kind: "lodestar"`) is always present. It means Lodestar itself plus all
work that belongs to no project: private-store, Hestia, unrouted mail, unmapped codes. A routing
row whose dir lies inside a registry row (Expenses in `~/dev/private-store/expenses`) takes
that row's key, so private-store burning folds into Lodestar as tickets do; a dir inside no
registry row keeps its own key but is never drawn as a `managed` ghost (C7). It appears even
when no Lodestar session is open. Its `sessions` count is 0 in that case.

**Code map: not Augur's (owner ruling 2026-10-31).** The earlier design had Augur keep an editable
code-to-project map (`~/ClaudeWork/augur/project-codes.json`). It is withdrawn: mapping account codes to
repos is Lodestar's job (ticket BURNING_WIRE_TO_PROJECTS). In pilot 2 Augur reads Lodestar's
per-project burning count and puts every unattributed item on the Lodestar entry.

**Source (built 2026-10-31, ticket AUGUR_WIRE_LODESTAR_BURNING_COUNTS).** Collector
`lodestar_burning` (counts tier, `augur/augur/lodestar/burning.py`) reads
`~/dev/.lodestar/companion/burning-projects.json` = `{built_at, unmapped_burning, projects:
{<routing name>: {burning, red, amber, verify}}}`, written by the Companion only when it changes,
every watched project with zeros included, `lodestar` always present. Keys are routing names
(`priority/routing.md`): each maps to Augur's project key through its routing `dir` -> the
`sync/registry.md` row at that path (Id and Name), else its lowercased name. Fresh = file mtime
under 5 min, or the Companion alive (`now.json` generated under 5 min) with `plots.burning.state` `ok`
and `plots.burning.checked_at` equal to the file's `built_at` (the Companion keys the file on
`built_at`, so an unchanged file still names the latest evaluation). Review R1 finding 6 retired an
interim rule (per-project sum equal to `plots.burning.total`): it passed a frozen feed as fresh and
made `pilot2_check.py burning` circular. That check now prints which freshness path held and counts
only an mtime-fresh pass as evidence. A row with no `burning` key leaves the key absent; no `lodestar`
row means no Lodestar burning, never a fabricated 0. Missing or unparseable = `counts.unknown: read_failed`, old = `stale`,
on every non-unmanaged entry: unmeasured, never 0. `unmapped_burning` rides on the Lodestar entry.
`basis` = `burning=lodestar-attribution`. Pilot 1 carries burning only; tickets_open, open and waiting
stay absent until pilot 2.

**Tickets and to-dos (built 2026-11-01, pilot 2).** The same `lodestar_counts` collector reads
the ticket directories from Lodestar's own resolved list (`~/dev/.lodestar/tickets/homes-cache.json`,
refreshed hourly by `ticket`; older than 6 h = unmeasured), keyed by registry Id. `tickets_open` = status
open or active, `waiting` = blocked. Files are re-read only when (mtime, size) changes: 33 ms cold,
6 ms warm per 60 s call. `open` = tickets_open + live `whatnow.json` items that are not tickets;
unprojected, private-store and Hestia items go to Lodestar. A part that is unmeasured leaves only its
own keys absent and is named in `basis` (`burning=stale`, `tickets=unmeasured`, `open=no-whatnow`).
A key with no ticket home, or a home that exists but cannot be listed, carries no ticket keys
(absent, never 0); a home whose directory does not exist yet is a real 0. Hestia and private-store
ticket homes count on the Lodestar entry. `whatnow.json` older than 6 h by its `built_at` reads as
`open=no-whatnow` (R1 findings 9 to 11).
Ticket counts never create a project entry: only a session or burning > 0 does. Check:
`augur/bin/pilot2_check.py tickets|burning`.

**Projects with burning and no session.** Sprites draws burning only (not tickets) as running
lights, and draws a ghost visitor for a project with `burning > 0` and no live session. So
`projects[]` carries every managed project whose `counts.burning > 0` even when its `sessions` is 0,
with its own per-project `burning` count. The schema already allows this (`sessions` minimum 0,
`counts` optional); no schema change.

### Machine

| Field | Source (all in-process unless marked) | Status |
|---|---|---|
| cpu | `host_statistics(HOST_CPU_LOAD_INFO)` deltas | measured (0.01 ms) |
| memory | `host_statistics64(HOST_VM_INFO64)`, `kern.memorystatus_vm_pressure_level` mapped 1/2/4 -> 0/1/2 | measured |
| thermal | notify `com.apple.system.thermalstate` (hostnative) | measured (state 0 tonight; never seen above 0) |
| strain | `load_levels` semantics and parameters, vendored. `score` = level index + the fraction of the way toward the next entry threshold. Sprites' 0..3 = score x 0.75. | levels measured 2026-10-22. **score is new.** |
| strain.background_level | load_levels' LODE-18 background-QoS probe is a compiled child binary run every 20 s. Augur does not run it in pilot 1, so `background_level` is **absent by design** (schema: optional). A shadow reading `light` from load_levels against Augur's absent is expected and is not a mismatch. | absent until a later pilot decides whether Augur owns that probe |
| net | sysctl `NET_RT_IFLIST2`, physical default-route interface | measured (0.48 ms) |
| vpn | a tunnel interface (`utun`/`ipsec`/`ppp`) holds the primary default route | measured (0.20 ms; utun4 tonight) |
| vpn.on_site | `~/dev/.lodestar/companion/ssid.json` (LodestarSSID.app) equals `$LODESTAR_NETWATCH_PROBE_SSID`. Only the boolean is kept; the SSID never enters the file. | the file was absent tonight: **unmeasured**, so the key is absent |
| vpn.on_site (work networks) | OR: a network service's DHCP domain (option 15, configd's `State:/Network/Service/*/DHCP`; no Location grant, no spawn) ends with a suffix in `$AUGUR_HOME/config/work.json`, written by `augur/bin/work_here.py`. Read every 15 s; only the boolean is kept. | measured 2026-11-04 on site: 0.11 ms, `on_site` true |
| path | unprivileged ICMP burst to the anchor, bound to the physical interface, worker thread (netwatch) | measured 2026-10-27 |
| bandwidth.strain | section 5 | **absent** until validated |
| power | IOKit power sources (hostnative) | measured, Laptop only |
| api | Claude Code transcripts of live sessions (`~/.claude/projects/<slug>/*.jsonl` and `<session>/subagents/*.jsonl`): assistant lines with `"isApiErrorMessage": true` and an `error` word are failed calls, assistant lines from a real model are good ones. Only appended bytes are read (offsets per file; first sight reads at most the last 64 KB; a partial last line waits for its newline; a shrunk or replaced file is re-read from its start). Only `type`, `timestamp`, `isApiErrorMessage`, `error` and `model` are kept; the error text is matched in memory to `error_kind` and dropped. `failing` = an error with no good call after it in any session, held up to 10 min (R2-3); or, while a session is busy, two consecutive failed TCP connects to the API host and port (on a worker thread; each probe bounded at 5 s including DNS; every 15 s while good calls flow, every tick once the transcript has been silent 6 s), which turns `failing` within about 10 s of a network outage. A good probe never clears a transcript-recorded failure (R3-3). **Probe URL source (R5-10, R6 F1):** the `ANTHROPIC_BASE_URL` each busy session itself runs with, read from the exec environment (`KERN_PROCARGS2`, own uid) of the session's root and its **direct children** only (the MCP servers and shell snapshot shells Claude Code spawns). Never `~/.claude/settings.json`, which names the *next* session's account; never a deeper descendant, since a tool command may set its own. Each pid is read once; a value counts only while its pid is still in the tree; if a session's own processes disagree, that session is unscoped and the transcript stands. No URL from any busy session reads `unknown: env_missing`, logged once (R3-5). That probe exists because Claude Code retries silently for about 3 min before it writes the error line (measured on 49 incidents: median 182 s, p10 174 s). `ok` = a good call in the last 2 min after the last error; otherwise **absent** (idle agents are unmeasured, never `ok`). `error_kind` is `network` whenever any failing session's newest error is network (R2-4). Unvalidated on real data: the `rate_limit` and `server` branches (no such case in the corpus). `error_kind`: `network` (ENOTFOUND, ECONNRESET, "Can't reach", connection lost, response stopped), `rate_limit` (429, 529, overloaded), `server` (other 5xx or `server_error`), `other`. **Only `network` should drive the Sprites lost-connection huddle**: a rate limit or a provider outage is not the link. Owner idea 2026-11-01: this is truer to the source than VPN and Wi-Fi. | built 2026-11-01, provisional; agents tier, 0.1 to 0.4 ms per tick measured on 4 live transcripts |

### Proposals from the prior-art pass (not built; `augur/research/PROCESS_TRACKING_PRIOR_ART.md`)

- **Microsecond start time as the internal identity.** The public id stays `pid@seconds`, which
  three consumers key on. Internally, use `pbi_start_tvusec` too, and revalidate nettop rows by
  identity. This is deferred because it changes every internal key, and the measured reuse risk is
  nil (R1-21: wrapping takes about 100,000 spawns).
- **An id-keyed subagent and background-task ledger** from SubagentStart/SubagentStop and the task
  hooks, reconciled with transcripts in the way Claude HUD's `src/transcript.ts` does it (MIT,
  credited). Transitions are idempotent, never bare inc/dec counters. Today's count reads the
  transcript's last line; a ledger would also see crashed agents.
- **API retry evidence.** `system/api_retry` exists only for stream-json and SDK sessions, so
  interactive sessions keep the transcript signal plus the reachability probe (R2-3).
- **Coverage fields** beyond `method` and `pending_reconciliation_cpu_s` (built): a `coverage`
  value of complete, partial or unknown, once truncation, failed reads and orphans can be summarised
  per session.

## 4. Collectors behind a platform-neutral schema

Augur's own code lives at `augur/augur/` when it is built. Layout:

- `core` is the scheduler: tiers, stamping, absent and unknown, atomic write, the cost meter, the off
  switch.
- `collectors/` holds plug-ins. Each is `name, tier, platforms, collect(ctx) -> {signal: dict}` and
  is timed per call (section 6).
- `darwin/` holds vendored ctypes readers, copied from `~/dev/Lodestar/bin/lib/hostnative.py`,
  `load_levels.py` and `netwatch.py`. Each copied function carries a `# from Lodestar <file>@<sha>`
  line, and a test diffs them against the source (section 9). This way Augur needs no Lodestar on
  the path and does not break when Lodestar refactors.
- `lodestar/` holds read-only feed readers. They are optional: each catches its own failure and
  marks its Signals unknown.

Collectors stay pure where they can: input structs in, Signal dicts out. Fixtures can then replay
them on any OS.

**What a Windows (Archmagi) port would need.** Each item is one collector. The schema does not
change.

| Signal | Windows source | Hard? |
|---|---|---|
| cpu, memory | `GetSystemTimes`, `GlobalMemoryStatusEx`. Windows has no kernel "pressure" level: derive one from commit charge and available memory | easy, but `pressure` is not equivalent and must be named as different |
| net, vpn | `GetIfTable2` byte counters. VPN = the default route's interface is a tunnel (`IF_TYPE_PPP` or an adapter description match) | easy |
| path | `IcmpSendEcho2`, no admin needed | easy |
| sessions | `CreateToolhelp32Snapshot` for the tree; `GetProcessTimes`, `GetProcessMemoryInfo`. Claude Code on Archmagi runs inside **WSL2**, so the trees live in the Linux VM and Windows sees only `vmmem`. The port is really a **Linux** collector (`/proc`) running inside WSL. | medium: a Linux collector set, not a Windows one |
| strain (sched delay) | the same burst trick works with `SetThreadPriority`; the thresholds need re-measuring | medium (re-baseline) |
| per-session net | `/proc/<pid>/net` is per network namespace, not per process; per-process bytes need eBPF or `nethogs` (root) | hard: leave absent |
| thermal | no unprivileged API | absent |
| install | systemd user unit (the sync sweep's pattern, `sync/systemd/`) | easy |

Verdict: the machine signals are a few days of work. Sessions need a Linux collector inside WSL.
Per-session network is absent. That fits "only if not much harder" for the machine half, so the
Windows port is **deferred**, not refused.

## 5. The two hard network signals (DATA_NEEDS items 3 and 4)

### Per-session rx/tx: `nettop` works, measured tonight

The nettop runs on mt-AAAAAA, 22:1x:
- `nettop -L 1 -n -x -J bytes_in,bytes_out,re-tx,rtt_avg -p <pid>...` printed one row per process
  plus one per flow. A Claude session's process shows as `2.1.292.<pid>` (its version string).
- Over 20 runs it took **13.3 ms wall and 11.4 ms CPU** for 4 pids, and 17.7 / 15.2 ms for all 48
  processes.
- That is an exec, but the 257 ms endpoint-security tax measured 2026-10-22 was not there tonight:
  `/usr/bin/true` spawned in 2.5-3.0 ms after a 36 ms first call.

How the values are derived:
- The values are cumulative per *live* flow, so Augur diffs per flow (by flow 4-tuple) between agents
  ticks. A flow that closes between ticks loses its last bytes. That under-counts short transfers,
  never over-counts.
- On the VPN the per-process rows still show the session's own bytes. The flow row
  showed the tunnel address (`<site address> <-> 100.x:443`), so attribution survives the VPN. hostrec
  had concluded the opposite from its talker top-5, which is read from interface-level totals.
- Remote addresses are read in memory only and never written.

Cost and cadence:
- One exec every 5 s costs ~0.23 % of one core.
- That is under the budget in section 6, but it is the single largest line item. So it is
  **collector `session_net`, on in pilot 1 only for measurement, kept only if the cost meter
  passes.**
- If it fails, `sessions[].net` is absent and consumers fall back to `machine.net`. Sprites already
  plans that fallback.

**Unvalidated:** whether the per-flow sum matches the interface bytes while a session is the only
heavy talker. That is pilot 1's falsifier.

### Bandwidth strain 0..1: a proposed definition (absent until it passes pilot 2)

"The link cannot keep up with what is being asked." Today's need/available is 1 by construction, so
it is not used. Proposal, using only passive signals, maximum of four 0..1 terms over a 30 s window:

1. **sendq**: TCP send-queue backlog that persists. Bytes queued on established non-loopback flows,
   from one `netstat -an -p tcp` every 15 s (6.2 ms wall, 2.8 ms CPU, measured). It counts only
   while the same flow holds a backlog over two consecutive reads. Scaled 0 at 64 KB, 1 at 1 MB.
2. **retx**: retransmitted / sent bytes on the Claude trees' flows, from nettop's `re-tx` column, at
   no extra cost (one session showed 1336 B of 520 KB tonight). Scaled 0 at 0.5 %, 1 at 5 %.
3. **rtt_inflation**: path RTT median over its own 1 h minimum. Scaled 0 at 2x, 1 at 6x (the
   2026-10-27 hotspot: 4 ms first hop vs 810 ms anchor).
4. **path_loss**: 0 at 2 %, 1 at 15 %.

`basis` names whichever term won. Every scale point is a guess, so the Signal ships `provisional`.

Falsifier: in pilot 2's labelled week, strain must exceed 0.5 in at least 4 of 5 times the owner
reports "the network is slow" and stay under 0.2 in 95 % of minutes he calls fine. Otherwise the key
stays absent. Any active probe is still under LODE-19's gate (trusted on-site network, no VPN, tiny), and Augur adds
none.

## 6. The self-cost meter and its pass/fail rule

What it measures:
- **Whole producer:** `getrusage(RUSAGE_SELF)` + `RUSAGE_CHILDREN` deltas (children = the nettop and
  netstat execs), rolling 60 s and 1 h windows.
- **Per collector:** `time.thread_time()` around each `collect()` + the children delta across it,
  + the CPU its own worker threads report (`drain_worker_cpu`: the strain burst thread, the path
  echo thread; review R1 finding 8), summed per collector per hour.
- **Also tracked:** RSS (current resident size, `ri_resident_size`; `ru_maxrss` is kept as the peak), spawns per hour, and lateness: tick start minus its slot,
  measured before re-gridding, so an overrunning tick makes the next one late. Sleep is excused only
  when the wall clock ran ahead of the monotonic clock (which stops in system sleep); a monotonic gap
  is a stall and counts (R1 finding 7).
- **Windows:** the newest sample older than the hour is kept as the base, so a long stall still has
  a window; with no window at all the verdict is `watch` ("no window"), never `pass` (R1 finding 17).
  The 1 h line is written once per wall-clock hour, also across restarts, with `window_s` saying how
  much of the hour this life measured; the 24 h check judges the available windows once the window
  has fully elapsed, with at least 20 of 24 present (R1 finding 18).

All of it goes into `cost` in the snapshot and into one line every 10 min in
`~/ClaudeWork/augur/cost.jsonl`.

**Budget** (mt-AAAAAA, M1 Max 10 cores; same on the Desktop):
- **Pass:** 1 h average CPU <= **1.0 % of one core**, RSS <= 40 MB, spawns <= 1500/h, and no fast
  tick late by more than 1 s in the hour except during sleep or wake. The current trio costs ~3 % of
  one core, so this is a cut by a third. Each collector also gets its own line:
  - fast <= 0.15 %
  - agents <= 0.40 % (session_net included)
  - probes <= 0.25 % (the 20 ms burst every 15 s alone is 0.13 %)
  - counts <= 0.10 %
  - write <= 0.10 %
- **Watch:** any line over budget for 1 h. The verdict reads `watch` and the log names the
  collector.
- **Fail:** the whole producer over 2.0 % for a 1 h window, or any collector over 3x its line. The
  failing collector is turned off by itself (its Signals then read unknown `disabled`), and the
  failure is logged. After a cut the line is judged on the collectors still running, so one bad
  collector never empties its tier (R1 finding 5).

**"In the noise" rule for keeping a signal:**
- Keep it if its cost is under 0.1 % of one core.
- Or keep it if it is the *only* source for something a consumer draws.
- Otherwise cut it, or move it to a slower tier.

Pilot 1 measures every collector for 24 h at rest and 24 h at work before any consumer reads the
file. **Not measured yet:** Augur's own Python baseline. Importing the vendored readers costs about
14.5 MB maxrss (measured with Lodestar's). The interpreter's idle wake cost at 2 s ticks is unknown.

## 7. File, delivery, privacy

Paths:
- **Snapshot:** `~/ClaudeWork/augur/live/snapshot.json`, under the agent storage root
  (`python3 ~/dev/Lodestar/bin/lib/agent_storage.py`; `$AUGUR_HOME` overrides it). Mode **0600**
  in 0700 directories, as are `samples/`, `cost.jsonl` and `audit.jsonl` (R5 S3): every consumer
  runs as the owner, and the "levels and counts" are not harmless. They republish Lodestar's
  0600 per-project burning counts and routing names, and every sample line carries
  `machine.vpn.on_site` and session activity, a per-minute location and presence trail. The
  LaunchAgent sets `Umask` 077. `samples/snap-<day>.jsonl` older than 14 days is deleted at the
  day rollover. `cost.jsonl` and `audit.jsonl` keep 7 days (by each line's own `t`, trimmed at
  rollover) and at most 8 MB each (cut to the newest whole lines at any sample), rewritten
  atomically at 0600.
- **Detail sibling:** `snapshot-detail.json`, mode **0600**. It holds what the shared file must not:
  per-session cwd paths and per-burning-item project attribution with ids. It is for the Companion
  only, and readers may ignore it.

Atomic write: a `mkstemp` temp file in `live/` (never a predictable name a link could sit on),
`fchmod`, `fsync`, `os.replace`. History lines are appended with `O_NOFOLLOW`; a failed append is
truncated back, and a torn tail gets its newline before the next record. A deleted `live/` or
`samples/` is re-made on the next write (R5 RB3). Each sleep span is logged to `audit.jsonl`
(`event: slept`) so the pilot checks can excuse it (R5 RB4). The file never changes in
place. Writing every 2 s means one write per 2 s, ~8 KB at 5 sessions.

Polling: consumers poll the **mtime** (Sprites' `FileWatch` already polls at 1 s), then parse, then
check `valid_until`.

**Compatibility rule:**
- `schema` = `augur.snapshot`, `version` = `major.minor`.
- A minor bump only adds optional keys, and readers ignore unknown keys. Every key added bumps the
  minor (1.1, 2026-11-01). A key whose meaning changes is a new key, or a major bump; the old key
  is never re-defined in place. `tests/test_core.py` pins a hash of the schema to the version.
- `off: true` wins over `valid_until`: the off file is written once and left to age, and it means
  off, not stale. `seq` restarts at 0 with the producer; a reader that sees it drop clears its windows (SidePulse does).
- A major bump means renamed, removed or re-unitted keys. Augur then writes `snapshot.v2.json` beside
  v1 for one release, and readers refuse a major they do not know.
- Units are in the key names (`_mbps`, `_gb`, `_pct`, `_s_per_s`) so nothing silently changes unit.

**Socket (later, optional):**
- `~/ClaudeWork/augur/live/augur.sock`, a Unix stream socket, mode 0600, newline-delimited JSON:
  each line is a complete snapshot, sent on every write.
- It is only worth building if a consumer needs data in under 1 s. None does today (Sprites polls at
  1 s and wants 15 s). Until then the file is the only interface.

**Off switches:**
- `~/ClaudeWork/augur/off`: if present, Augur writes `{"off": true, ...}` once with empty arrays.
  Readers show nothing, not idle. Augur then sleeps and re-checks every 5 s, with no restart needed.
- Per collector: `~/ClaudeWork/augur/collectors.json` (`{"session_net": false}`).
- Kill switch: `launchctl bootout gui/$UID/com.mandrake.augur`.

## 8. Install on both Macs

The install follows Lodestar's conventions:
- `augur/launchd/com.mandrake.augur.plist`, with `RunAtLoad` and `KeepAlive` true and
  `ThrottleInterval` 20.
- `ProcessType` `Standard` under `/usr/bin/nice -n 10`, with `LowPriorityIO` (Background was
  measured and dropped, below).
- The interpreter is `~/ClaudeWork/python/py`, the one the SidePulse plists use. Explicit `PATH`.
- Logs go to `~/Library/Logs/augur.log` / `.err`.
- `augur/bin/install.sh` (`--remove`) is modelled on `~/dev/Lodestar/bin/install_sidepulse_resources.sh`:
  it refuses on a different `$HOME` (one that is not the account's own home directory, checked with
  `dscl`), runs `plutil -lint`, bootouts, copies and bootstraps.

**Measured 2026-10-31, pilot 1: Background was dropped for `Standard` + `nice -n 10`.** Under
`ProcessType Background` the whole process ran Darwin-BG (scheduler priority 4), and so did its nettop
children: 6952 ms CPU over 163 execs, ~42 ms each, against ~12 ms for the same exec from a terminal.
session_net alone read 0.79 % of one core, twice the agents line. The plist now says `Standard`
(priority 20, nice 10) with `LowPriorityIO`; session_net also moved to its own 15 s period
(`every_s`, stamped valid for 37.5 s), which DESIGN section 6 allows before a cut.

**Caveat for the Background band (kept for the record):** Background QoS was starved at 100 % busy (hostrec D1). The
scheduler thread therefore raises itself to USER_INITIATED for the tick, as hostrec's `TICK_QOS`
does. The strain burst stays at UTILITY by design.

How it reaches both Macs:
- MandrakeWorkflows already syncs to both Macs (registry row `MandrakeWorkflows`, machines blank =
  all). The code reaches the Desktop by the sweep.
- The **LaunchAgent install is per machine and is not automatic**. Proposal: one row for
  `com.mandrake.augur` in whatever Lodestar uses for per-machine agents (the lifecycle receipts in
  `sync/lifecycle-receipts/<key>.json`), so that `doctor`/parity checks flag a Mac missing it.
- No skill is needed for v1. If one is added (`augur` status/off/cost), it gets a
  `claude/skills.md` row with Machines `mac`.

Desktop (mt-BBBBBB) differences:
- No battery: `power` is absent.
- No SidePulse card: that consumer is absent.
- Thermal as on the Laptop.

## 9. Tests

- **Schema:** `example.json` and every fixture validate against the schema (jsonschema 4.25 is
  present for `/usr/bin/python3`). A v2 version string must be rejected. That check was run tonight:
  0 errors, v2 rejected.
- **Fixtures:** recorded libproc, VM and interface structs plus nettop/netstat text, replayed through
  the pure collectors. Cases:
  - two sessions
  - a session with a Bash background shell and a subagent
  - pid reuse
  - a counter reset
  - a VPN flap
  - Lodestar absent (counts absent, the Lodestar entry present)
  - registry unreadable (`managed` absent)
  - VIP burning items with codes but no filing (they go to `unmapped_burning`)
- **Freshness:** a fake clock checks three things.
  - Each Signal's `valid_until` follows the tier rule.
  - A collector that raises yields `unknown` and no value keys, never the previous value.
  - A stopped producer makes the whole file stale after 5 x fast.
- **Absence:** a property test that walks every fixture output and fails on any numeric zero whose
  source was marked unavailable.
- **Cost meter:** a synthetic collector that burns a known 50 ms per call must be reported within
  ±20 %. A spawn-heavy fake must show its children's CPU. A collector over 3x its line must be
  disabled by itself.
- **Vendored-code drift:** diff each `# from Lodestar` function against its source sha. A failure
  names the function and does not block.
- **Privacy:** grep every fixture snapshot for `@`, `/Users/`, IPv4 patterns and fixture subject
  strings. Any hit fails.

## 10. Migration without regressions

**Owner ruling 2026-10-31 23:50 (supersedes the shadow lengths below and pilot 3's 7-day shadow and
14-day wait):** "Once you determine the readers are set up by all the consumers, please remove their
previous readers to avoid duplicate code, functionality, and CPU load." Augur becomes the sole source
as soon as it is validated against ground truth (a controlled busy loop with a known core count,
`top -l` deltas), not against the old collectors. The shadow comparators are evidence for the switch,
not a waiting period. Validation record: `augur/PILOT1.md`.

The order is Sprites first (it has no measuring code to lose), then SidePulse Resources, then the
Companion.

**Shadow period** (pilot 3, 7 days per consumer):
- The consumer keeps measuring as today and also reads Augur.
- A comparator logs paired readings each tick to `~/ClaudeWork/augur/shadow-<consumer>.jsonl`.
- **Agreement rule:** each paired field must agree in >= 95 % of ticks within the tolerance below.
  Levels may differ by at most one step, and only during a transition window (10 s). There must be
  no tick where one side reads a value and the other reads absent or unknown without a logged
  reason.
- Only then does the consumer switch to reading Augur. Its old measuring code stays in place,
  switched off by a flag, for 14 more days before it is deleted.

| Consumer field today | Augur field | Tolerance |
|---|---|---|
| Resources NEED (slots) | sessions[].attention.state | exact |
| Resources CPU level (`load_levels.current().overall`) | machine.strain.level | exact; it is the same algorithm |
| Resources MEM level (pressure, headroom capped at full) | machine.memory + strain.memory_level | exact |
| Resources NET 10 s rate | machine.net rx/tx (Augur 2 s, averaged by the reader to 10 s) | ±10 % or ±0.1 Mbit/s |
| Resources Claude CPU / GB | sum of sessions[].load | ±10 % |
| hostrec `answers.claude.rows[]` cpu, fp, n | sessions[].load cpu_cores, mem_gb, procs | ±10 %, procs exact |
| hostrec network rx/tx, path | machine.net, machine.path | ±10 %; path level exact |
| hostrec levels / dly | machine.strain | exact |
| Companion `plots.agents.segments[]` state, cpu, rss | sessions[] | state exact; cpu, rss ±10 % |

**What stays in the consumers:**
- **The Companion** keeps Burning, Orders, tickets, drafts, Bearing, spend and the launch-time probe
  (a spawn timer, not a level). hostrec's 24 h ring and rollups become a reader of Augur's values.
- **SidePulse runners** keep their LED programs and the `sidepulsed` lease logic.

**The migration risk:** load_levels' shared state. Today `levels-state.json` is refreshed by
whichever caller finds it stale, and its hysteresis and dwell live in that shared file. If Augur and
an old caller both drive it, they fight over one timeline. So Augur gets its own state file.
`load_levels.current()` gains a reader mode: "Augur's file is fresh, return its strain." It is
switched on only after the shadow agrees. The Sparkle and Clarity displays then read it too. Until
then, two ladders can disagree by one level near thresholds. That is expected, and it is logged, not
"fixed".

## 11. Reconciling with the Sprites contract

Sources: `sprites/docs/SHIP_PLAN.md` (commits 2ed439a, 63cda1a) and `sprites/docs/DATA_NEEDS.md`
(aa168b9). Sprites already isolates the conversion in one adapter in `app/stage.html`, so Augur
keeps its own shape and the adapter maps it. Below are the differences, each with a recommendation.

| SHIP_PLAN key | Augur | Difference | Recommendation |
|---|---|---|---|
| file `~/ClaudeWork/sprites/live/state.json`, `$SPRITES_STATE` | `~/ClaudeWork/augur/live/snapshot.json` | path | Set `SPRITES_STATE` to Augur's file in the Sprites plist. Keep `demo_feed.py` writing the old path for demos. |
| `schema: 1`, `t` | `schema`, `version`, `written_at`, `valid_until` | richer | The adapter treats `now > valid_until` as "all unknown", drawn calm. |
| `sessions[].id` = `"43901"` | `"43901@1793472837"` + `pid` | id carries the start time | Key sprites by Augur's `id`, so a reused pid never inherits a creature's species. |
| `project` | `project` (+ `project_key`, `managed`) | adds | Draw `managed: false` white and a different shape, with no counts (owner decision 5). |
| `hue`, `concept`, `iv` | none | Sprites-only | Augur never writes them: casting is Sprites' business (`cast.json`). |
| `cpu` (cores) | `load.cpu_cores` | name | map |
| `mem` (GB) | `load.mem_gb` | name | map |
| `procs` | `tasks.background` (1.1), `tasks.total` = shells + subagents | DATA_NEEDS wants Claude background shells + subagents | Satellites = `tasks.background` when present. Do not fall back to `load.procs` (every OS process in the tree, a different quantity: CONTRACT R1 C5); absent means satellites unset. Today's tasks are heuristic (section 3), and exact once the hook lands. |
| `state` working/idle/needs | `attention.state` working/idle/needs_you/stopped | adds `stopped` | Map needs_you -> needs and stopped -> idle (or give stopped its own dim look if wanted). |
| `rx`, `tx` (Mbit/s) | `net.rx_mbps`, `net.tx_mbps`, may be absent | absence | When absent, fall back to `machine.net` split by CPU share, or draw no pulses. The ruling forbids a 0. |
| `m.level` 0..3 | `machine.strain.score` 0..4 | scale | `level = score x 0.75`. |
| `m.thermal` 0..2 | `machine.thermal.state` 0..3 | scale | clamp to 2 |
| `m.mempress` 0..2 | `machine.memory.pressure` 0..2 | same | map |
| `net.mbps` | `machine.net.rx_mbps + tx_mbps` | split | sum, or keep in/out apart (GRAMMAR_V2 wants both) |
| `net.vpn` up/down | `machine.vpn.state` + `on_site` | adds | Lost-VPN behaviour = `down` and not `on_site`. Without this guard, on the on-site network the flock would huddle all day. |
| `net.loss` | `machine.path.loss_pct` | name | map |
| `net.strain` 0..1 | `machine.bandwidth.strain`, absent for now | absence | When absent, draw no jam (calm). Never draw strain 0 as "flowing freely". |
| (none) | `projects[].counts` | new | the burning running lights (burning only, not tickets: owner 2026-10-31), ghost visitors for projects with burning > 0 and no session, and the always-present Lodestar sprite |

### DATA_NEEDS, row by row

| DATA_NEEDS row | Augur field | Cadence | Cost (measured) | Status |
|---|---|---|---|---|
| id, pid | sessions[].id, pid | 5 s | in the sweep (~5 ms per 920 pids) | measured |
| project | sessions[].project, project_key, managed | 5 s (cached) | ~0 | measured; managed rule unbuilt |
| state | sessions[].attention.state | 2 s | 0.6 ms | measured (hook-driven) |
| cpu | sessions[].load.cpu_cores | 5 s | sweep | measured |
| mem | sessions[].load.mem_gb | 5 s | sweep | measured |
| tasks | sessions[].tasks.total (shells + subagents); tasks.background (bg_shells + subagents + other) for satellites, no fallback | 5 s | ~0.7 ms | heuristic, unvalidated; exact needs the hook ticket |
| rx, tx | sessions[].net.rx_mbps / tx_mbps; absent -> machine.net | 5 s | 11.4 ms CPU per nettop exec, ~0.23 % of a core | measured as possible, unvalidated (pilot 1) |
| strain level 0..3 | machine.strain.score x 0.75 | 15 s | 20 ms burst / 15 s | measured levels, new score |
| thermal 0..2 | machine.thermal.state (clamp) | 15 s | <1 ms | measured (never above 0 yet) |
| memory pressure 0..2 | machine.memory.pressure | 2 s | ~0 | measured |
| bandwidth strain 0..1 | machine.bandwidth.strain | 15 s | +2.8 ms CPU netstat / 15 s | **absent** until pilot 2 passes |
| vpn | machine.vpn.state (+ on_site) | 2 s | 0.2 ms | measured; on_site unmeasured (no ssid.json here) |
| lost connection (huddle) | machine.api.state `failing` with error_kind `network`; machine.vpn as context only | 5 s | 0.1 to 0.4 ms | built 2026-11-01, provisional: a failed API call is the direct evidence; absent = idle, never "connected" |
| total rx/tx | machine.net | 2 s | 0.5 ms | measured |
| burning (+ tier) per project | projects[].counts.burning, burning_red/amber/verify (copied from Lodestar's per-project count, BURNING_WIRE_TO_PROJECTS) | 60 s | <15 ms per minute | unbuilt (pilot 2); attribution is Lodestar's |
| todos per project | projects[].counts.tickets_open | 60 s | 63 ms cold, cached by mtime | measured read |
| code -> project map | none in Augur: Lodestar's job (BURNING_WIRE_TO_PROJECTS) | | | withdrawn 2026-10-31 |
| delivery | atomic file + mtime poll; socket later | | | designed |

## 12. Build order: three pilots

**Pilot 1: machine + sessions, write-only, measured.**
- Augur runs as a LaunchAgent on the Laptop. No consumer reads it.
- Success checks, all mechanical:
  - `snapshot.json` validates every minute for 24 h.
  - The `cost` verdict is `pass` for the 1 h windows (>= 22 of 24).
  - Per-session `procs` and `cpu_cores` match hostrec's rows within ±10 % in >= 95 % of
    paired ticks.
  - A forced `kill -STOP` of Augur makes the file stale within 10 s.
  - The off file produces `off: true` within 5 s.
- Falsifiers:
  - Per-session nettop bytes summed across all sessions exceed interface bytes. Attribution is then
    wrong: `session_net` is cut and the key goes absent.
  - Augur's cost over 1 % in the at-work day. The worst collector is then cut, and if that is not
    enough, Augur does not replace the trio.
  - The tasks heuristic disagrees with a hand count of 10 sampled moments by more than 1 in 3 of
    them. The key then stays `procs`-only until the hook lands.

**Pilot 2: Lodestar counts and bandwidth strain.**
- Counts:
  - The `lodestar` entry is present with Lodestar removed from the path (`HOME` fixture). Counts are
    absent, not zero.
  - The burning total in Augur equals `now.json` `plots.burning.total` every minute for 24 h.
  - Per-project `tickets_open` equals `ticket list --project P --status open` (plus active) for
    every project, 3 checks per day.
- Strain:
  - The labelled-week falsifier from section 5, from the owner's one-word "slow" reports logged with
    `ticket note`.
  - It fails if the hit rate is under 4 of 5 or the false rate is over 5 %. The key then stays
    absent.

**Pilot 3: readers and the shadow period.** (Shortened by the 23:50 ruling in section 10: once a consumer's reader is in place and Augur is validated, its old measuring code is removed, with no 7-day shadow or 14-day wait.)
- Sprites switches first: its adapter reads Augur, and its `demo_feed.py` stays for demos.
- SidePulse Resources and hostrec then run 7-day shadows each, against section 10's table.
- Success:
  - Agreement >= 95 % on every row, and zero unexplained value/absent mismatches.
  - After the switch, the trio's own CPU (`ps` time) drops by >= 50 % over 3 days.
- Falsifier: the owner reports one LED or Companion tile that is wrong and was right before the
  switch. That consumer reverts by its flag.

## 13. What could not be measured in this pass

- Augur's own cost: it is not built. The budget is a target set from the trio's measured ~3 %.
- Whether the tasks heuristics (shells, recent subagent transcripts) match real background work. No
  ground truth was available.
- Whether per-flow nettop bytes sum to the interface bytes. Short-lived flows are surely missed;
  by how much is unknown.
- Every bandwidth-strain scale point. No labelled slow-network period exists.
- `vpn.on_site`: `ssid.json` was absent tonight.
- Thermal above 0, and memory pressure above normal: never observed on these machines.
- The Desktop (mt-BBBBBB): nothing was measured there. All costs here are from the Laptop.
- The Reckoning's per-project `waiting`: there is no per-project source. Only the global
  `waiting_on_others` exists.
- The 257 ms exec tax: absent tonight (2.5-3 ms). If it returns, nettop and netstat cost ~100x more
  wall time. That costs wall time, not CPU, so it would show up as lateness on a worker thread. The
  cost meter would catch it, and the Fail rule would cut the collector.
