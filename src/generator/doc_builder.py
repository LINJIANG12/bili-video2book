"""Document Builder & File Persister.

Renders adaptive prompts and writes generated artifacts (Sober GitHub-styled Notes and Articles) to disk.
"""

from pathlib import Path
from typing import Any, Dict, Optional

from .classifier import NoteClassifier
from .prompt_templates import (
    NOTE_STUDY_PROMPT,
    NOTE_NEWS_PROMPT,
    NOTE_GENERAL_PROMPT,
    ARTICLE_LEARNING_PROMPT,
    ASR_RECTIFY_PROMPT,
)


class DocumentBuilder:
    @staticmethod
    def render_prompts(
        title: str,
        part_title: str,
        content: str,
        note_type: str = "auto",
        desc: str = "",
    ) -> Dict[str, Any]:
        """Render note, article, and rectify prompts based on adaptive classification."""
        if note_type == "auto" or not note_type:
            cat, reason = NoteClassifier.classify(title, desc=desc)
        else:
            cat = note_type.lower()
            reason = f"用户显式指定类型: {cat}"

        if cat == NoteClassifier.NEWS:
            chosen_prompt_template = NOTE_NEWS_PROMPT
        elif cat == NoteClassifier.STUDY:
            chosen_prompt_template = NOTE_STUDY_PROMPT
        else:
            chosen_prompt_template = NOTE_GENERAL_PROMPT

        safe_part = part_title or "单集"
        note_prompt = (
            chosen_prompt_template.replace("{title}", title)
            .replace("{part_title}", safe_part)
            .replace("{content}", content)
        )
        article_prompt = (
            ARTICLE_LEARNING_PROMPT.replace("{title}", title)
            .replace("{part_title}", safe_part)
            .replace("{content}", content)
        )

        domain_hint = f"视频标题: {title} | 讲次: {safe_part}"
        if desc:
            domain_hint += f" | 简介: {desc[:200]}"
        rectify_prompt = (
            ASR_RECTIFY_PROMPT.replace("{domain_hint}", domain_hint)
            .replace("{raw_text}", content)
        )

        return {
            "note_prompt": note_prompt,
            "article_prompt": article_prompt,
            "rectify_prompt": rectify_prompt,
            "note_type": cat,
            "classify_reason": reason,
        }

    @staticmethod
    def render_rectify_prompt(
        raw_text: str,
        domain_hint: str = "",
    ) -> str:
        """Render ASR literal semantic proofreading prompt."""
        hint = domain_hint or "普通中文音视频转录语料"
        return (
            ASR_RECTIFY_PROMPT.replace("{domain_hint}", hint)
            .replace("{raw_text}", raw_text)
        )

    @staticmethod
    def save_documents(
        output_dir: str,
        base_name: str,
        note_content: str,
        article_content: Optional[str] = None,
        note_suffix: str = "笔记",
    ) -> Dict[str, str]:
        """Save notes and optional articles into markdown files."""
        out_root = Path(output_dir).resolve()
        notes_dir = out_root / "notes"
        notes_dir.mkdir(parents=True, exist_ok=True)

        note_file = notes_dir / f"{base_name}_{note_suffix}.md"
        note_file.write_text(note_content, encoding="utf-8")

        result = {"note_path": str(note_file)}

        if article_content:
            articles_dir = out_root / "articles"
            articles_dir.mkdir(parents=True, exist_ok=True)
            article_file = articles_dir / f"{base_name}_精读文章.md"
            article_file.write_text(article_content, encoding="utf-8")
            result["article_path"] = str(article_file)

        return result

    @classmethod
    def save_deep_dive_article(cls, bvid: str, title: str, markdown_content: str, output_dir: str = "output") -> str:
        """Save deep dive article."""
        out_root = Path(output_dir).resolve() / "articles"
        out_root.mkdir(parents=True, exist_ok=True)
        safe_title = "".join(c for c in title if c.isalnum() or c in (" ", "-", "_")).strip()
        filepath = out_root / f"{bvid}_{safe_title}.md"
        filepath.write_text(markdown_content, encoding="utf-8")
        return str(filepath)
