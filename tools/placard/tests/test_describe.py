from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from placardlib import describe  # noqa: E402


class ImportsCleanly(unittest.TestCase):
    def test_module_imports_without_credentials(self):
        """placard.py must keep running under the system Python the hook falls
        back to, which has none of the env vars."""
        self.assertTrue(hasattr(describe, "Describer"))
        self.assertTrue(hasattr(describe, "available"))

    def test_availability_is_reported_with_a_remedy_not_raised(self):
        ready, reason = describe.available()
        self.assertIn(ready, (True, False))
        if not ready:
            self.assertTrue(reason, "an unavailable path must say why")
            self.assertIn("Fix:", reason, "and must name the remedy")


class Budget(unittest.TestCase):
    """Measured: an ungated converter sent its detailed prompt to all 31 figures including
    six logos, averaging 2,135 chars. Depth must bound the spend."""

    def test_only_full_and_brief_warrant_a_call(self):
        self.assertEqual(set(describe.MAX_TOKENS), {"full", "brief"})

    def test_brief_is_an_order_of_magnitude_cheaper_than_full(self):
        self.assertLess(describe.MAX_TOKENS["brief"] * 5,
                        describe.MAX_TOKENS["full"])

    def test_skip_and_caption_only_cannot_be_called(self):
        for depth in ("skip", "caption-only"):
            self.assertNotIn(depth, describe.MAX_TOKENS)

    def test_prompts_forbid_preamble_and_markdown(self):
        for prompt in (describe.PROMPT_FULL, describe.PROMPT_BRIEF):
            self.assertIn("markdown", prompt.lower())
        self.assertIn("preamble", describe.PROMPT_FULL.lower())

    def test_full_prompt_demands_exact_label_transcription(self):
        """The measured value of a description was its identifiers -- an image
        id, classifier names, domain vocabulary."""
        self.assertIn("EXACTLY", describe.PROMPT_FULL)
        self.assertIn("[unclear]", describe.PROMPT_FULL)


import contextlib


@contextlib.contextmanager
def _env(**values):
    saved = {k: os.environ.get(k) for k in values}
    try:
        for k, v in values.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        yield
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


class ModelResolution(unittest.TestCase):
    """The model was read at module import, before load_env() ran, so the .env
    value could never win. The endpoint caught it with a 400 naming the model;
    nothing in the code would have."""

    def test_env_value_wins_when_set(self):
        saved = os.environ.get("PLACARD_DESCRIBE_MODEL")
        os.environ["PLACARD_DESCRIBE_MODEL"] = "some-other-model"
        try:
            self.assertEqual(describe.default_model(), "some-other-model")
        finally:
            if saved is None:
                os.environ.pop("PLACARD_DESCRIBE_MODEL", None)
            else:
                os.environ["PLACARD_DESCRIBE_MODEL"] = saved

    def test_default_is_the_envs_sonnet_without_context_marker(self):
        """`[1m]` is a Claude Code marker; the endpoint 400s on it."""
        with _env(PLACARD_DESCRIBE_MODEL=None,
                  ANTHROPIC_DEFAULT_SONNET_MODEL="pfx.anthropic.claude-sonnet-x[1m]"):
            self.assertEqual(describe.default_model(), "pfx.anthropic.claude-sonnet-x")

    def test_blank_override_does_not_win(self):
        with _env(PLACARD_DESCRIBE_MODEL="   ",
                  ANTHROPIC_DEFAULT_SONNET_MODEL="m"):
            self.assertEqual(describe.default_model(), "m")

    def test_no_model_in_env_is_a_refusal_not_a_hardwired_default(self):
        with _env(PLACARD_DESCRIBE_MODEL=None, ANTHROPIC_DEFAULT_SONNET_MODEL=None):
            with self.assertRaises(describe.DescribeUnavailable) as cm:
                describe.default_model()
            self.assertIn("ANTHROPIC_DEFAULT_SONNET_MODEL", str(cm.exception))

    def test_source_names_no_account(self):
        src = Path(describe.__file__).read_text(encoding="utf-8")
        for needle in ("us-gov.", "us.anthropic", "sub-id-", "anthropic.claude-"):
            self.assertNotIn(needle, src)


_NO_CRED = dict(ANTHROPIC_API_KEY=None, ANTHROPIC_AUTH_TOKEN=None,
                PLACARD_API_KEY_HELPER=None)


class EndpointFollowsTheEnvironment(unittest.TestCase):
    def test_flips_with_anthropic_base_url(self):
        with _env(ANTHROPIC_BASE_URL="https://a.example/"):
            self.assertEqual(describe.endpoint(), "https://a.example/v1/messages")
        with _env(ANTHROPIC_BASE_URL="https://b.example/route"):
            self.assertEqual(describe.endpoint(), "https://b.example/route/v1/messages")

    def test_nothing_set_is_a_refusal_naming_the_variable(self):
        with _env(ANTHROPIC_BASE_URL=None):
            with self.assertRaises(describe.DescribeUnavailable) as cm:
                describe.endpoint()
            self.assertIn("ANTHROPIC_BASE_URL", str(cm.exception))

    def test_dotenv_cannot_supply_an_account(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d, _env(
                ANTHROPIC_BASE_URL=None, ANTHROPIC_API_KEY=None,
                PLACARD_DESCRIBE_MODEL=None, PLACARD_TEST_OK=None):
            Path(d, ".env").write_text(
                "ANTHROPIC_BASE_URL=https://stale.example\n"
                "ANTHROPIC_API_KEY=stale-key\n"
                "PLACARD_DESCRIBE_MODEL=stale-model\nPLACARD_TEST_OK=1\n")
            describe.load_env(d)
            self.assertIsNone(os.environ.get("ANTHROPIC_BASE_URL"))
            self.assertIsNone(os.environ.get("ANTHROPIC_API_KEY"))
            self.assertIsNone(os.environ.get("PLACARD_DESCRIBE_MODEL"))
            self.assertEqual(os.environ.get("PLACARD_TEST_OK"), "1")


class Credentials(unittest.TestCase):
    def test_api_key_wins_and_is_sent_as_x_api_key(self):
        with _env(ANTHROPIC_API_KEY="k1", ANTHROPIC_AUTH_TOKEN="t1"):
            self.assertEqual(describe.credential_source(), ("api_key", "k1"))

    def test_auth_token_is_a_bearer(self):
        with _env(ANTHROPIC_API_KEY=None, ANTHROPIC_AUTH_TOKEN="t1"):
            self.assertEqual(describe.credential_source(), ("auth_token", "t1"))

    def test_helper_from_the_environment(self):
        with _env(ANTHROPIC_API_KEY=None, ANTHROPIC_AUTH_TOKEN=None,
                  PLACARD_API_KEY_HELPER="printf tok"):
            self.assertEqual(describe.credential_source(), ("helper", "printf tok"))
            self.assertEqual(describe.fetch_token("printf 'a\\ntok'"), "tok")

    def test_no_credential_is_a_refusal_naming_every_variable(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d, _env(CLAUDE_CONFIG_DIR=d, **_NO_CRED):
            with self.assertRaises(describe.DescribeUnavailable) as cm:
                describe.credential_source()
            for name in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN",
                         "PLACARD_API_KEY_HELPER"):
                self.assertIn(name, str(cm.exception))

    def test_claude_codes_helper_is_found(self):
        import json
        import tempfile
        with tempfile.TemporaryDirectory() as d, _env(CLAUDE_CONFIG_DIR=d, **_NO_CRED):
            Path(d, "settings.json").write_text(json.dumps({"apiKeyHelper": "/x/h.sh"}))
            with _env(PLACARD_USE_CLAUDE_CODE_HELPER=None):
                with self.assertRaises(describe.DescribeUnavailable):
                    describe.credential_source()     # not without the opt-in
            with _env(PLACARD_USE_CLAUDE_CODE_HELPER="1"):
                self.assertEqual(describe.credential_source(), ("helper", "/x/h.sh"))

    def test_dotenv_cannot_choose_a_credential_route(self):
        import tempfile
        keys = ("PLACARD_API_KEY_HELPER", "PLACARD_USE_CLAUDE_CODE_HELPER",
                "CLAUDE_CONFIG_DIR", "ANTHROPIC_AUTH_TOKEN")
        with tempfile.TemporaryDirectory() as d, _env(**{k: None for k in keys}):
            Path(d, ".env").write_text("".join(f"{k}=x\n" for k in keys))
            describe.load_env(d)
            for k in keys:
                self.assertIsNone(os.environ.get(k), k)

    def test_explicit_model_needs_no_model_variable(self):
        with _env(ANTHROPIC_BASE_URL="https://a.example", ANTHROPIC_API_KEY="k",
                  PLACARD_DESCRIBE_MODEL=None, ANTHROPIC_DEFAULT_SONNET_MODEL=None):
            self.assertEqual(describe.Describer(model="explicit-id").model, "explicit-id")

    def _one_shot(self, status, payload):
        import http.server
        import json
        import threading

        class H(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                self.rfile.read(int(self.headers["content-length"]))
                out = json.dumps(payload).encode()
                self.send_response(status)
                self.send_header("content-length", str(len(out)))
                self.end_headers()
                self.wfile.write(out)

            def log_message(self, *a):
                pass

        srv = http.server.HTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=srv.handle_request, daemon=True).start()
        return srv

    def test_a_max_tokens_cutoff_is_not_a_description(self):
        srv = self._one_shot(200, {"stop_reason": "max_tokens",
                                   "content": [{"type": "text", "text": "a bar chart of \"Cedar"}]})
        try:
            with _env(ANTHROPIC_BASE_URL=f"http://127.0.0.1:{srv.server_port}",
                      ANTHROPIC_API_KEY="k1", PLACARD_DESCRIBE_MODEL="m1"):
                d = describe.Describer()
                with self.assertRaises(describe.DescribeUnavailable) as cm:
                    d.describe_image(b"PNG", depth="brief")
        finally:
            srv.server_close()
        self.assertIn("max_tokens", str(cm.exception))
        self.assertEqual((d.calls, d.failures), (1, 1), "the call was spent; it failed")

    def test_an_echoed_credential_is_redacted_from_the_error(self):
        canary = "sk-CANARY-0000-do-not-print"
        srv = self._one_shot(401, {"error": f"bad key {canary}"})
        try:
            with _env(ANTHROPIC_BASE_URL=f"http://127.0.0.1:{srv.server_port}",
                      ANTHROPIC_API_KEY=canary, PLACARD_DESCRIBE_MODEL="m1"):
                with self.assertRaises(describe.DescribeUnavailable) as cm:
                    describe.Describer().describe_image(b"PNG", depth="brief")
        finally:
            srv.server_close()
        self.assertNotIn(canary, str(cm.exception))
        self.assertIn("[redacted]", str(cm.exception))

    def test_request_shape_is_the_messages_api(self):
        """One call against a stub server: the image block, the version
        header and the credential header are what the Messages API expects."""
        import http.server
        import json
        import threading
        seen = {}

        class H(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                seen["path"] = self.path
                seen["headers"] = {k.lower(): v for k, v in self.headers.items()}
                seen["body"] = json.loads(self.rfile.read(int(self.headers["content-length"])))
                out = json.dumps({"content": [{"type": "text", "text": "a red square"}]}).encode()
                self.send_response(200)
                self.send_header("content-length", str(len(out)))
                self.end_headers()
                self.wfile.write(out)

            def log_message(self, *a):
                pass

        srv = http.server.HTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=srv.handle_request, daemon=True).start()
        try:
            with _env(ANTHROPIC_BASE_URL=f"http://127.0.0.1:{srv.server_port}",
                      ANTHROPIC_API_KEY="k1", PLACARD_DESCRIBE_MODEL="m1"):
                text = describe.Describer().describe_image(b"PNG", depth="brief")
        finally:
            srv.server_close()
        self.assertEqual(text, "a red square")
        self.assertEqual(seen["path"], "/v1/messages")
        self.assertEqual(seen["headers"].get("x-api-key"), "k1")
        self.assertEqual(seen["body"]["model"], "m1")
        block = seen["body"]["messages"][0]["content"][0]
        self.assertEqual(block["type"], "image")
        self.assertEqual(block["source"]["media_type"], "image/png")


class ModelLabel(unittest.TestCase):
    def test_route_prefixes_are_dropped(self):
        self.assertEqual(describe.model_label("eu.vendor.claude-sonnet-9"), "claude-sonnet-9")
        self.assertEqual(describe.model_label("xx.claude-haiku-4-5"), "claude-haiku-4-5")

    def test_a_bare_id_is_unchanged(self):
        self.assertEqual(describe.model_label("claude-sonnet-9"), "claude-sonnet-9")
        self.assertEqual(describe.model_label("gpt-5.1"), "gpt-5.1")


class MediaTypes(unittest.TestCase):
    def test_png(self):
        self.assertEqual(describe.media_type_for("a.png"), "image/png")

    def test_jpeg_variants(self):
        self.assertEqual(describe.media_type_for("a.jpg"), "image/jpeg")
        self.assertEqual(describe.media_type_for("a.JPEG"), "image/jpeg")

    def test_unknown_defaults_to_png_rather_than_failing(self):
        self.assertEqual(describe.media_type_for("a.weird"), "image/png")


class EnvLoading(unittest.TestCase):
    def test_load_env_does_not_clobber_an_existing_value(self):
        key = "PLACARD_TEST_ENV_KEY"
        os.environ[key] = "already-set"
        try:
            describe.load_env()
            self.assertEqual(os.environ[key], "already-set")
        finally:
            os.environ.pop(key, None)

    def test_load_env_is_silent_when_there_is_no_env_file(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            describe.load_env(d)          # must not raise


class FailuresAreVisible(unittest.TestCase):
    def test_describer_refuses_rather_than_returning_a_placeholder(self):
        """v1 wrote its own exception text into the body and flagged it full.
        A failed description must be visibly absent."""
        self.assertTrue(issubclass(describe.DescribeUnavailable, RuntimeError))

    def test_an_unavailable_describer_raises_on_construction(self):
        with _env(ANTHROPIC_BASE_URL=None):
            ready, _ = describe.available()
            self.assertFalse(ready)
            with self.assertRaises(describe.DescribeUnavailable):
                describe.Describer()



class TransientFailureHandling(unittest.TestCase):
    """Two of 31 real figures failed on SSL handshake timeouts, both the
    largest images. A 2MB PNG becomes ~2.7MB of base64."""

    def test_small_images_are_not_touched(self):
        data = b"x" * 1000
        out, note = describe.shrink_if_needed(data)
        self.assertIs(out, data)
        self.assertIsNone(note)

    def test_oversized_threshold_is_below_the_measured_failure_size(self):
        self.assertLess(describe.MAX_UPLOAD_BYTES, 2_000_000)

    def test_a_large_real_png_is_shrunk(self):
        try:
            import io

            from PIL import Image
        except ImportError:
            self.skipTest("PIL unavailable")
        buf = io.BytesIO()
        Image.new("RGB", (4000, 3000), (120, 80, 40)).save(
            buf, format="PNG", compress_level=0)
        big = buf.getvalue()
        if len(big) <= describe.MAX_UPLOAD_BYTES:
            self.skipTest("synthetic image did not exceed the threshold")
        out, note = describe.shrink_if_needed(big)
        self.assertLess(len(out), len(big))
        self.assertIsNotNone(note)
        self.assertIn("->", note)

    def test_retry_is_bounded(self):
        self.assertGreaterEqual(describe.RETRY_ATTEMPTS, 2)
        self.assertLessEqual(describe.RETRY_ATTEMPTS, 5)

    def test_shrink_failure_reports_rather_than_pretending(self):
        out, note = describe.shrink_if_needed(b"\x00" * (describe.MAX_UPLOAD_BYTES + 1))
        self.assertIsNotNone(note, "a failed shrink must say so")

if __name__ == "__main__":
    unittest.main()
