"""Unit tests for Plan A Agent-native transcription tasks (Antigravity & ChatGPT support)."""

import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.pipeline import export_transcribe_task
from src.core.workspace import TaskWorkspace


class TestNativeTranscribeTask(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.ws = TaskWorkspace.create(
            title="测试音视频网课",
            bvid="BV1test12345",
            base_dir=self.tmpdir,
        )

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_export_transcribe_task_antigravity_chatgpt_sections(self):
        """Should generate TRANSCRIBE_TASK.md containing explicit Antigravity and ChatGPT guides."""
        fake_audio = self.ws.audio_dir / "P01_导学与入门.m4a"
        fake_audio.write_bytes(b"fake audio bytes" * 100)

        task_path = export_transcribe_task(
            ws=self.ws,
            page_num=1,
            clean_title="导学与入门",
            audio_file=fake_audio,
            title="测试音视频网课",
            cid=123456,
        )

        self.assertTrue(task_path.exists())
        content = task_path.read_text(encoding="utf-8")

        # Verify Plan A markers
        self.assertIn("need-agent-transcribe", content)
        self.assertIn("方案 A", content)

        # Verify Antigravity support
        self.assertIn("Antigravity", content)
        self.assertIn("view_file", content)
        self.assertIn("Gemini", content)

        # Verify ChatGPT support
        self.assertIn("ChatGPT", content)
        self.assertIn("GPT-4o Audio", content)

        # Verify prompt inclusion
        self.assertIn("专业计算机/工程/学术术语", content)

    def test_export_transcribe_task_with_audio_chunking(self):
        """Should include slice items when AudioChunker generates chunks."""
        fake_audio = self.ws.audio_dir / "P02_核心架构.m4a"
        fake_audio.write_bytes(b"fake audio data" * 200)

        mock_slices = [
            {
                "chunk_index": 1,
                "start_time_str": "00:00:00",
                "end_time_str": "00:08:30",
                "filepath": str(self.ws.audio_dir / "P02_chunks" / "P02_part_001.m4a"),
            },
            {
                "chunk_index": 2,
                "start_time_str": "00:08:30",
                "end_time_str": "00:17:00",
                "filepath": str(self.ws.audio_dir / "P02_chunks" / "P02_part_002.m4a"),
            },
        ]

        with patch("src.core.audio_chunker.AudioChunker.chunk_audio", return_value=mock_slices):
            task_path = export_transcribe_task(
                ws=self.ws,
                page_num=2,
                clean_title="核心架构",
                audio_file=fake_audio,
                title="测试音视频网课",
            )

            content = task_path.read_text(encoding="utf-8")
            self.assertIn("切片 01 [00:00:00 -> 00:08:30]", content)
            self.assertIn("切片 02 [00:08:30 -> 00:17:00]", content)
            self.assertIn("P02_part_001.m4a", content)
            self.assertIn("P02_part_002.m4a", content)

    @patch("shutil.which", return_value="/usr/bin/ffmpeg")
    @patch("subprocess.run")
    def test_audio_chunker_ffmpeg_flags(self, mock_run, _mock_which):
        """AudioChunker should invoke ffmpeg with -avoid_negative_ts make_zero."""
        from src.core.audio_chunker import AudioChunker
        fake_audio = self.ws.audio_dir / "test.m4a"
        fake_audio.write_bytes(b"dummy")

        with patch.object(AudioChunker, "get_audio_duration", return_value=1200.0):
            AudioChunker.chunk_audio(fake_audio, chunk_minutes=10, balanced=True)

        self.assertTrue(mock_run.called)
        cmd = mock_run.call_args[0][0]
        self.assertIn("-avoid_negative_ts", cmd)
        self.assertIn("make_zero", cmd)


if __name__ == "__main__":
    unittest.main()
