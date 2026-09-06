"""Unit tests for KernelExtractor."""

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

from src.core.kernel_extractor import KernelExtractor


class TestKernelExtractor(unittest.TestCase):
    def test_clean_head_tail_heuristic(self):
        """Should strip basic greeting and outro chatter."""
        text = "大家好我们现在开始上课啊。今天我们主要讨论面向对象封装。下课了大家把作业交一下。"
        cleaned = KernelExtractor.strip_transient_chatter(text)
        self.assertIn("面向对象封装", cleaned)

    def test_degraded_fallback_kernel(self):
        """Should produce valid structured kernel even in circuit-breaker degradation mode."""
        text = "需求分析主要包含数据流图、状态迁移图以及实体关系模型。开发人员必须与业务人员确认边界。"
        kernel = KernelExtractor.degraded_extract(page=1, title="需求分析测试", text=text)
        self.assertEqual(kernel["page"], 1)
        self.assertEqual(kernel["status"], "degraded")
        self.assertTrue(len(kernel["definitions"]) > 0 or len(kernel["raw_summary"]) > 0)


if __name__ == "__main__":
    unittest.main()
