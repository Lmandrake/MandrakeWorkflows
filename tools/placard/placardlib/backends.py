"""Which route describes a figure: the Messages API, the Claude Code CLI, or Codex.

    PLACARD_DESCRIBER = api | claude | codex | auto     (default auto)

auto picks the first that is ready: `api` when describe.available() finds an
endpoint, a model and a credential; else `claude` when the Claude Code CLI is on
PATH; else `codex` when a Codex CLI is on PATH or the chatgpt-consult container
is set up. With none ready the reason names all three, and the digest records
the figures as not described, as before.

Both CLI routes inherit the machine's own configuration. Nothing here names a
host, an account, a key or a model prefix: the claude route asks the CLI for its
`sonnet` alias (the CLI resolves it from the environment) unless
PLACARD_DESCRIBE_MODEL says otherwise; the codex route uses the account's default
unless PLACARD_CODEX_MODEL says otherwise. Haiku (and Fable) are refused by name,
before the call and again if the CLI reports having used one.

Every backend has the Describer surface placard.py uses: `describe_image()`,
which raises DescribeUnavailable rather than returning a placeholder, plus
`backend`, `model`, `calls`, `failures` and `notes`.

Environment (read when called, never at import):

    PLACARD_DESCRIBER      api | claude | codex | auto
    PLACARD_DESCRIBE_MODEL claude route: a model or alias; default `sonnet`
    PLACARD_CLAUDE_BARE    1 / 0 forces `claude --bare` on or off. Default on when
                           Claude Code's settings.json names an apiKeyHelper or
                           ANTHROPIC_API_KEY is set (bare reads only those, and
                           skips hooks, CLAUDE.md and MCP: measured 4.6x cheaper)
    PLACARD_CODEX_MODEL    codex route: a model id; default the account's own
    PLACARD_CODEX_IMAGE    the container image; default the newest codex-consult:*
    CODEX_CONTAINER_HOME   the container's credential home; default ~/.codex-container
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from placardlib import describe as _d

DescribeUnavailable = _d.DescribeUnavailable

SELECT_ENV = "PLACARD_DESCRIBER"
CHOICES = ("api", "claude", "codex", "auto")
BARE_ENV = "PLACARD_CLAUDE_BARE"
CODEX_MODEL_ENV = "PLACARD_CODEX_MODEL"
CODEX_IMAGE_ENV = "PLACARD_CODEX_IMAGE"
CODEX_HOME_ENV = "CODEX_CONTAINER_HOME"
CLAUDE_DEFAULT_ALIAS = "sonnet"       # resolved by the CLI from the environment
BANNED_MODEL_WORDS = ("haiku", "fable")
CALL_TIMEOUT = 300                    # seconds per figure, either CLI
CLAUDE_MAX_BUDGET_USD = "0.50"        # per figure; measured ~0.03 bare
CODEX_LOCK_WAIT = 600                 # the consult worker's lock may be held
_EXT = {"image/png": ".png", "image/jpeg": ".jpg", "image/gif": ".gif",
        "image/webp": ".webp"}


def _refuse_banned(model: str, where: str) -> None:
    low = (model or "").lower()
    for word in BANNED_MODEL_WORDS:
        if word in low:
            raise DescribeUnavailable(
                f"{where} names a {word} model ({model}); {word} is not used here. "
                f"Fix: set {_d.MODEL_OVERRIDE_ENV} to a Sonnet or Opus model or alias.")


def _child_env() -> dict:
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    return env


def _staged(image_bytes: bytes, media_type: str, root: Path = None) -> Path:
    """A fresh private dir holding only the image, as `figure.<ext>`."""
    if root is not None:
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
    d = Path(tempfile.mkdtemp(prefix="placard-fig-", dir=root))
    p = d / ("figure" + _EXT.get(media_type, ".png"))
    p.write_bytes(image_bytes)
    return p


class _CLIDescriber:
    backend = "?"

    def __init__(self):
        self.calls = 0
        self.failures = 0
        self.notes = []
        # tokens is the TOTAL of all four kinds; cache tokens are most of the
        # volume on a claude call (measured 2026-11-09: 184 counted vs 3041).
        self.tokens = 0
        self.usage = {"input": 0, "output": 0, "cache_read": 0,
                      "cache_creation": 0, "cost_usd": 0.0}

    def _add_usage(self, input=0, output=0, cache_read=0, cache_creation=0,
                   cost_usd=0.0):
        u = self.usage
        u["input"] += input
        u["output"] += output
        u["cache_read"] += cache_read
        u["cache_creation"] += cache_creation
        u["cost_usd"] = round(u["cost_usd"] + cost_usd, 6)
        self.tokens += input + output + cache_read + cache_creation

    def _fail(self, message: str) -> DescribeUnavailable:
        self.failures += 1
        return DescribeUnavailable(f"{self.backend}: {message}")

    def _prepare(self, image_bytes, depth, media_type):
        if depth not in _d.MAX_TOKENS:
            raise ValueError(f"depth {depth!r} does not warrant a call")
        image_bytes, note = _d.shrink_if_needed(image_bytes)
        if note:
            self.notes.append(note)
            if "->" in note:
                media_type = "image/jpeg"
        return image_bytes, media_type


# ------------------------------------------------------------------ claude


def claude_binary() -> str:
    return shutil.which("claude") or ""


def _claude_settings_path() -> Path:
    cfg = os.getenv("CLAUDE_CONFIG_DIR") or os.path.join("~", ".claude")
    return Path(os.path.expanduser(cfg)) / "settings.json"


def claude_bare() -> bool:
    forced = os.getenv(BARE_ENV, "").strip()
    if forced in ("0", "1"):
        return forced == "1"
    if os.getenv(_d.API_KEY_ENV, "").strip():
        return True
    return bool(_d._claude_code_helper())


def claude_available() -> tuple:
    if not claude_binary():
        return False, "claude: the Claude Code CLI is not on PATH"
    model = os.getenv(_d.MODEL_OVERRIDE_ENV, "").strip() or CLAUDE_DEFAULT_ALIAS
    try:
        _refuse_banned(model, _d.MODEL_OVERRIDE_ENV)
    except DescribeUnavailable as exc:
        return False, f"claude: {exc}"
    return True, ""


class ClaudeCLIDescriber(_CLIDescriber):
    """`claude -p`, headless, with only the Read tool, in a dir holding only the
    image. The CLI brings its own account and gateway."""

    backend = "claude"

    def __init__(self, *, model=None, timeout=CALL_TIMEOUT, runner=subprocess.run):
        super().__init__()
        ready, reason = claude_available()
        if not ready:
            raise DescribeUnavailable(reason)
        self.binary = claude_binary()
        # `requested` is what --model gets on EVERY call; `model` is the label of
        # what answered. Feeding the label back as --model 400s on a gateway that
        # serves only prefixed ids (measured 2026-11-09: the second figure failed).
        self.requested = model or os.getenv(_d.MODEL_OVERRIDE_ENV, "").strip() \
            or CLAUDE_DEFAULT_ALIAS
        _refuse_banned(self.requested, "the claude model")
        self.model = self.requested
        self.timeout = timeout
        self.runner = runner
        self.bare = claude_bare()

    def command(self, prompt: str) -> list:
        cmd = [self.binary, "-p", prompt, "--model", self.requested,
               "--tools", "Read", "--allowedTools", "Read",
               "--output-format", "json", "--no-session-persistence",
               "--max-budget-usd", CLAUDE_MAX_BUDGET_USD]
        if self.bare:
            # bare reads auth only from ANTHROPIC_API_KEY or --settings' apiKeyHelper
            settings = _claude_settings_path()
            if settings.is_file():
                cmd += ["--settings", str(settings)]
            cmd.insert(1, "--bare")
        else:
            cmd += ["--strict-mcp-config", "--disable-slash-commands"]
        return cmd

    def describe_image(self, image_bytes: bytes, *, depth: str,
                       media_type: str = "image/png", caption: str = None) -> str:
        image_bytes, media_type = self._prepare(image_bytes, depth, media_type)
        path = _staged(image_bytes, media_type)
        prompt = (f"Use the Read tool to open the image file {path.name} in the "
                  f"current directory, then answer with the description only.\n\n"
                  + _d.prompt_for(depth, caption))
        try:
            try:
                out = self.runner(self.command(prompt), cwd=str(path.parent),
                                  env=_child_env(), capture_output=True,
                                  text=True, timeout=self.timeout,
                                  stdin=subprocess.DEVNULL)
            except subprocess.TimeoutExpired:
                raise self._fail(f"claude -p exceeded {self.timeout}s") from None
            except OSError as exc:
                raise self._fail(f"could not run claude ({exc})") from None
        finally:
            shutil.rmtree(path.parent, ignore_errors=True)
        self.calls += 1
        try:
            data = json.loads(out.stdout or "")
        except ValueError:
            tail = (out.stderr or out.stdout or "").strip()[-300:]
            raise self._fail(f"exit {out.returncode}, no JSON result: {tail}") from None
        text = (data.get("result") or "").strip() if isinstance(data, dict) else ""
        if not isinstance(data, dict) or data.get("is_error") \
                or data.get("subtype") not in (None, "success"):
            sub = data.get("subtype") if isinstance(data, dict) else "?"
            raise self._fail(f"the CLI reported an error ({sub}): {text[:1000]}")
        if data.get("stop_reason") == "max_tokens":
            raise self._fail("the description hit max_tokens and was cut off; "
                             "not recorded as described")
        usage = {k: v for k, v in (data.get("modelUsage") or {}).items()
                 if isinstance(v, dict)}
        if usage:
            # The model that wrote the answer is the one with the most output.
            key, top = max(usage.items(),
                           key=lambda kv: int(kv[1].get("outputTokens") or 0))
            writer = top.get("canonicalModel") or key
            if writer.endswith(_d.CONTEXT_MARKER):
                writer = writer[:-len(_d.CONTEXT_MARKER)]
            try:
                _refuse_banned(writer, "the CLI's reply")
            except DescribeUnavailable as exc:
                raise self._fail(str(exc)) from None
            self.model = writer
            def n(v, k):
                try:
                    return int(v.get(k) or 0)
                except (TypeError, ValueError):
                    return 0
            try:
                cost = float(data.get("total_cost_usd") or 0)
            except (TypeError, ValueError):
                cost = 0.0
            if not cost:
                cost = sum(float(v.get("costUSD") or 0) for v in usage.values())
            self._add_usage(
                input=sum(n(v, "inputTokens") for v in usage.values()),
                output=sum(n(v, "outputTokens") for v in usage.values()),
                cache_read=sum(n(v, "cacheReadInputTokens") for v in usage.values()),
                cache_creation=sum(n(v, "cacheCreationInputTokens")
                                   for v in usage.values()),
                cost_usd=cost)
        if not text:
            raise self._fail("the CLI returned an empty description")
        return text


# ------------------------------------------------------------------ codex


def codex_home() -> Path:
    return Path(os.path.expanduser(
        os.getenv(CODEX_HOME_ENV, "").strip() or os.path.join("~", ".codex-container")))


def _docker() -> list:
    ctx = os.getenv("CONSULT_DOCKER_CONTEXT", "colima")
    return ["docker", "--context", ctx] if ctx else ["docker"]


def codex_image(runner=subprocess.run) -> str:
    """PLACARD_CODEX_IMAGE, else the newest local codex-consult:* tag, else ""."""
    forced = os.getenv(CODEX_IMAGE_ENV, "").strip()
    if forced:
        return forced
    if not shutil.which("docker"):
        return ""
    try:
        out = runner([*_docker(), "images", "codex-consult",
                      "--format", "{{.Repository}}:{{.Tag}}"],
                     capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return ""
    tags = [t for t in (out.stdout or "").split() if t.startswith("codex-consult:")]
    def key(tag):
        return [int(x) if x.isdigit() else 0 for x in tag.split(":", 1)[1].split(".")]
    return max(tags, key=key) if tags else ""


def codex_route(runner=subprocess.run) -> tuple:
    """("native", path) | ("container", image) | ("", reason)."""
    native = shutil.which("codex")
    if native:
        return "native", native
    image = codex_image(runner)
    if not image:
        return "", ("codex: no Codex CLI on PATH and no codex-consult image "
                    "(the chatgpt-consult skill's container)")
    if not (codex_home() / "auth.json").is_file():
        return "", (f"codex: {codex_home()}/auth.json is missing; log in with the "
                    "chatgpt-consult skill's container login")
    return "container", image


def codex_available(runner=subprocess.run) -> tuple:
    kind, why = codex_route(runner)
    return (True, "") if kind else (False, why)


def parse_codex_events(text: str) -> tuple:
    """(answer, error, usage). The last error is the verdict; an answer with a
    completed, unfailed turn wins over earlier noise."""
    answer, errors, usage, completed, failed = "", [], None, False, False
    for line in (text or "").splitlines():
        try:
            e = json.loads(line)
        except ValueError:
            continue
        t = e.get("type")
        if t == "item.completed":
            it = e.get("item") or {}
            if it.get("type") == "agent_message":
                answer = it.get("text") or answer
            elif it.get("type") == "error":
                errors.append(it.get("message", ""))
        elif t == "turn.completed":
            completed, usage = True, e.get("usage")
        elif t == "turn.failed":
            failed = True
            errors.append((e.get("error") or {}).get("message", ""))
        elif t == "error":
            errors.append(e.get("message", ""))
    if completed and not failed and answer.strip():
        return answer.strip(), "", usage
    err = errors[-1] if errors else ("turn completed with an empty answer"
                                     if completed else "no completed turn")
    return "", err, usage


class _Lock:
    """The chatgpt-consult worker's own flock on the credential home: concurrent
    runs on one login race its refresh-token rotation."""

    def __init__(self, home: Path, wait: float):
        self.path, self.wait, self.fh = home / ".worker.lock", wait, None

    def __enter__(self):
        import fcntl
        self.fh = self.path.open("w")
        until = time.time() + self.wait
        while True:
            try:
                fcntl.flock(self.fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except OSError:
                if time.time() >= until:
                    self.fh.close()
                    raise TimeoutError("the codex worker lock is held by another run")
                time.sleep(0.5)

    def __exit__(self, *exc):
        self.fh.close()


class CodexDescriber(_CLIDescriber):
    """`codex exec -i <image>`: natively when a Codex CLI is on PATH, else in the
    chatgpt-consult container with that worker's hardening (read-only rootfs,
    cap-drop ALL, only the credential home and the one image mounted)."""

    backend = "codex"

    def __init__(self, *, model=None, timeout=CALL_TIMEOUT, runner=subprocess.run):
        super().__init__()
        self.runner = runner
        self.route, self.target = codex_route(runner)
        if not self.route:
            raise DescribeUnavailable(self.target)
        self.model = model or os.getenv(CODEX_MODEL_ENV, "").strip() or "codex-account-default"
        self.timeout = timeout

    def command(self, image_in_run: str) -> list:
        tail = ["exec", "--json", "--ephemeral", "--skip-git-repo-check",
                "--sandbox", "read-only", "-i", image_in_run]
        if self.model != "codex-account-default":
            tail += ["-m", self.model]
        tail.append("-")
        if self.route == "native":
            return [self.target, *tail]
        return [*_docker(), "run", "--rm", "-i",
                "--user", f"{os.getuid()}:{os.getgid()}",
                "--read-only", "--tmpfs", "/tmp:rw,size=256m,mode=1777",
                "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
                "--pids-limit", "256", "--memory", "2g",
                "-v", f"{codex_home()}:/codex",
                "-v", f"{self._dir}:/packet:ro", "-w", "/packet",
                self.target, *tail[:1], "--strict-config", "--ignore-rules",
                "-C", "/packet", *tail[1:]]

    def describe_image(self, image_bytes: bytes, *, depth: str,
                       media_type: str = "image/png", caption: str = None) -> str:
        image_bytes, media_type = self._prepare(image_bytes, depth, media_type)
        # Colima shares only $HOME into its VM, so the container's image lives there.
        root = (Path.home() / ".cache" / "placard" / "codex"
                if self.route == "container" else None)
        path = _staged(image_bytes, media_type, root)
        path.parent.chmod(0o755)
        path.chmod(0o644)
        self._dir = path.parent
        inside = (f"/packet/{path.name}" if self.route == "container" else str(path))
        prompt = _d.prompt_for(depth, caption) + "\n\nThe figure is the attached image."
        try:
            try:
                ctx = (_Lock(codex_home(), CODEX_LOCK_WAIT)
                       if self.route == "container" else _NoLock())
                with ctx:
                    out = self.runner(self.command(inside), input=prompt,
                                      cwd=str(path.parent), env=_child_env(),
                                      capture_output=True, text=True,
                                      timeout=self.timeout)
            except subprocess.TimeoutExpired:
                raise self._fail(f"codex exec exceeded {self.timeout}s") from None
            except (OSError, TimeoutError) as exc:
                raise self._fail(f"could not run codex ({exc})") from None
        finally:
            shutil.rmtree(path.parent, ignore_errors=True)
        self.calls += 1
        answer, err, usage = parse_codex_events(out.stdout)
        if isinstance(usage, dict):
            self._add_usage(input=int(usage.get("input_tokens") or 0),
                            output=int(usage.get("output_tokens") or 0))
        if not answer:
            tail = err or (out.stderr or "").strip()[-300:]
            raise self._fail(f"exit {out.returncode}: {tail[:300]}")
        return answer


class _NoLock:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


# ------------------------------------------------------------------ selection


def requested() -> str:
    return (os.getenv(SELECT_ENV, "").strip().lower() or "auto")


def choose(runner=subprocess.run) -> tuple:
    """(backend, "") when one is ready, else ("", reason naming each tried)."""
    want = requested()
    if want not in CHOICES:
        return "", (f"{SELECT_ENV}={want!r} is not one of {', '.join(CHOICES)}. "
                    f"Fix: export {SELECT_ENV}=auto.")
    checks = {"api": lambda: _d.available(),
              "claude": claude_available,
              "codex": lambda: codex_available(runner)}
    order = ("api", "claude", "codex") if want == "auto" else (want,)
    reasons = []
    for name in order:
        ready, why = checks[name]()
        if ready:
            return name, ""
        reasons.append(why if name != "api" else f"api: {why}")
    if want == "auto":
        return "", ("no describer is ready (PLACARD_DESCRIBER=auto tried api, "
                    "claude, codex): " + " | ".join(reasons) +
                    f" Fix: export {_d.API_KEY_ENV}=<key>, or install the Claude "
                    "Code CLI, or set up the chatgpt-consult codex container.")
    return "", (reasons[0] + f" (chosen by {SELECT_ENV}={want}). Fix: set "
                f"{SELECT_ENV}=auto or repair that route.")


def available() -> tuple:
    """(ready, reason, backend). Never raises."""
    name, why = choose()
    return bool(name), why, name


def make(backend: str = None):
    """A describer for `backend` (default: the chosen one). Raises
    DescribeUnavailable naming what is missing."""
    name = backend or choose()[0]
    if not name:
        raise DescribeUnavailable(choose()[1])
    if name == "api":
        return _d.Describer()
    if name == "claude":
        return ClaudeCLIDescriber()
    if name == "codex":
        return CodexDescriber()
    raise DescribeUnavailable(f"unknown describer {name!r}")
