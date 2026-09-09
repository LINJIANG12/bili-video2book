"""Semantic Topic Planner: Provides prompts for Agent to cluster episodes, plus local heuristic fallback.

Architecture: CLI provides tooling + fallback plan. The mature Agent performs semantic planning natively.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class SemanticTopicPlanner:
    PLAN_PROMPT = """你是一位国家级计算机学科教学大纲架构专家。
请仔细分析以下课程的分集标题以及【实际转录内容核心提要】。
根据实际学术知识体系与内容逻辑边界，识别视频之间的真实分界线，将属于同一有机知识模块的连续分集聚合为一个知识块（Knowledge Block）。

【课程标题】：{course_title}
【分集与实际内容提要清单】：
{episodes_text}

【规划要求】：
1. 坚决覆盖全部 1 到 {total_count} 集，不得遗漏任何一集，不得重复分配任何一集。
2. 每个知识块通常包含 1 到 3 集（极少数大型模块可包含 4 集），粒度要适中（避免切得太碎，也避免合得太糙）。
3. block_title 必须是结合【实际转录内容】提炼出的高度概括专业主题（如“软件工程导论与学科范式”、“软件过程模型体系与演进”、“需求分析方法与系统建模技术”）。
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
    def fallback_heuristic_plan(cls, parts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Heuristic fallback grouping consecutive parts with common title prefixes (without regex)."""
        if not parts:
            return []

        clusters: List[List[Dict[str, Any]]] = []
        current_cluster = [parts[0]]

        def get_stem(title_str: str) -> str:
            # Strip digits and hyphens to find semantic core words
            chars = [c for c in title_str if not c.isdigit() and c not in ("-", "_", " ", "(", ")", "（", "）", "第", "讲", "课")]
            return "".join(chars)[:6]

        # 兼顾标题词根关联度与总时长控制（单个 block 建议控制在 75 分钟 / 4500 秒以内）
        MAX_BLOCK_DURATION_SEC = 4500

        def get_cluster_duration(cluster: List[Dict[str, Any]]) -> int:
            return sum(int(item.get("duration", 0) or 0) for item in cluster)

        for p in parts[1:]:
            prev = current_cluster[-1]
            stem_prev = get_stem(prev["title"])
            stem_curr = get_stem(p["title"])
            p_dur = int(p.get("duration", 0) or 0)
            curr_dur = get_cluster_duration(current_cluster)

            # 时长超限检查：若加入当前集导致时长显著超过上限，则主动触发分块
            duration_ok = (curr_dur + p_dur) <= MAX_BLOCK_DURATION_SEC or curr_dur == 0

            if stem_prev and stem_curr and (stem_prev in stem_curr or stem_curr in stem_prev) and len(current_cluster) < 4 and duration_ok:
                current_cluster.append(p)
            else:
                clusters.append(current_cluster)
                current_cluster = [p]

        if current_cluster:
            clusters.append(current_cluster)

        plan = []
        for idx, cl in enumerate(clusters, 1):
            eps = [item["page"] for item in cl]
            title = cl[0]["title"]
            clean_title = "".join(c for c in title if c.isalnum() or c in (" ", "-", "_")).strip()
            plan.append({
                "block_id": idx,
                "block_title": clean_title,
                "episodes": eps,
                "core_theme": f"涵盖分集 {eps}",
            })

        return plan

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
                line += f"\n  [实录要点]: {summary_snippet}..."
            episodes_lines.append(line)
        safe_title = (course_title or "计算机专业课程").replace("{", "(").replace("}", ")")
        prompt = cls.PLAN_PROMPT.replace("{course_title}", safe_title).replace("{episodes_text}", "\n".join(episodes_lines)).replace("{total_count}", str(total_count))
        # Escape double-brace example JSON back to single braces for Agent readability
        return prompt.replace("{{", "{").replace("}}", "}")

    @classmethod
    def plan(
        cls,
        parts: List[Dict[str, Any]],
        course_title: str = "",
        ws: Optional[Any] = None,
        force: bool = False,
        transcript_summaries: Optional[Dict[int, str]] = None,
    ) -> List[Dict[str, Any]]:
        """Local tooling plan: reuse cache or fallback heuristic. Agent should refine via build_planning_prompt()."""
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

        if total_count == 1:
            trivial_plan = [{
                "block_id": 1,
                "block_title": parts[0]["title"],
                "episodes": [1],
                "core_theme": parts[0]["title"],
            }]
            if ws and hasattr(ws, "root_dir"):
                (ws.root_dir / "topic_plan.json").write_text(json.dumps(trivial_plan, ensure_ascii=False, indent=2), encoding="utf-8")
            return trivial_plan

        plan = cls.fallback_heuristic_plan(parts)

        if ws and hasattr(ws, "root_dir"):
            plan_file = ws.root_dir / "topic_plan.json"
            plan_file.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")

        return plan
