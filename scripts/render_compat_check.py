#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render Compatibility Check（交付物渲染合规体检）。

交付物默认在 Typora 阅读，并需兼容 VS Code Markmap / XMind / 纯文本。本脚本对工作区内**全部**
Markdown 成品（含历史遗留的手工镜像目录）做渲染层面的机器体检：

  ① GitHub 专有告警块 `> [!TIP]`（旧版 Typora 会原样露出 `[!TIP]` 字样）
  ② 围栏外裸字符画（渲染时连续空格被合并，图形会彻底错位）
  ③ 代码围栏未成对闭合 ④ 围栏缺失语言标识

  门禁口径：①②③ 为**致命项**，参与 `--strict`；④「缺语言标识」默认只提示不拦（历史成品
  中存在大量既有缺口），需要死守时显式追加 `--require-lang`。

用法：
    python scripts/render_compat_check.py                    # 体检全部工作区
    python scripts/render_compat_check.py --task 微机原理      # 只体检名称含关键字的工作区
    python scripts/render_compat_check.py --dir "<工作区路径>"
    python scripts/render_compat_check.py --strict           # 有致命项即返回非零
    python scripts/render_compat_check.py --strict --require-lang   # 把「缺语言标识」也纳入门禁
    python scripts/render_compat_check.py --json
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.deliverable_lint import (  # noqa: E402
    fatal_render_total,
    lint_render,
    summarize_render,
)
from src.core.task_cleanup import find_workspaces  # noqa: E402
from src.core.workspace import TaskWorkspace  # noqa: E402

# 排除：任务书（非交付物）与隐藏目录（归档/备份/缓存）
EXCLUDE_NAME_SUFFIXES = ("_TASK.md", "_KERNEL_TASK.md")


def collect_markdown(ws: Any) -> List[Path]:
    """工作区内所有 Markdown 成品（递归，含历史手工镜像目录；跳过任务书与隐藏目录）。"""
    files: List[Path] = []
    for path in sorted(ws.root_dir.rglob("*.md")):
        try:
            rel_parents = path.relative_to(ws.root_dir).parts[:-1]
        except ValueError:
            continue
        if any(part.startswith(".") for part in rel_parents):
            continue  # .archive / .backup_before_render_fix / .backup_single_notes 等
        if any(path.name.endswith(suffix) for suffix in EXCLUDE_NAME_SUFFIXES):
            continue
        try:
            if path.stat().st_size < 200:
                continue
        except OSError:
            continue
        files.append(path)
    return files


def check_workspace(ws: Any, require_lang: bool = False) -> Dict[str, Any]:
    entries: List[Dict[str, Any]] = []
    totals = {"alert_blocks": 0, "stray_art": 0, "fences_unbalanced": 0, "fence_without_lang": 0}

    for path in collect_markdown(ws):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        lint = lint_render(text)
        summary = summarize_render(lint)
        for key, value in summary.items():
            totals[key] += value
        # 默认只把「致命项」文件列入清单；缺语言标识属警告（历史语料量大，避免淹没真信号），
        # 显式 --require-lang 时才把它提升为门禁项。
        fatal_here = fatal_render_total(summary)
        if require_lang:
            fatal_here += summary["fence_without_lang"]
        if fatal_here == 0:
            continue
        entries.append({
            "file": TaskWorkspace.to_relative(path),
            "fatal": fatal_here,
            "summary": summary,
            "samples": {
                "alert_blocks": lint["alert_blocks"][:3],
                "stray_art": lint["stray_art"][:3],
                "fence_without_lang": lint["fence_without_lang"][:3],
            },
        })

    fatal = fatal_render_total(totals)
    if require_lang:
        fatal += totals["fence_without_lang"]
    return {
        "workspace": ws.root_dir.name,
        "workspace_path": str(ws.root_dir),
        "scanned_files": len(collect_markdown(ws)),
        "problem_files": len(entries),
        "totals": totals,
        "fatal_total": fatal,
        "require_lang": bool(require_lang),
        "entries": entries,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Deliverable render-compatibility check (alert blocks / bare art / fences)")
    parser.add_argument("--dir", default=None, help="直接指定单个工作区目录")
    parser.add_argument("--base-dir", default=None,
                        help="工作区基目录（默认：由 src/core/paths.py 解析的产物根 <home>/output）")
    parser.add_argument("--task", default=None, help="仅处理目录名包含该关键字的工作区")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    parser.add_argument("--strict", action="store_true", help="存在致命项即返回非零")
    parser.add_argument("--require-lang", action="store_true", dest="require_lang",
                        help="把「围栏缺语言标识」也纳入门禁（默认只提示；历史成品存在既有缺口）")
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

    reports = [check_workspace(ws, require_lang=args.require_lang) for ws in workspaces]

    if args.json:
        print(json.dumps({"reports": reports, "strict": bool(args.strict),
                          "require_lang": bool(args.require_lang)}, ensure_ascii=False, indent=2))
    else:
        print("=" * 72)
        print("[*] 交付物渲染合规体检（告警块 / 围栏外字符画 / 围栏配对 / 围栏语言标识）")
        scope = "语言标识=门禁项（--require-lang）" if args.require_lang else "语言标识=提示项（不参与 --strict）"
        print(f"[*] 门禁口径：{scope}")
        print("=" * 72)
        for report in reports:
            print(f"\n▶ {report['workspace']}")
            print(f"    扫描成品 {report['scanned_files']} 份 | 有问题 {report['problem_files']} 份 | "
                  f"致命 {report['fatal_total']} 处")
            t = report["totals"]
            print(f"    ── 告警块 {t['alert_blocks']} | 围栏外字符画 {t['stray_art']} | "
                  f"围栏未闭合 {t['fences_unbalanced']} | 缺语言标识 {t['fence_without_lang']}")
            for entry in report["entries"][:12]:
                s = entry["summary"]
                short = entry["file"].split("/", 2)[-1] if "/" in entry["file"] else entry["file"]
                print(f"    [✗] {short[:66]:68s} 告警块={s['alert_blocks']:3d} "
                      f"裸图={s['stray_art']:2d} 未闭合={s['fences_unbalanced']} 缺语言={s['fence_without_lang']}")
                for key in ("alert_blocks", "stray_art"):
                    for sample in entry["samples"].get(key, [])[:1]:
                        print(f"         └ {key} @{sample['line']}: {sample['text'][:84]}")
            if len(report["entries"]) > 12:
                print(f"    … 其余 {len(report['entries']) - 12} 份见 --json 输出")
            if report["problem_files"] == 0:
                print("    ── 全部合规")
        print("\n" + "=" * 72)

    any_fatal = any(r["fatal_total"] > 0 for r in reports)
    if any_fatal and args.strict:
        print("[FAIL] 存在渲染致命项（详见上方 [✗] 文件）")
        return 1
    if not args.json:
        print("[OK] 渲染合规体检完成" + ("（存在致命项，未开启 --strict）" if any_fatal else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
