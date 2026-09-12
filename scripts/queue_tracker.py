#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dynamic Queue Tracker for Micro-Agent Continuous Dispatch.

Tracks completed vs pending episodes in real time, supporting sliding-window
continuous dispatch ("完成一个，立即派生一个") without manual offsets.

`--next N --json` 输出的是**可直接转交子智能体的派发载荷**（任务书路径、音频切片清单、
长文目标路径、本集 token 预算），并附带派发建议（并发数 / 打包粒度 / 是否必须派发）。
`--log-dispatch` 可选地把本次建议写入 `<task>/.dispatch_log.jsonl` 作为派发台账。
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Set

# 允许从任意工作目录运行（SKILL.md 推荐直接调用 scripts/queue_tracker.py）
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def get_task_workspace(
    custom_path: Optional[str] = None,
    pattern: Optional[str] = None,
    base_dir: Optional[str] = None,
) -> Path:
    """定位目标任务工作区：显式 --dir > --base-dir > 产物根（<home>/output）。

    产物根由 `src/core/paths.py` 解析（$BVB_OUTPUT_DIR / $BVB_HOME / .bvb-home 标记），
    因此从任意工作目录调用都能找到同一批工作区，不再依赖当前目录下是否存在 output/。
    """
    if custom_path:
        p = Path(custom_path).resolve()
        if p.exists():
            return p
        raise FileNotFoundError(f"Specified workspace directory does not exist: {custom_path}")

    sys.path.insert(0, str(PROJECT_ROOT))
    from src.core.paths import resolve_base_dir

    out_dir = resolve_base_dir(base_dir)
    if not (out_dir.exists() and out_dir.is_dir()):
        raise RuntimeError(
            f"产物根不存在: {out_dir}（可用 --base-dir 指定，或设置 ${'BVB_OUTPUT_DIR'}）"
        )

    # 容忍把「工作区目录本身」当作 base-dir 传入（用户很自然会这么用）
    if (out_dir / "parts.json").exists() or (out_dir / "manifest.json").exists():
        return out_dir

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
    # 任务书（*_TASK.md）是派发用的临时产物，不计入交付资产，否则会把计数虚高
    notes = (
        [f for f in notes_dir.glob("*.md") if not f.name.endswith("_TASK.md")]
        if notes_dir.exists() else []
    )
    return {
        "workspace": str(ws),
        "workspace_name": ws.name,
        "total": len(parts),
        "completed_count": len(done_pages),
        "pending_count": len(pending),
        "done_pages": sorted(list(done_pages)),
        "pending_parts": pending,
        "parts": parts,
        "audio_dir": str(audio_dir),
        "subtitles_dir": str(subtitles_dir),
        "articles_dir": str(articles_dir),
        "invalid_articles": invalid_articles,
        "textbooks_count": len(textbooks),
        "notes_count": len(notes),
        "is_stage1_complete": len(pending) == 0 and len(parts) > 0,
    }


def _fmt_time(seconds: float) -> str:
    """秒 → HH:MM:SS（与 AudioChunker.format_seconds 同口径）。"""
    total = int(round(max(0.0, float(seconds or 0))))
    return f"{total // 3600:02d}:{(total % 3600) // 60:02d}:{total % 60:02d}"


def _audio_slices(audio_f: Path, duration_sec: float, chunk_minutes: int = 60) -> List[Dict]:
    """按 pipeline 的口径推算该集切片清单（≤60 分钟为单片，超长按 N=ceil(时长/60) 均分）。"""
    import math

    duration_sec = float(duration_sec or 0)
    if chunk_minutes <= 0 or duration_sec <= chunk_minutes * 60:
        return [{
            "index": 1, "start": "00:00:00", "end": _fmt_time(duration_sec),
            "path": str(audio_f), "exists": audio_f.exists(),
        }]

    num = max(1, math.ceil(duration_sec / (chunk_minutes * 60)))
    slice_dur = duration_sec / num
    chunks_dir = audio_f.parent / f"{audio_f.stem}_chunks"
    slices = []
    for i in range(1, num + 1):
        start = (i - 1) * slice_dur
        end = duration_sec if i == num else i * slice_dur
        chunk = chunks_dir / f"{audio_f.stem}_part_{i:03d}{audio_f.suffix}"
        slices.append({
            "index": i, "start": _fmt_time(start), "end": _fmt_time(end),
            "path": str(chunk), "exists": chunk.exists(),
        })
    return slices


def _budget_summary(status: Dict) -> Dict:
    """阶段一预算与派发建议（系数/窗口可用环境变量覆盖，见 src/core/budget.py）。"""
    from src.core import budget

    total_sec = sum(float(p.get("duration", 0) or 0) for p in status.get("parts", []))
    prefills = [
        budget.est_episode_prefill_tokens(p.get("duration", 0) or 0)
        for p in status.get("pending_parts", [])
    ]
    info = budget.describe(
        total_seconds=total_sec,
        episodes=status.get("total", 0),
        pending=status.get("pending_count", 0),
        prefills=prefills,
    )
    info["total_audio_min"] = total_sec / 60.0
    info["total_audio_hours"] = total_sec / 3600.0
    return info


def _dispatch_payload(status: Dict, n: int) -> List[Dict]:
    """可直接转交给子智能体的派发载荷（主 Agent 无需再自行拼路径）。"""
    from src.core import budget
    from src.core.workspace import sanitize_filename

    audio_dir = Path(status["audio_dir"])
    articles_dir = Path(status["articles_dir"])
    items: List[Dict] = []

    for p in status["pending_parts"][:n]:
        page = p["page"]
        duration = float(p.get("duration", 0) or 0)

        matched = sorted(audio_dir.glob(f"P{page:02d}_*.m4a"))
        if matched:
            audio_f = matched[0]
            clean_title = audio_f.stem[len(f"P{page:02d}_"):]
        else:
            clean_title = sanitize_filename(p["title"])
            audio_f = audio_dir / f"P{page:02d}_{clean_title}.m4a"

        task_file = articles_dir / f"P{page:02d}_{clean_title}_TASK.md"
        target_article = articles_dir / f"P{page:02d}_{clean_title}_精读文章.md"
        slices = _audio_slices(audio_f, duration)

        items.append({
            "page": page,
            "title": p["title"],
            "duration_sec": duration,
            "est_audio_tokens": budget.est_audio_tokens(duration),
            "est_episode_prefill_tokens": budget.est_episode_prefill_tokens(duration),
            "task_file": str(task_file),
            "task_file_exists": task_file.exists(),
            "audio_file": str(audio_f),
            "audio_exists": audio_f.exists(),
            "audio_slices": slices,
            "slices_ready": all(s["exists"] for s in slices),
            "target_article": str(target_article),
        })
    return items


def _log_dispatch(status: Dict, requested: int, payload: List[Dict], budget_info: Dict) -> None:
    """把本次建议的分集追加写入 <task>/.dispatch_log.jsonl（派发台账，观察性证据）。

    注意：本台账记录的是「工具建议派发了哪些集」，不是「谁真的写了」——执行者身份
    无法在工具层验证；它的用途是事后复盘派发节奏（例如某工作区从未出现台账，
    说明阶段一没有走派发流程）。
    """
    log_path = Path(status["workspace"]) / ".dispatch_log.jsonl"
    entry = {
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "requested": requested,
        "suggested": [i["page"] for i in payload],
        "suggest_workers": budget_info.get("suggest_workers"),
        "suggest_batch": budget_info.get("suggest_batch"),
        "audio_tokens_per_sec": budget_info.get("audio_tokens_per_sec"),
    }
    try:
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError as err:
        print(f"[!] 派发台账写入失败: {err}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Real-time Dynamic Queue Tracker (Sliding Window Dispatch)")
    parser.add_argument("--dir", default=None, help="Path to task workspace")
    parser.add_argument("--base-dir", default=None,
                        help="产物根（默认：由 src/core/paths.py 解析，即 <home>/output）")
    parser.add_argument("--pattern", default=None, help="Workspace directory name keyword filter")
    parser.add_argument("--next", type=int, default=0, dest="next_n", help="Show next N pending episodes for dispatch")
    parser.add_argument("--log-dispatch", action="store_true", dest="log_dispatch",
                        help="把本次建议的分集追加写入 <task>/.dispatch_log.jsonl（派发台账；默认关闭，--next N 时才有内容）")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    parser.add_argument("--summary", action="store_true", help="Output one-line summary for scripting")
    args = parser.parse_args()

    try:
        ws = get_task_workspace(args.dir, pattern=args.pattern, base_dir=args.base_dir)
        status = scan_status(ws)
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        sys.exit(1)

    if args.summary:
        budget = _budget_summary(status)
        print(
            f"TOTAL={status['total']};DONE={status['completed_count']};PENDING={status['pending_count']};"
            f"STAGE1_DONE={'1' if status['is_stage1_complete'] else '0'};"
            f"TOTAL_AUDIO_MIN={budget['total_audio_min']:.0f};"
            f"DISPATCH_REQUIRED={'1' if budget['dispatch_required'] else '0'};"
            f"SUGGEST_WORKERS={budget['suggest_workers']};"
            f"SUGGEST_BATCH={budget['suggest_batch']};"
            f"AUDIO_TOKENS_PER_SEC={budget['audio_tokens_per_sec']:g}"
        )
        return

    payload = _dispatch_payload(status, args.next_n) if args.next_n > 0 else []

    if args.json:
        out = {
            "workspace": status["workspace_name"],
            "workspace_path": status["workspace"],
            "total": status["total"],
            "completed": status["completed_count"],
            "pending": status["pending_count"],
            "is_stage1_complete": status["is_stage1_complete"],
            "budget": _budget_summary(status),
            "next": payload,
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
        if args.log_dispatch and payload:
            _log_dispatch(status, len(payload), payload, out["budget"])
        return

    print("=" * 68)
    print(f"[*] 动态任务队列追踪器 (Workspace: {status['workspace_name']})")
    print(f"[*] 总分集数: {status['total']} | 已完工: {status['completed_count']} | 待处理: {status['pending_count']}")
    pct = (status['completed_count'] / status['total']) * 100 if status['total'] else 0
    print(f"[*] 阶段一单集进度: {pct:.1f}% [{status['completed_count']}/{status['total']}]")
    print(f"[*] 阶段二模块资产: 模块全书 {status['textbooks_count']} 部 | 复习笔记 {status['notes_count']} 篇")
    status_label = "【已竣工 - 可放行进入阶段二模块整编】" if status["is_stage1_complete"] else "【阶段一动态滑动流水线进行中】"
    print(f"[*] 当前阶段状态: {status_label}")
    budget = _budget_summary(status)
    print(f"[*] 派发建议: {'必须派发' if budget['dispatch_required'] else '可主 Agent 串行（≤60 分钟）'}"
          f" | 并发 {budget['suggest_workers']} | 打包粒度 {budget['suggest_batch']} 集/子智能体"
          f" | 音频系数 {budget['audio_tokens_per_sec']:g} tok/s | 窗口 {budget['context_window_tokens']:,}")
    if status.get("invalid_articles"):
        print("\n[!] 发现异常过短文章（低于 1000 字节门禁，已自动重置为待办）：")
        for p_num, (f, sz) in status["invalid_articles"].items():
            print(f"    - P{p_num:02d}: {f.name} (仅 {sz} 字节)")
    print("=" * 68)

    if payload:
        print(f"\n【待派发队列 Next {len(payload)} 个分集】：")
        for item in payload:
            dur_m = item["duration_sec"] / 60.0
            slices = item["audio_slices"]
            slice_hint = "" if len(slices) <= 1 else f" 等 {len(slices)} 片"
            audio_line = slices[0]["path"] if slices else "（缺音频）"
            print(f"  • P{item['page']:02d} [{dur_m:.1f}m ≈ {item['est_audio_tokens']:,} tok]: {item['title']}")
            print(f"    - 任务书:  {item['task_file']}")
            print(f"    - Audio:   {audio_line}{slice_hint}")
            print(f"    - Article: {item['target_article']}")
        if args.log_dispatch:
            print(f"\n[i] 已追加派发台账: {Path(status['workspace']) / '.dispatch_log.jsonl'}")

    if args.log_dispatch and payload and not args.json:
        _log_dispatch(status, len(payload), payload, budget)


if __name__ == "__main__":
    main()
