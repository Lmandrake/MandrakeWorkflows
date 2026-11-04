#!/usr/bin/env python3
"""claude-account page: one machine's account switcher, served to the tailnet by `tailscale serve`.

Listens on a unix socket (~/.claude-accounts/run/page.sock), which `tailscale serve` proxies
HTTPS to (adding the Tailscale-User-Login header it then trusts), and, when machine.json sets
page_port, on this node's tailnet IP (identity from `tailscale whois`, headers ignored). When
machine.json sets page_loopback_port it also listens on 127.0.0.1:<that port>, which WSL forwards
to the machine's own Windows browser (the main desktop's Windows side is not on the tailnet, and its
localhost:8765 is RimPulse). A loopback caller is the machine's own user: any local process can
already run `claude-account` itself, so this grants nothing new; it is answered only when the
Host header names the loopback port (no DNS rebinding) and POSTs keep the header/JSON/Origin
rules below (no cross-site request can add them). Every action shells out to the claude-account
CLI (same locks, same refusals).

  GET  /              the page (status, one button per account, enroll, warm)
  GET  /api/status    JSON status
  POST /api/use       {"account": "alt", "confirm": "<machine>"}   closes every Claude window
  POST /api/enroll    {"account": "alt"}                            returns the login URL
  POST /api/code      {"account": "alt", "op": "<id>", "code": "..."} code goes to the CLI on stdin
  POST /api/warm      {}                                               warm every dormant login

POSTs must be JSON and carry the header X-Claude-Account: 1 (a browser form cannot forge
either); a present Origin must match the Host. The login allowlist is machine.json "page_allow".
"""
import html
import json
import os
import socket
import socketserver
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler

HOME = os.path.expanduser("~")
ROOT = os.environ.get("CLAUDE_ACCOUNT_ROOT", os.path.join(HOME, ".claude-accounts"))
SOCK = os.path.join(ROOT, "run", "page.sock")
CLI = os.environ.get("CLAUDE_ACCOUNT_CLI", os.path.join(HOME, ".local", "bin", "claude-account"))
BUSY = threading.Lock()


def conf():
    with open(os.path.join(ROOT, "machine.json")) as fh:
        return json.load(fh)


def run_cli(args, stdin=None, timeout=300):
    try:
        r = subprocess.run([sys.executable, CLI, *args, "--json"], input=stdin, text=True,
                           capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"ok": False, "refused": f"claude-account {args[0]} timed out after {timeout} s"}
    out = r.stdout.strip()
    for cand in (out, out.splitlines()[-1] if out else ""):
        try:
            return json.loads(cand)
        except ValueError:
            pass
    else:
        return {"ok": False, "refused": (r.stderr or r.stdout).strip()[-400:] or f"exit {r.returncode}"}


PAGE = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Claude account: {label}</title>
<style>body{{font:16px system-ui,sans-serif;max-width:640px;margin:1em auto;padding:0 1em}}
table{{border-collapse:collapse;width:100%}}td{{padding:.4em;border-bottom:1px solid #ccc}}
button{{font-size:1em;padding:.5em .8em;margin:.15em}}.live{{font-weight:bold}}
.ok{{background:#e8f4ea;padding:.5em;border:1px solid #8bc39a}}.warn{{background:#fff3cd;padding:.5em;border:1px solid #e0c060}}#out{{white-space:pre-wrap;background:#f4f4f4;padding:.5em}}</style>
</head><body><h2>{label}: Claude account</h2>
<p class="warn">Switching closes <b>every Claude window on {label}</b>, changes the login for the whole machine
and relaunches its Fleet ({fleet}).</p>
<p class="ok">/login in any window is fine &mdash; the switcher captures it automatically (every page
load and every 2 minutes), so the account it replaced is kept. It can still drop Remote Control on the other
windows on {label}; the <b>Log in</b> buttons here are the gentler route.</p>
<p>Live: <b>{live}</b> &middot; {procs} Claude process(es) &middot; {armed}</p>
<table>{rows}</table>
<p><button onclick="warm()">Warm dormant logins</button></p>
<div id="enr" hidden><p>Open this link in a browser signed in to <b id="em"></b>, approve, then paste the code:</p>
<p><a id="url" target="_blank">login link</a></p>
<input id="code" autocomplete="off" size="40"> <button onclick="sendCode()">Send code</button></div>
<div id="out"></div>
<script>
const M={machine_js};let op=null,acct=null;
async function post(path,body){{document.getElementById('out').textContent='working...';
 const r=await fetch(path,{{method:'POST',headers:{{'Content-Type':'application/json','X-Claude-Account':'1'}},body:JSON.stringify(body)}});
 const j=await r.json();document.getElementById('out').textContent=JSON.stringify(j,null,1);return j;}}
async function use(a){{if(!confirm('This will close every Claude window on '+M.label+', switch the whole machine to '+a+' and relaunch the Fleet. Continue?'))return;
 const j=await post('/api/use',{{account:a,confirm:M.machine}});if(j.ok)setTimeout(()=>location.reload(),1500);}}
async function enroll(a){{const j=await post('/api/enroll',{{account:a}});if(!j.ok)return;op=j.op;acct=a;
 document.getElementById('enr').hidden=false;document.getElementById('em').textContent=j.email;
 const u=document.getElementById('url');u.href=j.url;u.textContent='log in as '+j.email;}}
async function sendCode(){{const c=document.getElementById('code');const j=await post('/api/code',{{account:acct,op:op,code:c.value}});c.value='';
 if(j.ok)setTimeout(()=>location.reload(),1500);}}
async function warm(){{await post('/api/warm',{{}});}}
</script></body></html>"""


def render(st, c):
    rows = []
    for a in st.get("accounts", []):
        live = a["where"] == "live"
        state = html.escape(f"{a['state']}" + (f", {a['refresh_days_left']}d left" if a.get("refresh_days_left") is not None else ""))
        name = html.escape(a["name"])
        btns = ""
        if not live and a["state"] == "ok":
            btns += f"<button onclick=\"use('{name}')\">Switch {html.escape(c['label'])} to {name}</button>"
        btns += f"<button onclick=\"enroll('{name}')\">{'Re-login' if a['state'] == 'ok' else 'Log in'}</button>"
        note = f"<br><small>{html.escape(a['vault_note'])}</small>" if a.get("vault_note") else ""
        rows.append(f"<tr class='{'live' if live else ''}'><td>{name}{' (live)' if live else ''}<br><small>{html.escape(a['email'])}</small></td>"
                    f"<td>{state}{note}</td><td>{btns}</td></tr>")
    return PAGE.format(label=html.escape(c["label"]), fleet=html.escape(c.get("fleet", "")),
                       live=html.escape(str(st.get("live") or "none")), procs=st.get("claude_processes", "?"),
                       armed="armed" if st.get("armed") else "DISARMED (switching blocked)", rows="".join(rows),
                       machine_js=json.dumps({"machine": c["machine"], "label": c["label"]}))


class Handler(BaseHTTPRequestHandler):
    server_version = "claude-account-page"

    def log_message(self, fmt, *args):
        sys.stderr.write(f"{self.headers.get('Tailscale-User-Login', '-')} {fmt % args}\n")

    def _send(self, code, body, ctype="application/json"):
        data = body.encode() if isinstance(body, str) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _who(self, c):
        if getattr(self.server, "loopback", False):
            # This machine's own user (see the docstring); refuse any Host but our own loopback name.
            host = (self.headers.get("Host") or "").lower()
            port = self.server.server_address[1]
            if host not in (f"localhost:{port}", f"127.0.0.1:{port}"):
                return None
            allow = c.get("page_allow") or []
            return (allow[0].lower() if allow else None)
        if self.server.tcp:
            # Direct tailnet listener: the header could be forged, so ask tailscaled who the peer is.
            login = whois(self.client_address[0])
        else:
            login = (self.headers.get("Tailscale-User-Login") or "").lower()
        allow = [x.lower() for x in c.get("page_allow", [])]
        return login if login and login in allow else None

    def do_GET(self):
        c = conf()
        if not self._who(c):
            return self._send(403, {"ok": False, "refused": "not an allowed tailnet login"})
        if self.path == "/api/status":
            return self._send(200, run_cli(["status"]))
        if self.path in ("/", "/index.html"):
            return self._send(200, render(run_cli(["status"]), c), "text/html")
        return self._send(404, {"ok": False, "refused": "no such page"})

    def do_POST(self):
        c = conf()
        if not self._who(c):
            return self._send(403, {"ok": False, "refused": "not an allowed tailnet login"})
        if self.headers.get("X-Claude-Account") != "1" or not (self.headers.get("Content-Type") or "").startswith("application/json"):
            return self._send(400, {"ok": False, "refused": "POST JSON with header X-Claude-Account: 1"})
        origin = self.headers.get("Origin")
        if origin and origin.split("://", 1)[-1] != (self.headers.get("Host") or ""):
            return self._send(403, {"ok": False, "refused": "cross-origin request"})
        try:
            n = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(min(n, 65536)) or b"{}")
            acct = str(body.get("account", ""))
        except (ValueError, AttributeError):
            return self._send(400, {"ok": False, "refused": "bad JSON"})
        if acct and not acct.isalnum():
            return self._send(400, {"ok": False, "refused": "bad account name"})
        if not BUSY.acquire(blocking=False):
            return self._send(409, {"ok": False, "refused": "another account action is running on this machine"})
        try:
            if self.path == "/api/use":
                res = run_cli(["use", acct, "--confirm", str(body.get("confirm", ""))], timeout=420)
            elif self.path == "/api/enroll":
                res = run_cli(["enroll", acct], timeout=90)
            elif self.path == "/api/code":
                op = str(body.get("op", ""))
                if not op.isalnum():
                    return self._send(400, {"ok": False, "refused": "bad op"})
                res = run_cli(["code", acct, "--op", op], stdin=str(body.get("code", "")) + "\n", timeout=120)
            elif self.path == "/api/warm":
                res = run_cli(["warm"], timeout=420)
            else:
                return self._send(404, {"ok": False, "refused": "no such action"})
        finally:
            BUSY.release()
        return self._send(200 if res.get("ok") else 422, res)


_WHOIS = {}


def whois(ip):
    """Tailnet login of a peer IP, from tailscaled itself (cached 60 s); None if not a tailnet peer."""
    hit = _WHOIS.get(ip)
    if hit and time.time() - hit[1] < 60:
        return hit[0]
    login = None
    try:
        r = subprocess.run(["tailscale", "whois", "--json", ip], capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            login = ((json.loads(r.stdout).get("UserProfile") or {}).get("LoginName") or "").lower() or None
    except (OSError, ValueError, subprocess.TimeoutExpired):
        login = None
    _WHOIS[ip] = (login, time.time())
    return login


class TailnetHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True
    tcp = True


class LoopbackHTTPServer(TailnetHTTPServer):
    loopback = True


class UnixHTTPServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True
    tcp = False

    def get_request(self):
        req, _ = super().get_request()
        return req, ("tailnet", 0)


def main():
    os.makedirs(os.path.dirname(SOCK), mode=0o700, exist_ok=True)
    if os.path.exists(SOCK):
        os.unlink(SOCK)
    srv = UnixHTTPServer(SOCK, Handler)
    os.chmod(SOCK, 0o600)  # tailscaled runs as root; nobody else needs it
    sys.stderr.write(f"claude-account page on {SOCK}\n")
    port = int(conf().get("page_port", 0) or 0)
    if port:
        # Also listen on this node's tailnet address only (works without tailnet Serve/HTTPS;
        # WireGuard encrypts it). Identity comes from `tailscale whois`, never from a header.
        ip = subprocess.run(["tailscale", "ip", "-4"], capture_output=True, text=True, timeout=10).stdout.split()[0]
        tsrv = TailnetHTTPServer((ip, port), Handler)
        threading.Thread(target=tsrv.serve_forever, daemon=True).start()
        sys.stderr.write(f"claude-account page on http://{ip}:{port}/\n")
    lport = int(conf().get("page_loopback_port", 0) or 0)
    if lport:
        lsrv = LoopbackHTTPServer(("127.0.0.1", lport), Handler)
        threading.Thread(target=lsrv.serve_forever, daemon=True).start()
        sys.stderr.write(f"claude-account page on http://localhost:{lport}/ (this machine's own browser)\n")
    srv.serve_forever()


if __name__ == "__main__":
    main()
