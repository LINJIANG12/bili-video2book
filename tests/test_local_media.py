"""Unit tests for Local Media Processing & Universal Audio Extraction."""

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.local_media import LocalMediaParser, natural_sort_key, SUPPORTED_VIDEO_EXTS
from src.core.audio_chunker import AudioChunker
from src.cli import _resolve_target_info


class TestLocalMedia(unittest.TestCase):
    def test_natural_sort_key(self):
        """Natural sort should place P2 before P10 and 第2讲 before 第10讲."""
        files = ["P10.mp4", "P1.mp4", "P2.mp4", "P20.mp4"]
        sorted_files = sorted(files, key=natural_sort_key)
        self.assertEqual(sorted_files, ["P1.mp4", "P2.mp4", "P10.mp4", "P20.mp4"])

        lectures = ["第10讲_复习.mkv", "第1讲_概述.mp4", "第2讲_理论.flv"]
        sorted_lectures = sorted(lectures, key=natural_sort_key)
        self.assertEqual(sorted_lectures, ["第1讲_概述.mp4", "第2讲_理论.flv", "第10讲_复习.mkv"])

    def test_is_local_media(self):
        """Detect local files and directories correctly."""
        self.assertFalse(LocalMediaParser.is_local_media("https://www.bilibili.com/video/BV16g411M7r2"))
        self.assertFalse(LocalMediaParser.is_local_media("BV16g411M7r2"))
        self.assertFalse(LocalMediaParser.is_local_media("non_existent_file_xyz.mp4"))

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            video_file = tmp_path / "test_lecture.mp4"
            video_file.write_bytes(b"dummy")
            txt_file = tmp_path / "readme.txt"
            txt_file.write_text("hello", encoding="utf-8")

            self.assertTrue(LocalMediaParser.is_local_media(video_file))
            self.assertFalse(LocalMediaParser.is_local_media(txt_file))
            self.assertTrue(LocalMediaParser.is_local_media(tmp_path))

    def test_parse_single_video(self):
        """Parsing a single local video file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            video_file = Path(tmpdir) / "01_软件架构基础.mp4"
            video_file.write_bytes(b"dummy")

            with patch.object(LocalMediaParser, "get_duration", return_value=120.0):
                meta = LocalMediaParser.parse(video_file)

            self.assertTrue(meta["is_local"])
            self.assertEqual(meta["video_type"], "single")
            self.assertFalse(meta["has_multi_pages"])
            self.assertEqual(len(meta["parts"]), 1)
            self.assertEqual(meta["parts"][0]["title"], "01_软件架构基础")
            self.assertEqual(meta["parts"][0]["duration"], 120)
            self.assertEqual(meta["duration"], 120)

    def test_parse_course_directory(self):
        """Parsing a directory containing multiple local videos with natural sorting."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            (tmp_path / "02_需求工程.mkv").write_bytes(b"dummy")
            (tmp_path / "01_课程概述.mp4").write_bytes(b"dummy")
            (tmp_path / "10_课程总结.flv").write_bytes(b"dummy")
            (tmp_path / "ignore_me.txt").write_bytes(b"dummy")

            with patch.object(LocalMediaParser, "get_duration", return_value=60.0):
                meta = LocalMediaParser.parse(tmp_path)

            self.assertTrue(meta["is_local"])
            self.assertEqual(meta["video_type"], "multi_page")
            self.assertTrue(meta["has_multi_pages"])
            self.assertEqual(len(meta["parts"]), 3)

            # Check natural sort order
            part_titles = [p["title"] for p in meta["parts"]]
            self.assertEqual(part_titles, ["01_课程概述", "02_需求工程", "10_课程总结"])
            self.assertEqual(meta["parts"][0]["page"], 1)
            self.assertEqual(meta["parts"][1]["page"], 2)
            self.assertEqual(meta["parts"][2]["page"], 3)

    @patch("shutil.which", return_value="/usr/bin/ffmpeg")
    @patch("subprocess.run")
    def test_extract_audio_ffmpeg_command(self, mock_run, _mock_which):
        """Verify universal FFmpeg extraction command options (64k 16kHz mono AAC)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_video = Path(tmpdir) / "source.mkv"
            src_video.write_bytes(b"dummy_video_bytes")
            out_audio = Path(tmpdir) / "out.m4a"

            # Simulate subprocess.run creating the target file
            def side_effect(cmd, **kwargs):
                out_audio.write_bytes(b"dummy_audio_bytes")
                return MagicMock(returncode=0, stderr="")

            mock_run.side_effect = side_effect

            res = LocalMediaParser.extract_audio(src_video, out_audio)
            self.assertEqual(res, out_audio)

            # Inspect FFmpeg invocation command arguments
            called_cmd = mock_run.call_args[0][0]
            self.assertIn("-vn", called_cmd)
            self.assertIn("-map", called_cmd)
            self.assertIn("0:a:0?", called_cmd)
            self.assertIn("-c:a", called_cmd)
            self.assertIn("aac", called_cmd)
            self.assertIn("-b:a", called_cmd)
            self.assertIn("64k", called_cmd)
            self.assertIn("-ar", called_cmd)
            self.assertIn("16000", called_cmd)
            self.assertIn("-ac", called_cmd)
            self.assertIn("1", called_cmd)

    def test_polymorphic_target_resolution(self):
        """Verify _resolve_target_info routes local media to LocalMediaParser and BV to BilibiliParser."""
        with tempfile.TemporaryDirectory() as tmpdir:
            local_vid = Path(tmpdir) / "local_course.mp4"
            local_vid.write_bytes(b"dummy")

            with patch.object(LocalMediaParser, "get_duration", return_value=30.0):
                info_local = _resolve_target_info(str(local_vid))
            self.assertTrue(info_local.get("is_local"))

        # Bilibili URL / BVID
        with patch("src.core.parser.BilibiliParser.parse_video", return_value={"bvid": "BV16g411M7r2", "is_local": False}):
            info_bili = _resolve_target_info("BV16g411M7r2")
            self.assertFalse(info_bili.get("is_local"))
            self.assertEqual(info_bili["bvid"], "BV16g411M7r2")

    def test_parse_nested_subdirectories(self):
        """Verify LocalMediaParser.parse recursively discovers media in nested chapter subfolders."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            ch1 = tmp_path / "01_基础篇"
            ch2 = tmp_path / "02_进阶篇"
            ch1.mkdir()
            ch2.mkdir()
            (ch1 / "01_绪论.mp4").write_bytes(b"dummy")
            (ch1 / "02_环境搭建.mp4").write_bytes(b"dummy")
            (ch2 / "01_核心原理.mkv").write_bytes(b"dummy")

            with patch.object(LocalMediaParser, "get_duration", return_value=50.0):
                meta = LocalMediaParser.parse(tmp_path)

            self.assertEqual(len(meta["parts"]), 3)
            titles = [p["title"] for p in meta["parts"]]
            self.assertEqual(titles[0], "01_基础篇 - 01_绪论")
            self.assertEqual(titles[1], "01_基础篇 - 02_环境搭建")
            self.assertEqual(titles[2], "02_进阶篇 - 01_核心原理")


if __name__ == "__main__":
    unittest.main()
