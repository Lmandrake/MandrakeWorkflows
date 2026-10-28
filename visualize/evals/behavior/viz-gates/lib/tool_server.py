#!/usr/bin/env python3
"""MCP tool server (stdio, newline-delimited JSON-RPC) giving the executor ONE tool, identical in every arm:

  run_python(script)   run <script> (a .py path inside the workspace) with the eval venv's python,
                       cwd = workspace, MPLBACKEND=Agg, 120 s limit; returns exit code, the last
                       3000 chars of stdout/stderr, and the image files written or changed.

The executor has no Bash, so this is its only way to execute code; it can then view chart.png with
Read. Every call is logged to <log_path> (outside the workspace) with the script's full text.

Usage: tool_server.py <python_exe> <workspace_dir> <log_path>
"""
import json, os, subprocess, sys, time

PY, WS, LOG = sys.argv[1], os.path.realpath(sys.argv[2]), sys.argv[3]
TOOL = {"name": "run_python",
        "description": "Run a Python script from the working directory (matplotlib, numpy and pandas are installed; "
                       "headless Agg backend). Returns the exit code, stdout/stderr and the image files it wrote.",
        "inputSchema": {"type": "object", "properties": {"script": {"type": "string", "description": "path of the .py file, relative to the working directory"}},
                        "required": ["script"]}}


def images():
    out = {}
    for root, _, files in os.walk(WS):
        if "/.git" in root:
            continue
        for f in files:
            if f.lower().endswith((".png", ".svg", ".pdf", ".jpg", ".jpeg")):
                p = os.path.join(root, f); st = os.stat(p)
                out[os.path.relpath(p, WS)] = (st.st_mtime, st.st_size)
    return out


def run(script):
    if not isinstance(script, str) or not script.strip():
        return "no script given", True, None
    full = os.path.realpath(os.path.join(WS, script))
    if not full.startswith(WS + os.sep) or not os.path.isfile(full):
        return f"script not found in the working directory: {script}", True, None
    src = open(full, errors="replace").read()
    before = images()
    env = {k: v for k, v in os.environ.items()}
    env["MPLBACKEND"] = "Agg"
    t0 = time.time()
    try:
        p = subprocess.run([PY, full], cwd=WS, capture_output=True, text=True, timeout=120, env=env)
        rc, so, se = p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        rc, so, se = "timeout (120 s)", "", ""
    after = images()
    changed = [f"{k} ({v[1]} bytes)" for k, v in sorted(after.items()) if before.get(k) != v]
    out = (f"exit code: {rc}  ({time.time() - t0:.1f} s)\nimages written/changed: {', '.join(changed) or 'none'}\n"
           f"--- stdout (tail) ---\n{so[-3000:]}\n--- stderr (tail) ---\n{se[-3000:]}")
    return out, rc != 0, src


def send(o):
    sys.stdout.write(json.dumps(o) + "\n"); sys.stdout.flush()


for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    try:
        msg = json.loads(line)
    except Exception:
        continue
    mid, method = msg.get("id"), msg.get("method")
    if method == "initialize":
        pv = (msg.get("params") or {}).get("protocolVersion", "2024-11-05")
        send({"jsonrpc": "2.0", "id": mid, "result": {"protocolVersion": pv, "capabilities": {"tools": {}},
                                                       "serverInfo": {"name": "py", "version": "1.0"}}})
    elif method == "tools/list":
        send({"jsonrpc": "2.0", "id": mid, "result": {"tools": [TOOL]}})
    elif method == "tools/call":
        prm = msg.get("params") or {}; args = prm.get("arguments") or {}
        if prm.get("name") == "run_python":
            out, err, src = run(args.get("script"))
        else:
            out, err, src = f"unknown tool {prm.get('name')}", True, None
        with open(LOG, "a") as f:
            f.write(json.dumps({"tool": prm.get("name"), "args": args, "response": out, "is_error": err, "script_text": src}) + "\n")
        send({"jsonrpc": "2.0", "id": mid, "result": {"content": [{"type": "text", "text": out}], "isError": err}})
    elif method == "ping":
        send({"jsonrpc": "2.0", "id": mid, "result": {}})
    elif mid is not None:
        send({"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"method not found: {method}"}})
