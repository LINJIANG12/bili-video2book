"""State Sync: 以磁盘为唯一真相回填 manifest.json（对账）。

问题背景：`manifest.json` 只记录**工具自己派发**的活。宿主 Agent 事后写进 `articles/` 的成品
永远不会回填，于是三门课的清单里都写着「一集都没完成 / 全流程未完成」，而硬盘上成品早已齐全——
账本与仓库脱节，任何依赖清单的自动判断都会误判。

本模块做一件事：**数硬盘，然后改账本**。
- 分集完成度：以 `articles/` 中合格长文（≥ `min_article_bytes`）为准，兼容旧工作区的宽松命名；
- 模块资产：以 `notes/`、`textbooks/` 实际文件为准（排除任务书）；
- 规划：优先采用 `topic_plan.json`（Agent 语义产出的权威边界）；
- 失败/跳过名单：原样保留，不因对账而抹掉历史故障记录。
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .kernel_extractor import KernelExtractor

MIN_ARTICLE_BYTES = 1000


def _list_products(directory: Path, suffix: str = ".md") -> List[Path]:
    """列出目录下的成品文件（排除 `*_TASK.md` 任务书与隐藏目录）。"""
    if not directory.exists():
        return []
    return sorted(
        p for p in directory.glob(f"*{suffix}")
        if not p.name.endswith("_TASK.md") and p.stat().st_size >= 200
    )


def reconcile_workspace_manifest(
    ws: Any,
    min_article_bytes: int = MIN_ARTICLE_BYTES,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """按磁盘现状回填 manifest，返回对账摘要（dry_run 时不落盘）。"""
    from .workspace import TaskWorkspace

    manifest = ws.load_manifest(absolute=True)
    parts = ws.load_parts() or []

    details: Dict[Any, Dict[str, Any]] = {}
    for entry in manifest.get("details", []):
        if isinstance(entry, dict) and entry.get("page") is not None:
            details[entry["page"]] = dict(entry)
    for part in parts:
        page = part.get("page")
        if page is None:
            continue
        details.setdefault(page, {
            "page": page,
            "title": part.get("title", ""),
            "cid": part.get("cid", 0),
        })

    success_pages: List[int] = []
    pending_pages: List[int] = []
    for page in sorted(details, key=lambda x: (x is None, x)):
        article = KernelExtractor.find_article(ws, page)
        entry = details[page]
        if article is not None and article.stat().st_size >= min_article_bytes:
            entry["status"] = "success"
            entry["article"] = str(article)
            # 任务书已回收时不再留悬空引用
            task_prompt = entry.get("task_prompt")
            if task_prompt and not Path(str(task_prompt)).exists():
                entry.pop("task_prompt", None)
            success_pages.append(page)
        else:
            entry["status"] = "need-agent-article"
            entry.pop("article", None)
            pending_pages.append(page)

    total = len(parts) or len(details)
    note_files = _list_products(ws.notes_dir)
    textbook_files = _list_products(ws.root_dir / "textbooks")

    plan: Optional[List[Dict[str, Any]]] = None
    plan_file = ws.root_dir / "topic_plan.json"
    if plan_file.exists():
        try:
            loaded = json.loads(plan_file.read_text(encoding="utf-8"))
            if isinstance(loaded, list) and loaded:
                plan = loaded
        except Exception:
            plan = None

    failed_entries = [d for d in manifest.get("failed_episodes", []) if isinstance(d, dict)]
    skipped_pages = [p for p in manifest.get("skipped_pages", []) if p is not None]
    effective_total = max(0, total - len(skipped_pages))

    # 整编完成证据：优先看权威规划文件；历史工作区（旧架构）没有 topic_plan.json，
    # 但已有模块笔记与教材落盘，同样视为整编完成，不应被误判为「未完工」。
    consolidation_evidence = plan is not None or total == 1 or (len(note_files) > 0 and len(textbook_files) > 0)
    completed = (
        effective_total > 0
        and len([p for p in success_pages if p not in skipped_pages]) >= effective_total
        and not failed_entries
        and consolidation_evidence
    )

    updated: Dict[str, Any] = {
        "details": [details[k] for k in sorted(details, key=lambda x: (x is None, x))],
        "processed_episodes": len(success_pages),
        "episode_total": total,
        "episode_pending": len([p for p in pending_pages if p not in skipped_pages]),
        "pipeline_completed": bool(completed),
        "notes_files": [TaskWorkspace.to_relative(p) for p in note_files],
        "textbooks": [TaskWorkspace.to_relative(p) for p in textbook_files],
        "reconciled_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    if plan is not None:
        updated["knowledge_blocks_plan"] = plan

    if not dry_run:
        merged = dict(manifest)
        merged.update(updated)
        ws.save_manifest(merged)

    return {
        "workspace": ws.root_dir.name,
        "workspace_path": str(ws.root_dir),
        "total": total,
        "success": len(success_pages),
        "pending": len([p for p in pending_pages if p not in skipped_pages]),
        "skipped": len(skipped_pages),
        "failed": len(failed_entries),
        "notes": len(note_files),
        "textbooks": len(textbook_files),
        "plan_blocks": len(plan) if plan else 0,
        "pipeline_completed": bool(completed),
        "dry_run": bool(dry_run),
        "updated_fields": sorted(updated.keys()),
    }


def reconcile_all(base_dir: Any = "output", dry_run: bool = False) -> List[Dict[str, Any]]:
    """对 base_dir 下所有工作区逐一执行对账。"""
    from .task_cleanup import find_workspaces

    return [
        reconcile_workspace_manifest(ws, dry_run=dry_run)
        for ws in find_workspaces(base_dir)
    ]
