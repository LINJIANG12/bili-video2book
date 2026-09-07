"""Resilience tests: WBI sign + key cache, 412 retry/backoff, manifest relative, parts cache."""

import json
import sys
import tempfile
import time
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.wbi import WbiSigner
import src.core.fetcher as fetcher_mod
from src.core.workspace import TaskWorkspace
import src.cli as cli_mod


class TestWbiSign(unittest.TestCase):
    def setUp(self):
        WbiSigner.clear_cache()

    def tearDown(self):
        WbiSigner.clear_cache()

    def test_enc_wbi_has_wrid_wts_mock_network(self):
        """enc_wbi must append w_rid/wts without real network."""
        with mock.patch.object(WbiSigner, "obtain_mixin_key", return_value="a" * 32):
            signed = WbiSigner.enc_wbi({"bvid": "BV1234567890"})
        self.assertIn("w_rid", signed)
        self.assertIn("wts", signed)
        self.assertEqual(len(signed["w_rid"]), 32)
        int(signed["w_rid"], 16)  # hex
        self.assertIsInstance(signed["wts"], int)
        self.assertGreater(signed["wts"], 0)
        self.assertEqual(signed["bvid"], "BV1234567890")

    def test_keys_file_cache_hit_no_network(self):
        """Valid keys file must be reused without calling nav API."""
        img = "b" * 32
        sub = "c" * 32
        with tempfile.TemporaryDirectory() as tmpdir:
            kf = Path(tmpdir) / ".wbi_keys.json"
            kf.write_text(
                json.dumps({"img_key": img, "sub_key": sub, "expire_at": time.time() + 3600}),
                encoding="utf-8",
            )
            with mock.patch.object(
                WbiSigner, "get_wbi_keys", side_effect=AssertionError("must not call network")
            ):
                mixin = WbiSigner.obtain_mixin_key(keys_file=str(kf))
            expect = WbiSigner.get_mixin_key(img + sub)
            self.assertEqual(mixin, expect)
            self.assertEqual(len(mixin), 32)


class TestRetry412(unittest.TestCase):
    def test_412_retries_exact_times_then_raises(self):
        """412 must retry exactly max_times then raise with 412 text."""
        orig_max = fetcher_mod._最大重试次数
        orig_fail = fetcher_mod._连续失败次数
        fetcher_mod._最大重试次数 = 2
        fetcher_mod._连续失败次数 = 0
        calls = {"n": 0}

        class FakeOpener:
            def open(self, req, timeout=None):
                calls["n"] += 1
                raise urllib.error.HTTPError(
                    getattr(req, "full_url", "http://example.invalid"),
                    412, "Precondition Failed", {}, None,
                )

        try:
            with mock.patch.object(fetcher_mod, "_获取会话打开器", return_value=FakeOpener()):
                with mock.patch.object(WbiSigner, "wait_rate_limit", return_value=None):
                    with mock.patch("src.core.fetcher.time.sleep", return_value=None):
                        with self.assertRaises(RuntimeError) as ctx:
                            fetcher_mod._请求元数据("http://example.invalid", {})
            self.assertEqual(calls["n"], 3)  # max(2)+1 attempts
            self.assertIn("412", str(ctx.exception))
        finally:
            fetcher_mod._最大重试次数 = orig_max
            fetcher_mod._连续失败次数 = orig_fail

    def test_412_message_three_elements(self):
        """412 copy must contain 定性/可复制动作/预期."""
        msg = cli_mod._format_412(RuntimeError("412 demo"))
        for key in ("定性", "可复制动作", "预期"):
            self.assertIn(key, msg)
        self.assertIn("412", msg)
        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch.object(cli_mod, "_STATUS_FILE", Path(tmpdir) / ".cli_status.json"):
                enriched = cli_mod._enrich_network_error(RuntimeError("HTTP 412 blocked"))
        for key in ("定性", "可复制动作", "预期"):
            self.assertIn(key, enriched)


class TestManifestRelative(unittest.TestCase):
    def test_save_manifest_relative_no_drive(self):
        """Manifest save must relativize absolute paths (no drive letters)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ws = TaskWorkspace.create(title="t", bvid="BVtest12345", base_dir=tmpdir)
            abs_audio = str((cli_mod.PROJECT_ROOT / "output" / "audio" / "P01_x.m4a").resolve())
            cli_mod._save_manifest_rel(ws, {
                "details": [{"page": 1, "audio": abs_audio, "transcript": abs_audio}],
            })
            raw = ws.manifest_file.read_text(encoding="utf-8")
            self.assertNotRegex(raw, r"[A-Za-z]:[\\/]")
            self.assertNotIn(abs_audio, raw)


class TestPartsCache(unittest.TestCase):
    def test_save_load_roundtrip(self):
        """parts.json save/load must round-trip exactly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ws = TaskWorkspace.create(title="t", bvid="BVtest12345", base_dir=tmpdir)
            parts = [
                {"page": 1, "title": "A", "cid": 11},
                {"page": 2, "title": "B", "cid": 22},
            ]
            ws.save_parts(parts)
            self.assertEqual(ws.load_parts(), parts)


if __name__ == "__main__":
    unittest.main()
