"""Block Synthesizer: 导出「模块笔记」融合任务书（文章直供版）。

架构定位：工具层只负责**备料与渲染提示词**——把该模块各集单集精读长文（`articles/`）的路径清单、
模块边界信息、专属提示词（`MODULE_NOTE_PROMPT`）、渲染兼容规则与笔记版式规范组装成
`notes/模块XX_*_TASK.md`，交由宿主 Agent（通常是每模块一个子智能体）原生撰写。

语料变更（v1.7）：模块笔记的唯一事实来源是**单集精读长文**；
知识元（kernel）已从「前置门禁」降级为「可选索引」（`kernel_index` 显式传入才注入），
因为空壳知识元会把笔记质量一并拖垮。成品产出后任务书由 task_cleanup 自动回收。

风格变更（v1.8）：笔记**只有这一种风格**（旧版八种风格矩阵已删除），不再需要 `--style`。
"""

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from src.generator.prompt_templates import (
    MODULE_NOTE_PROMPT,
    NOTE_VISUAL_SPEC,
    RENDER_COMPAT_RULES,
)

# 成品体积门槛：低于该值视为空壳，需重新派发
MIN_NOTE_BYTES = 1000


class BlockSynthesizer:
    @classmethod
    def _render_article_list(cls, article_paths: Iterable[Any]) -> str:
        """渲染「唯一事实来源」清单：仓库相对路径 + 字节数，便于 Agent 逐篇 Read。"""
        lines: List[str] = []
        for raw in article_paths:
            path = Path(raw)
            try:
                from src.core.workspace import TaskWorkspace
                shown = TaskWorkspace.to_relative(path)
            except Exception:
                shown = path.as_posix()
            try:
                size = path.stat().st_size if path.exists() else 0
            except OSError:
                size = 0
            lines.append(f"- {shown}  ({size:,} 字节)")
        return "\n".join(lines) if lines else "- （本模块尚无单集精读长文，请先补齐 articles/ 后再派发）"

    @classmethod
    def collect_block_articles(cls, episodes: Iterable[Dict[str, Any]], ws: Any):
        """收集本模块各集的单集精读长文，返回 (文章路径列表, 缺文章的分集号列表)。

        复用 KernelExtractor 的宽容定位，兼容历史工作区无 `_精读文章` 后缀的命名。
        """
        from src.core.kernel_extractor import KernelExtractor

        found: List[Any] = []
        missing: List[int] = []
        for ep in episodes:
            page = ep.get("page")
            article = KernelExtractor.find_article(ws, page)
            if article is None:
                missing.append(page)
            else:
                found.append(article)
        return found, missing

    @classmethod
    def build_synthesis_prompt(
        cls,
        block_meta: Dict[str, Any],
        article_paths: Optional[Iterable[Any]] = None,
        kernel_index: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """组装模块笔记撰写提示词（文章直供 + 渲染硬约束 + 统一版式规范）。

        笔记只有这一种风格，因此不再接受 `style` 参数。
        """
        eps = sorted(block_meta.get("episodes", []))
        p_str = f"P{eps[0]:02d}-P{eps[-1]:02d}" if len(eps) > 1 else (f"P{eps[0]:02d}" if eps else "P??")
        b_id_str = f"{block_meta.get('block_id', 1):02d}"

        def 安全(值: Any) -> str:
            return str(值).replace("{", "(").replace("}", ")")

        prompt = (
            MODULE_NOTE_PROMPT
            .replace("{block_id:02d}", b_id_str)
            .replace("{block_id}", b_id_str)
            .replace("{block_title}", 安全(block_meta.get("block_title", "知识模块")))
            .replace("{episodes_str}", p_str)
            .replace("{core_theme}", 安全(block_meta.get("core_theme", "")))
            .replace("{article_list}", cls._render_article_list(article_paths or []))
        )
        prompt = prompt.replace("{{", "{").replace("}}", "}")

        # 可选索引：仅当调用方显式传入知识元时才注入（默认不参与，避免空壳知识元拖垮笔记质量）
        if kernel_index:
            compact = json.dumps(kernel_index, ensure_ascii=False, indent=2)
            prompt += (
                "\n━━━━━━━━━━━━━━━━━━\n"
                "六、可选结构化索引（仅供定位，不得作为唯一事实来源）\n"
                "━━━━━━━━━━━━━━━━━━\n"
                "下列知识元索引可能存在缺失或不完整之处；**它只用于帮助你定位主题**，"
                "一切事实仍以上方单集精读长文为准。索引与长文冲突时，一律以长文为准。\n\n"
                f"```json\n{compact}\n```\n"
            )

        # 排版硬约束 + 统一版式规范：在此统一注入（笔记只有这一种风格，不再按风格分支）
        prompt += f"\n━━━━━━━━━━━━━━━━━━\n{RENDER_COMPAT_RULES}\n"
        prompt += f"\n━━━━━━━━━━━━━━━━━━\n{NOTE_VISUAL_SPEC}\n"
        return prompt

    @classmethod
    def get_task_filename(cls, block_meta: Dict[str, Any]) -> str:
        """Construct block synthesis task-file name: 模块01_软件工程概述_TASK.md."""
        block_id = block_meta.get("block_id", 1)
        raw_title = block_meta.get("block_title", "知识模块")
        clean_title = "".join(c for c in raw_title if c.isalnum() or c in (" ", "-", "_")).strip()
        return f"模块{block_id:02d}_{clean_title}_TASK.md"

    @classmethod
    def get_note_filename(cls, block_meta: Dict[str, Any]) -> str:
        """Construct the delivered note filename: 模块01_软件工程概述_笔记.md."""
        return cls.get_task_filename(block_meta)[: -len("_TASK.md")] + "_笔记.md"

    @classmethod
    def _find_existing_note(cls, ws: Any, block_meta: Dict[str, Any]) -> Optional[Path]:
        """定位该模块已落盘的笔记成品（规范名优先，回退按模块号前缀匹配）。"""
        note_file = ws.notes_dir / cls.get_note_filename(block_meta)
        try:
            from src.core.task_cleanup import find_module_note
        except Exception:
            return note_file if note_file.exists() else None
        return find_module_note(ws, block_meta.get("block_id"), preferred_name=note_file.name)

    @classmethod
    def synthesize_block(
        cls,
        block_meta: Dict[str, Any],
        articles: Optional[Iterable[Any]] = None,
        ws: Any = None,
        force: bool = False,
        kernel_index: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """导出模块笔记融合任务书（文章直供版），供宿主 Agent / 子智能体原生撰写。

        门禁：本模块各集单集精读长文齐备才导出任务书；笔记成品已存在则跳过（除非 force）。
        """
        eps = sorted(block_meta.get("episodes", []))
        p_str = f"P{eps[0]:02d}-P{eps[-1]:02d}" if len(eps) > 1 else (f"P{eps[0]:02d}" if eps else "P??")
        task_file = ws.notes_dir / cls.get_task_filename(block_meta)
        note_file = ws.notes_dir / cls.get_note_filename(block_meta)

        base_result = {
            "block_id": block_meta.get("block_id"),
            "block_title": block_meta.get("block_title"),
            "episodes": eps,
            "task_file": str(task_file),
            "note_file": str(note_file),
        }

        # 成品已存在：不再重复派发，并顺手回收残留任务书（保留编号最小的范本）
        # 复用判定统一交给 task_cleanup.find_module_note：先规范名，再按模块号前缀回退，
        # 否则历史工作区里叫 `模块XX_…_思维导图速查笔记.md` 的成品会被判成「无成品」而重复派发。
        cached_note = cls._find_existing_note(ws, block_meta)
        if (
            cached_note is not None
            and cached_note.stat().st_size >= MIN_NOTE_BYTES
            and not force
        ):
            try:
                from src.core.task_cleanup import reclaim_module_note_task
                reclaim_module_note_task(ws, int(block_meta.get("block_id", 1)))
            except Exception:
                pass
            print(f"[*] 模块 {block_meta['block_id']:02d} ({p_str}) 模块笔记已存在，跳过派发: {cached_note.name}")
            return {
                **base_result,
                "note_file": str(cached_note),
                "size_bytes": cached_note.stat().st_size,
                "status": "cached",
            }

        synthesis_prompt = cls.build_synthesis_prompt(
            block_meta, article_paths=articles, kernel_index=kernel_index
        )
        header = (
            f"# 模块 {block_meta['block_id']:02d} {block_meta.get('block_title', '')} 模块笔记任务书（MODULE_NOTE_TASK）\n\n"
            f"> 状态：need-agent-note | 语料：本模块单集精读长文（articles/） | 由宿主 Agent / 子智能体原生撰写\n"
            f"> 工作区绝对路径：`{Path(ws.root_dir).as_posix()}`\n\n"
            f"## 1. 落盘要求\n\n"
            f"- 撰写提示词见下方第 2 节（含模块信息、语料清单、结构要求、密度纪律、零套话禁令与笔记版式规范）\n"
            f"- 目标文件：`{Path(note_file).as_posix()}`\n"
            f"- 必须逐篇完整读取上方列出的单集精读长文后再撰写；成品产出后本任务书会被自动回收\n"
            f"- 执行须知：建议由**一个子智能体负责一个模块**；完成后只需回报"
            f"「模块号 | 目标文件 | 字节数 | 覆盖分集 | 套话/分集标题/截断 三项自检结果」，**不要回传正文**\n\n"
            f"---\n\n"
            f"## 2. 模块笔记撰写提示词\n\n"
        )
        content = header + synthesis_prompt

        content_unchanged = False
        if task_file.exists():
            try:
                content_unchanged = task_file.read_text(encoding="utf-8") == content
            except OSError:
                content_unchanged = False

        if content_unchanged:
            print(f"[*] 模块 {block_meta['block_id']:02d} ({p_str}) 任务书内容无变化，跳过重写: {task_file.name}")
            return {**base_result, "size_bytes": task_file.stat().st_size, "status": "cached"}

        task_file.parent.mkdir(parents=True, exist_ok=True)
        task_file.write_text(content, encoding="utf-8")
        print(f"[✓] 模块 {block_meta['block_id']:02d} ({p_str}: {block_meta.get('block_title', '')}) 笔记任务书已导出: {task_file.name}")

        return {**base_result, "size_bytes": task_file.stat().st_size, "status": "generated"}
