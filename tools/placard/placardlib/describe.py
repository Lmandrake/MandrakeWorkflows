"""Vision descriptions through an Anthropic Messages API endpoint.

One POST to `$ANTHROPIC_BASE_URL/v1/messages` with an inline base64 image. The
endpoint, the model and the credential all come from the environment at call
time; nothing here names a host, an account or a model id, and a missing value
is a refusal that names the variable, never a fallback.

What is deliberately bounded is the SPEND. Measured over 31 real figures, an
ungated converter sent its detailed prompt to all 31 -- including six logos and
icons -- and averaged 2,135 characters per figure, of which ten figures added at
most one term the text did not already carry.

So here the prompt is chosen by the gate in `figures.py`, and the cost of each
depth is bounded by `max_tokens` rather than by hope:

    full         a diagram, chart or drawing whose structure IS the content
    brief        one or two sentences naming what the thing is
    caption-only no call at all -- the document's own caption already says it
    skip         no call at all -- furniture

Every call is counted and every skip keeps its reason, so a digest can never
report "figures complete" when a third of them were quietly dropped.

Nothing here is imported unless a description is actually requested: the module
imports cleanly with no credentials and no network, because `placard.py` must
keep running under the system Python a hook falls back to.

Environment (read when called, never at import):

    ANTHROPIC_BASE_URL         required; e.g. https://api.anthropic.com
    PLACARD_DESCRIBE_MODEL     the model id; else ANTHROPIC_DEFAULT_SONNET_MODEL
    credential, first found:   ANTHROPIC_API_KEY      (sent as x-api-key)
                               ANTHROPIC_AUTH_TOKEN   (sent as a Bearer token)
                               PLACARD_API_KEY_HELPER (a command printing a token)
    PLACARD_USE_CLAUDE_CODE_HELPER=1   opt in to the `apiKeyHelper` command named in
                               Claude Code's settings.json (found via CLAUDE_CONFIG_DIR or
                               ~/.claude), for a process started outside Claude Code

None of these may come from Placard's own `.env` (see ACCOUNT_KEYS).
"""
from __future__ import annotations

import base64
import json
import os
import shlex
from pathlib import Path

BASE_URL_ENV = "ANTHROPIC_BASE_URL"
MODEL_OVERRIDE_ENV = "PLACARD_DESCRIBE_MODEL"
MODEL_ENV = "ANTHROPIC_DEFAULT_SONNET_MODEL"
API_KEY_ENV = "ANTHROPIC_API_KEY"
AUTH_TOKEN_ENV = "ANTHROPIC_AUTH_TOKEN"
HELPER_ENV = "PLACARD_API_KEY_HELPER"
OPT_IN_ENV = "PLACARD_USE_CLAUDE_CODE_HELPER"
CONTEXT_MARKER = "[1m]"   # a Claude Code context marker, not a served id
API_VERSION = "2023-06-01"
# Keys that choose an endpoint, a model or a credential. Placard's own .env may
# not supply them: an account written into a file is the stale default this
# module exists to refuse. They come from the live environment or not at all.
ACCOUNT_KEYS = frozenset({BASE_URL_ENV, MODEL_OVERRIDE_ENV, MODEL_ENV,
                          API_KEY_ENV, AUTH_TOKEN_ENV, HELPER_ENV, OPT_IN_ENV,
                          "CLAUDE_CONFIG_DIR", "PLACARD_EVAL_MODEL",
                          # backends.py: which route describes, and how it authenticates
                          "PLACARD_DESCRIBER", "PLACARD_CLAUDE_BARE",
                          "PLACARD_CODEX_MODEL", "PLACARD_CODEX_IMAGE",
                          "CODEX_CONTAINER_HOME"})


def default_model() -> str:
    """PLACARD_DESCRIBE_MODEL if set, else the Sonnet id Claude Code exports,
    minus its `[1m]` context marker."""
    override = os.getenv(MODEL_OVERRIDE_ENV, "").strip()
    if override:
        return override
    value = os.getenv(MODEL_ENV, "").strip()
    if not value:
        raise DescribeUnavailable(
            f"{MODEL_OVERRIDE_ENV} and {MODEL_ENV} are both unset. Fix: export "
            f"{MODEL_OVERRIDE_ENV}=<a vision-capable model id>.")
    if value.endswith(CONTEXT_MARKER):
        value = value[:-len(CONTEXT_MARKER)]
    return value


def model_label(model: str) -> str:
    """The model's own name, without a cloud route prefix such as `<region>.`
    or `<region>.<vendor>.`. A digest records which model wrote a description;
    the route that served it is the reader's environment, not the digest's."""
    import re
    return re.sub(r"^(?:[a-z0-9-]+\.)+(?=[a-z][a-z0-9-]*-\d)", "", model.strip())


def endpoint() -> str:
    """The Messages API URL, from ANTHROPIC_BASE_URL. No default."""
    base = os.getenv(BASE_URL_ENV, "").strip().rstrip("/")
    if not base:
        raise DescribeUnavailable(
            f"{BASE_URL_ENV} is unset. Fix: export {BASE_URL_ENV}=<your "
            "Messages API base URL>, e.g. https://api.anthropic.com.")
    return f"{base}/v1/messages"


def _claude_code_helper() -> str:
    """Claude Code's own `apiKeyHelper`, if its settings.json names one."""
    cfg = os.getenv("CLAUDE_CONFIG_DIR") or os.path.join("~", ".claude")
    path = Path(os.path.expanduser(cfg)) / "settings.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8")).get("apiKeyHelper")
    except (OSError, ValueError, AttributeError):
        return ""
    return value.strip() if isinstance(value, str) else ""


def credential_source() -> tuple:
    """(kind, value) where kind is api_key | auth_token | helper. Raises naming
    every variable it looked for when none is set."""
    for kind, name in (("api_key", API_KEY_ENV), ("auth_token", AUTH_TOKEN_ENV)):
        value = os.getenv(name, "").strip()
        if value:
            return kind, value
    helper = os.getenv(HELPER_ENV, "").strip()
    if not helper and os.getenv(OPT_IN_ENV, "").strip() == "1":
        helper = _claude_code_helper()
    if helper:
        return "helper", helper
    raise DescribeUnavailable(
        f"no credential: {API_KEY_ENV}, {AUTH_TOKEN_ENV} and {HELPER_ENV} are "
        f"unset (and {OPT_IN_ENV}=1 did not find a Claude Code apiKeyHelper). "
        f"Fix: export {API_KEY_ENV}=<key>.")


def fetch_token(helper: str) -> str:
    """Run a key helper and return the last line it prints. Never logged."""
    import subprocess
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    out = subprocess.run(shlex.split(helper), env=env, capture_output=True,
                         text=True, timeout=180)
    lines = out.stdout.strip().splitlines()
    token = lines[-1].strip() if lines else ""
    if out.returncode != 0 or not token:
        raise DescribeUnavailable(
            f"the API key helper failed (rc={out.returncode}) and printed no "
            f"token. Fix: run it by hand, or export {API_KEY_ENV}.")
    return token


# Bounded by depth. The full prompt is for pictures whose structure carries the
# meaning; the brief prompt exists because naming a Mars terrain photo is worth
# one line and not two thousand characters.
MAX_TOKENS = {"full": 1400, "brief": 160}

PROMPT_FULL = (
    "Describe this technical figure for a reader who cannot see it.\n"
    "Transcribe every visible label, axis title, unit, legend entry, node name "
    "and annotation EXACTLY as written — these are often the only place that "
    "information exists. For a chart give the axes, their units and the trend. "
    "For a diagram give the nodes and what connects to what. For a drawing give "
    "the labelled parts and their relationships.\n"
    "Do not speculate about anything you cannot see. If text is illegible write "
    "[unclear] rather than guessing. Use plain prose with no markdown headings, "
    "and do not begin with a preamble such as 'This image shows'."
)

PROMPT_BRIEF = (
    "In at most two sentences, say what this picture shows and transcribe its "
    "title and any identifier visible in it exactly as written. If it is a chart, "
    "give the values it shows rather than listing every axis label. No preamble, "
    "no markdown, no speculation."
)

def prompt_for(depth: str, caption: str = None) -> str:
    """The prompt for a depth, shared by every backend so they answer alike."""
    prompt = PROMPT_FULL if depth == "full" else PROMPT_BRIEF
    if caption:
        prompt += (f"\n\nThe document's own caption for this figure is: "
                   f"{caption!r}. Do not repeat it; add what it omits.")
    return prompt


_MEDIA = {
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".gif": "image/gif", ".webp": "image/webp", ".bmp": "image/bmp",
    ".tif": "image/tiff", ".tiff": "image/tiff",
}


# A 2 MB PNG becomes ~2.7 MB of base64, which measurably timed out the SSL
# handshake on 2 of 31 figures. Downscaling first is cheaper than retrying a
# doomed upload, and a description does not need print resolution.
MAX_UPLOAD_BYTES = 1_200_000
MAX_EDGE_PX = 1600

# Transient failures are retried; a 4xx that is not 429 is permanent and is not.
RETRY_ATTEMPTS = 3
RETRY_BACKOFF = 1.8


def shrink_if_needed(image_bytes: bytes) -> tuple:
    """(bytes, note). Returns the input unchanged when PIL is unavailable --
    and says so, rather than pretending the image was fine."""
    if len(image_bytes) <= MAX_UPLOAD_BYTES:
        return image_bytes, None
    try:
        import io

        from PIL import Image
    except ImportError:
        return image_bytes, ("image is large and PIL is unavailable to shrink "
                             "it; the upload may time out")
    try:
        with Image.open(io.BytesIO(image_bytes)) as im:
            im = im.convert("RGB")
            if max(im.size) > MAX_EDGE_PX:
                scale = MAX_EDGE_PX / max(im.size)
                im = im.resize((max(1, int(im.width * scale)),
                                max(1, int(im.height * scale))),
                               Image.Resampling.LANCZOS)
            buf = io.BytesIO()
            im.save(buf, format="JPEG", quality=85, optimize=True)
        out = buf.getvalue()
        return out, f"downscaled {len(image_bytes)}B -> {len(out)}B for upload"
    except Exception as exc:
        return image_bytes, f"could not downscale ({type(exc).__name__})"


class DescribeUnavailable(RuntimeError):
    """Raised with a remedy, never swallowed into an empty description.

    v1's extraction path wrote its own exception text into the body and still
    flagged it `body: full`. A failed description must be visibly absent, not
    silently substituted.
    """


def media_type_for(path) -> str:
    return _MEDIA.get(Path(str(path)).suffix.lower(), "image/png")


def available(model=None) -> tuple:
    """(ready, reason). Never raises, so callers can report rather than crash.
    An explicit `model` stands in for the model variables."""
    try:
        endpoint()
        if not model:
            default_model()
        credential_source()
    except DescribeUnavailable as exc:
        return False, f"{exc}"
    return True, ""


def load_env(root=None) -> None:
    """Load Placard's own .env without depending on python-dotenv.

    Deliberately does not read any other project's .env: coupling Placard's
    credentials to a checkout it does not own is how a tool breaks when someone
    else reorganises their directory. ACCOUNT_KEYS are ignored here: an account
    written into a file is the stale default this module exists to refuse.
    """
    root = Path(root) if root else Path(__file__).resolve().parents[1]
    path = root / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key.startswith("export "):
            key = key[len("export "):].strip()
        if key in ACCOUNT_KEYS:
            continue
        os.environ.setdefault(key, value.strip())


class Describer:
    """Thin client over an Anthropic Messages API endpoint."""

    backend = "api"

    def __init__(self, *, model=None, timeout=180):
        ready, reason = available(model)
        if not ready:
            raise DescribeUnavailable(reason)
        self.model = model or default_model()
        self.timeout = timeout
        self.url = endpoint()
        self._cred_kind, self._cred = credential_source()
        self._token = None
        self.calls = 0
        self.failures = 0
        self.notes = []

    def _headers(self) -> dict:
        headers = {"anthropic-version": API_VERSION,
                   "content-type": "application/json"}
        if self._cred_kind == "api_key":
            headers["x-api-key"] = self._cred
            return headers
        if self._token is None:
            self._token = (self._cred if self._cred_kind == "auth_token"
                           else fetch_token(self._cred))
        headers["authorization"] = f"Bearer {self._token}"
        return headers

    def _redact(self, text: str) -> str:
        """An endpoint may echo the credential back in an error body. The body
        is kept, because it is the diagnosis; the secret is not."""
        for secret in (self._cred if self._cred_kind != "helper" else None,
                       self._token):
            if secret and len(secret) >= 8:
                text = text.replace(secret, "[redacted]")
        return text

    def _http_error(self, exc) -> "DescribeUnavailable":
        """The body of a 4xx is where the endpoint says WHAT it objected to.
        Discarding it turns a precise complaint into a guessing game -- it is
        how the invalid model id was found."""
        self.failures += 1
        try:
            detail = self._redact(exc.read().decode("utf-8", "replace")[:600])
        except Exception:
            detail = "(no response body)"
        hint = ("the credential was refused or has expired"
                if exc.code in (401, 403)
                else "the request shape or model was rejected")
        return DescribeUnavailable(
            f"the endpoint returned HTTP {exc.code} ({hint}).\nEndpoint said: {detail}")

    def describe_image(self, image_bytes: bytes, *, depth: str,
                       media_type: str = "image/png",
                       caption: str = None) -> str:
        """One description. Raises DescribeUnavailable rather than returning a
        placeholder, so a failure can never be mistaken for content."""
        import urllib.error
        import urllib.request

        if depth not in MAX_TOKENS:
            raise ValueError(f"depth {depth!r} does not warrant a call")
        image_bytes, shrink_note = shrink_if_needed(image_bytes)
        if shrink_note:
            self.notes.append(shrink_note)
        if shrink_note and "->" in shrink_note:
            media_type = "image/jpeg"           # shrink_if_needed re-encodes as JPEG
        prompt = prompt_for(depth, caption)

        payload = {
            "model": self.model,
            "max_tokens": MAX_TOKENS[depth],
            "messages": [{"role": "user", "content": [
                {"type": "image", "source": {
                    "type": "base64", "media_type": media_type,
                    "data": base64.b64encode(image_bytes).decode("ascii")}},
                {"type": "text", "text": prompt},
            ]}],
        }
        import time
        body = json.dumps(payload).encode("utf-8")
        last = None
        for attempt in range(1, RETRY_ATTEMPTS + 1):
            request = urllib.request.Request(
                self.url, data=body,
                headers=self._headers(), method="POST")
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                break
            except urllib.error.HTTPError as exc:
                # A 4xx that is not 429 is permanent: retrying a rejected model
                # or a malformed payload just spends the quota again.
                if exc.code != 429 and 400 <= exc.code < 500:
                    raise self._http_error(exc) from exc
                last = exc
            except Exception as exc:
                last = exc            # transient: SSL timeout, broken pipe
            if attempt < RETRY_ATTEMPTS:
                time.sleep(RETRY_BACKOFF ** attempt)
        else:
            self.failures += 1
            raise DescribeUnavailable(
                f"the description call failed after {RETRY_ATTEMPTS} attempts "
                f"({type(last).__name__}: {last})")
        self.calls += 1
        try:
            text = "".join(block.get("text", "") for block in data["content"]
                           if block.get("type") == "text")
        except (KeyError, TypeError, AttributeError) as exc:
            raise DescribeUnavailable(
                "the response had no text content") from exc
        if not (text or "").strip():
            raise DescribeUnavailable("the endpoint returned an empty description")
        if data.get("stop_reason") == "max_tokens":
            # A description cut off mid-word is not a description. Shipped once
            # in the example deck as "figures_described: 1" (found in review).
            self.failures += 1
            raise DescribeUnavailable(
                f"the description hit max_tokens ({MAX_TOKENS[depth]}) and was "
                "cut off; not recorded as described")
        return text.strip()
