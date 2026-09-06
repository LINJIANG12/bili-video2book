"""Unit tests for non-destructive TextCleaner."""

import unittest
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.generator.cleaner import TextCleaner


class TestNonDestructiveCleaner(unittest.TestCase):
    def test_preserve_chinese_idioms_and_repeated_words(self):
        """Valid Chinese idioms, repeated characters, and technical words must never be mutilated."""
        text = "我们要常常复习，代代相传，步步为营，层层递进。生生不息的技术在向前演进。端端加密是核心要素。"
        res = TextCleaner.clean(text)
        cleaned = res["cleaned_text"]
        self.assertIn("常常", cleaned)
        self.assertIn("代代相传", cleaned)
        self.assertIn("步步为营", cleaned)
        self.assertIn("层层递进", cleaned)
        self.assertIn("生生不息", cleaned)
        self.assertIn("端端加密", cleaned)

    def test_preserve_grammatical_verbs_and_pronouns(self):
        """Grammatical words like '是不是' (predicate verb) and '这个' (demonstrative pronoun) must be preserved."""
        text = "请首先判断当前节点是不是叶子节点。如果是，则选用这个特定算法进行计算，而不是那个冗余方案。"
        res = TextCleaner.clean(text)
        cleaned = res["cleaned_text"]
        self.assertIn("是不是", cleaned)
        self.assertIn("这个", cleaned)
        self.assertIn("那个", cleaned)

    def test_normalize_repeated_punctuations(self):
        """Consecutive identical punctuations like '，，，' or '。。。' should be collapsed."""
        text = "需求分析包括数据流图，，，状态迁移图以及实体模型。。。。这是核心要素！！！"
        res = TextCleaner.clean(text)
        cleaned = res["cleaned_text"]
        self.assertNotIn("，，", cleaned)
        self.assertNotIn("。。", cleaned)
        self.assertNotIn("！！", cleaned)
        self.assertIn("数据流图，状态迁移图以及实体模型。这是核心要素！", cleaned)


if __name__ == "__main__":
    unittest.main()
