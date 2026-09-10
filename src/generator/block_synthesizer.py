"""Block Synthesizer: Exports module-level synthesis task-files for Agent-native note authoring.

Architecture: CLI provides tooling only (task-file export); the mature host dialogue model performs
the real block-note synthesis natively from the exported SYNTHESIS_PROMPT.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.generator.prompt_templates import NOTE_STYLES


class BlockSynthesizer:
    SYNTHESIS_PROMPT = """你是一位擅长高密度知识提炼与体系重构的资深学科主编。

输入是从一个专题模块的多集视频中提取的【高纯度知识元集合】。你的任务不是逐集流水账复述，而是把这些知识元【深度融合】为一份紧凑干练、极高信息密度的【模块复习速查笔记】。同一主题在不同分集中的内容必须合并归拢，消除割裂痕迹，最终成品读起来应像一本权威专著中的自洽章节。

【模块信息】
- 模块编号: {block_id}
- 模块主题: {block_title}
- 涵盖分集: {episodes_str}
- 核心议题: {core_theme}

【知识元集合】
{kernels_json}

━━━━━━━━━━━━━━━━━━
一、定位与融合规则
━━━━━━━━━━━━━━━━━━
1. **纯粹的复习速查定位**：
   - 本笔记专精于核心知识骨架与要点速查，**不收录长篇案例记叙，不包含练习测验题**，全篇追求极高信息密度。
2. **概念本体深度融合（Ontology Merge）**：
   - 同一概念/主题在多个分集中分散讲解的，必须完整合并到同一条目下统一阐述（核心本质 → 工作机理 → 变体演进 → 局限边界）；
   - 在每个核心概念条目末尾，用一行小字标注来源分集（如 `> 来源: P01, P03`），方便读者回溯原视频。
3. **冲突演进处理**：
   - 若后分集对前分集内容有补充、深化或修正，按最终演化结果统一；若为并列争议观点，客观并列呈现。
4. **消除跨集割裂痕迹**：
   - 正文中严禁出现“在上一讲中”、“本集”、“P01中提到”等分集口吻。
5. **事实边界（Strict Grounding）**：
   - 所有事实、定义、机制、结论严格来自知识元，严禁引入外部术语、概念或脑补细节；语料未提及的细节写明“未说明”，严禁编造。

━━━━━━━━━━━━━━━━━━
二、结构与表达（按需生长，拒绝僵化）
━━━━━━━━━━━━━━━━━━
1. **章节语境化**：
   - 根据模块所属领域（技术、学术、游戏、社科等）自适应拟定贴切自然的二级标题（## ），严禁机械套用生硬的工科模板词汇。
2. **表达工具箱（自然融入，无则坚决不写）**：
   - **知识拓扑**：在开篇使用清晰紧凑的 ASCII 树状图展现本模块的概念体系与脉络全貌；
   - **横向对比表格（按需，非必须）**：仅在语料中客观存在 2~N 个天然可比的实体（如不同方案、机制、流派、工具、易混概念）时自然使用 Markdown 表格，列名自适应；**若语料中并无横向对比要素，严禁强行画表，也绝不要输出任何带有“对比”字样的空白小节**；
   - **易错/反模式清单（按需）**：仅当语料中明确指出了认知误区、避坑要点或失误陷阱时条目化列出，无则不强加。

直接输出完整笔记 Markdown，标题为 `# 模块 {block_id}：{block_title}`，不输出任何前缀废话或分析说明。
"""

    @classmethod
    def build_synthesis_prompt(
        cls,
        block_meta: Dict[str, Any],
        kernels: List[Dict[str, Any]],
        style: Optional[str] = None,
    ) -> str:
        """Build the synthesis prompt for the Agent to execute natively (no network in tooling)."""
        eps = sorted(block_meta.get("episodes", []))
        p_str = f"P{eps[0]:02d}-P{eps[-1]:02d}" if len(eps) > 1 else f"P{eps[0]:02d}"
        kernels_clean_json = json.dumps(kernels, ensure_ascii=False, indent=2)
        b_id_str = f"{block_meta.get('block_id', 1):02d}"
        prompt = (
            cls.SYNTHESIS_PROMPT
            .replace("{block_id:02d}", b_id_str)
            .replace("{block_id}", b_id_str)
            .replace("{block_title}", str(block_meta.get("block_title", "知识模块")))
            .replace("{episodes_str}", p_str)
            .replace("{core_theme}", str(block_meta.get("core_theme", "")))
            .replace("{kernels_json}", kernels_clean_json)
        )
        prompt = prompt.replace("{{", "{").replace("}}", "}")

        # Inject selected note style (e.g. minimal / SSHeRun/CS-Xmind-Note)
        if style:
            style_key = style.lower().strip()
            for k, v in NOTE_STYLES.items():
                if style.strip() == k or style.strip() == v.get("label"):
                    style_key = k
                    break
            if style_key in NOTE_STYLES:
                st = NOTE_STYLES[style_key]
                prompt += (
                    f"\n━━━━━━━━━━━━━━━━━━\n"
                    f"三、指定笔记风格：{st['label']} ({style_key})\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"{st['instruction']}\n"
                )
        return prompt

    @classmethod
    def get_task_filename(cls, block_meta: Dict[str, Any]) -> str:
        """Construct block synthesis task-file name: 模块01_软件工程概述_TASK.md."""
        block_id = block_meta.get("block_id", 1)
        raw_title = block_meta.get("block_title", "知识模块")
        clean_title = "".join(c for c in raw_title if c.isalnum() or c in (" ", "-", "_")).strip()
        return f"模块{block_id:02d}_{clean_title}_TASK.md"

    @classmethod
    def synthesize_block(
        cls,
        block_meta: Dict[str, Any],
        kernels: List[Dict[str, Any]],
        ws: Any,
        force: bool = False,
        style: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Tooling export: persist the module synthesis task-file (SYNTHESIS_PROMPT) for Agent-native authoring."""
        task_file = ws.notes_dir / cls.get_task_filename(block_meta)

        eps = sorted(block_meta.get("episodes", []))
        p_str = f"P{eps[0]:02d}-P{eps[-1]:02d}" if len(eps) > 1 else f"P{eps[0]:02d}"

        # 中文注释：任务书已存在且内容完备即跳过重写；若旧任务书为空壳且当前已有知识元，自动刷新
        if task_file.exists() and not force:
            should_refresh = False
            try:
                content = task_file.read_text(encoding="utf-8")
                if len(content) < 100:
                    should_refresh = True
                elif kernels and any(k.get("definitions") or k.get("mechanisms_and_models") or k.get("title") for k in kernels):
                    if "【知识元集合】\n[]" in content or "【知识元集合】\n[\n]" in content or '"definitions": []' in content:
                        should_refresh = True
            except Exception:
                should_refresh = True

            if not should_refresh:
                print(f"[*] 模块 {block_meta['block_id']:02d} ({p_str}) 任务书已存在，跳过导出: {task_file.name}")
                return {
                    "block_id": block_meta["block_id"],
                    "block_title": block_meta["block_title"],
                    "episodes": eps,
                    "task_file": str(task_file),
                    "size_bytes": task_file.stat().st_size,
                    "status": "cached",
                }

        synthesis_prompt = cls.build_synthesis_prompt(block_meta, kernels, style=style)
        task_file.parent.mkdir(parents=True, exist_ok=True)
        task_file.write_text(synthesis_prompt, encoding="utf-8")
        print(f"[✓] 模块 {block_meta['block_id']:02d} ({p_str}: {block_meta['block_title']}) 融合笔记任务书已导出: {task_file.name}")

        return {
            "block_id": block_meta["block_id"],
            "block_title": block_meta["block_title"],
            "episodes": eps,
            "task_file": str(task_file),
            "size_bytes": task_file.stat().st_size,
            "status": "generated",
        }
