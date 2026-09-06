"""Unit tests for AgentModelClient and Transcriber Fallback Gate."""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.agent_client import AgentModelClient
from src.core.transcriber import AudioTranscriber


class TestAgentModelClient(unittest.TestCase):
    def setUp(self):
        AgentModelClient._cached_config = None

    def tearDown(self):
        AgentModelClient._cached_config = None

    def test_discover_config_from_env(self):
        """Should discover config from environment variables when set."""
        with patch.dict(os.environ, {
            "AGENT_BASE_URL": "http://127.0.0.1:9999/v1beta",
            "AGENT_API_KEY": "test_key",
            "AGENT_MODEL": "gemini-3.8-flash-high",
        }):
            cfg = AgentModelClient.discover_config(force_refresh=True)
            self.assertIsNotNone(cfg)
            self.assertEqual(cfg["base_url"], "http://127.0.0.1:9999/v1beta")
            self.assertEqual(cfg["model"], "gemini-3.8-flash-high")
            self.assertTrue(AgentModelClient.can_transcribe_audio())

    def test_can_transcribe_audio_false_for_text_only(self):
        """Should return False when model is configured as text-only."""
        with patch.dict(os.environ, {
            "AGENT_BASE_URL": "http://127.0.0.1:9999/v1",
            "AGENT_API_KEY": "test_key",
            "AGENT_MODEL": "deepseek-chat",
        }):
            cfg = AgentModelClient.discover_config(force_refresh=True)
            cfg["modalities"] = ["text"]
            self.assertFalse(AgentModelClient.can_transcribe_audio())


class TestTranscriberHaltAndAsk(unittest.TestCase):
    @patch("src.core.agent_client.AgentModelClient.can_transcribe_audio", return_value=False)
    def test_transcribe_halts_when_agent_lacks_audio_and_fallback_denied(self, _mock_can):
        """When dialogue model lacks audio modality and fallback is not allowed, should raise RuntimeError."""
        with patch.object(Path, "exists", return_value=True):
            with self.assertRaises(RuntimeError) as ctx:
                AudioTranscriber.transcribe(
                    audio_path="dummy.m4a",
                    engine="auto",
                    allow_local_fallback=False,
                )
            self.assertIn("未授权使用本地模型", str(ctx.exception))

    @patch("src.core.agent_client.AgentModelClient.can_transcribe_audio", return_value=False)
    def test_transcribe_halts_with_callback_denied(self, _mock_can):
        """When user prompt callback returns False, should halt task."""
        with patch.object(Path, "exists", return_value=True):
            with self.assertRaises(RuntimeError) as ctx:
                AudioTranscriber.transcribe(
                    audio_path="dummy.m4a",
                    engine="auto",
                    fallback_callback=lambda: False,
                )
            self.assertIn("未授权使用本地模型", str(ctx.exception))

    @patch("src.core.agent_client.AgentModelClient.can_transcribe_audio", return_value=False)
    @patch.object(AudioTranscriber, "transcribe_local")
    def test_transcribe_proceeds_when_fallback_confirmed(self, mock_local, _mock_can):
        """When user prompt callback returns True, should proceed to local model."""
        mock_local.return_value = {"full_text": "本地转录成功", "total_segments": 1}
        with patch.object(Path, "exists", return_value=True):
            res = AudioTranscriber.transcribe(
                audio_path="dummy.m4a",
                engine="auto",
                fallback_callback=lambda: True,
            )
            self.assertEqual(res["full_text"], "本地转录成功")
            mock_local.assert_called_once()


if __name__ == "__main__":
    unittest.main()
