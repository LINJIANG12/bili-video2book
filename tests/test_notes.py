"""Tests for adaptive note classification and sober GitHub-styled note generation."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.generator.classifier import NoteClassifier
from src.generator.prompt_templates import (
    NOTE_STUDY_PROMPT,
    NOTE_NEWS_PROMPT,
    NOTE_GENERAL_PROMPT,
)
from src.generator.doc_builder import DocumentBuilder


class TestAdaptiveNotes(unittest.TestCase):
    def test_classifier_study(self):
        """Course / Tutorial titles should classify as 'study'."""
        titles = [
            "【公开课】浙江大学：软件工程 陈越（全33讲） P1",
            "手把手教你从零实现 Transformer 架构与注意力机制教程",
            "王道考研 计算机网络 知识点与期末高频考点速成",
        ]
        for t in titles:
            cat, reason = NoteClassifier.classify(t)
            self.assertEqual(cat, NoteClassifier.STUDY, f"Failed for title: {t} (reason: {reason})")

    def test_classifier_news(self):
        """Product release / tech announcement titles should classify as 'news'."""
        titles = [
            "Godot 4.8 Dev4 重磅来袭！最新功能真的超惊艳",
            "虚幻引擎5.8预览版来了：新特性全面评测与盘点",
            "Claude 3.7 Sonnet 震撼发布！混合思考模型实测，行业动向深度速递",
        ]
        for t in titles:
            cat, reason = NoteClassifier.classify(t)
            self.assertEqual(cat, NoteClassifier.NEWS, f"Failed for title: {t} (reason: {reason})")

    def test_classifier_general(self):
        """Talks, interviews, and general sharing should classify as 'general'."""
        titles = [
            "雷军年度演讲：穿越人生低谷的感悟与思考",
            "程序员三十岁后的人生选择与职场经验谈",
            "对话前沿创业者：商业模式探索与团队成长心得",
        ]
        for t in titles:
            cat, reason = NoteClassifier.classify(t)
            self.assertEqual(cat, NoteClassifier.GENERAL, f"Failed for title: {t} (reason: {reason})")

    def test_classifier_override(self):
        """Explicit override should take precedence over auto-detection."""
        cat, _ = NoteClassifier.classify("任意标题", override="news")
        self.assertEqual(cat, NoteClassifier.NEWS)

    def test_prompt_templates_sober_style(self):
        """Prompts should have plain, sober GitHub-style structure and no spammy emojis."""
        for p in [NOTE_STUDY_PROMPT, NOTE_NEWS_PROMPT, NOTE_GENERAL_PROMPT]:
            # Should have standard markdown headings
            self.assertIn("# ", p)
            self.assertIn("## ", p)
            # Should format cleanly
            rendered = p.format(title="测试标题", part_title="P1", content="测试转录内容")
            self.assertIn("测试标题", rendered)
            self.assertIn("测试转录内容", rendered)

    def test_doc_builder_render_prompts_adaptive(self):
        """DocumentBuilder.render_prompts should auto-detect or respect note_type."""
        # Auto detection for news
        res_news = DocumentBuilder.render_prompts(
            title="Godot 4.8 Dev4 重磅更新",
            part_title="P1",
            content="内容",
            note_type="auto",
        )
        self.assertEqual(res_news["note_type"], "news")
        self.assertIn("重大更新与特性清单", res_news["note_prompt"])

        # Auto detection for study
        res_study = DocumentBuilder.render_prompts(
            title="数据结构公开课 第一讲",
            part_title="P1",
            content="内容",
            note_type="auto",
        )
        self.assertEqual(res_study["note_type"], "study")
        self.assertIn("核心知识点精炼", res_study["note_prompt"])

        # Explicit override
        res_forced = DocumentBuilder.render_prompts(
            title="数据结构公开课 第一讲",
            part_title="P1",
            content="内容",
            note_type="news",
        )
        self.assertEqual(res_forced["note_type"], "news")

    def test_block_task_export_only(self):
        """synthesize_block must export 模块XX_*_TASK.md and never write baseline note files."""
        from src.generator.block_synthesizer import BlockSynthesizer

        class _FakeWs:
            def __init__(self, notes_dir):
                self.notes_dir = notes_dir

        block_meta = {
            "block_id": 1,
            "block_title": "软件工程概述与学科认知",
            "episodes": [1, 2],
            "core_theme": "学科定位与考核机制",
        }
        kernels = [
            {"page": 1, "title": "软件工程概述-1", "definitions": [{"term": "软件工程", "essence": "系统化方法"}]},
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            ws = _FakeWs(Path(tmpdir))
            res = BlockSynthesizer.synthesize_block(block_meta, kernels, ws=ws)
            task_path = Path(res["task_file"])
            self.assertTrue(str(task_path).endswith("_TASK.md"))
            self.assertTrue(task_path.exists())
            task_md = task_path.read_text(encoding="utf-8")
            self.assertIn("软件工程概述与学科认知", task_md)
            self.assertIn("深度融合", task_md)
            self.assertEqual(res["status"], "generated")
            # No baseline 模块笔记 file may exist
            self.assertEqual(list(ws.notes_dir.glob("模块*_笔记.md")), [])
            # Cache rule: task file exists -> skip rewrite
            res2 = BlockSynthesizer.synthesize_block(block_meta, kernels, ws=ws)
            self.assertEqual(res2["status"], "cached")

    def test_article_and_rectify_prompt_rendering(self):
        """Verify replacement article prompt and literal ASR rectification prompt rendering."""
        res = DocumentBuilder.render_prompts(
            title="软件工程与系统设计",
            part_title="P01 需求分析与建模",
            content="这是一段测试语料内容。",
            desc="这是一门关于软件工程的精品课程。",
        )
        # Article prompt checks
        art = res["article_prompt"]
        self.assertIn("软件工程与系统设计", art)
        self.assertIn("P01 需求分析与建模", art)
        self.assertIn("尽可能替代观看原视频进行学习和理解的系统化长文", art)
        self.assertIn("随堂自测/练习题", art)

        # Rectify prompt checks
        rec = res["rectify_prompt"]
        self.assertIn("只改“字”，不改“话”", rec)
        self.assertIn("这是一段测试语料内容。", rec)
        self.assertIn("软件工程与系统设计", rec)

        # Standalone rectify helper
        rec_helper = DocumentBuilder.render_rectify_prompt(
            raw_text="忍见工程包括虚球分析",
            domain_hint="计算机科学 软件工程",
        )
        self.assertIn("忍见工程包括虚球分析", rec_helper)
        self.assertIn("计算机科学 软件工程", rec_helper)

    def test_cmd_note_multi_page_filename_prefix(self):
        """cmd_note on multi-page course must prefix filename with P{page:02d} to avoid collision."""
        import argparse
        import src.cli as cli_mod
        from unittest import mock

        fake_info = {
            "title": "多P课程",
            "bvid": "BVmulti123",
            "has_multi_pages": True,
            "parts": [
                {"page": 1, "title": "第一节", "cid": 101},
                {"page": 2, "title": "第二节", "cid": 102},
            ],
            "cid": 101,
            "url_page": 2,
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            args = argparse.Namespace(
                url="https://www.bilibili.com/video/BVmulti123?p=2",
                page=2,
                sessdata=None,
                task="test_multinote",
                base_dir=tmpdir,
                output=None,
                transcript_file=None,
                note_type="auto",
            )
            with mock.patch("src.cli._resolve_target_info", return_value=fake_info):
                cli_mod.cmd_note(args)

            notes_dir = Path(tmpdir) / "test_multinote" / "notes"
            files = list(notes_dir.glob("*.md"))
            self.assertEqual(len(files), 1)
            self.assertTrue(files[0].name.startswith("P02_BVmulti123_"))
            self.assertTrue(files[0].name.endswith("_NOTE_TASK.md"))


if __name__ == "__main__":
    unittest.main()
