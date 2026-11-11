from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from placardlib import backends, describe  # noqa: E402
from tests.test_describe import _env  # noqa: E402

_NO_API = dict(ANTHROPIC_BASE_URL=None, ANTHROPIC_API_KEY=None,
               ANTHROPIC_AUTH_TOKEN=None, PLACARD_API_KEY_HELPER=None,
               PLACARD_USE_CLAUDE_CODE_HELPER=None, PLACARD_DESCRIBE_MODEL=None)


class Proc:
    def __init__(self, stdout="", stderr="", returncode=0):
        self.stdout, self.stderr, self.returncode = stdout, stderr, returncode


class Recorder:
    """A stand-in for subprocess.run that keeps the argv and checks the image."""

    def __init__(self, reply):
        self.reply, self.calls = reply, []

    def __call__(self, cmd, **kw):
        self.calls.append((cmd, kw))
        cwd = Path(kw.get("cwd") or ".")
        self.saw_image = any(p.name.startswith("figure.") for p in cwd.iterdir())
        if isinstance(self.reply, BaseException):
            raise self.reply
        return self.reply


def _claude_json(text="a heatmap of scores", model="claude-sonnet-9", **extra):
    data = {"type": "result", "subtype": "success", "is_error": False,
            "result": text, "stop_reason": "end_turn",
            "modelUsage": {f"pfx.{model}[1m]": {"canonicalModel": model,
                                                "inputTokens": 10, "outputTokens": 5}}}
    data.update(extra)
    return json.dumps(data)


def _claude(reply, **env):
    with _env(PLACARD_CLAUDE_BARE="0", **env), \
            mock.patch.object(backends, "claude_binary", return_value="/bin/claude"):
        return backends.ClaudeCLIDescriber(runner=reply)


class Selection(unittest.TestCase):
    def test_auto_prefers_api_then_claude_then_codex(self):
        with _env(PLACARD_DESCRIBER="auto", **_NO_API), \
                mock.patch.object(backends, "claude_available", return_value=(True, "")):
            self.assertEqual(backends.choose()[0], "claude")
        with _env(PLACARD_DESCRIBER=None, **_NO_API), \
                mock.patch.object(backends, "claude_available", return_value=(False, "x")), \
                mock.patch.object(backends, "codex_available", return_value=(True, "")):
            self.assertEqual(backends.choose()[0], "codex")
        with _env(PLACARD_DESCRIBER="auto", ANTHROPIC_BASE_URL="https://a.example",
                  ANTHROPIC_API_KEY="k", PLACARD_DESCRIBE_MODEL="m"):
            self.assertEqual(backends.choose()[0], "api")

    def test_none_ready_names_all_three(self):
        with tempfile.TemporaryDirectory() as d, \
                _env(PLACARD_DESCRIBER="auto", CLAUDE_CONFIG_DIR=d, **_NO_API), \
                mock.patch.object(backends, "claude_available",
                                  return_value=(False, "claude: not on PATH")), \
                mock.patch.object(backends, "codex_available",
                                  return_value=(False, "codex: no image")):
            name, why = backends.choose()
        self.assertEqual(name, "")
        for word in ("api:", "claude:", "codex:", "Fix:"):
            self.assertIn(word, why)

    def test_an_explicit_choice_does_not_fall_through(self):
        with _env(PLACARD_DESCRIBER="codex", ANTHROPIC_BASE_URL="https://a.example",
                  ANTHROPIC_API_KEY="k", PLACARD_DESCRIBE_MODEL="m"), \
                mock.patch.object(backends, "codex_available",
                                  return_value=(False, "codex: no image")):
            name, why = backends.choose()
        self.assertEqual(name, "")
        self.assertIn("PLACARD_DESCRIBER=codex", why)

    def test_an_unknown_choice_is_refused_by_name(self):
        with _env(PLACARD_DESCRIBER="gemini"):
            name, why = backends.choose()
        self.assertEqual(name, "")
        self.assertIn("PLACARD_DESCRIBER", why)

    def test_dotenv_cannot_choose_the_route(self):
        with tempfile.TemporaryDirectory() as d, _env(PLACARD_DESCRIBER=None):
            Path(d, ".env").write_text("PLACARD_DESCRIBER=codex\n")
            describe.load_env(d)
            self.assertIsNone(os.environ.get("PLACARD_DESCRIBER"))

    def test_source_names_no_account_or_model_prefix(self):
        src = Path(backends.__file__).read_text(encoding="utf-8")
        import re
        for needle in ("us-gov.", "us.anthropic", "anthropic.claude-"):
            self.assertNotIn(needle, src)
        self.assertIsNone(re.search(r"gpt-\d|claude-(sonnet|opus)-\d", src))


class ClaudeRoute(unittest.TestCase):
    def test_a_good_reply_is_the_description_and_the_writer_is_recorded(self):
        rec = Recorder(Proc(_claude_json()))
        d = _claude(rec)
        self.assertEqual(d.describe_image(b"PNG", depth="brief"), "a heatmap of scores")
        cmd, kw = rec.calls[0]
        self.assertTrue(rec.saw_image, "the image is staged in the run's cwd")
        self.assertIn("--output-format", cmd)
        self.assertEqual(cmd[cmd.index("--tools") + 1], "Read")
        self.assertEqual(cmd[cmd.index("--model") + 1], "sonnet")
        self.assertIn("figure.png", cmd[cmd.index("-p") + 1])
        self.assertIn("timeout", kw)
        self.assertEqual((d.calls, d.failures, d.model), (1, 0, "claude-sonnet-9"))
        self.assertFalse(Path(kw["cwd"]).exists(), "the staging dir is removed")

    def test_cache_tokens_and_cost_are_recorded(self):
        """Measured 2026-11-09: 6 in + 178 out counted as 184 while the CLI
        also reported 1404 cache-read and 1453 cache-creation tokens."""
        mu = {"pfx.claude-sonnet-9[1m]": {
            "canonicalModel": "claude-sonnet-9", "inputTokens": 6,
            "outputTokens": 178, "cacheReadInputTokens": 1404,
            "cacheCreationInputTokens": 1453, "costUSD": 0.0079}}
        d = _claude(Recorder(Proc(_claude_json(modelUsage=mu, total_cost_usd=0.0079))))
        d.describe_image(b"PNG", depth="brief")
        self.assertEqual(d.usage, {"input": 6, "output": 178, "cache_read": 1404,
                                   "cache_creation": 1453, "cost_usd": 0.0079})
        self.assertEqual(d.tokens, 6 + 178 + 1404 + 1453)

    def test_missing_cache_fields_count_as_zero(self):
        d = _claude(Recorder(Proc(_claude_json())))
        d.describe_image(b"PNG", depth="brief")
        self.assertEqual((d.usage["cache_read"], d.usage["cache_creation"],
                          d.tokens), (0, 0, 15))

    def test_the_reported_model_is_never_fed_back_as_model(self):
        """Measured 2026-11-09: call one recorded the reply's canonical name, call
        two sent it as --model and the gateway answered 400 invalid model."""
        rec = Recorder(Proc(_claude_json(model="claude-sonnet-9")))
        d = _claude(rec)
        d.describe_image(b"PNG", depth="brief")
        d.describe_image(b"PNG", depth="full")
        sent = [c[c.index("--model") + 1] for c, _kw in rec.calls]
        self.assertEqual(sent, ["sonnet", "sonnet"])
        self.assertEqual(d.model, "claude-sonnet-9")

    def test_bare_mode_passes_the_users_settings_for_auth(self):
        with tempfile.TemporaryDirectory() as cfg:
            Path(cfg, "settings.json").write_text('{"apiKeyHelper": "/x/h"}')
            with _env(CLAUDE_CONFIG_DIR=cfg, PLACARD_CLAUDE_BARE=None, ANTHROPIC_API_KEY=None):
                self.assertTrue(backends.claude_bare())
                with mock.patch.object(backends, "claude_binary", return_value="/bin/claude"):
                    cmd = backends.ClaudeCLIDescriber(runner=None).command("p")
        self.assertIn("--bare", cmd)
        self.assertEqual(cmd[cmd.index("--settings") + 1], str(Path(cfg, "settings.json")))

    def test_a_haiku_model_is_refused_before_any_call(self):
        rec = Recorder(Proc(_claude_json()))
        with self.assertRaises(describe.DescribeUnavailable) as cm:
            _claude(rec, PLACARD_DESCRIBE_MODEL="claude-haiku-9")
        self.assertIn("haiku", str(cm.exception))
        self.assertEqual(rec.calls, [])

    def test_a_reply_written_by_haiku_is_a_failure(self):
        d = _claude(Recorder(Proc(_claude_json(model="claude-haiku-9"))))
        with self.assertRaises(describe.DescribeUnavailable):
            d.describe_image(b"PNG", depth="brief")
        self.assertEqual(d.failures, 1)

    def test_failures_are_counted_never_empty(self):
        cases = [Proc(_claude_json(is_error=True, subtype="error_max_turns")),
                 Proc(_claude_json(text="  ")),
                 Proc("not json", stderr="boom", returncode=1),
                 Proc(_claude_json(stop_reason="max_tokens")),
                 subprocess.TimeoutExpired("claude", 1)]
        for reply in cases:
            d = _claude(Recorder(reply))
            with self.assertRaises(describe.DescribeUnavailable, msg=repr(reply)):
                d.describe_image(b"PNG", depth="full")
            self.assertEqual(d.failures, 1, repr(reply))

    def test_skip_depths_never_call(self):
        rec = Recorder(Proc(_claude_json()))
        with self.assertRaises(ValueError):
            _claude(rec).describe_image(b"PNG", depth="skip")
        self.assertEqual(rec.calls, [])


def _codex_events(answer="a line chart", fail=None):
    ev = [{"type": "thread.started", "thread_id": "t"},
          {"type": "item.completed", "item": {"type": "error", "message": "code mode off"}}]
    if fail:
        ev.append({"type": "turn.failed", "error": {"message": fail}})
    else:
        ev.append({"type": "item.completed", "item": {"type": "agent_message", "text": answer}})
        ev.append({"type": "turn.completed", "usage": {"input_tokens": 9, "output_tokens": 3}})
    return "\n".join(json.dumps(e) for e in ev)


class CodexRoute(unittest.TestCase):
    def _codex(self, reply, route=("native", "/bin/codex")):
        with mock.patch.object(backends, "codex_route", return_value=route), \
                _env(PLACARD_CODEX_MODEL=None):
            return backends.CodexDescriber(runner=reply)

    def test_native_passes_the_image_with_dash_i(self):
        rec = Recorder(Proc(_codex_events()))
        d = self._codex(rec)
        self.assertEqual(d.describe_image(b"PNG", depth="brief"), "a line chart")
        cmd, kw = rec.calls[0]
        self.assertEqual(cmd[:2], ["/bin/codex", "exec"])
        self.assertTrue(cmd[cmd.index("-i") + 1].endswith("figure.png"))
        self.assertNotIn("-m", cmd, "no model is named unless the env names one")
        self.assertIn("attached image", kw["input"])
        self.assertEqual((d.calls, d.failures), (1, 0))

    def test_container_mounts_only_the_home_and_the_image_dir(self):
        with tempfile.TemporaryDirectory() as home, _env(CODEX_CONTAINER_HOME=home):
            rec = Recorder(Proc(_codex_events()))
            d = self._codex(rec, route=("container", "codex-consult:1.0"))
            d.describe_image(b"PNG", depth="brief")
        cmd = rec.calls[0][0]
        mounts = [cmd[i + 1] for i, a in enumerate(cmd) if a == "-v"]
        self.assertEqual(len(mounts), 2)
        self.assertTrue(mounts[0].startswith(home))
        self.assertTrue(mounts[1].endswith(":/packet:ro"))
        for flag in ("--read-only", "--cap-drop", "--strict-config"):
            self.assertIn(flag, cmd)
        self.assertEqual(cmd[cmd.index("-i", cmd.index("exec")) + 1], "/packet/figure.png")

    def test_a_failed_turn_is_a_counted_failure_with_its_message(self):
        d = self._codex(Recorder(Proc(_codex_events(fail="usage limit reached"), returncode=1)))
        with self.assertRaises(describe.DescribeUnavailable) as cm:
            d.describe_image(b"PNG", depth="full")
        self.assertIn("usage limit", str(cm.exception))
        self.assertEqual(d.failures, 1)

    def test_timeout_is_a_failure(self):
        d = self._codex(Recorder(subprocess.TimeoutExpired("codex", 1)))
        with self.assertRaises(describe.DescribeUnavailable):
            d.describe_image(b"PNG", depth="brief")
        self.assertEqual(d.failures, 1)

    def test_no_route_is_a_refusal_naming_it(self):
        with mock.patch.object(backends.shutil, "which", return_value=None), \
                _env(PLACARD_CODEX_IMAGE=None):
            ready, why = backends.codex_available()
        self.assertFalse(ready)
        self.assertIn("codex", why)


class DigestRecordsTheBackend(unittest.TestCase):
    def test_frontmatter_names_the_describer(self):
        import placard

        class Fake:
            backend, model, calls, failures, notes = "claude", "claude-sonnet-9", 0, 0, []

            def describe_image(self, data, **kw):
                return "a diagram of three boxes"

        class Result:
            figures = [(1, b"\x89PNG" + b"x" * 5000, None, "flow_chart", 300000.0)]

        with mock.patch.object(backends, "available", return_value=(True, "", "claude")), \
                mock.patch.object(backends, "make", return_value=Fake()):
            counts, section = placard._describe_figures(Result(), True)
        self.assertEqual(counts.get("figures_describer"), "claude")
        self.assertEqual(counts.get("figures_described"), "1")
        self.assertIn("three boxes", section)


if __name__ == "__main__":
    unittest.main()
