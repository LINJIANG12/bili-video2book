#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dynamic Queue Tracker for Micro-Agent Continuous Dispatch.

Tracks completed vs pending episodes in real time, supporting sliding-window
continuous dispatch ("完成一个，立即派生一个") without manual offsets.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set

# 允许从任意工作目录运行（SKILL.md 推荐直接调用 scripts/queue_tracker.py）
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def get_task_workspace(custom_path: Optional[str] = None, pattern: Optional[str] = None) -> Path:
    """Locate the target task workspace under output directory or custom path."""
    if custom_path:
        p = Path(custom_path).resolve()
        if p.exists():
            return p
        raise FileNotFoundError(f"Specified workspace directory does not exist: {custom_path}")

    # Search in ./output or ../output
    candidates = [
        Path("./output").resolve(),
        Path(__file__).resolve().parent.parent / "output",
    ]
    out_dir = None
    for c in candidates:
        if c.exists() and c.is_dir():
            out_dir = c
            break

    if not out_dir:
        raise RuntimeError("No 'output' directory found in current working path or project root.")

    # Find directories that contain parts.json or manifest.json
    valid_dirs = [
        d for d in out_dir.iterdir()
        if d.is_dir() and (d / "parts.json").exists()
    ]

    if not valid_dirs:
        # Fallback to any directory in output
        valid_dirs = [d for d in out_dir.iterdir() if d.is_dir()]

    if not valid_dirs:
        raise RuntimeError(f"No task workspace found under {out_dir}")

    def get_latest_mtime(d: Path) -> float:
        try:
            # Check key subdirs first for speed
            sample_files = []
            for sub in ["articles", "subtitles", "textbooks", "notes"]:
                sub_dir = d / sub
                if sub_dir.exists():
                    sample_files.extend(list(sub_dir.glob("*"))[-10:])
            sample_files.extend([d / "manifest.json", d / "parts.json", d])
            return max([f.stat().st_mtime for f in sample_files if f.exists()] or [0.0])
        except Exception:
            return 0.0

    # If pattern specified, filter by pattern
    if pattern:
        matched = [d for d in valid_dirs if pattern in d.name]
        if matched:
            matched.sort(key=get_latest_mtime, reverse=True)
            return matched[0]

    # Default: sort by most recent activity across workspaces
    valid_dirs.sort(key=get_latest_mtime, reverse=True)
    return valid_dirs[0]



AUDIO_EXTS = {".m4a", ".mp3", ".wav", ".aac", ".flac"}


def load_parts(ws: Path) -> List[Dict]:
    """读取分集清单：parts.json 优先，缺失时按可信度回退，取覆盖面最广者。

    清理过产物的旧工作区（只剩逐字稿与音频、或 manifest 逐集详情不全）仍需可判定进度，
    故依次回退 manifest 逐集详情 → 音频文件名 → 讲义文件名 → 模块规划，全不可用才报错。
    """
    parts_file = ws / "parts.json"
    if parts_file.exists():
        try:
            parts = json.loads(parts_file.read_text(encoding="utf-8"))
            if isinstance(parts, list) and parts:
                return parts
        except Exception:
            pass

    manifest = {}
    manifest_file = ws / "manifest.json"
    if manifest_file.exists():
        try:
            manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        except Exception:
            manifest = {}

    candidates: List[List[Dict]] = []

    # 1) manifest 逐集详情：含真实标题
    details = [d for d in manifest.get("details", []) if isinstance(d, dict) and "page" in d]
    if details:
        candidates.append([
            {"page": d["page"], "title": d.get("title", f"P{d['page']:02d}")} for d in details
        ])

    # 2) 音频文件名：阶段一原料，产物被清理后仍在盘，含真实标题
    audio_dir = ws / "audio"
    if audio_dir.exists():
        found = []
        for f in sorted(audio_dir.glob("P*_*")):
            if not f.is_file() or f.suffix.lower() not in AUDIO_EXTS:
                continue
            m = re.match(r"P(\d+)_(.+)$", f.stem)
            if m:
                found.append({"page": int(m.group(1)), "title": m.group(2)})
        if found:
            candidates.append(found)

    # 3) 讲义文件名：排除任务书
    articles_dir = ws / "articles"
    if articles_dir.exists():
        found = []
        for f in sorted(articles_dir.glob("P*_*.md")):
            if f.name.endswith("_TASK.md"):
                continue
            m = re.match(r"P(\d+)_(.*?)(?:_精读文章)?\.md$", f.name)
            if m:
                found.append({"page": int(m.group(1)), "title": m.group(2).strip()})
        if found:
            candidates.append(found)

    # 4) 模块规划分集编号：覆盖全量但无逐集标题，仅作兜底
    planned = sorted({
        ep for b in (manifest.get("knowledge_blocks_plan") or [])
        for ep in (b.get("episodes") or [])
    })
    if planned:
        candidates.append([{"page": ep, "title": f"P{ep:02d}"} for ep in planned])

    if candidates:
        return max(candidates, key=len)

    raise FileNotFoundError(
        f"未找到分集清单：{ws} 下 parts.json / manifest.json / audio / articles 均不可用，无法判定进度"
    )


def scan_status(ws: Path, min_article_bytes: int = 1000) -> Dict:
    """Scans workspace disk state and returns detailed progress statistics.

    Stage-1 completion is decided solely by the presence of a valid single-episode
    article: the zero-transcript pipeline writes articles/ directly and produces
    no intermediate subtitle files.
    """
    parts = load_parts(ws)

    articles_dir = ws / "articles"
    subtitles_dir = ws / "subtitles"
    audio_dir = ws / "audio"
    textbooks_dir = ws / "textbooks"
    notes_dir = ws / "notes"

    done_pages: Set[int] = set()
    art_map = {}
    invalid_articles = {}

    if articles_dir.exists():
        for f in articles_dir.glob("*.md"):
            # 任务书（*_TASK.md）与长文同目录、同以 PXX_ 开头且体积同样远超门禁，必须排除
            if f.name.endswith("_TASK.md"):
                continue
            m = re.match(r"^P(\d+)_", f.name)
            if m:
                p_num = int(m.group(1))
                if f.stat().st_size >= min_article_bytes:
                    art_map[p_num] = f
                else:
                    invalid_articles[p_num] = (f, f.stat().st_size)

    for p in parts:
        p_num = p["page"]
        # Single-stage direct-to-article completion gate: valid article >= 1000 bytes
        if p_num in art_map:
            done_pages.add(p_num)

    pending = [p for p in parts if p["page"] not in done_pages]

    textbooks = list(textbooks_dir.glob("*.md")) if textbooks_dir.exists() else []
    notes = list(notes_dir.glob("*.md")) if notes_dir.exists() else []

    return {
        "workspace": str(ws),
        "workspace_name": ws.name,
        "total": len(parts),
        "completed_count": len(done_pages),
        "pending_count": len(pending),
        "done_pages": sorted(list(done_pages)),
        "pending_parts": pending,
        "audio_dir": str(audio_dir),
        "subtitles_dir": str(subtitles_dir),
        "articles_dir": str(articles_dir),
        "invalid_articles": invalid_articles,
        "textbooks_count": len(textbooks),
        "notes_count": len(notes),
        "is_stage1_complete": len(pending) == 0 and len(parts) > 0,
    }


def main():
    parser = argparse.ArgumentParser(description="Real-time Dynamic Queue Tracker (Sliding Window Dispatch)")
    parser.add_argument("--dir", default=None, help="Path to task workspace")
    parser.add_argument("--pattern", default=None, help="Workspace directory name keyword filter")
    parser.add_argument("--next", type=int, default=0, dest="next_n", help="Show next N pending episodes for dispatch")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    parser.add_argument("--summary", action="store_true", help="Output one-line summary for scripting")
    args = parser.parse_args()

    try:
        ws = get_task_workspace(args.dir, pattern=args.pattern)
        status = scan_status(ws)
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        sys.exit(1)

    if args.summary:
        print(f"TOTAL={status['total']};DONE={status['completed_count']};PENDING={status['pending_count']};STAGE1_DONE={'1' if status['is_stage1_complete'] else '0'}")
        return

    if args.json:
        out = {
            "workspace": status["workspace_name"],
            "total": status["total"],
            "completed": status["completed_count"],
            "pending": status["pending_count"],
            "is_stage1_complete": status["is_stage1_complete"],
            "next": status["pending_parts"][:args.next_n] if args.next_n > 0 else []
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return

    print("=" * 68)
    print(f"[*] 动态任务队列追踪器 (Workspace: {status['workspace_name']})")
    print(f"[*] 总分集数: {status['total']} | 已完工: {status['completed_count']} | 待处理: {status['pending_count']}")
    pct = (status['completed_count'] / status['total']) * 100 if status['total'] else 0
    print(f"[*] 阶段一单集进度: {pct:.1f}% [{status['completed_count']}/{status['total']}]")
    print(f"[*] 阶段二模块资产: 模块全书 {status['textbooks_count']} 部 | 模块笔记 {status['notes_count']} 部")
    status_label = "【已竣工 - 可放行进入阶段二模块整编】" if status["is_stage1_complete"] else "【阶段一动态滑动流水线进行中】"
    print(f"[*] 当前阶段状态: {status_label}")
    if status.get("invalid_articles"):
        print("\n[!] 发现异常过短文章（低于 1000 字节门禁，已自动重置为待办）：")
        for p_num, (f, sz) in status["invalid_articles"].items():
            print(f"    - P{p_num:02d}: {f.name} (仅 {sz} 字节)")
    print("=" * 68)

    if args.next_n > 0 and status["pending_parts"]:
        print(f"\n【待派发队列 Next {min(args.next_n, len(status['pending_parts']))} 个分集】：")
        for p in status["pending_parts"][:args.next_n]:
            p_num = p["page"]
            # Look for exact existing audio file on disk first
            matched_audio = list(Path(status["audio_dir"]).glob(f"P{p_num:02d}_*.m4a"))
            if matched_audio:
                audio_f = matched_audio[0]
                clean_t = audio_f.stem[len(f"P{p_num:02d}_"):]
            else:
                from src.core.workspace import sanitize_filename
                clean_t = sanitize_filename(p["title"])
                audio_f = Path(status["audio_dir"]) / f"P{p_num:02d}_{clean_t}.m4a"

            art_f = Path(status["articles_dir"]) / f"P{p_num:02d}_{clean_t}_精读文章.md"
            dur_m = p.get("duration", 0) / 60.0
            print(f"  • P{p_num:02d} [{dur_m:.1f}m]: {p['title']}")
            print(f"    - Audio:   {audio_f}")
            print(f"    - Article: {art_f}")


if __name__ == "__main__":
    main()
