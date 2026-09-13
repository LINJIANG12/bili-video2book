#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Note Quality Check（模块笔记成色体检）。

把「只能靠人眼发现的毛病」变成可复算的指标，用于笔记交付前的验收：
  ① 套话填充行 ② 空壳容器标题 ③ 分集平铺标题 ④ 行内残缺引用块 ⑤ 分集口吻 ⑥ 断句 ⑦ 结构缺件

判定分级（已用三套真实语料标定）：
  - 致命项：①②③④⑤ —— 「微机原理（人工精修）」「软件工程」两套合格语料均为 0；
  - 警告项：⑥ 断句、⑦ 结构缺件 —— 启发式指标，连基准语料也无法归零，按阈值提示。

用法：
    python scripts/note_quality_check.py                       # 体检全部工作区
    python scripts/note_quality_check.py --task 数据库          # 只体检名称含关键字的工作区
    python scripts/note_quality_check.py --dir "<工作区绝对路径>"
    python scripts/note_quality_check.py --strict              # 有致命项/超阈值即返回非零
    python scripts/note_quality_check.py --json
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.console import enable_utf8_console  # noqa: E402

# 控制台硬化：输出含 `▶`/`✗`/`──` 等符号，管道捕获时若按 locale(cp936) 编码会崩。
enable_utf8_console()

from src.core.deliverable_lint import (  # noqa: E402
    FATAL_NOTE_KEYS,
    STRUCTURE_KEYS,
    fatal_note_total,
    lint_note,
    summarize_note,
)
from src.core import fsutil  # noqa: E402
from src.core.task_cleanup import find_workspaces  # noqa: E402
from src.core.workspace import TaskWorkspace  # noqa: E402

# 断句警告阈值（每工作区合计）；基准语料实测为 2（微机原理）/13（软件工程）
DEFAULT_MAX_TRUNCATED = 4


def collect_notes(ws: Any) -> List[Path]:
    """工作区内的模块笔记成品（排除任务书与隐藏目录）。

    `stat()` 单独包 try：工作区里若混入不可访问的装入点，`p.stat()` 会抛 OSError
    （`Path.exists()` 会吞掉该错误，`stat()` 不会），不能让它打断整轮体检。
    """
    if not ws.notes_dir.exists():
        return []
    notes: List[Path] = []
    for path in sorted(ws.notes_dir.glob("*.md")):
        if path.name.endswith("_TASK.md"):
            continue
        try:
            if path.stat().st_size < 1000:
                continue
        except OSError:
            continue
        notes.append(path)
    return notes


def check_workspace(ws: Any, max_truncated: int, args_require_structure: bool = False) -> Dict[str, Any]:
    files: List[Dict[str, Any]] = []
    totals: Dict[str, int] = {}
    fatal_total = 0

    for path in collect_notes(ws):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as err:
            files.append({"file": path.name, "error": str(err)})
            continue
        lint = lint_note(text)
        summary = summarize_note(lint)
        notes_fatal = fatal_note_total(summary)
        fatal_total += notes_fatal
        for key, value in summary.items():
            totals[key] = totals.get(key, 0) + value

        missing = [k for k in STRUCTURE_KEYS if not lint["structure"].get(k)]
        detail: Dict[str, Any] = {
            "file": TaskWorkspace.to_relative(path),
            "bytes": fsutil.file_size(path),
            "summary": summary,
            "fatal": notes_fatal,
            "structure_missing": missing,
            "samples": {
                key: lint[key][:3] for key in (*FATAL_NOTE_KEYS, "truncated") if lint.get(key)
            },
        }
        files.append(detail)

    failed = [
        f for f in files
        if f.get("fatal", 0) > 0
        or (args_require_structure and f.get("structure_missing"))
        or f.get("summary", {}).get("truncated", 0) > max_truncated
    ]
    return {
        "workspace": ws.root_dir.name,
        "workspace_path": str(ws.root_dir),
        "file_count": len(files),
        "fatal_total": fatal_total,
        "totals": totals,
        "files": files,
        "failed": [f["file"] for f in failed],
        "fatal_failed": [f["file"] for f in files if f.get("fatal", 0) > 0],
        "structure_gap": [f["file"] for f in files if f.get("structure_missing")],
        "truncated_threshold": max_truncated,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Module-note quality check (boilerplate / episode headings / truncation / structure)")
    parser.add_argument("--dir", default=None, help="直接指定单个工作区目录")
    parser.add_argument("--base-dir", default=None,
                        help="工作区基目录（默认：由 src/core/paths.py 解析的产物根 <home>/output）")
    parser.add_argument("--task", default=None, help="仅处理目录名包含该关键字的工作区")
    parser.add_argument("--max-truncated", type=int, default=DEFAULT_MAX_TRUNCATED,
                        help=f"每份笔记允许的断句上限（默认 {DEFAULT_MAX_TRUNCATED}）")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    parser.add_argument("--strict", action="store_true", help="有致命项或断句超阈值即返回非零")
    parser.add_argument("--require-structure", action="store_true",
                        help="把「结构缺件」也纳入门禁（v2 版式完整要求；历史工作区可能未达标）")
    args = parser.parse_args()

    if args.dir:
        ws_path = Path(args.dir)
        if not ws_path.exists():
            print(f"[ERROR] 工作区不存在: {ws_path}", file=sys.stderr)
            return 1
        workspaces = [TaskWorkspace.from_existing(ws_path)]
    else:
        workspaces = find_workspaces(args.base_dir)
        if args.task:
            workspaces = [w for w in workspaces if str(args.task) in w.root_dir.name]

    if not workspaces:
        print(f"[ERROR] 未找到可用工作区（base-dir={args.base_dir or '产物根'}）", file=sys.stderr)
        return 1

    reports = [check_workspace(ws, args.max_truncated, args.require_structure) for ws in workspaces]

    if args.json:
        print(json.dumps({"reports": reports, "strict": bool(args.strict)}, ensure_ascii=False, indent=2))
    else:
        print("=" * 72)
        print(f"[*] 模块笔记成色体检（致命项门禁 = {'/'.join(FATAL_NOTE_KEYS)}）")
        print("=" * 72)
        for report in reports:
            print(f"\n▶ {report['workspace']}  （{report['file_count']} 份笔记）")
            if not report["file_count"]:
                print("    （无笔记成品）")
                continue
            for item in report["files"]:
                if "error" in item:
                    print(f"    [!] {item['file']}: {item['error']}")
                    continue
                s = item["summary"]
                flag = "[✗]" if item["file"] in report["failed"] else "[✓]"
                miss = ("/".join(k.replace("has_", "") for k in item["structure_missing"])) or "-"
                print(
                    f"    {flag} {Path(item['file']).name[:44]:46s} 套话={s['boilerplate']:4d} "
                    f"空壳={s['hollow_headings']:2d} 分集标题={s['episode_headings']:3d} "
                    f"行内引用={s['inline_quote']:2d} 分集口吻={s['episode_voice']:2d} "
                    f"断句={s['truncated']:2d} 缺件={miss}"
                )
                for key in FATAL_NOTE_KEYS:
                    for sample in item["samples"].get(key, [])[:2]:
                        print(f"         └ {key} @{sample['line']}: {sample['text'][:88]}")
            t = report["totals"]
            print(f"    ── 合计：致命 {report['fatal_total']} 处 | 套话 {t.get('boilerplate', 0)} | "
                  f"空壳标题 {t.get('hollow_headings', 0)} | 分集标题 {t.get('episode_headings', 0)} | "
                  f"行内引用 {t.get('inline_quote', 0)} | 分集口吻 {t.get('episode_voice', 0)} | "
                  f"断句合计 {t.get('truncated', 0)}（阈值按**每份**笔记 {report['truncated_threshold']} 处判定）| "
                  f"结构缺件 {t.get('structure_missing', 0)}")
            if report["failed"]:
                print(f"    ── 未通过：{len(report['failed'])} 份（{'；'.join(Path(f).name for f in report['failed'][:4])}）")
            elif report["structure_gap"]:
                print(f"    ── 致命项全 0；另有 {len(report['structure_gap'])} 份缺 v2 结构构件"
                      f"（历史工作区遗留，加 --require-structure 可纳入门禁）")
            else:
                print("    ── 全部通过")
        print("\n" + "=" * 72)

    any_failed = any(r["failed"] for r in reports)
    if any_failed and args.strict:
        print("[FAIL] 笔记成色不达标（详见上方 ✗ 项）")
        return 1
    if not args.json:
        print("[OK] 笔记成色体检完成" + ("（存在不达标项，未开启 --strict）" if any_failed else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
