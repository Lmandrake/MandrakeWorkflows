"""Vendored in-process macOS readers for Augur (DESIGN.md section 4). Stdlib ctypes only, no spawns.

Every function marked `# from Lodestar bin/lib/<file>.py@<sha> <name>` is copied verbatim from that
Lodestar revision (tests/test_vendored_drift.py diffs them and warns on drift; it never blocks).
Augur imports nothing from ~/dev/Lodestar at runtime. Functions below the "Augur's own" line are new.

Thermal note: DESIGN.md names notify "com.apple.system.thermalstate"; hostnative reads
"com.apple.system.thermalpressurelevel" (0 nominal, 1 moderate, 2 heavy, 3 trapping, 4 sleeping),
the value ProcessInfo.thermalState reads. Augur uses hostnative's key and clamps 4 -> 3 for the
schema's 0..3 (thermal_state below).
"""

import ctypes
import json
import os
import plistlib
import socket
import struct
import threading
import time
from typing import Dict, List, Optional, Tuple


# ------------------------------------------------------------------ libraries and constants

# from Lodestar bin/lib/hostnative.py@098ae26c PRIO_DARWIN_PROCESS
PRIO_DARWIN_PROCESS, PRIO_DARWIN_BG = 4, 0x1000

# from Lodestar bin/lib/hostnative.py@098ae26c PROC_PIDTBSDINFO
PROC_PIDTBSDINFO, PROC_PIDTASKINFO = 3, 4

# from Lodestar bin/lib/hostnative.py@098ae26c _L
_L: Dict[str, ctypes.CDLL] = {}

# from Lodestar bin/lib/hostnative.py@098ae26c _TB
_TB: List[float] = []

# from Lodestar bin/lib/hostnative.py@098ae26c _sys
def _sys():
    if "sys" not in _L:
        s = ctypes.CDLL("/usr/lib/libSystem.dylib", use_errno=True)
        s.mach_host_self.restype = ctypes.c_uint
        _L["sys"] = s
    return _L["sys"]

# from Lodestar bin/lib/hostnative.py@098ae26c _proc
def _proc():
    if "proc" not in _L:
        _L["proc"] = ctypes.CDLL("/usr/lib/libproc.dylib", use_errno=True)
    return _L["proc"]

# from Lodestar bin/lib/hostnative.py@098ae26c _proc_fast
def _proc_fast():
    """libproc through ctypes.PyDLL: the call does NOT release the GIL. For the sweep's struct
    copies only (proc_listallpids, proc_pidinfo BSDINFO, proc_pid_rusage), which never block on
    I/O. Through CDLL every one of ~3,000 calls per sweep dropped and re-took the GIL, and with
    another thread of the collector runnable each re-take could wait a full switch interval
    (5 ms) or, if that thread was itself starved of a core, much longer (D1, LODE-19: 7.5-8.9 s
    sweeps at 20 busy threads). Path lookups (pidpath, cwd, cmdline) stay on CDLL."""
    if "procf" not in _L:
        _L["procf"] = ctypes.PyDLL("/usr/lib/libproc.dylib", use_errno=True)
    return _L["procf"]

# from Lodestar bin/lib/hostnative.py@098ae26c _abs_to_s
def _abs_to_s(t: int) -> float:
    if not _TB:
        class TB(ctypes.Structure):
            _fields_ = [("numer", ctypes.c_uint32), ("denom", ctypes.c_uint32)]
        tb = TB()
        _sys().mach_timebase_info(ctypes.byref(tb))
        _TB.append(tb.numer / float(tb.denom) / 1e9)
    return t * _TB[0]


# ------------------------------------------------------------------ sysctl / host statistics

# from Lodestar bin/lib/hostnative.py@098ae26c sysctl_int
def sysctl_int(name: str, size: int = 4) -> Optional[int]:
    v = ctypes.c_int64(0) if size == 8 else ctypes.c_int32(0)
    sz = ctypes.c_size_t(size)
    if _sys().sysctlbyname(name.encode(), ctypes.byref(v), ctypes.byref(sz), None, 0) != 0:
        return None
    return int(v.value)

# from Lodestar bin/lib/hostnative.py@098ae26c mem_pressure_level
def mem_pressure_level() -> Optional[int]:
    """1 normal, 2 warn, 4 critical (kern.memorystatus_vm_pressure_level)."""
    return sysctl_int("kern.memorystatus_vm_pressure_level")

# from Lodestar bin/lib/hostnative.py@098ae26c memsize_bytes
def memsize_bytes() -> Optional[int]:
    return sysctl_int("hw.memsize", 8)

# from Lodestar bin/lib/hostnative.py@098ae26c cpu_ticks
def cpu_ticks() -> Optional[Tuple[int, int, int, int]]:
    """(user, system, idle, nice) cumulative ticks over all cores."""
    a = (ctypes.c_uint32 * 4)()
    n = ctypes.c_uint(4)
    s = _sys()
    if s.host_statistics(s.mach_host_self(), 3, a, ctypes.byref(n)) != 0:
        return None
    return tuple(a)  # type: ignore[return-value]

# from Lodestar bin/lib/hostnative.py@098ae26c vm_counters
def vm_counters() -> Optional[Dict[str, float]]:
    """Cumulative pageins/pageouts/swapins/swapouts and the available-memory percentage, from
    host_statistics64(HOST_VM_INFO64). Offsets: struct vm_statistics64 (152 bytes)."""
    s = _sys()
    buf = (ctypes.c_uint32 * 40)()
    n = ctypes.c_uint(38)
    if s.host_statistics64(s.mach_host_self(), 4, buf, ctypes.byref(n)) != 0:
        return None
    b = bytes(buf)
    free, _active, inactive, _wired = struct.unpack_from("4I", b, 0)
    pageins, pageouts = struct.unpack_from("2Q", b, 32)
    purgeable, speculative = struct.unpack_from("2I", b, 88)
    swapins, swapouts = struct.unpack_from("2Q", b, 112)
    page = sysctl_int("hw.pagesize", 8) or 16384
    mem = memsize_bytes()
    avail = (100.0 * (free + inactive + speculative + purgeable) * page / mem) if mem else None
    return {"pageins": pageins, "pageouts": pageouts, "swapins": swapins, "swapouts": swapouts,
            "avail_pct": avail}


# ------------------------------------------------------------------ notify (thermal, low power)

# from Lodestar bin/lib/hostnative.py@098ae26c _notify_state
def _notify_state(name: bytes) -> Optional[int]:
    s = _sys()
    tok = ctypes.c_int(0)
    st = ctypes.c_uint64(0)
    if s.notify_register_check(name, ctypes.byref(tok)) != 0:
        return None
    try:
        if s.notify_get_state(tok, ctypes.byref(st)) != 0:
            return None
        return int(st.value)
    finally:
        s.notify_cancel(tok)

# from Lodestar bin/lib/hostnative.py@098ae26c thermal_level
def thermal_level() -> Optional[int]:
    """OSThermalPressureLevel: 0 nominal, 1 moderate, 2 heavy, 3 trapping, 4 sleeping (the same
    value ProcessInfo.thermalState reads; `pmset -g therm` reports nothing on this Mac)."""
    return _notify_state(b"com.apple.system.thermalpressurelevel")

# from Lodestar bin/lib/hostnative.py@098ae26c low_power_mode
def low_power_mode() -> Optional[bool]:
    v = _notify_state(b"com.apple.system.lowpowermode")
    return None if v is None else bool(v)


# ------------------------------------------------------------------ processes (the sessions collector imports these)

# from Lodestar bin/lib/hostnative.py@098ae26c all_pids
def all_pids() -> List[int]:
    p = _proc_fast()
    n = p.proc_listallpids(None, 0)
    if n <= 0:
        return []
    buf = (ctypes.c_int * (n + 128))()
    n = p.proc_listallpids(buf, ctypes.sizeof(buf))
    return [x for x in buf[:max(0, n)] if x > 0]

# from Lodestar bin/lib/hostnative.py@098ae26c bsdinfo
def bsdinfo(pid: int) -> Optional[Tuple[int, int, int, str]]:
    """(ppid, uid, start_epoch_s, comm) or None (gone, or another uid: libproc refuses)."""
    b = ctypes.create_string_buffer(136)
    if _proc_fast().proc_pidinfo(int(pid), PROC_PIDTBSDINFO, 0, b, 136) != 136:
        return None
    ppid, uid = struct.unpack_from("<II", b.raw, 16)
    comm = b.raw[48:64].split(b"\0", 1)[0].decode("utf-8", "replace")
    return ppid, uid, struct.unpack_from("<Q", b.raw, 120)[0], comm

# from Lodestar bin/lib/hostnative.py@098ae26c start_epoch
def start_epoch(pid: int) -> Optional[int]:
    bi = bsdinfo(pid)
    return bi[2] if bi else None

# from Lodestar bin/lib/hostnative.py@098ae26c pid_alive
def pid_alive(pid: int) -> bool:
    """libproc, never os.kill (os.kill stalled under load: Lodestar LESSONS 2026-10-22)."""
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return False
    buf = ctypes.create_string_buffer(4096)
    if _proc().proc_pidpath(pid, buf, 4096) > 0:
        return True
    return ctypes.get_errno() == 1   # EPERM: exists, not ours

# from Lodestar bin/lib/hostnative.py@098ae26c rusage
def rusage(pid: int) -> Optional[Tuple[float, float, int, int]]:
    """(cpu_s, runnable_s, phys_footprint_bytes, disk_bytes_rw) from proc_pid_rusage
    (RUSAGE_INFO_V4, a V4-sized buffer: flavor 6 with a V6 struct segfaulted); own uid only.
    Indices are u64 slots of struct rusage_info_v4 (uuid = slots 0-1)."""
    buf = (ctypes.c_uint64 * 64)()
    if _proc_fast().proc_pid_rusage(int(pid), 4, buf) != 0:
        return None
    return _abs_to_s(buf[2] + buf[3]), _abs_to_s(buf[36]), int(buf[9]), int(buf[18] + buf[19])

# from Lodestar bin/lib/hostnative.py@098ae26c pidpath
def pidpath(pid: int) -> str:
    b = ctypes.create_string_buffer(4096)
    return b.value.decode("utf-8", "replace") if _proc().proc_pidpath(int(pid), b, 4096) > 0 else ""

# from Lodestar bin/lib/hostnative.py@098ae26c cmdline
def cmdline(pid: int) -> str:
    """argv joined by spaces (sysctl KERN_PROCARGS2; own uid only)."""
    mib = (ctypes.c_int * 3)(1, 49, int(pid))
    size = ctypes.c_size_t(65536)
    b = ctypes.create_string_buffer(size.value)
    if _sys().sysctl(mib, 3, b, ctypes.byref(size), None, 0) != 0:
        return ""
    raw = b.raw[:size.value]
    if len(raw) < 4:
        return ""
    argc = struct.unpack_from("<i", raw, 0)[0]
    parts = [p for p in raw[4:].split(b"\0") if p][1:1 + argc]
    return " ".join(p.decode("utf-8", "replace") for p in parts)

# from Lodestar bin/lib/hostnative.py@098ae26c cwd
def cwd(pid: int) -> str:
    """The process's current directory (PROC_PIDVNODEPATHINFO: vnode_info 152 bytes, then the
    1024-byte path). Own uid only; '' when unreadable."""
    b = ctypes.create_string_buffer(2352)
    if _proc().proc_pidinfo(int(pid), 9, 0, b, 2352) <= 0:
        return ""
    return b.raw[152:152 + 1024].split(b"\0", 1)[0].decode("utf-8", "replace")


# ------------------------------------------------------------------ network (netwatch)

# from Lodestar bin/lib/netwatch.py@51517eaa IFT_ETHER
IFT_ETHER, IFT_LOOP, IFT_GIF, IFT_STF, IFT_OTHER = 0x06, 0x18, 0x37, 0x39, 0x01

# from Lodestar bin/lib/netwatch.py@51517eaa IFF_UP
IFF_UP, IFF_RUNNING, IFF_POINTOPOINT = 0x1, 0x40, 0x10

# from Lodestar bin/lib/netwatch.py@51517eaa _d
def _d(new, old, bits=64):
    if new >= old:
        return new - old
    if bits == 32 and old - new > (1 << 31):
        return new + (1 << 32) - old         # 32-bit wrap
    return None                              # reset: no delta this tick

_IFNAME = {}


def _ifname(idx):
    """if_indextoname, cached: ~26 syscalls per fast tick otherwise (measured 0.6 ms of 1.5 ms).
    An index is reused only after an interface is destroyed; a miss or error drops the cache."""
    n = _IFNAME.get(idx)
    if n is None:
        n = socket.if_indextoname(idx)
        if len(_IFNAME) > 256:
            _IFNAME.clear()
        _IFNAME[idx] = n
    return n


# from Lodestar bin/lib/netwatch.py@51517eaa if_counters
# modified: socket.if_indextoname -> cached _ifname (cost)
def if_counters():
    """{name: {type, flags, ibytes, obytes, ierrors, oerrors, iqdrops, baud}} via NET_RT_IFLIST2."""
    s = _sys()
    mib = (ctypes.c_int * 6)(4, 17, 0, 0, 6, 0)       # CTL_NET, PF_ROUTE, 0, 0, NET_RT_IFLIST2, 0
    n = ctypes.c_size_t(0)
    if s.sysctl(mib, 6, None, ctypes.byref(n), None, 0) != 0:
        return {}
    b = ctypes.create_string_buffer(n.value + 8192)
    n = ctypes.c_size_t(len(b))
    if s.sysctl(mib, 6, b, ctypes.byref(n), None, 0) != 0:
        return {}
    raw, o, out = b.raw[:n.value], 0, {}
    while o + 4 <= len(raw):
        ml, _ver, typ = struct.unpack_from("<HBB", raw, o)
        if ml == 0:
            break
        if typ == 0x12 and o + 32 + 128 <= len(raw):      # RTM_IFINFO2
            flags, idx = struct.unpack_from("<iH", raw, o + 8)
            d = o + 32                                     # if_data64
            baud, = struct.unpack_from("<Q", raw, d + 16)
            ipk, ierr, opk, oerr, _col, ib, ob = struct.unpack_from("<7Q", raw, d + 24)
            iqd, = struct.unpack_from("<Q", raw, d + 96)
            try:
                name = _ifname(idx)
            except OSError:
                name = "if%d" % idx
            out[name] = {"type": raw[d], "flags": flags, "ibytes": ib, "obytes": ob,
                         "ierrors": ierr, "oerrors": oerr, "iqdrops": iqd, "baud": baud}
        o += ml
    return out

# from Lodestar bin/lib/netwatch.py@51517eaa default_routes
# modified: socket.if_indextoname -> cached _ifname (cost)
def default_routes():
    """[(interface, gateway_ip, flags)] for IPv4 default routes, primary first (NET_RT_DUMP)."""
    s = _sys()
    mib = (ctypes.c_int * 6)(4, 17, 0, 2, 1, 0)       # CTL_NET, PF_ROUTE, 0, AF_INET, NET_RT_DUMP, 0
    n = ctypes.c_size_t(0)
    if s.sysctl(mib, 6, None, ctypes.byref(n), None, 0) != 0:
        return []
    b = ctypes.create_string_buffer(n.value + 8192)
    n = ctypes.c_size_t(len(b))
    if s.sysctl(mib, 6, b, ctypes.byref(n), None, 0) != 0:
        return []
    raw, o, out = b.raw[:n.value], 0, []
    while o + 92 <= len(raw):
        ml, = struct.unpack_from("<H", raw, o)
        if ml == 0:
            break
        idx, = struct.unpack_from("<H", raw, o + 4)
        flags, addrs = struct.unpack_from("<ii", raw, o + 8)
        p = o + 92                                         # sizeof(rt_msghdr)
        sas = {}
        for bit in range(8):
            if addrs & (1 << bit):
                if p >= o + ml:
                    break
                sl = raw[p] or 4
                sas[bit] = raw[p:p + sl]
                p += (sl + 3) & ~3
        dst, gw, mask = sas.get(0), sas.get(1), sas.get(2)
        is_default = dst is not None and len(dst) >= 8 and dst[1] == socket.AF_INET and dst[4:8] == b"\0\0\0\0" \
            and (mask is None or len(mask) < 8 or mask[4:8] in (b"\0\0\0\0", b"\0\0\0", b""))
        if is_default and (flags & 0x1) and gw is not None and len(gw) >= 8 and gw[1] == socket.AF_INET:
            try:
                name = _ifname(idx)
            except OSError:
                name = None
            out.append((name, socket.inet_ntoa(gw[4:8]), flags))
        o += ml
    # primary = the unscoped one (RTF_IFSCOPE 0x1000000 clear), as `route get default` picks
    out.sort(key=lambda r: 1 if r[2] & 0x1000000 else 0)
    return out

# from Lodestar bin/lib/netwatch.py@51517eaa _cksum
def _cksum(b):
    if len(b) % 2:
        b += b"\0"
    t = sum(struct.unpack("!%dH" % (len(b) // 2), b))
    t = (t >> 16) + (t & 0xffff)
    t += t >> 16
    return (~t) & 0xffff

# from Lodestar bin/lib/netwatch.py@51517eaa _SEQ
_SEQ = [0]

# from Lodestar bin/lib/netwatch.py@51517eaa ping_burst
def ping_burst(ip, ifname=None, count=4, gap=0.25, timeout=1.5):
    """count echoes on one unprivileged ICMP socket, gap s apart; [ms or None] per echo, in order.
    Each reply is matched by id and sequence, so a late answer is never credited to a later echo.
    Wall time at most (count-1)*gap + timeout."""
    import select
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_ICMP)
    except OSError:
        return []                      # no socket = no evidence, not loss
    ident = (os.getpid() ^ 0x5a5a) & 0xffff
    out, sent = [None] * count, {}
    try:
        s.setblocking(False)
        if ifname:
            try:
                s.setsockopt(socket.IPPROTO_IP, 25, socket.if_nametoindex(ifname))
            except OSError:
                return []              # interface gone: no evidence
        t0 = time.perf_counter()
        i = 0
        while True:
            now = time.perf_counter()
            if i < count and now >= t0 + i * gap:
                _SEQ[0] = (_SEQ[0] + 1) & 0xffff
                seq = _SEQ[0]
                p = struct.pack("!BBHHH", 8, 0, 0, ident, seq) + b"lodestar-path"
                p = p[:2] + struct.pack("!H", _cksum(p)) + p[4:]
                try:
                    s.sendto(p, (ip, 0))
                    sent[seq] = (i, time.perf_counter())
                except OSError:
                    out[i] = False     # never sent (no route): not an echo, dropped below
                i += 1
                continue
            end = t0 + (count - 1) * gap + timeout
            if now >= end or (i >= count and not sent):
                break
            nxt = min(end, t0 + i * gap) if i < count else end
            r, _w, _x = select.select([s], [], [], max(0.0, nxt - now))
            if not r:
                continue
            try:
                d, _a = s.recvfrom(512)
            except OSError:
                continue
            t = time.perf_counter()
            o = (d[0] & 0x0f) * 4 if d and d[0] >> 4 == 4 else 0
            if len(d) < o + 8:
                continue
            typ, _c, _k, rid, rseq = struct.unpack_from("!BBHHH", d, o)
            if typ == 0 and rid == ident and rseq in sent:
                k, ts = sent.pop(rseq)
                out[k] = (t - ts) * 1000.0
        return [r for r in out if r is not False]
    finally:
        s.close()

# from Lodestar bin/lib/netwatch.py@51517eaa DEFAULT_ANCHOR
DEFAULT_ANCHOR = "1.1.1.1"

# from Lodestar bin/lib/netwatch.py@51517eaa path_anchor
def path_anchor():
    """The upstream anchor for the path probe: $LODESTAR_NETWATCH_ANCHOR, else 1.1.1.1."""
    return (os.environ.get("LODESTAR_NETWATCH_ANCHOR") or "").strip() or DEFAULT_ANCHOR

# from Lodestar bin/lib/netwatch.py@51517eaa DEFAULT_PROBE_SSID
DEFAULT_PROBE_SSID = "OnSiteWifi"

# from Lodestar bin/lib/netwatch.py@51517eaa SSID_MAX_AGE
SSID_MAX_AGE = 120.0

# from Lodestar bin/lib/netwatch.py@51517eaa ssid_from_file
def ssid_from_file(path=None, now=None, max_age=SSID_MAX_AGE):
    """The SSID LodestarSSID.app last wrote (companion/ssid/, launchd com.lodestar.ssid, every
    60 s), or None. That app holds the Location Services grant a bare python cannot. Missing,
    unparseable, stale (> max_age s, or from the future), unauthorized or empty all read None,
    so the probe gate stays closed."""
    try:
        with open(path or SSID_FILE) as fh:
            d = json.load(fh)
        at = float(d.get("at"))
    except (OSError, ValueError, TypeError, AttributeError):
        return None
    age = (time.time() if now is None else now) - at
    if not (-5.0 <= age <= max_age) or d.get("authorized") is not True:
        return None
    ss = d.get("ssid")
    return ss if isinstance(ss, str) and ss.strip() else None

# from Lodestar bin/lib/netwatch.py@51517eaa is_tunnel
def is_tunnel(name, info=None):
    return name.startswith(("utun", "ipsec", "ppp", "gpd", "tun", "tap"))

# from Lodestar bin/lib/netwatch.py@51517eaa physical_for
def physical_for(counters, routes):
    """The physical interface carrying traffic: a non-tunnel default route, else the busiest
    up Ethernet-type interface."""
    for name, _gw, _f in routes:
        if name and not is_tunnel(name) and name in counters:
            return name
    best = None
    for n, c in counters.items():
        if c["type"] == IFT_ETHER and c["flags"] & IFF_UP and c["flags"] & IFF_RUNNING and not n.startswith(("awdl", "llw", "bridge", "ap")):
            if best is None or c["ibytes"] + c["obytes"] > counters[best]["ibytes"] + counters[best]["obytes"]:
                best = n
    return best


# ------------------------------------------------------------------ scheduling-delay burst (load_levels)

# from Lodestar bin/lib/load_levels.py@3f98c64b _lib
_lib = None

# from Lodestar bin/lib/load_levels.py@3f98c64b _libc
def _libc():
    global _lib
    if _lib is None:
        _lib = ctypes.CDLL("/usr/lib/libSystem.dylib")
        _lib.mach_host_self.restype = ctypes.c_uint
    return _lib

# from Lodestar bin/lib/load_levels.py@3f98c64b QOS
QOS = {"user_interactive": 0x21, "user_initiated": 0x19, "default": 0x15, "utility": 0x11,
       "background": 0x09}

# from Lodestar bin/lib/load_levels.py@3f98c64b burst_stretch
def burst_stretch(ms=20.0, qos="utility"):
    """Wall/CPU of one `ms` CPU burst on a fresh thread at `qos`: 1.0 = no wait for a core."""
    out = []

    def run():
        _libc().pthread_set_qos_class_self_np(QOS.get(qos, 0x11), 0)
        t, w = time.thread_time(), time.perf_counter()
        while time.thread_time() - t < ms / 1000.0:
            pass
        out.append((time.perf_counter() - w) / (time.thread_time() - t))
    th = threading.Thread(target=run, name="load_levels-burst")
    th.start()
    th.join()
    return out[0] if out else None


SSID_FILE = os.path.expanduser("~/dev/.lodestar/companion/ssid.json")   # ssid_from_file's default


# from Lodestar bin/lib/load_levels.py@3f98c64b _tree
def _tree(pid, limit=200):
    lib, out, todo = _libc(), [], [int(pid)]
    buf = (ctypes.c_int * 1024)()
    while todo and len(out) < limit:
        p = todo.pop()
        if p in out:
            continue
        out.append(p)
        ctypes.memset(buf, 0, ctypes.sizeof(buf))     # a count in bytes must not read stale pids
        n = lib.proc_listchildpids(p, buf, ctypes.sizeof(buf))
        todo.extend(buf[i] for i in range(max(0, min(n, 1024))) if buf[i] > 0)
    return out


# ================================================================== Augur's own (not vendored)

def thermal_state() -> Optional[int]:
    """thermal_level() mapped onto the schema's 0..3: 4 (sleeping) clamps to 3."""
    v = thermal_level()
    return None if v is None else max(0, min(3, int(v)))


def _ps():
    """CoreFoundation + IOKit power-source entry points, typed once."""
    if "ps" not in _L:
        vp = ctypes.c_void_p
        cf = ctypes.CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
        io = ctypes.CDLL("/System/Library/Frameworks/IOKit.framework/IOKit")
        io.IOPSCopyPowerSourcesInfo.restype = vp
        io.IOPSCopyPowerSourcesList.restype = vp
        io.IOPSCopyPowerSourcesList.argtypes = [vp]
        io.IOPSGetPowerSourceDescription.restype = vp
        io.IOPSGetPowerSourceDescription.argtypes = [vp, vp]
        cf.CFArrayGetCount.restype = ctypes.c_long
        cf.CFArrayGetCount.argtypes = [vp]
        cf.CFArrayGetValueAtIndex.restype = vp
        cf.CFArrayGetValueAtIndex.argtypes = [vp, ctypes.c_long]
        cf.CFDictionaryGetValue.restype = vp
        cf.CFDictionaryGetValue.argtypes = [vp, vp]
        cf.CFNumberGetValue.restype = ctypes.c_bool
        cf.CFNumberGetValue.argtypes = [vp, ctypes.c_int, vp]
        cf.CFStringGetCString.restype = ctypes.c_bool
        cf.CFStringGetCString.argtypes = [vp, ctypes.c_char_p, ctypes.c_long, ctypes.c_uint32]
        cf.CFStringCreateWithCString.restype = vp
        cf.CFStringCreateWithCString.argtypes = [vp, ctypes.c_char_p, ctypes.c_uint32]
        cf.CFRelease.argtypes = [vp]
        keys = {k: cf.CFStringCreateWithCString(None, k.encode(), 0x08000100)
                for k in ("Type", "Current Capacity", "Max Capacity", "Power Source State")}
        _L["ps"] = (cf, io, keys)
    return _L["ps"]


def battery_entry(kind, state, cur, mx) -> Dict:
    """The internal battery's entry from its raw values. An unreadable Power Source State is
    on_battery None (unknown), never "on AC" (R1 finding 16)."""
    pct = 100.0 * cur / mx if cur is not None and mx else None
    on = None if state is None else state == "Battery Power"
    return {"present": True, "on_battery": on, "battery_pct": pct}


def power_source() -> Optional[Dict]:
    """{"present": False} when no internal battery exists (the Desktop: the signal is absent);
    {"present": True, "on_battery": bool, "battery_pct": float or None} for the internal battery;
    None when the read failed. Reads the source dictionaries with CFDictionaryGetValue (keys
    "Type" == "InternalBattery", "Power Source State" == "Battery Power", "Current Capacity" /
    "Max Capacity"), never a description string."""
    try:
        cf, io, k = _ps()
    except OSError:
        return None
    blob = io.IOPSCopyPowerSourcesInfo()
    if not blob:
        return None
    buf = ctypes.create_string_buffer(64)

    def text(d, key):
        v = cf.CFDictionaryGetValue(d, k[key])
        return buf.value.decode() if v and cf.CFStringGetCString(v, buf, 64, 0x08000100) else None

    def num(d, key):
        v = cf.CFDictionaryGetValue(d, k[key])
        x = ctypes.c_int64(0)
        return int(x.value) if v and cf.CFNumberGetValue(v, 4, ctypes.byref(x)) else None
    try:
        lst = io.IOPSCopyPowerSourcesList(blob)
        if not lst:
            return None
        try:
            for i in range(cf.CFArrayGetCount(lst)):
                d = io.IOPSGetPowerSourceDescription(blob, cf.CFArrayGetValueAtIndex(lst, i))
                if not d or text(d, "Type") != "InternalBattery":
                    continue
                return battery_entry("InternalBattery", text(d, "Power Source State"),
                                     num(d, "Current Capacity"), num(d, "Max Capacity"))
            return {"present": False}
        finally:
            cf.CFRelease(lst)
    finally:
        cf.CFRelease(blob)


NETIF_PLIST = "/Library/Preferences/SystemConfiguration/NetworkInterfaces.plist"
_LINK = {"mtime": None, "types": {}}


def link_types(path: str = NETIF_PLIST) -> Dict[str, str]:
    """{bsd name: SCNetworkInterfaceType} ("IEEE80211", "Ethernet", ...), parsed with plistlib and
    cached by the file's mtime (one stat per call). {} when unreadable."""
    try:
        mt = os.stat(path).st_mtime
    except OSError:
        return {}
    if mt != _LINK["mtime"]:
        try:
            with open(path, "rb") as fh:
                d = plistlib.load(fh)
            _LINK["types"] = {i.get("BSD Name"): i.get("SCNetworkInterfaceType")
                              for i in d.get("Interfaces") or [] if i.get("BSD Name")}
        except Exception:  # noqa: BLE001 - unreadable plist: no types, link reads "other"
            _LINK["types"] = {}
        _LINK["mtime"] = mt
    return _LINK["types"]


def set_thread_qos(qos: str = "utility") -> bool:
    """Set the calling thread's QoS class (QOS from load_levels). True on success."""
    return _libc().pthread_set_qos_class_self_np(QOS.get(qos, 0x11), 0) == 0


def tree(pid: int, limit: int = 200) -> List[int]:
    """The pid and its descendants (proc_listchildpids walk, root first, capped at `limit`)."""
    return _tree(pid, limit)


def rusage_children(pid: int) -> Optional[Tuple[float, float, int, int, float]]:
    """rusage() plus the reaped children's CPU: (cpu_s, runnable_s, phys_footprint_bytes,
    disk_bytes_rw, child_cpu_s). child_cpu_s = ri_child_user_time + ri_child_system_time
    (rusage_info_v4 u64 slots 12 and 13): short-lived children born and reaped between two
    sweeps are only visible here."""
    buf = (ctypes.c_uint64 * 64)()
    if _proc_fast().proc_pid_rusage(int(pid), 4, buf) != 0:
        return None
    return (_abs_to_s(buf[2] + buf[3]), _abs_to_s(buf[36]), int(buf[9]), int(buf[18] + buf[19]),
            _abs_to_s(buf[12] + buf[13]))


def stdout_path(pid: int) -> str:
    """The path open on fd 1 (PROC_PIDFDVNODEPATHINFO: proc_fileinfo 24 + vnode_info 152, then the
    1024-byte path). Own uid only; '' when it is not a vnode or unreadable. Used only to tell a
    Bash-tool background shell (stdout = .../tasks/<id>.output) from others; never output."""
    b = ctypes.create_string_buffer(1200)
    if _proc().proc_pidfdinfo(int(pid), 1, 2, b, 1200) != 1200:
        return ""
    return b.raw[176:176 + 1024].split(b"\0", 1)[0].decode("utf-8", "replace")


def _procargs_env(raw: bytes, name: str) -> Optional[str]:
    """`name`'s value among the environment strings of a KERN_PROCARGS2 buffer: argc (int32), the
    exec path, NUL padding, argc argv strings, then env strings up to an empty one. None when the
    buffer is short or the name is absent. Pure, so it is tested on a hand-built buffer."""
    if len(raw) < 4:
        return None
    argc = struct.unpack_from("<i", raw, 0)[0]
    i = raw.find(b"\0", 4)
    if i < 0 or argc < 0:
        return None
    n = len(raw)
    while i < n and raw[i] == 0:
        i += 1
    for _ in range(argc):                 # argv strings, each NUL-terminated
        j = raw.find(b"\0", i)
        if j < 0:
            return None
        i = j + 1
    want = name.encode() + b"="
    while i < n:
        j = raw.find(b"\0", i)
        if j < 0:
            j = n
        s = raw[i:j]
        if not s:
            return None                   # end of the environment
        if s.startswith(want):
            return s[len(want):].decode("utf-8", "replace")
        i = j + 1
    return None


_ARGMAX: List[int] = []


def env_var(pid: int, name: str) -> Optional[str]:
    """One environment variable of a process as it was at exec (sysctl KERN_PROCARGS2; own uid
    only). None when unreadable or unset. R5-10: a running Claude Code session's children carry
    the ANTHROPIC_BASE_URL the session started with; settings.json names the NEXT session's."""
    if not _ARGMAX:
        _ARGMAX.append(sysctl_int("kern.argmax") or 1 << 20)
    mib = (ctypes.c_int * 3)(1, 49, int(pid))
    size = ctypes.c_size_t(0)
    # R6 F2: ask the kernel for this pid's size first (a few KB) rather than allocating
    # kern.argmax (1 MiB) per call, which the allocator kept as resident memory
    if _sys().sysctl(mib, 3, None, ctypes.byref(size), None, 0) != 0 or not size.value:
        return None
    size.value = min(size.value + 4096, _ARGMAX[0])
    b = ctypes.create_string_buffer(size.value)
    if _sys().sysctl(mib, 3, b, ctypes.byref(size), None, 0) != 0:
        return None
    return _procargs_env(b.raw[:size.value], name)
