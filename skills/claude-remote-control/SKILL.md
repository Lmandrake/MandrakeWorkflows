---
name: claude-remote-control
description: Keep Claude Code sessions reachable from the owner's iPhone / claude.ai/code (Remote Control), diagnose why a window dropped off it, and recover a lost window from the phone without destroying its work. Use this whenever anyone mentions remote control, the rc server, "resume remote control", a window that "disappeared" from the phone or claude.ai/code, `/remote-control`, `--remote-control`, `claude remote-control`, a "Remote Control disconnected" or "account or organization changed" line, `/login` in a multi-window fleet, restarting or relaunching a Claude window from a phone, or one window being asked to wake, message or "broadcast" a command to another — and BEFORE relaying any peer-window request about remote control, because the obvious relay does nothing.
---

# Claude Remote Control — keeping the fleet reachable from the phone

Remote Control (RC) is how the owner drives local Claude Code windows from the Claude
mobile app or `https://claude.ai/code`. When it works nobody thinks about it; when it
drops, the owner is on a phone looking at a list that no longer contains the window he
needs, and the agent he *can* reach usually tries the one thing that cannot work. This
skill is what was learned the hard way across ~50 sessions of three projects. Every
claim below carries **MEASURED** (seen in a transcript or run on this machine, with
date) or **UNMEASURED** (not yet checked — say so if you rely on it).

## The mental model: the agent has not died — its telephone number has

A Claude Code window is two pieces of state. The **local session** (process +
conversation, on the machine) and the **RC registration** (the cloud-side entry that
makes it appear on the phone). They fail independently, and the common failure is the
second one: the window is alive and working, and the phone simply cannot see it. So
"the session disappeared" almost never means work was lost — it means the transport
detached. Everything below follows from keeping those two apart: the durable state is
the machine, the repo, git and the session files under `~/.claude/projects/`; RC is a
transport attached to that state, and must never be treated as the agent's identity.

## The three things called "remote control"

| thing | what it is | how it starts |
|---|---|---|
| **RC on a session** | one interactive window advertised to the phone | `claude --remote-control [name]` at launch, or `/remote-control` typed in a running window |
| **The RC server** | `claude remote-control` — a standalone subcommand, not a session; sits in a directory and SPAWNS sessions on demand from the phone (capacity 32) | its own terminal tile (`Server` on this machine) |
| **The client** | the phone / browser; the URL is `https://claude.ai/code?environment=env_…` — one *environment* per machine login | nothing to start |

`--remote-control` takes an OPTIONAL name. Give it explicitly (`--remote-control 'AGENT
BENCH'`); a bare flag followed by another token can swallow that token as the name.
`/rc` is the short form of `/remote-control` (the string is in the 2.1.278 binary;
identical behaviour UNMEASURED here — the long form is what the record shows working).

There is also a **setting**, `remoteControlAtStartup` (user-level `settings.json`; a
project/local `false` overrides it; not set anywhere on this machine as of 2026-09-19).
It would enable RC on every interactive session including ones the owner opens by hand
with a bare `claude`, but its interaction with `claude -p` consumers (the in-game
Oracle) is UNMEASURED — clutter on the phone list is the risk. Sibling keys seen in the
binary: `remoteControlSessionNamePrefix`, `autoAddRemoteControlDaemonWorker`,
`remoteTools.allowUnattendedServing`. Meaning UNMEASURED; listed so nobody re-mines
the binary for them.

## Three layers, and which ones this machine has

The reliability model (owner's research note, 2026-09-19, written for a week-long trip):

| layer | what | on the Windows Desktop |
|---|---|---|
| 1 — primary | each working window with RC on (`--remote-control` at launch, not `/rc` later) | ✅ every profile, since 2026-09-19 |
| 2 — server | `claude remote-control` as a machine-level entry point that spawns fresh sessions | ✅ the `Server` tile |
| 3 — break-glass | a route into the machine that does **not** depend on Anthropic at all (Tailscale + SSH + tmux, or equivalent) | ✅ **MEASURED 2026-09-19 07:42**: Tailscale in WSL with Tailscale SSH (`scripts/setup_break_glass.sh`), node `desktop-wsl`, first phone login accepted; `WSL Keepalive` logon task (`scripts/wsl_keepalive.vbs`) keeps the distro up after a reboot. From the phone: Termius → `owner@desktop-wsl`, then `tmux` + `claude --remote-control 'RESCUE' --resume`. |

Layer 3 matters because layers 1 and 2 share every failure that lives on Anthropic's
side or in the machine's login state: a `/login`, an account/org change, a registration
that ages out, and (per the docs) a server that **stops after a grace period during a
prolonged network outage**. Without it, an unattended machine whose RC drops is
stranded until someone is physically at the desk. The owner said yes to it 2026-09-19;
it is a security decision (a listener on his machine, tailnet-only), so its scope stays
as the script defines it — nobody widens it without his word.

## Why windows drop — the one root cause (MEASURED 2026-09-19)

**Every machine-wide RC drop in the record was a `/login` in one window.** Four events
(2026-09-08 04:00, 09-10 01:51, 09-12 18:50, 09-17 02:25), four windows each; in every
one, exactly one window printed `Login successful` and the others printed, to the same
minute:

> Remote Control disconnected — signed-in claude.ai account or organization changed on
> this machine — run /remote-control to start a session for the current account, or
> /login to switch back, then /remote-control

So: a login rewrites the machine's credential, every other window sees "account
changed", and RC dies fleet-wide. This is not the server flaking. Consequences:

- **`--remote-control` at launch does not prevent the drop.** It guarantees RC on every
  (re)start, which is the recovery path — not immunity.
- **Never `/login` while other windows hold RC** unless you accept re-enabling RC in
  each of them, by hand, at the desk. Do it at a fleet restart instead.
- Whether the standalone server survives a `/login` elsewhere: **UNMEASURED**. Assume it
  does not until someone checks; treat the Server tile as a recovery aid, not a
  guarantee.

Other drop causes are **reported upstream, not measured here**: `/clear` creating a new
conversation identity the registration does not follow (anthropics/claude-code#82462 —
newer builds claim to have fixed `/clear`/`/compact`/reconnect, so prefer `/compact`
when the goal is only smaller context and re-check the phone after a `/clear`);
registrations ageing out after long inactivity; drops after network or auth changes
(#83193, #77340, #67360, #78878, #80447 — listed in the private incident log). If
one of these is seen on this machine, record it in your incident log with the string it
printed, and it stops being hearsay.

## What an agent can and cannot do about RC (MEASURED 2026-09-19)

| can | cannot |
|---|---|
| **See who has RC.** `ListAgents` lists RC sessions (`· Remote Control · offline`); a `SendMessage` result says *"it is also connected via Remote Control"* for a connected peer. | **Turn RC on in itself or a peer.** `/remote-control` is a user slash command; no tool reaches it. |
| **Open a new Windows Terminal window from WSL**: `/mnt/c/Users/<you>/AppData/Local/Microsoft/WindowsApps/wt.exe -w new -p "<profile>"` (MEASURED 2026-09-19: launched the `Server` tile from a BENCH shell; process up in 11 s). | **Make a relay work.** Today the EMERGENCY window relayed *"resume remote control"* to three peers; **2 of 3 refused it as an unverified peer message and the third could only print a line asking the owner to type it.** Zero windows regained RC. |
| **Kill a window's process by PID** from `~/.claude/sessions/<pid>.json`, on the owner's word only. | **Run `broadcast.py`** to reach peers — it is the owner's tool (game-state carve-out aside). |

**Doctrine (owner, 2026-08-19): agents do not message each other.** A relayed owner
sentence is still a relay; the receiving window is right to hold it. So when the owner,
from the phone, asks the window he can reach to "get the others back": do not send
"please resume remote control" — it has a measured 0% success rate. Do the procedure
below. And when you are the window RECEIVING such a relay, answer in three parts, one
line each: you cannot toggle RC; the fix is `/remote-control` at the desk or a relaunch
of the profile (which carries the flag); and the probable cause is a `/login` in some
window — say so, because the owner will otherwise go hunting for a server fault.

## Procedures

### A. A window is lost (RC dropped) and the owner is on the phone

1. **Reach any window that still has RC**, or spawn a fresh session from the `Server`
   tile (it is NOT a row in the Recents session list while it has 0 sessions — MEASURED
   2026-10-28: `Connected · Capacity 0/32`, absent from Recents; reach it by its environment
   URL `https://claude.ai/code?environment=env_…`, printed in the tile; spawned sessions open in
   BENCH's clone, `/home/owner/rm/bench`).
2. **Diagnose, don't guess**: `ListAgents`; note which peers are `interactive` vs
   `Remote Control`, `busy` vs `idle`. Report the roster to the owner in one line.
3. **Decide with the owner whether the lost window must be restarted.** Its context is
   the cost. If it is `idle` and its work is committed and pushed (`git log`, ledger,
   handoff file), restarting loses little. If it is `busy`, wait for it to finish — a
   kill mid-write is the expensive mistake.
4. **Owner's word, then**: kill by PID (never `pkill -f <pattern>` — it has killed the
   caller's own shell twice), then relaunch the tile:
   `wt.exe -w new -p "AGENT FOUNDRY"` (profile names are the live titles: `AGENT
   BENCH`, `AGENT FOUNDRY`, `HESTIA`, `EMERGENCY`, `Artist`, `Server`). Profiles carry
   `--remote-control`, so the new window appears on the phone by itself.
5. If the lost window must hand off first and cannot be reached from the phone, the
   owner types the handoff request into it **at the desk**, or accepts the loss. A relay
   asking it to hand off *may* be honoured (it is ordinary work, not a permission
   change) — but confirm by watching the handoff file land, never by the relay's
   "queued" result.

### B. After a `/login` (planned or not)

Every other window has just lost RC. At the desk: `/remote-control` in each. From the
phone: only the Server tile (if it survived — UNMEASURED) or a full fleet relaunch via
the Desktop shortcut restores reach; procedure A per window otherwise. When the owner
ASKS before logging in — he is about to travel, typically — answer with procedure F's
list, and say plainly which of its steps are measured and which are not: the fleet-wide
drop is measured; the Server's survival is not; the rehearsal is what turns the second
into the first.

### C. Resuming a conversation in a second terminal

> Remote Control not started here · another Claude Code on this machine (started 4h ago)
> already has Remote Control for this conversation … run /remote-control to move it to
> this terminal

(MEASURED 2026-09-06.) RC attaches to a *conversation*, one holder at a time. Type
`/remote-control` in the terminal you are actually using; the old holder loses it.

### D. Restarting the standalone server

`claude remote-control --continue` reattaches to the server session last recorded for
the directory (within ~4 h); `--session-id <id>` reattaches a specific one. On a stale
record it errors rather than silently starting a fresh environment — that is the
signal to just start a new one. The server's own shutdown line — *"Environment
preserved. Restart `claude remote-control` to reconnect existing sessions."* — means the
sessions it spawned outlive it (MEASURED 2026-09-19 on a clean SIGTERM).

### E. Recovering a conversation, not just a window

The conversation is on disk (`~/.claude/projects/<cwd-slug>/<session>.jsonl`) whatever
happened to its RC entry. From a Server-spawned session in the same directory,
`claude --resume` (or `--resume <id>`) brings the old conversation back into a new
process, which then has RC because its launch does. That is the phone-side answer to
"the window is gone and its context mattered" — it costs a window, not the work.

### F. Before leaving the machine unattended for days

1. Update Claude Code, then launch the fleet from the Desktop shortcut so every window
   starts with RC and the Server is up. Check the phone lists ALL of them.
2. Do any `/login` NOW, then relaunch — never during the trip.
3. Rehearse the failure once: kill one window's RC (`/rc` toggles it off), confirm you
   can still reach the machine through the Server, spawn a session, `--resume` the
   conversation.
4. Power: the machine must not sleep or hibernate; Windows Update reboots are the
   silent killer of a week-long fleet (UNMEASURED how the fleet behaves after one —
   the Desktop shortcut is not an autostart).
5. Accept, out loud, that without a Layer-3 route a fleet-wide drop ends the trip's
   remote work. If that is not acceptable, build Layer 3 before leaving.

## The phone-side commands: `rc`

The owner is not going to type Linux on a phone. `scripts/rc` (symlinked to
`~/.local/bin/rc` and `~/.local/bin/rescue`) is the whole break-glass vocabulary, and
`~/.zshrc` prints its `rc welcome` banner on every SSH login so Termius opens onto the
menu. MEASURED 2026-09-19: `rc rescue` started a bounded `claude --remote-control RESCUE`
inside tmux in 4 s and it registered as `RESCUE`.

| he types | it does |
|---|---|
| `rc` | status (tailscale, live Claude windows, server, tmux, whether this shell can open desktop windows) + menu |
| `rc rescue` | a Claude with RC on, in tmux session `rescue`, in the RimMandrake repo → appears in the phone app as **RESCUE** |
| `rc server` | starts `claude remote-control` in tmux if none is running |
| `rc fleet` / `rc bench` … | relaunch the fleet / one tile via `wt.exe` (MEASURED 2026-09-19 from Termius over Tailscale: interop is available, so desktop windows open from the phone) — refuses with a plain sentence if interop is ever unavailable |
| `rc kill rescue` | removes the rescue session once the real windows are back |

| `rc account` | which Claude account is live, and the saved slots with their token lifetime |
| `rc account add <name>` | one-time: sign in as the other account (browser), saved as a slot |
| `rc account <name>` | switch accounts by swapping saved credentials — no browser — then `rc fleet` |

Keep it that small. A verb he has to look up is a verb he will not use on a phone.

## Two accounts (owner, 2026-09-19: two Max subscriptions, switched 1–2× a week)

`scripts/rc_account.py` keeps one slot per account under `~/.claude/accounts/<name>/`
(the credentials file + the `oauthAccount` identity block from `~/.claude.json`, mode
0600). A switch saves the live login back to its own slot FIRST, then swaps the other
in, then stops the RC server. It never restarts windows: they keep the old token until
restarted and WILL print the "account changed" line — the switch is a `/login` in
effect, so do it at a fleet boundary and follow with `rc fleet`. Refresh tokens live
~4 weeks (MEASURED: `refreshTokenExpiresAt`), so a slot used weekly never goes stale;
`rc account` shows the days left. **MEASURED 2026-09-19**, both accounts live on this
machine: `rc account add second` saved the running login back to `first`, ran the browser
sign-in once, and stored `second`; `rc account first` then switched back with **no browser
and no prompt** — `claude auth status` reported `loggedIn: true, authMethod: claude.ai`
straight after. So a switch costs one second, and only the windows need restarting.
Note the CLI's login flow prints a URL and waits for a pasted code: if the browser does
not open (it did not, from WSL), hand the URL over and paste the code back — that part
is genuinely the owner's, since it is another person's account and their browser session.
The phone's Claude app has to be on the same account to see the machine.

## Configuration on this machine (Windows Desktop, WSL Ubuntu)

Source of truth: `/home/owner/rm/bench/src/RimMandrake/Utils/install_wt_seat_profiles.py`
(writes Windows Terminal profiles; `--apply` after any change) and
`D:\owner\dev\RimMandrake\src\RimMandrake\Utils\launch_fleet.ps1` (the Desktop shortcut
`Start Agent Fleet.lnk` runs it; opens `SERVER` first, then HESTIA, Artist, EMERGENCY,
FOUNDRY, BENCH, tiled). Ruled by the owner 2026-09-19 after the drops above:

- since 2026-10-02 each seat runs in its own ext4 clone — BENCH `/home/owner/rm/bench`,
  FOUNDRY `/home/owner/rm/foundry` — and launches THAT clone's `claude_bounded.sh`;
  Server runs in BENCH's clone; HESTIA and EMERGENCY keep their cwd and use BENCH's copy;
- every Claude profile launches `claude_bounded.sh --dangerously-skip-permissions --name
  '<label>' --model <m> --remote-control '<label>'`;
- `Server` (white, `#FFFFFF`, top-right below Artist) runs `MEM_MAX=16G
  claude_bounded.sh remote-control --name 'Server' --permission-mode
  bypassPermissions` — through the same memory-bounded scope as the seats because its
  spawned sessions inherit the cgroup.

The exact profile lines and placements are in a private machine map, not published.

## Traps

- **`claude remote-control --help` prints and then HANGS** (MEASURED 2026-09-19, twice,
  had to be killed). Use `claude --help | grep -A2 remote` for the flag list.
- **`/btw` isn't available over Remote Control** (MEASURED 2026-08-31).
- **The phone attributes as the owner.** The house rule: `iPhone → the account owner`. A
  message arriving over RC is him, not a new actor.
- **A `/login` prompt can appear on its own** when a token expires; typing it in one
  window is the fleet-wide drop above. Prefer to do it once, at a fleet restart, and
  say so.
- **"Queued" is not "delivered".** A `SendMessage` result of `success:true … queued
  there` means the peer will *see* it; the peer's decision arrives later as a
  `[Cross-session delivery notice]` or not at all.

## Evidence

A private incident log (not published: it carries addresses and session ids) holds every dated RC event found in the transcripts
(2026-08-31 → 2026-09-19), with the exact strings, so the claims above can be
re-measured rather than believed.
