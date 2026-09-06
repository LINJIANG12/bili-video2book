"""Task Workspace Manager for Output Directory Segregation.

Enforces a task-centric directory hierarchy:
output/
└── <Task_Name>/
    ├── audio/       # Extracted m4a audio and chunk files
    ├── notes/       # Structured markdown study/news/general notes
    ├── articles/    # Deep dive markdown articles
    ├── subtitles/   # Extracted AI/human subtitles or raw transcripts
    └── manifest.json
"""

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional, Union


class TaskWorkspace:
    ILLEGAL_CHARS_REGEX = re.compile(r'[\\/*?:"<>|#\n\r\t]+')

    def __init__(self, task_name: str, base_dir: Union[str, Path] = "output"):
        self.task_name = self.sanitize_name(task_name)
        self.base_dir = Path(base_dir).resolve()
        self.root_dir = self.base_dir / self.task_name
        self.audio_dir = self.root_dir / "audio"
        self.notes_dir = self.root_dir / "notes"
        self.articles_dir = self.root_dir / "articles"
        self.subtitles_dir = self.root_dir / "subtitles"
        self.manifest_file = self.root_dir / "manifest.json"

        self.ensure_dirs()

    @classmethod
    def sanitize_name(cls, raw_name: str) -> str:
        """Strip invalid filesystem characters and limit length."""
        cleaned = cls.ILLEGAL_CHARS_REGEX.sub("_", raw_name)
        cleaned = re.sub(r"_+", "_", cleaned).strip(" ._-")
        return cleaned[:100] if cleaned else "task_unnamed"

    def ensure_dirs(self):
        """Ensure task root and all categorized subfolders exist."""
        for d in [self.root_dir, self.audio_dir, self.notes_dir, self.articles_dir, self.subtitles_dir]:
            d.mkdir(parents=True, exist_ok=True)

    @classmethod
    def create(
        cls,
        title: str,
        bvid: str = "",
        custom_name: Optional[str] = None,
        base_dir: Union[str, Path] = "output",
    ) -> "TaskWorkspace":
        """Factory method to scaffold a task workspace."""
        if custom_name:
            task_name = custom_name
        else:
            safe_title = cls.sanitize_name(title)
            task_name = f"{safe_title}_{bvid}" if bvid else safe_title

        return cls(task_name=task_name, base_dir=base_dir)

    def save_manifest(self, data: Dict[str, Any]):
        """Persist or update task manifest JSON atomically."""
        existing = {}
        if self.manifest_file.exists():
            try:
                with open(self.manifest_file, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            except Exception:
                existing = {}

        existing.update(data)
        tmp_file = self.manifest_file.with_suffix(f".tmp.{os.getpid()}")
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_file, self.manifest_file)

    def load_manifest(self) -> Dict[str, Any]:
        """Load manifest JSON or return empty dict."""
        if not self.manifest_file.exists():
            return {}
        try:
            with open(self.manifest_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
