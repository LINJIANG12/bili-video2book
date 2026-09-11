#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Command-Line Interface for Bilibili Audio & Knowledge Extraction.

Commands:
  parse            - Parse URL/BVID, classify video type, and inspect sub-videos
  audio            - Fetch audio stream URL, download m4a, and optionally chunk via ffmpeg
  transcribe       - Export per-episode ARTICLE_TASK (zero intermediate transcript)
  pipeline         - Two-stage orchestration: gather audio, then dispatch task-files
  cluster-notes    - Export module synthesis task-files from extracted knowledge kernels
  cluster-articles - Consolidate single-episode articles into modular textbooks
  dedup            - Synchronize duplicate audio assets to save LLM tokens
  login / logout   - Persist or clear the Bilibili SESSDATA credential
  info             - Show environment & toolchain readiness status
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

# Enable real-time line buffering
try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

# Add parent directory to sys.path to allow running directly from anywhere
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core import paths as _paths
from src.core.local_media import LocalMediaParser
from src.core.fetcher import AudioFetcher
from src.core.audio_chunker import AudioChunker
from src.core.workspace import TaskWorkspace, sanitize_filename
from src.core.kernel_extractor import KernelExtractor
from src.core.credentials import SessdataStore, resolve_sessdata, store_path
from src.core.pipeline import (
    PipelineCoordinator,
    PipelineGateError,
    _STATUS_FILE,
    export_article_task,
    get_audio_stream,
    parse_range_string,
    resolve_target_info,
)
from src.generator.topic_planner import SemanticTopicPlanner
from src.generator.block_synthesizer import BlockSynthesizer


BASE_DIR_HELP = (
    "Base output directory for task workspaces "
    "(default: the products root resolved by src/core/paths.py, i.e. <home>/output; "
    f"override with ${_paths.ENV_OUTPUT_DIR} or ${_paths.ENV_HOME})"
)


def _resolve_base_dir(value):
    """把 --base-dir 解析为绝对路径（空值即产物根，不随当前工作目录漂移）。"""
    return str(_paths.resolve_base_dir(value))


def _save_manifest_rel(ws, data):
    """保存清单（TaskWorkspace 原生相对路径化，保留兼容入口）。"""
    ws.save_manifest(data)


def _to_relative_str(val):
    """绝对路径转仓库相对路径，非路径原样返回（复用 TaskWorkspace 统一实现）。"""
    if not isinstance(val, str) or not val:
        return val
    try:
        p = Path(val)
        if not p.is_absolute():
            return val
        return TaskWorkspace.to_relative(p)
    except Exception:
        return val


def _confirm_article_prompt_style(args) -> str:
    """确认使用哪种长文提示词风格（学习 / 旧版）。

    用户明确指定就照用；未指定时打印风格菜单，交互终端下请用户当场选择；
    仍然拿不到选择则终止任务（工具层不猜、不兜底）。
    """
    from src.generator.prompt_templates import render_article_prompt_menu

    chosen = (getattr(args, "article_type", "") or "").strip()
    if chosen:
        return chosen

    print("\n" + "=" * 65)
    print(render_article_prompt_menu())
    print("=" * 65)
    if sys.stdin.isatty():
        try:
            typed = input("请选择长文提示词风格 (learning / legacy，直接回车取消): ").strip()
        except (EOFError, KeyboardInterrupt):
            typed = ""
        if typed:
            return typed

    print("[!] 未确认长文提示词风格，任务终止。请显式指定后重跑，例如：", file=sys.stderr)
    print('    python src/cli.py pipeline "<链接>" --all --article-type learning   # 学习（推荐）', file=sys.stderr)
    print('    python src/cli.py pipeline "<链接>" --all --article-type legacy     # 旧版（原稳定版）', file=sys.stderr)
    sys.exit(4)


def _export_article_task_guarded(ws, page_num, clean_title, audio_file, **kwargs):
    """单集长文任务书导出的唯一出口：提示词风格未命中已提供预设时，打印风格菜单并终止任务。

    工具层刻意不做关键词猜测、不做默认兜底——风格由用户确认。
    """
    from src.generator.prompt_templates import ArticlePromptTypeError

    try:
        return export_article_task(ws, page_num, clean_title, audio_file, **kwargs)
    except ArticlePromptTypeError as err:
        print("\n" + err.report, file=sys.stderr)
        print("去向：确认使用哪种提示词风格后，用 --article-type 重跑本命令。", file=sys.stderr)
        sys.exit(4)


def _owner_line(info) -> str:
    """渲染 UP 主一行：兼容正常元数据（dict）与离线自愈缓存（owner 为字符串/空）。

    离线自愈分支刻意不伪造 UP 主信息（owner 为空），若直接取 info['owner']['name']
    会抛 TypeError（string indices must be integers），把一条本来可用的离线路径打断。
    """
    owner = info.get("owner")
    if isinstance(owner, dict):
        name = str(owner.get("name") or "").strip() or "未知"
        mid = owner.get("mid", 0)
    else:
        name = str(owner or "").strip() or "未知（离线缓存）"
        mid = info.get("owner_mid", 0)
    return f"{name} (mid: {mid})"


def cmd_parse(args):
    info = resolve_target_info(
        args.url,
        sessdata=args.sessdata,
        custom_task=getattr(args, "task", None),
        base_dir=getattr(args, "base_dir", None),
    )
    if args.json:
        print(json.dumps(info, ensure_ascii=False, indent=2))
        return

    if info.get("is_local"):
        mins = info["duration"] // 60
        secs = info["duration"] % 60
        print("=" * 65)
        print(f"【视频标题】: {info['title']}")
        print(f"【来源路径】: {info.get('source_path')}")
        print(f"【类型判定】: {info['type_desc']}")
        print(f"【总时长】  : {mins:02d}:{secs:02d}")
        print("=" * 65)

        if info["has_multi_pages"]:
            print(f"\n▶ 本地分集列表 (共 {len(info['parts'])} P):")
            for p in info["parts"][:args.limit]:
                pmins = p["duration"] // 60
                psecs = p["duration"] % 60
                print(f"  P{p['page']:02d} [{pmins:02d}:{psecs:02d}] {p['title']}")
                print(f"      文件: {p['filepath']}")
            if len(info["parts"]) > args.limit:
                print(f"  ... 剩余 {len(info['parts']) - args.limit} 个分P已省略，可用 --limit 查看全量")
        return

    print("=" * 65)
    print(f"【视频标题】: {info['title']}")
    print(f"【UP 主】   : {_owner_line(info)}")
    print(f"【BV 号】   : {info['bvid']}")
    print(f"【类型判定】: {info['type_desc']}")
    if info.get("url_page"):
        print(f"【定位分P】: P{info['url_page']:02d} 《{info.get('selected_title')}》 (CID: {info.get('selected_cid')})")
    print("=" * 65)

    if info["has_multi_pages"]:
        print(f"\n▶ 稿件内分P列表 (共 {len(info['parts'])} P):")
        for p in info["parts"][:args.limit]:
            mins = p["duration"] // 60
            secs = p["duration"] % 60
            print(f"  P{p['page']:02d} [{mins:02d}:{secs:02d}] {p['title']}")
            print(f"      CID: {p['cid']} | 链接: {p['url']}")
        if len(info["parts"]) > args.limit:
            print(f"  ... 剩余 {len(info['parts']) - args.limit} 个分P已省略，可用 --limit 查看全量")

    if info["has_ugc_season"]:
        s_info = info["season_info"]
        print(f"\n▶ 所属合集【{s_info['title']}】(共 {len(info['season_episodes'])} 个稿件):")
        for ep in info["season_episodes"][:args.limit]:
            print(f"  [{ep['section_title']}] 第{ep['episode_index']}集: {ep['title']}")
            print(f"      BV号: {ep['bvid']} | CID: {ep['cid']} | 链接: {ep['url']}")
        if len(info["season_episodes"]) > args.limit:
            print(f"  ... 剩余 {len(info['season_episodes']) - args.limit} 个稿件已省略")


def cmd_audio(args):
    info = resolve_target_info(args.url, sessdata=args.sessdata, custom_task=args.task, base_dir=args.base_dir)
    bvid = info["bvid"]

    # Initialize Task Workspace
    ws = TaskWorkspace.create(
        title=info["title"],
        bvid=bvid,
        custom_name=args.task,
        base_dir=args.base_dir,
    )
    target_audio_dir = Path(args.output).resolve() if args.output else ws.audio_dir
    target_audio_dir.mkdir(parents=True, exist_ok=True)
    print(f"[*] 任务工作区已就绪: {ws.root_dir.name}")
    print(f"    - 音频目录: {target_audio_dir}")

    # Determine multi-page batch mode
    is_batch = args.all or bool(args.range)
    if is_batch and info["has_multi_pages"]:
        all_parts = info["parts"]
        if args.range:
            target_indices = parse_range_string(args.range, len(all_parts))
            selected_parts = [all_parts[i - 1] for i in target_indices]
        else:
            selected_parts = all_parts

        total_parts = len(selected_parts)
        prefetch_workers = max(1, int(getattr(args, "prefetch_workers", 12) or 1))
        print("=" * 65)
        print(f"[*] 批量提取与无损转换任务启动 (共 {total_parts} 个分集，并发 {prefetch_workers} 线程)")
        print(f"[*] 目标音轨存储目录: {target_audio_dir}")
        print("=" * 65)

        def _download_worker(p):
            p_num = p["page"]
            clean_p_title = sanitize_filename(p["title"])
            target_file = target_audio_dir / f"P{p_num:02d}_{clean_p_title}.m4a"

            # Check if cached and non-empty
            if target_file.exists() and target_file.stat().st_size > 10240 and not args.force:
                size_mb = round(target_file.stat().st_size / (1024 * 1024), 2)
                print(f"[cached] P{p_num:02d} [{size_mb} MB] 已存在，跳过: {target_file.name}")
                return {
                    "page": p_num,
                    "title": p["title"],
                    "cid": p["cid"],
                    "duration": p["duration"],
                    "audio_file": str(target_file),
                    "size_bytes": target_file.stat().st_size,
                    "status": "cached",
                }

            print(f"[fetch] 正在提取 P{p_num:02d}: {p['title']} (CID: {p['cid']})...")
            try:
                if info.get("is_local"):
                    LocalMediaParser.extract_audio(p["filepath"], target_file)
                    saved_path = str(target_file)
                    f_size = Path(saved_path).stat().st_size
                    print(f"    [✓] 本地音频提取完成: {Path(saved_path).name} ({round(f_size / (1024 * 1024), 2)} MB)")
                    return {
                        "page": p_num,
                        "title": p["title"],
                        "cid": p["cid"],
                        "duration": p["duration"],
                        "audio_file": saved_path,
                        "size_bytes": f_size,
                        "quality": "64kbps-aac-mono",
                        "status": "downloaded",
                    }
                else:
                    # 中文注释：统一走 412 富化入口
                    stream_info = get_audio_stream(
                        bvid,
                        p["cid"],
                        sessdata=args.sessdata,
                        prefer_quality=getattr(args, "quality", "low"),
                    )
                    saved_path = AudioFetcher.download_audio(
                        stream_info["best_stream_url"],
                        str(target_file),
                        repackage_m4a=True,
                    )
                    f_size = Path(saved_path).stat().st_size
                    print(f"    [✓] 下载与封装完成: {Path(saved_path).name} ({round(f_size / (1024 * 1024), 2)} MB)")
                    return {
                        "page": p_num,
                        "title": p["title"],
                        "cid": p["cid"],
                        "duration": p["duration"],
                        "audio_file": saved_path,
                        "size_bytes": f_size,
                        "quality": stream_info.get("quality_desc", "64kbps-aac-mono"),
                        "status": "downloaded",
                    }
            except Exception as err:
                print(f"    [✗] 处理 P{p_num:02d} 发生异常: {err}", file=sys.stderr)
                return {
                    "page": p_num,
                    "title": p["title"],
                    "cid": p["cid"],
                    "error": str(err),
                    "status": "failed",
                }

        from concurrent.futures import ThreadPoolExecutor
        manifest_items = []
        with ThreadPoolExecutor(max_workers=prefetch_workers) as pool:
            futs = [pool.submit(_download_worker, p) for p in selected_parts]
            for f in futs:
                manifest_items.append(f.result())
        manifest_items.sort(key=lambda x: x["page"])

        # 中文注释：保存时相对路径化
        _save_manifest_rel(ws, {
            "bvid": bvid,
            "title": info["title"],
            "total_selected": total_parts,
            "downloaded_count": sum(1 for m in manifest_items if m.get("status") in ("downloaded", "cached")),
            "episodes": manifest_items,
        })
        print("\n" + "=" * 65)
        print(f"[✓] 批量任务执行完成！成功同步 {sum(1 for m in manifest_items if m.get('status') in ('downloaded', 'cached'))}/{total_parts} 个分集")
        print(f"[✓] 任务元数据清单已写入: {ws.manifest_file}")
        print("=" * 65)
        return

    # Single Part Mode
    req_page = args.page if args.page is not None else (info.get("url_page") or 1)
    target_part = 1
    target_cid = info["cid"]
    target_title = info["title"]

    if info["has_multi_pages"]:
        target_part = max(1, min(req_page, len(info["parts"])))
        matched = info["parts"][target_part - 1]
        target_cid = matched["cid"]
        target_title = f"P{target_part:02d}_{matched['title']}"

    clean_title = sanitize_filename(target_title)
    target_m4a = target_audio_dir / f"{clean_title}.m4a"

    if info.get("is_local"):
        source_file = matched["filepath"] if info["has_multi_pages"] else info["source_path"]
        print(f"[*] 正在从本地视频提取通用 64kbps 纯音频...")
        saved_path = str(LocalMediaParser.extract_audio(source_file, target_m4a))
        stream_info = {"quality_desc": "64kbps AAC Mono (16kHz)", "best_stream_url": saved_path}
        print(f"[✓] 音频提取完成: {saved_path}")
    else:
        print(f"[*] 解析音频流中... BV: {bvid}, CID: {target_cid}")
        # 中文注释：统一走 412 富化入口
        stream_info = get_audio_stream(
            bvid,
            target_cid,
            sessdata=args.sessdata,
            prefer_quality=getattr(args, "quality", "low"),
        )

        if args.url_only:
            if args.json:
                print(json.dumps(stream_info, ensure_ascii=False, indent=2))
            else:
                print(f"【音质】: {stream_info['quality_desc']}")
                print(f"【音频下载直链】:\n{stream_info['best_stream_url']}")
            return

        print(f"[*] 正在下载最高音质音频 ({stream_info['quality_desc']})...")
        saved_path = AudioFetcher.download_audio(
            stream_info["best_stream_url"],
            str(target_m4a),
            repackage_m4a=True,
        )
        print(f"[✓] 音频下载完成: {saved_path}")

    chunks_manifest = []
    if args.chunk_minutes > 0:
        print(f"[*] 正在使用 FFmpeg 进行无损音频切片（每切片 {args.chunk_minutes} 分钟）...")
        chunks_manifest = AudioChunker.chunk_audio(
            saved_path,
            chunk_minutes=args.chunk_minutes,
        )
        print(f"[✓] 切片完成，共切分出 {len(chunks_manifest)} 个片段:")
        for ch in chunks_manifest:
            print(f"    - 第{ch['chunk_index']}段 [{ch['start_time_str']} -> {ch['end_time_str']}]: {ch['filepath']}")

    if args.json:
        result = {
            "bvid": bvid,
            "cid": target_cid,
            "title": target_title,
            "quality": stream_info["quality_desc"],
            "audio_file": saved_path,
            "chunks": chunks_manifest,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_transcribe(args):
    # 中文注释：零中间逐字稿 —— 直接导出单集精读文章任务书（已存在长文则视为完成）。
    target_p = Path(args.target).resolve()
    if target_p.exists() and target_p.is_file():
        ws0 = TaskWorkspace.create(title=target_p.stem, bvid="", custom_name=args.task, base_dir=args.base_dir)
        # 该分支的任务书落盘名带 P01_ 前缀，复用判定须走宽容定位而非裸文件名
        existing_article = KernelExtractor.find_article(ws0, 1)
        if existing_article is not None and existing_article.stat().st_size >= 1000:
            print(f"[✓] 单集精读长文已存在，无需重新派发: {existing_article}")
            if args.output:
                out_p = Path(args.output).resolve()
                out_p.parent.mkdir(parents=True, exist_ok=True)
                out_p.write_text(existing_article.read_text(encoding="utf-8"), encoding="utf-8")
                print(f"[✓] 长文已复制至: {out_p}")
            return

        tf = _export_article_task_guarded(
            ws0, 1, target_p.stem, target_p, title=target_p.stem,
            article_type=_confirm_article_prompt_style(args),
        )
        print(f"[✓] 已导出单集精读文章任务书（零中间逐字稿，听音后直接撰写）: {tf} (status=need-agent-article)")
        return

    # Polymorphically resolve metadata (Local directory course or Bilibili URL/BVID)
    info = resolve_target_info(args.target, sessdata=args.sessdata)
    bvid = info["bvid"]
    ws = TaskWorkspace.create(title=info["title"], bvid=bvid, custom_name=args.task, base_dir=args.base_dir)

    target_part = 1
    target_cid = info["cid"]
    p_title = info["title"]
    req_page = args.page if args.page is not None else (info.get("url_page") or 1)
    if info["has_multi_pages"]:
        target_part = max(1, min(req_page, len(info["parts"])))
        matched = info["parts"][target_part - 1]
        target_cid = matched["cid"]
        p_title = matched["title"]

    clean_p_title = sanitize_filename(p_title)
    article_file = ws.articles_dir / f"P{target_part:02d}_{clean_p_title}_精读文章.md"
    # 复用判定走宽容定位，兼容历史工作区无 _精读文章 后缀的长文
    existing_article = KernelExtractor.find_article(ws, target_part)
    if existing_article is not None and existing_article.stat().st_size >= 1000:
        print(f"[✓] 单集精读长文已存在，无需重新派发: {existing_article}")
        if args.output:
            out_p = Path(args.output).resolve()
            out_p.parent.mkdir(parents=True, exist_ok=True)
            out_p.write_text(existing_article.read_text(encoding="utf-8"), encoding="utf-8")
            print(f"[✓] 长文已复制至: {out_p}")
        return

    audio_file = ws.audio_dir / f"P{target_part:02d}_{clean_p_title}.m4a"

    # Audio check or extraction/download
    if not audio_file.exists() or audio_file.stat().st_size < 10240:
        if info.get("is_local"):
            source_file = matched["filepath"] if info["has_multi_pages"] else info["source_path"]
            print(f"[*] 正在从本地视频提取 64kbps 纯音频...")
            LocalMediaParser.extract_audio(source_file, audio_file)
        else:
            print(f"[*] 音频未缓存，正在下载 P{target_part:02d} 音频...")
            # 中文注释：统一走 412 富化入口
            stream_info = get_audio_stream(
                bvid,
                target_cid,
                sessdata=args.sessdata,
                prefer_quality=getattr(args, "quality", "low"),
            )
            AudioFetcher.download_audio(stream_info["best_stream_url"], str(audio_file), repackage_m4a=True)

    tf = _export_article_task_guarded(
        ws, target_part, clean_p_title, audio_file, title=info["title"], cid=target_cid,
        article_type=_confirm_article_prompt_style(args),
    )
    print(f"[✓] 已导出单集精读文章任务书（零中间逐字稿，听音后直接撰写）: {tf} (status=need-agent-article)")


def cmd_pipeline(args):
    """两阶段流水线：调度编排委托领域服务 PipelineCoordinator，CLI 仅负责参数解析与退出码转换。"""
    article_type = _confirm_article_prompt_style(args)
    coordinator = PipelineCoordinator()
    try:
        coordinator.run(
            url=args.url,
            sessdata=args.sessdata,
            task=args.task,
            base_dir=args.base_dir,
            page=args.page,
            range_str=args.range,
            process_all=args.all,
            force=args.force,
            prefetch_workers=args.prefetch_workers,
            skip_failed=args.skip_failed,
            quality=args.quality,
            chunk_minutes=getattr(args, "chunk_minutes", 60),
            article_type=article_type,
        )
    except PipelineGateError as gate:
        sys.exit(gate.exit_code)


def cmd_cluster_notes(args):
    info = resolve_target_info(
        args.url,
        sessdata=args.sessdata,
        custom_task=getattr(args, "task", None),
        base_dir=getattr(args, "base_dir", None),
    )
    bvid = info["bvid"]
    ws = TaskWorkspace.create(title=info["title"], bvid=bvid, custom_name=args.task, base_dir=args.base_dir)

    print("=" * 65)
    print(f"[*] 启动知识块智能聚合重构流水线 (Knowledge-Block Aggregation)")
    print(f"[*] 课程标题: 《{info['title']}》 (共 {len(info['parts'])} 个分集)")
    print(f"[*] 任务工作区: {ws.root_dir}")
    print("=" * 65)

    # 1. Semantic Topic Planner：规划由宿主 Agent 语义产出（零本地关键词聚类）
    print(f"\n[Phase 1/2] 收集语料摘要并校验知识块规划...")
    summaries = {}
    for p in info["parts"]:
        p_num = p["page"]
        art = KernelExtractor.find_article(ws, p_num)
        if art is not None:
            try:
                summaries[p_num] = art.read_text(encoding="utf-8")[:400]
            except Exception:
                pass
    for p in info["parts"]:
        p_num = p["page"]
        if p_num in summaries:
            continue
        clean_t = sanitize_filename(p["title"])
        clean_f = ws.subtitles_dir / f"P{p_num:02d}_{clean_t}_clean.txt"
        if clean_f.exists() and clean_f.stat().st_size > 50:
            summaries[p_num] = clean_f.read_text(encoding="utf-8")[:300]

    if not summaries:
        print("=" * 65)
        print("[!] 当前工作区尚无任何语料（articles/ 与 subtitles/ 均为空）。")
        print("[*] 请先让 Agent 完成单集长文（articles/PXX_*_精读文章.md），再运行 cluster-notes。")
        print("=" * 65)
        sys.exit(2)

    plan = SemanticTopicPlanner.plan(
        info["parts"],
        course_title=info["title"],
        ws=ws,
        force=args.force_plan,
        transcript_summaries=summaries,
    )
    if not plan:
        print("=" * 65)
        print("[!] 知识块规划尚未产出：已导出规划任务书，等待宿主 Agent 完成语义规划。")
        print(f"[*] 任务书   : {ws.root_dir / 'topic_plan_TASK.md'}")
        print(f"[*] 目标文件 : {ws.root_dir / 'topic_plan.json'}")
        print("[*] 完成后重跑本命令即可继续（校验通过会自动复用）。")
        print("=" * 65)
        sys.exit(2)

    print(f"[✓] 知识块规划已就绪，共 {len(plan)} 个逻辑知识块:")
    for b in plan:
        eps = b["episodes"]
        p_str = f"P{min(eps):02d}-P{max(eps):02d}" if len(eps) > 1 else f"P{eps[0]:02d}"
        print(f"    - 模块 {b['block_id']:02d} ({p_str}): {b['block_title']}")

    # Clean old single-episode notes if replace requested (safely backed up first)
    if args.replace:
        # 1.7 之前遗留的旧版单集笔记（模块笔记上线前的产物），原地替换为模块大笔记
        old_single_notes = list(ws.notes_dir.glob("P[0-9][0-9]_*_笔记.md"))
        if old_single_notes:
            backup_dir = ws.notes_dir / ".backup_single_notes"
            backup_dir.mkdir(parents=True, exist_ok=True)
            print(f"\n[*] 正在备份并清理 {len(old_single_notes)} 篇旧版单集笔记（已备份至 {backup_dir.name}，原地替换为模块大笔记）...")
            for f in old_single_notes:
                try:
                    shutil.copy2(f, backup_dir / f.name)
                    f.unlink()
                except OSError:
                    pass

    # Filter blocks if block_id or range specified
    target_blocks = plan
    if args.block_id:
        target_blocks = [b for b in plan if b["block_id"] == args.block_id]
    elif args.start_block or args.end_block:
        s_b = args.start_block or 1
        e_b = args.end_block or len(plan)
        target_blocks = [b for b in plan if s_b <= b["block_id"] <= e_b]

    # 2. 模块笔记派发：语料门禁 = 本模块各集单集精读长文齐备（知识元已降级为可选索引）
    print(f"\n[Phase 2/2] 逐模块导出模块笔记任务书 (待处理 {len(target_blocks)} 个知识块；笔记只有一种风格)...")
    block_results = []
    for b in target_blocks:
        b_id = b["block_id"]
        eps = b["episodes"]
        p_str = f"P{min(eps):02d}-P{max(eps):02d}" if len(eps) > 1 else f"P{eps[0]:02d}"
        print(f"\n▶ 正在处理模块 {b_id:02d} ({p_str}): 《{b['block_title']}》...")

        block_parts = [p for p in info["parts"] if p["page"] in eps]
        articles, missing = BlockSynthesizer.collect_block_articles(block_parts, ws)
        if missing:
            missing_str = ", ".join(f"P{m:02d}" for m in missing)
            print(f"    [gate] 本模块尚有 {len(missing)} 集无单集精读长文（{missing_str}），跳过笔记派发")
            print(f"    [gate] 请先让 Agent 补齐 articles/ 后再重跑本命令（已产出的模块会自动复用）")
            continue
        print(f"    [✓] 语料齐备：已锁定 {len(articles)} 篇单集精读长文")

        kernel_index = None
        if getattr(args, "kernel_index", False):
            kernels = KernelExtractor.extract_batch_kernels(block_parts, ws=ws)
            kernel_index = [k for k in kernels if k.get("status") == "extracted"] or None
            if kernel_index:
                print(f"    [i] --kernel-index 已开启：注入 {len(kernel_index)} 条知识元索引（仅供参考定位）")

        res = BlockSynthesizer.synthesize_block(
            b, articles, ws=ws, force=args.force, kernel_index=kernel_index
        )
        block_results.append(res)

    # 加载转绝对、保存转相对（TaskWorkspace 原生支持）
    manifest = ws.load_manifest(absolute=True)
    manifest["knowledge_blocks_plan"] = plan
    manifest["knowledge_blocks_results"] = block_results
    ws.save_manifest(manifest)

    print("\n" + "=" * 65)
    print(f"[✓] 知识块聚合重构执行完毕！共导出 {len(block_results)} 份模块笔记任务书")
    print(f"[✓] 任务书目录: {ws.notes_dir}")
    print("=" * 65)


def cmd_cluster_articles(args):
    """Consolidates single-episode articles in articles/ into modular chapter textbooks in textbooks/."""
    from src.generator.integrator import ArticleIntegrator

    info = resolve_target_info(
        args.url,
        sessdata=args.sessdata,
        custom_task=getattr(args, "task", None),
        base_dir=getattr(args, "base_dir", None),
    )
    bvid = info["bvid"]
    ws = TaskWorkspace.create(title=info["title"], bvid=bvid, custom_name=args.task, base_dir=args.base_dir)

    print("=" * 65)
    print(f"[*] 启动单集精读教材整编模块全书流水线 (Modular Textbook Integration)")
    print(f"[*] 课程标题: 《{info['title']}》 (共 {len(info['parts'])} 个分集)")
    print(f"[*] 任务工作区: {ws.root_dir}")
    print(f"[*] 目标教材目录: {ws.root_dir / 'textbooks'}")
    print("=" * 65)

    integrator = ArticleIntegrator(ws.root_dir)
    force = bool(getattr(args, "force", False))
    results = integrator.run(course_title=info["title"], force=force)

    # Update manifest（textbooks 属列表型路径字段，save_manifest 会自动反向相对化）
    manifest = ws.load_manifest(absolute=True)
    manifest["textbooks"] = [str(r) for r in results]
    ws.save_manifest(manifest)

    print("\n" + "=" * 65)
    print(f"[✓] 模块教材已就绪，共 {len(results)} 部模块精读全书"
          f"（{'已按最新章节强制重编' if force else '已有教材默认复用，需重编请加 --force'}）:")
    for r in results:
        size_kb = round(r.stat().st_size / 1024, 1)
        print(f"    - [{size_kb} KB] {r.name}")
    print(f"[✓] 单集微粒度文章保持完整: {ws.articles_dir} (未做任何删除)")
    print("=" * 65)


def cmd_dedup(args):
    """Scans and synchronizes duplicate audio assets to save 100% of redundant LLM token costs."""
    info = resolve_target_info(
        args.url,
        sessdata=args.sessdata,
        custom_task=getattr(args, "task", None),
        base_dir=getattr(args, "base_dir", None),
    )
    bvid = info["bvid"]
    ws = TaskWorkspace.create(title=info["title"], bvid=bvid, custom_name=args.task, base_dir=args.base_dir)

    print("=" * 65)
    print(f"[*] 启动音频 SHA-256 指纹去重扫描流水线 (Audio Fingerprint Deduplication)")
    print(f"[*] 任务工作区: {ws.root_dir}")
    print("=" * 65)

    synced = ws.sync_duplicate_assets(dry_run=args.dry_run)
    if synced:
        print(f"\n[✓] 发现并同步了 {len(synced)} 组重复音频资产 (0 Token 消耗):")
        for item in synced:
            print(f"    - P{item['src_page']:02d} ──► P{item['dst_page']:02d} [Hash: {item['hash']}] (字幕: {item['synced_sub']}, 文章: {item['synced_art']})")
    else:
        print("\n[✓] 未发现需要同步的重复分集（所有音频独一无二或已全部同步就绪）。")
    print("=" * 65)


def cmd_cleanup(args):
    """回收已完成的派发任务书（*_TASK.md），每类保留 N 份范本供查阅提示词。"""
    from src.core.task_cleanup import CATEGORY_LABELS, cleanup_completed_tasks, find_workspaces

    workspaces = find_workspaces(args.base_dir)
    if getattr(args, "task", None):
        keyword = str(args.task)
        workspaces = [w for w in workspaces if keyword in w.root_dir.name]
    if not workspaces:
        print(f"[!] 在 {Path(args.base_dir).resolve()} 下未找到可用工作区。", file=sys.stderr)
        sys.exit(1)

    keep_n = max(0, int(getattr(args, "keep", 1) or 0))
    dry_run = bool(getattr(args, "dry_run", False))

    print("=" * 65)
    print(f"[*] 任务书回收流水线（{'预演，不落盘' if dry_run else '执行删除'}；每类保留 {keep_n} 份范本）")
    print(f"[*] 扫描基目录: {Path(args.base_dir).resolve()}")
    print("=" * 65)

    total_deleted = total_kept = total_skipped = total_failed_delete = 0
    for ws in workspaces:
        result = cleanup_completed_tasks(ws, keep_per_category=keep_n, dry_run=dry_run)
        counts = result["counts"]
        print(f"\n▶ {ws.root_dir.name}")
        for category, stat in counts.items():
            print(
                f"    {CATEGORY_LABELS[category]:<12} 共 {stat['total']:>4} 份 | "
                f"回收 {stat['deleted']:>4} | 保留范本 {stat['kept']} | "
                f"成品未产出仍保留 {stat['skipped_pending']} | 删除失败 {stat.get('failed_delete', 0)}"
            )
        total_deleted += len(result["deleted"])
        total_kept += len(result["kept"])
        total_skipped += len(result["skipped_pending"])
        total_failed_delete += len(result.get("failed_delete", []))
        for path in result["kept"]:
            print(f"    [留] {path}")
        for path in result.get("failed_delete", []):
            print(f"    [!] 删除失败（文件被占用或无权限）: {path}")

    print("\n" + "=" * 65)
    verb = "可回收" if dry_run else "已回收"
    print(f"[✓] {verb}任务书 {total_deleted} 份 | 保留范本 {total_kept} 份 | "
          f"成品未产出仍保留 {total_skipped} 份 | 删除失败 {total_failed_delete} 份")
    print("[i] topic_plan_TASK.md 属课程级规划任务书，唯一存在，永不回收。")
    if dry_run:
        print("[i] 当前为预演模式；去掉 --dry-run 即真正删除。")
    print("=" * 65)


def cmd_sync(args):
    """按磁盘产成对账并回填 manifest.json（账本以硬盘为唯一真相）。"""
    from src.core.state_sync import reconcile_workspace_manifest
    from src.core.task_cleanup import find_workspaces

    workspaces = find_workspaces(args.base_dir)
    if getattr(args, "task", None):
        keyword = str(args.task)
        workspaces = [w for w in workspaces if keyword in w.root_dir.name]
    if not workspaces:
        print(f"[!] 在 {Path(args.base_dir).resolve()} 下未找到可用工作区。", file=sys.stderr)
        sys.exit(1)

    dry_run = bool(getattr(args, "dry_run", False))
    print("=" * 65)
    print(f"[*] 任务账本对账（{'预演，不写盘' if dry_run else '写入 manifest.json'}）")
    print("[*] 判定依据：articles/ 合格长文（≥1000 字节）+ notes/ + textbooks/ + topic_plan.json")
    print("=" * 65)

    for ws in workspaces:
        report = reconcile_workspace_manifest(ws, dry_run=dry_run)
        print(f"\n▶ {report['workspace']}")
        print(f"    分集：{report['success']}/{report['total']} 集达标 | 待办 {report['pending']} | "
              f"跳过 {report['skipped']} | 历史失败 {report['failed']}")
        print(f"    模块资产：模块笔记 {report['notes']} 份 | 教材 {report['textbooks']} 部 | "
              f"规划 {report['plan_blocks']} 块")
        print(f"    pipeline_completed = {report['pipeline_completed']}")

    print("\n" + "=" * 65)
    print(f"[✓] 已对账 {len(workspaces)} 个工作区" + ("（预演模式，未写盘）" if dry_run else ""))
    print("=" * 65)


def cmd_login(args):
    """持久化保存 SESSDATA，之后所有命令无需再传 --sessdata。

    刻意不提供交互式输入：本工具主要供 Agent 自动化调度，等待人工键入的分支
    在非交互环境下会直接卡死。
    """
    value = (getattr(args, "sessdata", None) or "").strip()
    if not value:
        print("[!] 未提供 SESSDATA，拒绝写入空凭证。", file=sys.stderr)
        print('    用法：python src/cli.py login --sessdata "<你的 SESSDATA>"', file=sys.stderr)
        print("    获取：浏览器登录 bilibili.com → F12 → 应用/存储 → Cookie → 复制 SESSDATA 的值", file=sys.stderr)
        sys.exit(1)

    path = SessdataStore.save(value)
    print(f"[✓] SESSDATA 已持久化保存: {path}")
    print(f"    指纹: {SessdataStore.mask(value)}")
    print("[i] 该文件已被 .gitignore 排除，不会进入版本库。")
    print("[i] 撤销保存请运行：python src/cli.py logout")


def cmd_logout(args):
    """清除本地保存的 SESSDATA。"""
    if SessdataStore.clear():
        print("[✓] 已清除本地保存的 SESSDATA。")
    else:
        print("[*] 本地没有保存过 SESSDATA，无需清除。")


def cmd_info(args):
    """中文注释：做实 info：WBI 有效期/sessdata 有无/412 状态/断点续跑示例。"""
    import shutil
    import sys
    import time as _time
    if getattr(args, "refresh", False):
        try:
            if _STATUS_FILE.exists():
                _STATUS_FILE.unlink()
                print("[*] 已清理缓存状态文件")
        except Exception:
            pass
    print("=" * 65)
    print("【系统运行环境与工具链检查】")
    print(f"• Python 运行环境: v{sys.version.split()[0]} ({sys.executable})")
    ffmpeg_path = shutil.which("ffmpeg")
    print(f"• FFmpeg 状态   : {'已就绪 (' + ffmpeg_path + ')' if ffmpeg_path else '未找到（建议安装以支持音频切片）'}")
    print("• 架构模式      : 宿主 Agent 原生派发模式（零环境变量、零网络代理绑定；转录=对话模型原生唯一路径）")
    print("=" * 65)
    print("【三域路径（代码 / MCP / 产物 互相隔离）】")
    _三域 = _paths.describe()
    print(f"• 代码根       : {_三域['code_root']}")
    print(f"• 容器根 home  : {_三域['home_root']}" + ("  [来自 ${}]".format(_paths.ENV_HOME) if _三域["home_from_env"] else ""))
    print(f"• 产物根       : {_三域['products_root']}" + ("  [来自 ${}]".format(_paths.ENV_OUTPUT_DIR) if _三域["products_from_env"] else ""))
    print(f"  工作区清单   : {store_path().parent}")
    print(f"  覆盖方式     : export {_paths.ENV_HOME}=<容器根> / export {_paths.ENV_OUTPUT_DIR}=<产物根>，或用 --base-dir")
    print("=" * 65)
    # 中文注释：WBI key 有效期读内存缓存+缓存文件
    print("【WBI Key 状态】")
    try:
        from src.core.wbi import WbiSigner
        exp = getattr(WbiSigner, "_cache_expire_time", 0.0)
        has_key = bool(getattr(WbiSigner, "_cached_mixin_key", None))
        if has_key and exp > _time.time():
            print(f"• WBI Key：有效，有效期至 {_time.strftime('%Y-%m-%d %H:%M:%S', _time.localtime(exp))}")
        elif has_key:
            print("• WBI Key：已过期，下次请求自动刷新")
        else:
            print("• WBI Key：无记录（尚未请求，首次调用自动获取）")
    except Exception as err:
        print(f"• WBI Key：无记录（{err}）")
    # 中文注释：sessdata 只显示来源与脱敏指纹，绝不回显完整值
    sess = getattr(args, "sessdata", None)
    src = getattr(args, "sessdata_source", None)
    if sess:
        print(f"• SESSDATA：有（来源：{src}，指纹：{SessdataStore.mask(sess)}）")
    else:
        print("• SESSDATA：无（未传入 --sessdata，本地也无存档）")
    if SessdataStore.load():
        print(f"• 凭证存档：已保存于 {store_path()}")
    else:
        print('• 凭证存档：无（可用 python src/cli.py login --sessdata "<值>" 持久化保存）')
    # 中文注释：上次 412/熔断状态
    print("【上次 412/熔断状态】")
    try:
        if _STATUS_FILE.exists():
            print(f"• 状态文件：{_STATUS_FILE}（仓库相对：{_to_relative_str(str(_STATUS_FILE))}）")
            print(f"• 内容：{_STATUS_FILE.read_text(encoding='utf-8')[:500]}")
        else:
            print("• 无记录")
    except Exception as err:
        print(f"• 无记录（读取失败：{err}）")
    print("=" * 65)
    print("【Agent 自主驱动工作协议】：")
    print("0. 类型判定（工作流第一步）: 依课程标题/分集标题判定长文类型，未命中已提供提示词的类型即终止任务")
    print("   - 当前已提供提示词：learning（学习类：系统网课/公开课/讲座）")
    print("1. 物理层跑批: python src/cli.py pipeline \"<链接>\" --all --article-type learning")
    print("   - 长文提示词风格由用户确认：learning=学习（推荐）/ legacy=旧版；不确认即终止任务")
    print("2. 语料与任务书自动生成于 output/<任务名>/")
    print("   - articles/PXX_*_TASK.md: 单集精读文章提示词")
    print("   - notes/模块XX_*_TASK.md: 知识块聚合复习笔记提示词")
    print("3. 宿主 Agent 主程序以 5 个并发通道（Task子代理或并行生成）读取任务书，直接撰写落盘！")
    print("=" * 65)
    print("【可复制的断点续跑命令示例】：")
    print('python src/cli.py login --sessdata "<你的 SESSDATA>"   # 一次持久化，后续命令免传')
    print('python src/cli.py pipeline "<链接>" --all --article-type learning')
    print('python src/cli.py pipeline "<链接>" --range 1-10 --article-type learning')
    print("=" * 65)


cmd_agent_info = cmd_info


def main():
    parser = argparse.ArgumentParser(description="Bilibili Audio & Knowledge Extraction Agent Toolkit")
    subparsers = parser.add_subparsers(dest="subcommand", help="Available subcommands")

    # parse
    p_parse = subparsers.add_parser("parse", help="Parse video topology & list parts (Bilibili URL or local media)")
    p_parse.add_argument("url", help="Bilibili URL/BV ID or local video/audio/directory path")
    p_parse.add_argument("--sessdata", help="Optional SESSDATA cookie", default=None)
    p_parse.add_argument("--limit", type=int, default=10, help="Max items to display")
    p_parse.add_argument("--json", action="store_true", help="Output in JSON format")

    # audio
    p_audio = subparsers.add_parser("audio", help="Fetch & download/extract audio stream")
    p_audio.add_argument("url", help="Bilibili URL/BV ID or local video/audio/directory path")
    p_audio.add_argument("--page", type=int, default=None, help="Page/Part index (auto-detects ?p=X from URL if omitted)")
    p_audio.add_argument("--all", action="store_true", help="Batch download/extract all parts")
    p_audio.add_argument("--range", default=None, help="Episode range to download (e.g. 1-10, 1,3,5)")
    p_audio.add_argument("--quality", choices=["low", "medium", "high"], default="low", help="Audio quality (low=64k speech default, medium=132k, high=192k)")
    p_audio.add_argument("--task", default=None, help="Custom task workspace folder name")
    p_audio.add_argument("--base-dir", default=None, help=BASE_DIR_HELP)
    p_audio.add_argument("--force", action="store_true", help="Force re-download/re-extraction even if audio file already exists")
    p_audio.add_argument("--sessdata", help="Optional SESSDATA cookie", default=None)
    p_audio.add_argument("--url-only", action="store_true", help="Only print stream URL without downloading")
    p_audio.add_argument("--output", default=None, help="Optional explicit output directory override")
    p_audio.add_argument("--chunk-minutes", type=int, default=10, help="Split audio into balanced chunks of ~N minutes (0=disabled)")
    p_audio.add_argument("--json", action="store_true", help="Output in JSON format")

    # transcribe
    p_tr = subparsers.add_parser("transcribe", help="Export per-episode ARTICLE_TASK (zero intermediate transcript)")
    p_tr.add_argument("target", help="Bilibili URL/BVID, local audio file, or local video file")
    p_tr.add_argument("--page", type=int, default=None, help="Page index for Bilibili video or local course (auto-detects ?p=X from URL if omitted)")
    p_tr.add_argument("--task", default=None, help="Custom task workspace folder name")
    p_tr.add_argument("--base-dir", default=None, help=BASE_DIR_HELP)
    p_tr.add_argument("--output", default=None, help="Optional custom output path (only used when cached clean transcript exists)")
    p_tr.add_argument("--sessdata", help="Optional SESSDATA cookie", default=None)
    p_tr.add_argument(
        "--article-type", default=None, dest="article_type",
        help="长文提示词风格（用户确认）：learning=学习（推荐，当前版）/ legacy=旧版（原稳定版）；"
             "未指定时打印风格菜单并请用户确认，确认不了即终止任务。"
             "另有 consulting/interview/review/livestream 四种形态已登记但提示词未提供，命中即终止。",
    )

    # pipeline
    p_pipe = subparsers.add_parser("pipeline", help="Execute complete automated pipeline (Audio -> ASR -> Notes & Articles)")
    p_pipe.add_argument("url", help="Bilibili URL/BV ID, local video file, or local course directory")
    p_pipe.add_argument("--page", type=int, default=None, help="Page/Part index (auto-detects ?p=X from URL if omitted)")
    p_pipe.add_argument("--all", action="store_true", help="Process all episodes in multi-P collection or local course directory")
    p_pipe.add_argument("--range", default=None, help="Episode range to process (e.g. 1-10, 1,3,5)")
    p_pipe.add_argument("--quality", choices=["low", "medium", "high"], default="low", help="Audio quality (low=64k speech default, medium=132k, high=192k)")
    p_pipe.add_argument("--task", default=None, help="Custom task workspace folder name")
    p_pipe.add_argument("--base-dir", default=None, help=BASE_DIR_HELP)
    p_pipe.add_argument("--force", action="store_true", help="Force re-transcribing and re-generating even if exists")
    p_pipe.add_argument("--prefetch-workers", type=int, default=12, help="Parallel audio prefetch (download/extract) threads")
    p_pipe.add_argument("--skip-failed", action="store_true", default=False, help="Explicit opt-in: exempt failed episodes from transcription gate (recorded in manifest skip list)")
    p_pipe.add_argument("--chunk-minutes", type=int, default=60, help="Split audio into chunks of ~N minutes (0=disabled, default=60)")
    p_pipe.add_argument("--sessdata", help="Optional SESSDATA cookie", default=None)
    p_pipe.add_argument(
        "--article-type", default=None, dest="article_type",
        help="长文提示词风格（用户确认）：learning=学习（推荐，当前版）/ legacy=旧版（原稳定版）；"
             "未指定时打印风格菜单并请用户确认，确认不了即终止任务。"
             "另有 consulting/interview/review/livestream 四种形态已登记但提示词未提供，命中即终止。",
    )

    # info / agent-info
    p_info = subparsers.add_parser("info", aliases=["agent-info"], help="Show environment & toolchain readiness status")
    p_info.add_argument("--refresh", action="store_true", help="Clear cached status")
    # 中文注释：sessdata 仅显示来源与脱敏指纹
    p_info.add_argument("--sessdata", help="Optional SESSDATA cookie (only shows source & masked fingerprint)", default=None)

    # login / logout：SESSDATA 持久化
    p_login = subparsers.add_parser("login", help="Persist Bilibili SESSDATA so later commands need no --sessdata")
    p_login.add_argument("--sessdata", help="SESSDATA cookie value (required; no interactive prompt)", default=None)

    subparsers.add_parser("logout", help="Remove the persisted SESSDATA")

    # cluster-notes
    p_cl = subparsers.add_parser("cluster-notes", help="Cluster multi-P course into coherent knowledge block notes")
    p_cl.add_argument("url", help="Bilibili URL or BV ID")
    p_cl.add_argument("--block-id", type=int, default=None, help="Process specific block ID only")
    p_cl.add_argument("--start-block", type=int, default=None, help="Start block ID")
    p_cl.add_argument("--end-block", type=int, default=None, help="End block ID")
    p_cl.add_argument("--task", default=None, help="Custom task workspace folder name")
    p_cl.add_argument("--base-dir", default=None, help=BASE_DIR_HELP)
    p_cl.add_argument("--replace", action="store_true", default=False, help="Replace old single-episode notes in notes/ directory")
    p_cl.add_argument("--force", action="store_true", help="Force re-exporting block task files even if they exist")
    p_cl.add_argument("--force-plan", action="store_true", help="Force re-generating semantic topic plan")
    p_cl.add_argument(
        "--kernel-index",
        action="store_true",
        default=False,
        help="Optional: also inject existing knowledge-kernel JSON as a locating index (long articles stay the source of truth)",
    )
    p_cl.add_argument("--sessdata", help="Optional SESSDATA cookie", default=None)

    # cluster-articles
    p_ca = subparsers.add_parser("cluster-articles", help="Consolidate single-episode articles into modular textbooks in textbooks/")
    p_ca.add_argument("url", help="Bilibili URL or BV ID")
    p_ca.add_argument("--task", default=None, help="Custom task workspace folder name")
    p_ca.add_argument("--base-dir", default=None, help=BASE_DIR_HELP)
    p_ca.add_argument("--force", action="store_true", help="Force re-integrating modular textbooks (default: reuse existing textbooks/)")
    p_ca.add_argument("--sessdata", help="Optional SESSDATA cookie", default=None)

    # dedup
    p_dd = subparsers.add_parser("dedup", help="Scan and synchronize duplicate audio assets to save LLM tokens")
    p_dd.add_argument("url", help="Bilibili URL, BV ID, or local media path")
    p_dd.add_argument("--task", default=None, help="Custom task workspace folder name")
    p_dd.add_argument("--base-dir", default=None, help=BASE_DIR_HELP)
    p_dd.add_argument("--dry-run", action="store_true", help="Only check for duplicates without copying files")
    p_dd.add_argument("--sessdata", help="Optional SESSDATA cookie", default=None)

    # cleanup：任务书回收（成品已产出的 *_TASK.md 清场，每类保留 N 份范本）
    p_cl2 = subparsers.add_parser("cleanup", help="Reclaim completed dispatch task-files (*_TASK.md), keeping N samples per category")
    p_cl2.add_argument("--task", default=None, help="Only process workspaces whose folder name contains this keyword")
    p_cl2.add_argument("--base-dir", default=None, help=BASE_DIR_HELP)
    p_cl2.add_argument("--keep", type=int, default=1, help="Samples to keep per category (default 1; 0=delete all completed)")
    p_cl2.add_argument("--all", action="store_true", help="Process every workspace under base-dir (compatibility flag; this is already the default)")
    p_cl2.add_argument("--dry-run", action="store_true", help="Only report what would be reclaimed")

    # sync：账本对账（以磁盘产物回填 manifest.json）
    p_sync = subparsers.add_parser("sync", help="Reconcile manifest.json with on-disk products (disk is the source of truth)")
    p_sync.add_argument("--task", default=None, help="Only process workspaces whose folder name contains this keyword")
    p_sync.add_argument("--base-dir", default=None, help=BASE_DIR_HELP)
    p_sync.add_argument("--all", action="store_true", help="Process every workspace under base-dir (compatibility flag; this is already the default)")
    p_sync.add_argument("--dry-run", action="store_true", help="Only report the reconciled state without writing")

    args = parser.parse_args()
    if not args.subcommand:
        parser.print_help()
        sys.exit(1)

    # 凭证解析：命令行显式传入优先于本地存档；login 需拿到原始值以区分“未传”。
    raw_sessdata = (getattr(args, "sessdata", None) or "").strip()
    if args.subcommand == "login":
        args.sessdata = raw_sessdata or None
        args.sessdata_source = "命令行参数" if raw_sessdata else None
    else:
        args.sessdata = resolve_sessdata(raw_sessdata)
        args.sessdata_source = "命令行参数" if raw_sessdata else ("本地存档" if args.sessdata else None)

    # 产物根解析：--base-dir 缺省即产物根（绝对路径），使命令与当前工作目录彻底解耦。
    if hasattr(args, "base_dir"):
        args.base_dir = _resolve_base_dir(args.base_dir)

    dispatch = {
        "parse": cmd_parse,
        "audio": cmd_audio,
        "transcribe": cmd_transcribe,
        "pipeline": cmd_pipeline,
        "cluster-notes": cmd_cluster_notes,
        "cluster-articles": cmd_cluster_articles,
        "dedup": cmd_dedup,
        "cleanup": cmd_cleanup,
        "sync": cmd_sync,
        "login": cmd_login,
        "logout": cmd_logout,
        "agent-info": cmd_agent_info,
        "info": cmd_info,
    }
    dispatch[args.subcommand](args)


if __name__ == "__main__":
    main()
