"""Semantic Topic Planner: Exports module-boundary planning task-files for Agent-native execution.

Architecture: the CLI only provides tooling (prompt rendering, validation, cache reuse).
The host dialogue model performs the real semantic module planning and writes topic_plan.json.
A missing plan is reported as pending -- the CLI never fabricates a module split locally.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class SemanticTopicPlanner:
    STATUS_PENDING = "need-agent-plan"

    PLAN_PROMPT = """你是一位国家级计算机学科教学大纲架构专家。
请仔细分析以下课程的分集标题以及【实际语料核心提要】。
根据实际学术知识体系与内容逻辑边界，识别视频之间的真实分界线，将属于同一有机知识模块的连续分集聚合为一个知识块（Knowledge Block）。

【课程标题】：{course_title}
【分集与实际内容提要清单】：
{episodes_text}

【规划要求】：
1. 坚决覆盖全部 1 到 {total_count} 集，不得遗漏任何一集，不得重复分配任何一集。
2. 每个知识块通常包含 1 到 3 集（极少数大型模块可包含 4 集），粒度要适中（避免切得太碎，也避免合得太糙）。
3. block_title 必须是结合【实际语料】提炼出的高度概括专业主题（如“软件工程导论与学科范式”、“软件过程模型体系与演进”、“需求分析方法与系统建模技术”）。
4. 输出严格遵循以下 JSON Array 规范，严禁输出任何 Markdown 格式外的前后寒暄废话：

```json
[
  {{
    "block_id": 1,
    "block_title": "软件工程导论与学科范式",
    "episodes": [1, 2],
    "core_theme": "学科定位、管理学属性、历史反模式、防搭便车考核机制"
  }}
]
```
"""

    @classmethod
    def validate_plan(cls, plan: List[Dict[str, Any]], total_episodes: int) -> Tuple[bool, str]:
        """Validate that all episodes 1..total_episodes are strictly and uniquely covered."""
        if not isinstance(plan, list) or not plan:
            return False, "规划为空或非列表格式"

        assigned_episodes = []
        for b_idx, block in enumerate(plan, 1):
            eps = block.get("episodes", [])
            if not eps:
                return False, f"模块 {b_idx} 未包含任何分集"
            assigned_episodes.extend(eps)

        all_unique = set(assigned_episodes)
        if len(assigned_episodes) != len(all_unique):
            duplicates = [x for x in all_unique if assigned_episodes.count(x) > 1]
            return False, f"发现重复分配的分集: {duplicates}"

        expected = set(range(1, total_episodes + 1))
        missing = expected - all_unique
        if missing:
            return False, f"发现缺失未分配的分集: {sorted(missing)}"

        extra = all_unique - expected
        if extra:
            return False, f"发现超出有效范围的分集编号: {sorted(extra)}"

        return True, "规划完整有效"

    @classmethod
    def build_planning_prompt(
        cls,
        parts: List[Dict[str, Any]],
        course_title: str = "",
        transcript_summaries: Optional[Dict[int, str]] = None,
    ) -> str:
        """Build the planning prompt for the Agent to execute natively (no network in tooling)."""
        total_count = len(parts)
        episodes_lines = []
        for p in parts:
            p_num = p["page"]
            line = f"- P{p_num:02d}: {p['title']}"
            if transcript_summaries and p_num in transcript_summaries:
                summary_snippet = transcript_summaries[p_num][:220].replace("\n", " ").strip()
                line += f"\n  [语料要点]: {summary_snippet}..."
            episodes_lines.append(line)
        safe_title = (course_title or "计算机专业课程").replace("{", "(").replace("}", ")")
        prompt = (
            cls.PLAN_PROMPT
            .replace("{course_title}", safe_title)
            .replace("{episodes_text}", "\n".join(episodes_lines))
            .replace("{total_count}", str(total_count))
        )
        # Escape double-brace example JSON back to single braces for Agent readability
        return prompt.replace("{{", "{").replace("}}", "}")

    @classmethod
    def export_plan_task(
        cls,
        parts: List[Dict[str, Any]],
        course_title: str,
        ws: Any,
        transcript_summaries: Optional[Dict[int, str]] = None,
    ) -> Path:
        """Export the TOPIC_PLAN_TASK file instructing the Agent to plan module boundaries."""
        plan_file = ws.root_dir / "topic_plan.json"
        task_file = ws.root_dir / "topic_plan_TASK.md"
        prompt = cls.build_planning_prompt(
            parts, course_title=course_title, transcript_summaries=transcript_summaries
        )
        content = (
            f"# 课程知识块规划任务书（TOPIC_PLAN_TASK）\n\n"
            f"> 状态：{cls.STATUS_PENDING} | 由宿主 Agent 依据真实语料语义规划；CLI 不做本地关键词聚类\n\n"
            f"## 1. 落盘要求\n\n"
            f"- 目标文件：`{plan_file.as_posix()}`\n"
            f"- 必须为合法 JSON Array\n"
            f"- 分集 1..{len(parts)} 必须被**唯一**覆盖：不得遗漏、不得重复、不得越界\n"
            f"- 校验规则：空模块、重复分集、缺失分集、越界编号均会被拒绝并回退到本任务书\n"
            f"- 规划完成后重跑对应 CLI 命令即可自动复用\n\n"
            f"---\n\n"
            f"## 2. 规划提示词\n\n{prompt}\n"
        )
        task_file.write_text(content, encoding="utf-8")
        return task_file

    @classmethod
    def plan(
        cls,
        parts: List[Dict[str, Any]],
        course_title: str = "",
        ws: Optional[Any] = None,
        force: bool = False,
        transcript_summaries: Optional[Dict[int, str]] = None,
    ) -> Optional[List[Dict[str, Any]]]:
        """Reuse the Agent-produced topic_plan.json, or export a task-file and return None.

        Returns None when no valid plan exists yet (a task-file will have been exported), so
        callers can gate the next stage instead of proceeding on a fabricated module split.
        """
        total_count = len(parts)
        if total_count == 0:
            return []

        if ws and hasattr(ws, "root_dir"):
            plan_file = ws.root_dir / "topic_plan.json"
            if plan_file.exists() and not force:
                try:
                    cached_plan = json.loads(plan_file.read_text(encoding="utf-8"))
                    is_valid, _ = cls.validate_plan(cached_plan, total_count)
                    if is_valid:
                        return cached_plan
                except Exception:
                    pass

        # A single-episode course needs no semantic split; the trivial plan is exact, not a guess.
        if total_count == 1:
            trivial_plan = [{
                "block_id": 1,
                "block_title": parts[0]["title"],
                "episodes": [1],
                "core_theme": parts[0]["title"],
            }]
            if ws and hasattr(ws, "root_dir"):
                (ws.root_dir / "topic_plan.json").write_text(
                    json.dumps(trivial_plan, ensure_ascii=False, indent=2), encoding="utf-8"
                )
            return trivial_plan

        if ws and hasattr(ws, "root_dir"):
            cls.export_plan_task(
                parts, course_title, ws, transcript_summaries=transcript_summaries
            )
        return None
