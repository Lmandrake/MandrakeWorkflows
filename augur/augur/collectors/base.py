"""The collector contract (DESIGN.md section 4). Every collector module follows it.

A collector is an object with:
    name: str            unique, used for the per-collector cost line and collectors.json switches
    tier: str            "fast" | "agents" | "probes" | "counts"
    platforms: tuple     e.g. ("darwin",)
    signals: tuple       the signal paths it produces (see below); a collector that raises gets
                         every one of these marked {"unknown": "read_failed"} by the core
    collect(ctx) -> dict {signal_path: value}
    drain_worker_cpu()   optional: CPU seconds its own worker threads burnt since the last call;
                         the core adds it to the collector's cost line (thread_time cannot see it).
    lpm_exempt: bool     default False. In Low Power Mode the core stops the probes tier and marks
                         its signals {"unknown": "disabled"}; thermal and power set this True so
                         they keep running (they are how LPM is seen at all).

Signal paths and their values (the core stamps observed_at / valid_until, never the collector):
    "machine.<key>"      a dict of value keys for machine.<key> (schema $defs), e.g.
                         {"busy_pct": 12.5, "cores_busy": 1.25, "ncpu": 10}.
                         {"unknown": "<reason>"} when the source exists but this read failed
                         (reasons: warming_up, read_failed, timeout, counter_reset,
                         gap_after_sleep, disabled, not_permitted, stale, truncated).
                         Then NO value keys.
                         Omit the path entirely when this machine has no source (power on the
                         Desktop): absent, never zero. A value of None is dropped by the core.
                         "provisional": True may ride along with values.
    "sessions"           a list of session identity dicts (schema $defs/session): id, pid,
                         started_at, project, project_key, managed (omit when unknowable), plus
                         nested signal value dicts "load" and "tasks" (stamped by the core).
    "sessions.attention" {session_id: {"state": ..., "since": ...}} merged into sessions[] by id
    "sessions.net"       {session_id: {rx_mbps, tx_mbps, flows, retx_pct}}; or
                         {"unknown": "<reason>"} = every live session's net reads unknown.
                         Omit the path = sessions[].net absent.

ctx (core.Ctx): now (epoch s, wall), mono (monotonic s), cadence {tier: s}, state (a dict private
to this collector that persists between calls), shared (one dict shared by all collectors),
home (the user's HOME), storage (Augur's home dir, ~/ClaudeWork/augur), lodestar (Lodestar
checkout path or None).

Shared keys in use:
    shared["session_trees"]      {session_id: [pid, ...]}  written by the sessions collector
    shared["agent_wait_s_per_s"] float or None              written by the sessions collector
    shared["low_power"]          bool or None               written by the thermal collector
    shared["on_battery"]         bool or None               written by the power collector
    shared["session_ids_by_pid"] {pid: session_id}          written by the sessions collector
    shared["transcript_dirs"]    {session_id: ~/.claude/projects/<slug>} by the sessions collector
    shared["audit"]              dict, cumulative counters for the pilot-1 checker (never in the
                                 snapshot; written to the 0600 history only)

Collectors stay pure where they can: readers are injectable (constructor `readers=` or similar)
so tests replay recorded fixtures on any OS. Floats are rounded to 2-3 decimals. Never put a
path, command line, remote address, SSID, title or session name in a value.
"""


class Collector(object):
    name = "base"
    tier = "fast"
    platforms = ("darwin",)
    signals = ()
    lpm_exempt = False

    def collect(self, ctx):  # pragma: no cover - interface
        raise NotImplementedError
