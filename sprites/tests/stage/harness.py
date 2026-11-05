"""Shared harness for the headless stage tests (app/stage.html in ONE headless Chromium per test file).
Run each file through ~/agent-storage/sprites/live/native/tools/gate.py (tests/run_all.sh does): one render at a time,
nice 19, load < 8. Every check prints PASS/FAIL; done() exits 1 if any check failed.
KNOWN_OPEN: checks for review findings another fixer still owns. They print XFAIL and do not fail the run; once
they pass they print XPASS, a cue to drop the marker."""
import functools, http.server, json, socketserver, subprocess, sys, threading
from pathlib import Path
SPR = Path(__file__).resolve().parents[2]
FIX = SPR / "tests/fixtures"
SPECIES = ["c1_choir", "c2_siphon", "c3_sigils", "c4_kaleido", "c5_fireflies"]
_fails, _xfail = [], []

def check(ok, msg, open_finding=None):
    ok = bool(ok)
    if open_finding is not None:
        print(("XPASS " if ok else "XFAIL ") + f"(open R1 #{open_finding}) " + msg, flush=True)
        if not ok: _xfail.append(msg)
        return ok
    print(("PASS " if ok else "FAIL ") + msg, flush=True)
    if not ok: _fails.append(msg)
    return ok

def done():
    print("ALL PASS" if not _fails else f"{len(_fails)} FAIL", f"({len(_xfail)} known-open XFAIL)" if _xfail else "", flush=True)
    sys.exit(1 if _fails else 0)

def serve():
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a): pass
    h = functools.partial(Quiet, directory=str(SPR))
    srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), h); srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv.server_address[1]

PORT = serve()
def url(query="stale=0&dpr=1"): return f"http://127.0.0.1:{PORT}/app/stage.html?{query}"

def feed(*a):
    return json.loads(subprocess.check_output([sys.executable, str(SPR / "tools/demo_feed.py"), "--print", *a]))

def fixture(name): return json.loads((FIX / name).read_text())

def errors_on(pg):
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: m.type == "error" and errs.append(m.text))
    return errs

def layer_errors(pg):
    out = []
    for c in pg.evaluate("Object.keys(__stage.layers)"):
        out += pg.evaluate(f"(() => {{ const V = __stage.V({c!r}); return V ? [] : ['no layer {c}']; }})()")
    out += pg.evaluate("window.__errors || []")
    return out

class Layer:
    """evaluate(js) runs js with V, __report bound to one species' runtime instance (one-canvas stage)."""
    def __init__(self, pg, sp): self.pg, self.sp = pg, sp
    def evaluate(self, js):
        s = js.strip(); expr = f"({s})()" if s.startswith("()") else f"({s})"
        return self.pg.evaluate(f"""(() => {{ const V = __stage.V({self.sp!r}); if (!V) return null;
          const __report = V.__report; return {expr}; }})()""")

def one_session(scenario="calm"):
    """A single managed session from a demo_feed scenario, no projects (no ghosts)."""
    base = feed("--scenario", scenario, "--at", "30")
    base["sessions"] = [s for s in base["sessions"] if s.get("managed", True)][:1]; base["projects"] = []
    return base, base["sessions"][0]["project"]
