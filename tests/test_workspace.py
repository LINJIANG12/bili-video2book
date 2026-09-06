"""Unit tests for TaskWorkspace directory management."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.workspace import TaskWorkspace


class TestTaskWorkspace(unittest.TestCase):
    def test_workspace_creation_default(self):
        """Default workspace creates structured subdirectories without invalid chars."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ws = TaskWorkspace.create(
                title="【公开课】浙江大学：软件工程 陈越（全33讲）",
                bvid="BV16g411M7r2",
                base_dir=tmpdir,
            )
            self.assertTrue(ws.root_dir.exists())
            self.assertTrue(ws.audio_dir.exists())
            self.assertTrue(ws.notes_dir.exists())
            self.assertTrue(ws.articles_dir.exists())
            self.assertTrue(ws.subtitles_dir.exists())

            # Ensure colon and slash were safely stripped
            self.assertNotIn(":", ws.task_name)
            self.assertNotIn("/", ws.task_name)
            self.assertIn("BV16g411M7r2", ws.task_name)

    def test_workspace_custom_name(self):
        """Custom task name takes precedence."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ws = TaskWorkspace.create(
                title="任意标题",
                bvid="BV1234567890",
                custom_name="my_custom_task",
                base_dir=tmpdir,
            )
            self.assertEqual(ws.task_name, "my_custom_task")
            self.assertEqual(ws.root_dir, Path(tmpdir) / "my_custom_task")

    def test_workspace_manifest(self):
        """Manifest can be written and read accurately."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ws = TaskWorkspace.create(
                title="测试课程",
                bvid="BVtest12345",
                base_dir=tmpdir,
            )
            data = {"total_episodes": 33, "status": "completed"}
            ws.save_manifest(data)
            loaded = ws.load_manifest()
            self.assertEqual(loaded["total_episodes"], 33)
            self.assertEqual(loaded["status"], "completed")


if __name__ == "__main__":
    unittest.main()
