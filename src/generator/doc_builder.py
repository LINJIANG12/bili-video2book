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
    def render_note(
        cls,
        title: str,
        part_title: str,
        content: str,
        note_type: str = "auto",
        desc: str = "",
    ) -> str:
        """Render a sober GitHub-styled markdown note locally."""
        if note_type == "auto" or not note_type:
            cat, reason = NoteClassifier.classify(title, desc=desc)
        else:
            cat = note_type.lower()
            reason = f"指定分类: {cat}"

        display_title = f"{title} - {part_title}" if part_title else title

        if cat == NoteClassifier.NEWS:
            return (
                f"# {display_title}\n\n"
                f"> 整理自音视频转录 | 类型：前沿资讯与版本动态 | 分类原因：{reason}\n\n"
                "## 核心动态摘要\n"
                f"{content[:240]}...\n\n"
                "## 核心更新与特性清单\n"
                "- **关键变更**：核心架构与运行效率优化\n"
                "- **技术机理**：底层逻辑重构与易用性提升\n"
                f"{content[240:600]}...\n\n"
                "## 优缺点与技术权衡\n\n"
                "| 维度 | 亮点与优势 | 局限性与成本 |\n"
                "| :--- | :--- | :--- |\n"
                "| 运行性能 | 资源占用低，吞吐提升明显 | 复杂场景需适配测试 |\n"
                "| 工程落地 | 开箱即用，降低搭建成本 | 迁移需评估兼顾旧版本 |\n\n"
                "## 影响评估与采用建议\n"
                "- **推荐受众**：追求新技术红利与工作流加速的开发者或技术团队。\n"
                "- **避坑指南**：严禁直接在冲刺上线的生产环境中盲目升级，建议通过独立沙盒验证。\n"
            )
        elif cat == NoteClassifier.STUDY:
            return (
                f"# {display_title}\n\n"
                f"> 整理自音视频转录 | 类型：课程与教学笔记 | 分类原因：{reason}\n\n"
                "## 知识结构导图\n"
                "- 基础概念与背景痛点\n"
                "- 核心理论模型与关键参数\n"
                "- 典型算法流程与工程实现\n"
                "- 易混淆对比与课后自测\n\n"
                "## 核心知识点精炼\n"
                "### 1. 核心理论与本质\n"
                f"{content[:200]}...\n\n"
                "### 2. 底层运行流程与关键参数\n"
                f"{content[200:500]}...\n\n"
                "## 易混淆概念对比与辨析\n\n"
                "| 对比维度 | 方案 A / 概念 A | 方案 B / 概念 B | 适用场景与权衡 |\n"
                "| :--- | :--- | :--- | :--- |\n"
                "| 复杂度 | 简单直观，开发周期短 | 抽象度高，扩展性好 | 结合项目规模选型 |\n"
                "| 性能损耗 | 内存开销小 | 计算吞吐高 | 关注底层瓶颈 |\n\n"
                "## 随堂自测与练习\n"
                "1. **核心思考**：该知识点解决的核心矛盾是什么？在什么边界条件下有效？\n"
                "2. **解析**：应紧扣底层机理与场景约束进行推演，避免死记硬背。\n"
            )
        else:
            return (
                f"# {display_title}\n\n"
                f"> 整理自音视频转录 | 类型：通用分享与知识笔记 | 分类原因：{reason}\n\n"
                "## 核心主旨与背景脉络\n"
                f"{content[:220]}...\n\n"
                "## 关键论点与论据拆解\n"
                "### 论点一：认知升级与底层逻辑\n"
                f"{content[220:500]}...\n\n"
                "## 方法论与实践框架\n"
                "- **第一步**：识别核心瓶颈，明确目标边界\n"
                "- **第二步**：建立反馈循环，快速验证假设\n"
                "- **第三步**：形成结构化沉淀，持续复盘优化\n\n"
                "## 关键见解与行动清单\n"
                "- 核心洞察：知其然更要知其所以然。\n"
                "- 行动建议：结合当下实际任务，小步快跑落地。\n"
            )

    @classmethod
    def render_learning_article(cls, title: str, part_title: str, content: str) -> str:
        """Render a full tutorial deep-dive article."""
        display_title = f"{part_title} - {title}" if part_title else title
        return (
            f"# {display_title}：从原理到实践深度精读\n\n"
            "## 一、 为什么关注这一议题\n"
            f"{content[:200]}...\n\n"
            "## 二、 核心原理与模型拆解\n"
            f"{content[200:600]}...\n\n"
            "## 三、 行业落地与最佳实践\n"
            "在真实工程实践中，必须综合考量架构演进、性能损耗以及可维护性。\n\n"
            "## 四、 总结与延展思考\n"
            "温故而知新，掌握底层逻辑比记住单一语法更具长久价值。\n"
        )

    @classmethod
    def save_deep_dive_article(cls, bvid: str, title: str, markdown_content: str, output_dir: str = "output") -> str:
        """Save deep dive article."""
        out_root = Path(output_dir).resolve() / "articles"
        out_root.mkdir(parents=True, exist_ok=True)
        safe_title = "".join(c for c in title if c.isalnum() or c in (" ", "-", "_")).strip()
        filepath = out_root / f"{bvid}_{safe_title}.md"
        filepath.write_text(markdown_content, encoding="utf-8")
        return str(filepath)
