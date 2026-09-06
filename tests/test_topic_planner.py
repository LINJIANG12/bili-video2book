"""Unit tests for SemanticTopicPlanner."""

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

from src.generator.topic_planner import SemanticTopicPlanner


class TestSemanticTopicPlanner(unittest.TestCase):
    def test_validate_plan_valid(self):
        """Valid plan covering 1 to 5 strictly should pass validation."""
        valid_plan = [
            {"block_id": 1, "block_title": "软件工程概述", "episodes": [1, 2], "core_theme": "概述"},
            {"block_id": 2, "block_title": "软件过程", "episodes": [3, 4, 5], "core_theme": "过程模型"},
        ]
        is_valid, reason = SemanticTopicPlanner.validate_plan(valid_plan, total_episodes=5)
        self.assertTrue(is_valid, reason)

    def test_validate_plan_missing_episode(self):
        """Plan missing episode 3 should fail validation."""
        invalid_plan = [
            {"block_id": 1, "block_title": "软件工程概述", "episodes": [1, 2], "core_theme": "概述"},
            {"block_id": 2, "block_title": "软件过程", "episodes": [4, 5], "core_theme": "过程模型"},
        ]
        is_valid, reason = SemanticTopicPlanner.validate_plan(invalid_plan, total_episodes=5)
        self.assertFalse(is_valid)
        self.assertIn("缺失", reason)

    def test_validate_plan_duplicate_episode(self):
        """Plan with duplicate episode should fail validation."""
        duplicate_plan = [
            {"block_id": 1, "block_title": "软件工程概述", "episodes": [1, 2, 3], "core_theme": "概述"},
            {"block_id": 2, "block_title": "软件过程", "episodes": [3, 4, 5], "core_theme": "过程模型"},
        ]
        is_valid, reason = SemanticTopicPlanner.validate_plan(duplicate_plan, total_episodes=5)
        self.assertFalse(is_valid)
        self.assertIn("重复", reason)

    def test_fallback_heuristic_plan(self):
        """Fallback planner clusters consecutive parts without regex."""
        sample_parts = [
            {"page": 1, "title": "第1讲 软件工程概述-1"},
            {"page": 2, "title": "第2讲 软件工程概述-2"},
            {"page": 3, "title": "第3讲 软件过程-1"},
            {"page": 4, "title": "第4讲 软件过程-2"},
            {"page": 5, "title": "第5讲 软件过程-3"},
        ]
        plan = SemanticTopicPlanner.fallback_heuristic_plan(sample_parts)
        is_valid, _ = SemanticTopicPlanner.validate_plan(plan, total_episodes=5)
        self.assertTrue(is_valid)
        self.assertEqual(len(plan), 2)
        self.assertEqual(plan[0]["episodes"], [1, 2])
        self.assertEqual(plan[1]["episodes"], [3, 4, 5])


if __name__ == "__main__":
    unittest.main()
