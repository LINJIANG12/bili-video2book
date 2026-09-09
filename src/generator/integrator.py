#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Module Textbook Integrator.

Integrates single-episode articles in `articles/` into unified modular textbooks in `textbooks/`.
Original articles in `articles/` are strictly preserved.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional


class ArticleIntegrator:
    """Consolidates individual episode articles into comprehensive modular chapter textbooks."""

    def __init__(self, task_dir: Path):
        self.task_dir = Path(task_dir)
        self.articles_dir = self.task_dir / "articles"
        self.textbooks_dir = self.task_dir / "textbooks"
        self.parts_file = self.task_dir / "parts.json"
        self.textbooks_dir.mkdir(parents=True, exist_ok=True)

    def load_parts(self) -> List[dict]:
        if self.parts_file.exists():
            try:
                return json.loads(self.parts_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        # Fallback 1: manifest.json details or episodes
        manifest_file = self.task_dir / "manifest.json"
        if manifest_file.exists():
            try:
                m_data = json.loads(manifest_file.read_text(encoding="utf-8"))
                details = m_data.get("details", [])
                if details and len(details) > 1:
                    return [{"page": d["page"], "title": d.get("title", f"P{d['page']:02d}")} for d in details if "page" in d]
            except Exception:
                pass

        # Fallback 2: parse articles directory
        parts = []
        if self.articles_dir.exists():
            for f in sorted(self.articles_dir.glob("P*_精读文章.md")):
                m = re.match(r"P(\d+)_(.*?)_精读文章\.md", f.name)
                if m:
                    parts.append({"page": int(m.group(1)), "title": m.group(2).strip()})
        if parts:
            return parts

        # Fallback 3: topic_plan.json or manifest knowledge_blocks_plan
        plan = []
        topic_plan_file = self.task_dir / "topic_plan.json"
        if topic_plan_file.exists():
            try:
                plan = json.loads(topic_plan_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        elif manifest_file.exists():
            try:
                m_data = json.loads(manifest_file.read_text(encoding="utf-8"))
                plan = m_data.get("knowledge_blocks_plan", [])
            except Exception:
                pass

        all_eps = set()
        for b in plan:
            for ep in b.get("episodes", []):
                all_eps.add(ep)
        if all_eps:
            return [{"page": ep, "title": f"第{ep}讲"} for ep in sorted(all_eps)]

        return []

    def group_episodes_by_module(self, parts: List[dict]) -> Dict[str, List[dict]]:
        """Groups parts into distinct logical modules based on title semantics."""
        modules: Dict[str, List[dict]] = {}
        # First try to load from knowledge_blocks_plan if present in manifest.json or topic_plan.json
        manifest_file = self.task_dir / "manifest.json"
        topic_plan_file = self.task_dir / "topic_plan.json"
        plan = []
        if manifest_file.exists():
            try:
                m_data = json.loads(manifest_file.read_text(encoding="utf-8"))
                plan = m_data.get("knowledge_blocks_plan", [])
            except Exception:
                pass
        if not plan and topic_plan_file.exists():
            try:
                plan = json.loads(topic_plan_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        if plan:
            page_map = {p["page"]: p for p in parts}
            for b in plan:
                title = b.get("block_title", "知识模块")
                b_eps = [page_map[ep] for ep in b.get("episodes", []) if ep in page_map]
                if b_eps:
                    modules[title] = b_eps
            if modules:
                return modules

        for p in parts:
            title = p.get("title", "")
            # Pattern: XX. 核心语法-[模块名]-xxx
            m = re.search(r"核心语法-([^-]+)", title)
            if m:
                module_name = m.group(1).strip()
            else:
                module_name = "综合模块"
            
            # Unify related submodules
            if module_name in ("函数基础", "函数进阶"):
                module_key = "函数基础与进阶"
            elif module_name in ("类型注解", "模块"):
                module_key = "类型注解与模块化编程"
            elif module_name == "异常":
                module_key = "异常处理与容错机制"
            else:
                module_key = module_name

            if module_key not in modules:
                modules[module_key] = []
            modules[module_key].append(p)
        return modules

    def integrate_module(self, module_idx: int, module_name: str, episodes: List[dict], course_title: str) -> Path:
        """Compiles articles of a module into a single unified textbook."""
        out_filename = f"模块{module_idx:02d}_{module_name}_精读全书.md"
        out_path = self.textbooks_dir / out_filename

        ep_pages = [ep["page"] for ep in episodes]
        page_range = f"P{min(ep_pages):02d} ~ P{max(ep_pages):02d}"

        # Header and TOC
        lines = [
            f"# 模块 {module_idx:02d}：{module_name} 精读全书",
            "",
            f"> **所属课程**：{course_title}  ",
            f"> **模块跨度**：{page_range}（全模块共 {len(episodes)} 讲系统重构）  ",
            f"> **出版定位**：模块化出版级系统教材全卷，融合底层机制、架构全景、生产级代码拆解与避坑自测。  ",
            f"> **关联说明**：单集微粒度教材长文同步完整保留于 `articles/` 目录供定向查阅。",
            "",
            "---",
            "",
            "## 📖 模块全书导读与全景目录",
            "",
        ]

        # TOC
        for i, ep in enumerate(episodes, 1):
            title = ep.get("title", "")
            clean_t = re.sub(r"^\d+\.\s*", "", title)
            lines.append(f"- **第 {i} 章**：{clean_t}")
        lines.extend(["", "---", ""])

        # Chapters
        for i, ep in enumerate(episodes, 1):
            page = ep["page"]
            title = ep.get("title", "")
            clean_t = re.sub(r"^\d+\.\s*", "", title)
            matches = list(self.articles_dir.glob(f"P{page:02d}_*_精读文章.md"))
            
            lines.append(f"## 第 {i} 章：{clean_t}")
            lines.append(f"> 对应分集：P{page:02d} | 原始标题：《{title}》")
            lines.append("")

            if matches:
                art_content = matches[0].read_text(encoding="utf-8")
                # Normalize any unescaped literal \n in markdown text
                norm_lines = []
                in_c = False
                for l in art_content.splitlines():
                    if l.strip().startswith("```"):
                        in_c = not in_c
                        norm_lines.append(l)
                    elif not in_c and r"\n" in l:
                        norm_lines.extend(l.replace(r"\n", "\n").splitlines())
                    else:
                        norm_lines.append(l)
                art_content = "\n".join(norm_lines)

                # Strip out top H1 and header block / separator
                art_content = re.sub(r"^#\s+.*?\n+", "", art_content.strip())
                art_content = re.sub(r"^>\s+.*?\n+", "", art_content)
                art_content = re.sub(r"^---*\s*\n+", "", art_content.strip())
                
                # Demote existing H2 (##) to H3 (###) and H3 to H4 for hierarchical consistency
                demoted = []
                in_code = False
                for line in art_content.strip().splitlines():
                    if line.startswith("```"):
                        in_code = not in_code
                    if not in_code:
                        if line.startswith("#### "):
                            line = "#" + line  # becomes #####
                        elif line.startswith("### "):
                            line = "#" + line  # becomes ####
                        elif line.startswith("## "):
                            line = "#" + line  # becomes ###
                    demoted.append(line)
                lines.append("\n".join(demoted))
            else:
                lines.append(f"> ⚠️ 单集精读长文暂未生成，可在后续流水线中补充。")

            # Transition bridge if not last chapter
            if i < len(episodes):
                next_title = re.sub(r"^\d+\.\s*", "", episodes[i].get("title", ""))
                lines.extend([
                    "",
                    f"> 💡 **承前启后**：完成对「{clean_t}」的理解后，下一章我们将深入探讨「{next_title}」，进一步完善知识图谱体系。",
                    "",
                    "---",
                    "",
                ])
            else:
                lines.extend(["", "---", ""])

        # Module Summary section
        lines.extend([
            f"## 模块 {module_idx:02d} 全景总结与技术沉淀",
            "",
            f"本全书系统整合了 {module_name} 模块的 {len(episodes)} 个核心专题（{page_range}）。",
            "建议读者在学完本章后，对照 `notes/` 目录下的思维导图树状笔记进行复盘与知识自测，巩固底层机理与工程实践能力。",
            "",
        ])

        out_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
        return out_path

    def run(self, course_title: str = "黑马程序员Python+AI全套视频教程") -> List[Path]:
        """Runs the complete module integration process."""
        parts = self.load_parts()
        grouped = self.group_episodes_by_module(parts)
        results = []
        for idx, (mod_name, eps) in enumerate(grouped.items(), 1):
            path = self.integrate_module(idx, mod_name, eps, course_title)
            results.append(path)
        return results
