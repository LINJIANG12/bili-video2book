"""Unit tests for BlockSynthesizer."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.generator.block_synthesizer import BlockSynthesizer


class TestBlockSynthesizer(unittest.TestCase):
    def test_format_filename(self):
        """Should format block note filename correctly with padding and safe chars."""
        block_meta = {
            "block_id": 1,
            "block_title": "软件工程概述与学科认知",
            "episodes": [1, 2],
        }
        filename = BlockSynthesizer.get_block_filename(block_meta)
        self.assertTrue(filename.startswith("模块01_"))
        self.assertIn("P01-P02", filename)
        self.assertTrue(filename.endswith("_笔记.md"))

    def test_fallback_local_synthesis(self):
        """Should synthesize structured markdown note from kernels locally without external API."""
        block_meta = {
            "block_id": 1,
            "block_title": "软件工程概述与学科认知",
            "episodes": [1, 2],
            "core_theme": "学科定位与考核机制",
        }
        kernels = [
            {
                "page": 1,
                "title": "软件工程概述-1",
                "definitions": [{"term": "软件工程", "essence": "大规模协同构建软件的系统化方法"}],
                "mechanisms_and_models": [{"name": "考核熔断机制", "details": "期末卷面小于40分强制总评59分"}],
                "comparisons": [],
                "case_studies": [{"case_name": "在线支付系统", "context": "多组协同", "lesson": "接口先行"}],
                "anti_patterns": ["单兵作战谬误"],
            },
            {
                "page": 2,
                "title": "软件工程概述-2",
                "definitions": [{"term": "管理型学科", "essence": "注重流程规范与风险防范"}],
                "mechanisms_and_models": [],
                "comparisons": [{"entities": "技术型 vs 管理型", "distinction": "微观编码实现 vs 宏观流程治理"}],
                "case_studies": [],
                "anti_patterns": ["假集成外壳陷阱"],
            },
        ]

        md = BlockSynthesizer.render_local_fallback(block_meta, kernels)
        self.assertIn("模块01", md)
        self.assertIn("软件工程概述与学科认知", md)
        self.assertIn("P01-P02", md)
        self.assertIn("软件工程", md)
        self.assertIn("假集成外壳陷阱", md)

    def test_build_synthesis_prompt(self):
        """Should construct streamlined synthesis prompt without case studies or self-test mandates."""
        block_meta = {
            "block_id": 2,
            "block_title": "软件生命周期与过程模型",
            "episodes": [3, 4],
            "core_theme": "瀑布、敏捷与演化模型对比",
        }
        kernels = [
            {"page": 3, "title": "生命周期模型", "definitions": [{"term": "瀑布模型", "essence": "线性顺序模型"}]},
        ]
        prompt = BlockSynthesizer.build_synthesis_prompt(block_meta, kernels)
        self.assertIn("模块 02", prompt)
        self.assertIn("软件生命周期与过程模型", prompt)
        self.assertIn("P03-P04", prompt)
        self.assertIn("模块复习速查笔记", prompt)
        self.assertIn("不收录长篇案例记叙，不包含练习测验题", prompt)
        self.assertIn("横向对比表格（按需，非必须）", prompt)
        # Should NOT contain rigid unescaped template braces
        self.assertNotIn("{block_title}", prompt)
        self.assertNotIn("{kernels_json}", prompt)


if __name__ == "__main__":
    unittest.main()
