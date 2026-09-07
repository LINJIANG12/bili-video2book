"""Block Synthesizer: Provides prompts for Agent to synthesize block notes, plus local fallback rendering.

Architecture: CLI provides tooling + local fallback. The mature Agent performs high-quality synthesis natively.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


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
    def get_block_filename(cls, block_meta: Dict[str, Any]) -> str:
        """Construct standard block note filename: 模块01_软件工程概述_P01-P02_笔记.md."""
        block_id = block_meta.get("block_id", 1)
        raw_title = block_meta.get("block_title", "知识模块")
        clean_title = "".join(c for c in raw_title if c.isalnum() or c in (" ", "-", "_")).strip()

        eps = sorted(block_meta.get("episodes", []))
        if not eps:
            p_range = "P01"
        elif len(eps) == 1:
            p_range = f"P{eps[0]:02d}"
        else:
            p_range = f"P{eps[0]:02d}-P{eps[-1]:02d}"

        return f"模块{block_id:02d}_{clean_title}_{p_range}_笔记.md"

    @classmethod
    def render_local_fallback(
        cls,
        block_meta: Dict[str, Any],
        kernels: List[Dict[str, Any]],
    ) -> str:
        """Generate structured markdown note locally from kernel atoms if model is unavailable."""
        block_id = block_meta.get("block_id", 1)
        block_title = block_meta.get("block_title", "核心知识模块")
        eps = sorted(block_meta.get("episodes", []))
        p_str = f"P{eps[0]:02d}-P{eps[-1]:02d}" if len(eps) > 1 else f"P{eps[0]:02d}"

        lines = [
            f"# 模块{block_id:02d}：{block_title}（{p_str}）\n",
            f"> 体系化知识模块复习笔记 | 涵盖分集：{p_str} | 核心议题：{block_meta.get('core_theme', '')}\n",
            "## 知识拓扑框架导图\n",
            f"- 模块核心：{block_title}",
        ]
        for k in kernels:
            lines.append(f"  ├── P{k['page']:02d}: {k['title']}")

        lines.append("\n## 核心概念与理论模型精炼\n")
        all_defs = []
        for k in kernels:
            all_defs.extend(k.get("definitions", []))
        for d in all_defs:
            lines.append(f"### {d.get('term')}\n- **核心本质**：{d.get('essence')}\n")

        all_models = []
        for k in kernels:
            all_models.extend(k.get("mechanisms_and_models", []))
        if all_models:
            lines.append("\n## 关键机制与理论模型\n")
            for m in all_models:
                lines.append(f"### {m.get('name')}\n- **运作机理**：{m.get('details')}\n")

        all_comps = []
        for k in kernels:
            all_comps.extend(k.get("comparisons", []))
        if all_comps:
            lines.append("\n## 关键要素对比辨析\n")
            lines.append("| 对比实体 | 核心差异与适用场景 |")
            lines.append("| :--- | :--- |")
            for c in all_comps[:5]:
                lines.append(f"| {c.get('entities', '概念对比')} | {c.get('distinction', '详见解析')} |")

        all_anti = []
        for k in kernels:
            all_anti.extend(k.get("anti_patterns", []))
        if all_anti:
            lines.append("\n## 常见反模式与避坑要点\n")
            for a in set(all_anti):
                lines.append(f"- **避坑提醒**：{a}")

        return "\n".join(lines)

    @classmethod
    def build_synthesis_prompt(
        cls,
        block_meta: Dict[str, Any],
        kernels: List[Dict[str, Any]],
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
        return prompt.replace("{{", "{").replace("}}", "}")

    @classmethod
    def synthesize_block(
        cls,
        block_meta: Dict[str, Any],
        kernels: List[Dict[str, Any]],
        ws: Any,
        force: bool = False,
    ) -> Dict[str, Any]:
        """Local tooling synthesis: persist local fallback note. Agent should upgrade via build_synthesis_prompt()."""
        filename = cls.get_block_filename(block_meta)
        note_file = ws.notes_dir / filename

        eps = sorted(block_meta.get("episodes", []))
        p_str = f"P{eps[0]:02d}-P{eps[-1]:02d}" if len(eps) > 1 else f"P{eps[0]:02d}"

        if note_file.exists() and note_file.stat().st_size > 1500 and not force:
            print(f"[*] 模块 {block_meta['block_id']:02d} ({p_str}) 笔记已存在，跳过生成: {note_file.name}")
            return {
                "block_id": block_meta["block_id"],
                "block_title": block_meta["block_title"],
                "episodes": eps,
                "note_file": str(note_file),
                "size_bytes": note_file.stat().st_size,
                "status": "cached",
            }

        print(f"[*] 正在为模块 {block_meta['block_id']:02d} ({p_str}: {block_meta['block_title']}) 生成本地基础笔记 (Agent 可基于 prompt 升级)...")

        note_md = cls.render_local_fallback(block_meta, kernels)

        note_file.parent.mkdir(parents=True, exist_ok=True)
        note_file.write_text(note_md, encoding="utf-8")
        print(f"[✓] 模块 {block_meta['block_id']:02d} 本地笔记落盘完成 ({len(note_md)} 字) -> {note_file.name}")

        return {
            "block_id": block_meta["block_id"],
            "block_title": block_meta["block_title"],
            "episodes": eps,
            "note_file": str(note_file),
            "size_bytes": note_file.stat().st_size,
            "status": "generated",
        }
