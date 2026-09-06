"""Comprehensive test suite for Bilibili Skill pipeline."""

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.parser import BilibiliParser
from src.core.fetcher import AudioFetcher
from src.generator.cleaner import TextCleaner
from src.generator.doc_builder import DocumentBuilder


class TestBilibiliSkill(unittest.TestCase):
    def test_parser_multi_page(self):
        """Test parsing multi-page video (BV16g411M7r2)."""
        bvid = "BV16g411M7r2"
        meta = BilibiliParser.parse(bvid)
        self.assertEqual(meta["video_type"], "multi_page")
        self.assertTrue(len(meta["parts"]) >= 33)
        p1 = meta["parts"][0]
        self.assertEqual(p1["page"], 1)
        self.assertIn("第1讲", p1["title"])
        self.assertTrue(p1["url"].endswith("?p=1"))

    def test_audio_stream_fetch(self):
        """Test fetching DASH audio direct stream url with WBI signing."""
        bvid = "BV16g411M7r2"
        meta = BilibiliParser.parse(bvid)
        cid = meta["parts"][0]["cid"]
        stream_info = AudioFetcher.get_audio_stream_url(bvid=bvid, cid=cid)
        self.assertIn("best_stream_url", stream_info)
        self.assertTrue(stream_info["best_stream_url"].startswith("http"))
        self.assertGreater(stream_info["quality_id"], 0)

        # Test quality selection
        stream_low = AudioFetcher.get_audio_stream_url(bvid=bvid, cid=cid, prefer_quality="low")
        stream_high = AudioFetcher.get_audio_stream_url(bvid=bvid, cid=cid, prefer_quality="high")
        self.assertLessEqual(stream_low["quality_id"], stream_high["quality_id"])

    def test_text_cleaner(self):
        """Test safe text normalization and punctuation collapsing."""
        raw_text = "软件工程包括需求分析、架构设计和测试。。。这是核心要素！！！"
        clean_res = TextCleaner.clean(raw_text)
        cleaned = clean_res["cleaned_text"]
        self.assertIn("软件工程", cleaned)
        self.assertIn("架构设计", cleaned)
        self.assertNotIn("。。。", cleaned)
        self.assertNotIn("！！！", cleaned)
        self.assertGreater(clean_res["cleaned_length"], 0)

    def test_doc_builder(self):
        """Test building revision notes and tutorial articles."""
        title = "软件工程测试课"
        part_title = "第1讲 需求工程"
        content = "本节课详细介绍了需求工程的理论模型、功能性需求和非功能性需求，以及需求分析的边界条件和验证策略。"
        
        note_md = DocumentBuilder.render_note(title, part_title, content, note_type="study")
        article_md = DocumentBuilder.render_learning_article(title, part_title, content)

        self.assertIn("课程与教学笔记", note_md)
        self.assertIn("深度精读", article_md)

        with tempfile.TemporaryDirectory() as tmpdir:
            res = DocumentBuilder.save_documents(
                output_dir=tmpdir,
                base_name="P01_需求工程",
                note_content=note_md,
                article_content=article_md,
            )
            self.assertTrue(os.path.exists(res["note_path"]))
            self.assertTrue(os.path.exists(res["article_path"]))


if __name__ == "__main__":
    unittest.main()
