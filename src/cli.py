#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Command-Line Interface for Bilibili Audio & Knowledge Extraction.

Commands:
  parse     - Parse URL/BVID, classify video type, and inspect sub-videos
  audio     - Fetch audio stream URL, download m4a, and optionally chunk via ffmpeg
  subtitle  - Probe and download official AI/human subtitles (Fallback)
  clean     - Clean spoken transcript and eliminate filler phrases
  prompt    - Build revision note and tutorial article prompts for AI agent
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

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

from src.core.parser import BilibiliParser
from src.core.local_media import LocalMediaParser, SUPPORTED_VIDEO_EXTS
from src.core.fetcher import AudioFetcher
from src.core.audio_chunker import AudioChunker
from src.core.subtitle import SubtitleFetcher
from src.core.workspace import TaskWorkspace
from src.core.transcriber import AudioTranscriber
from src.core.kernel_extractor import KernelExtractor
from src.generator.cleaner import TextCleaner
from src.generator.doc_builder import DocumentBuilder
from src.generator.topic_planner import SemanticTopicPlanner
from src.generator.block_synthesizer import BlockSynthesizer


def _resolve_target_info(target: str, sessdata: Optional[str] = None) -> Dict[str, Any]:
    """Polymorphically resolve metadata from either local media path or Bilibili URL/BVID."""
    if LocalMediaParser.is_local_media(target):
        return LocalMediaParser.parse(target)
    return BilibiliParser.parse_video(target, sessdata=sessdata)


def _parse_range_string(range_str: str, max_val: int):
    """Parse range string like '1-10', '1,3,5', or '5-' into a set of 1-based page indices."""
    pages = set()
    for part in range_str.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            s_str, e_str = part.split("-", 1)
            start = int(s_str.strip()) if s_str.strip() else 1
            end = int(e_str.strip()) if e_str.strip() else max_val
            for i in range(max(1, start), min(max_val, end) + 1):
                pages.add(i)
        else:
            p = int(part)
            if 1 <= p <= max_val:
                pages.add(p)
    return sorted(pages)


def cmd_parse(args):
    info = _resolve_target_info(args.url, sessdata=args.sessdata)
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
    print(f"【UP 主】   : {info['owner']['name']} (mid: {info['owner']['mid']})")
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
    info = _resolve_target_info(args.url, sessdata=args.sessdata)
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
            target_indices = _parse_range_string(args.range, len(all_parts))
            selected_parts = [all_parts[i - 1] for i in target_indices]
        else:
            selected_parts = all_parts

        total_parts = len(selected_parts)
        print("=" * 65)
        print(f"[*] 批量提取与无损转换任务启动 (共 {total_parts} 个分集)")
        print(f"[*] 目标音轨存储目录: {target_audio_dir}")
        print("=" * 65)

        manifest_items = []
        for idx, p in enumerate(selected_parts, 1):
            p_num = p["page"]
            clean_p_title = "".join([c for c in p["title"] if c.isalnum() or c in (" ", "-", "_")]).strip()
            target_file = target_audio_dir / f"P{p_num:02d}_{clean_p_title}.m4a"

            # Check if cached and non-empty
            if target_file.exists() and target_file.stat().st_size > 10240 and not args.force:
                size_mb = round(target_file.stat().st_size / (1024 * 1024), 2)
                print(f"[{idx:02d}/{total_parts:02d}] P{p_num:02d} [{size_mb} MB] 已存在，跳过: {target_file.name}")
                manifest_items.append({
                    "page": p_num,
                    "title": p["title"],
                    "cid": p["cid"],
                    "duration": p["duration"],
                    "audio_file": str(target_file),
                    "size_bytes": target_file.stat().st_size,
                    "status": "cached",
                })
                continue

            print(f"\n[{idx:02d}/{total_parts:02d}] 正在提取 P{p_num:02d}: {p['title']} (CID: {p['cid']})...")
            try:
                if info.get("is_local"):
                    LocalMediaParser.extract_audio(p["filepath"], target_file)
                    saved_path = str(target_file)
                    f_size = Path(saved_path).stat().st_size
                    print(f"    [✓] 本地音频提取完成: {Path(saved_path).name} ({round(f_size / (1024 * 1024), 2)} MB)")
                    manifest_items.append({
                        "page": p_num,
                        "title": p["title"],
                        "cid": p["cid"],
                        "duration": p["duration"],
                        "audio_file": saved_path,
                        "size_bytes": f_size,
                        "quality": "64kbps-aac-mono",
                        "status": "downloaded",
                    })
                else:
                    stream_info = AudioFetcher.get_audio_stream_info(
                        bvid,
                        p["cid"],
                        sessdata=args.sessdata,
                        prefer_quality=getattr(args, "quality", "low"),
                    )
                    print(f"    - 流码率: {stream_info['quality_desc']}")
                    saved_path = AudioFetcher.download_audio(
                        stream_info["best_stream_url"],
                        str(target_file),
                        repackage_m4a=True,
                    )
                    f_size = Path(saved_path).stat().st_size
                    print(f"    [✓] 下载与封装完成: {Path(saved_path).name} ({round(f_size / (1024 * 1024), 2)} MB)")
                    manifest_items.append({
                        "page": p_num,
                        "title": p["title"],
                        "cid": p["cid"],
                        "duration": p["duration"],
                        "audio_file": saved_path,
                        "size_bytes": f_size,
                        "quality": stream_info["quality_desc"],
                        "status": "downloaded",
                    })
            except Exception as err:
                print(f"    [✗] 处理 P{p_num:02d} 发生异常: {err}", file=sys.stderr)
                manifest_items.append({
                    "page": p_num,
                    "title": p["title"],
                    "cid": p["cid"],
                    "error": str(err),
                    "status": "failed",
                })

        ws.save_manifest({
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

    clean_title = "".join([c for c in target_title if c.isalnum() or c in (" ", "-", "_")]).strip()
    target_m4a = target_audio_dir / f"{clean_title}.m4a"

    if info.get("is_local"):
        source_file = matched["filepath"] if info["has_multi_pages"] else info["source_path"]
        print(f"[*] 正在从本地视频提取通用 64kbps 纯音频...")
        saved_path = str(LocalMediaParser.extract_audio(source_file, target_m4a))
        stream_info = {"quality_desc": "64kbps AAC Mono (16kHz)", "best_stream_url": saved_path}
        print(f"[✓] 音频提取完成: {saved_path}")
    else:
        print(f"[*] 解析音频流中... BV: {bvid}, CID: {target_cid}")
        stream_info = AudioFetcher.get_audio_stream_info(
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


def cmd_subtitle(args):
    info = BilibiliParser.parse_video(args.url, sessdata=args.sessdata)
    bvid = info["bvid"]
    target_cid = info["cid"]
    req_page = args.page if args.page is not None else (info.get("url_page") or 1)
    page_idx = req_page
    if info["has_multi_pages"]:
        p_idx = max(1, min(req_page, len(info["parts"])))
        target_cid = info["parts"][p_idx - 1]["cid"]
        page_idx = p_idx

    ws = TaskWorkspace.create(
        title=info["title"],
        bvid=bvid,
        custom_name=getattr(args, "task", None),
        base_dir=getattr(args, "base_dir", "output"),
    )

    print(f"[*] 正在探测 B 站官方/AI字幕: {bvid} (CID: {target_cid})...")
    sub_res = SubtitleFetcher.fetch_best_subtitle(bvid, target_cid, sessdata=args.sessdata)
    if not sub_res:
        print("[-] 本视频暂无可用官方/AI字幕，请使用本地音频大模型转录流程。")
        return

    print(f"[✓] 成功获取字幕 ({sub_res['language_doc']}, 是否AI生成: {sub_res['is_ai']}, 条数: {sub_res['total_items']})")
    if args.output:
        out_p = Path(args.output).resolve()
        if out_p.is_dir() or out_p.suffix == "":
            out_file = out_p / f"P{page_idx:02d}_subtitle.txt"
        else:
            out_file = out_p
    else:
        out_file = ws.subtitles_dir / f"P{page_idx:02d}_subtitle.txt"

    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(sub_res["full_text"], encoding="utf-8")
    print(f"[✓] 字幕纯文本已保存至: {out_file}")


def cmd_clean(args):
    in_path = Path(args.file).resolve()
    if not in_path.exists():
        print(f"[-] 文件不存在: {in_path}", file=sys.stderr)
        return
    text = in_path.read_text(encoding="utf-8")
    cleaned_res = TextCleaner.clean(text)
    print(f"[*] 清洗统计: 原始长度={cleaned_res['original_length']}, 清洗后={cleaned_res['cleaned_length']}, 压缩率={cleaned_res['compression_ratio']}%")

    if args.output:
        out_path = Path(args.output).resolve()
        out_path.write_text(cleaned_res["cleaned_text"], encoding="utf-8")
        print(f"[✓] 清洗后文本已保存至: {out_path}")
    else:
        print("-" * 50)
        print(cleaned_res["cleaned_text"][:500] + "...")


def cmd_prompt(args):
    info = _resolve_target_info(args.url, sessdata=args.sessdata)
    title = info["title"]
    req_page = args.page if args.page is not None else (info.get("url_page") or 1)
    part_title = "P1"
    if info["has_multi_pages"] and req_page > 0:
        p_idx = max(1, min(req_page, len(info["parts"])))
        part_title = f"P{p_idx:02d} {info['parts'][p_idx - 1]['title']}"

    content = "[请在此处填入转录文本或将音频直接提供给模型]"
    if args.transcript_file:
        content = Path(args.transcript_file).read_text(encoding="utf-8")

    note_type = getattr(args, "note_type", "auto")
    prompts = DocumentBuilder.render_prompts(
        title=title,
        part_title=part_title,
        content=content,
        note_type=note_type,
        desc=info.get("desc", ""),
    )

    if args.type == "note":
        print(prompts["note_prompt"])
    elif args.type == "article":
        print(prompts["article_prompt"])
    elif args.type == "rectify":
        print(prompts["rectify_prompt"])
    else:
        print(f"=== 【自适应笔记 Prompt (识别分类: {prompts['note_type']} | 原因: {prompts['classify_reason']})】 ===")
        print(prompts["note_prompt"])
        print("\n=== 【精读文章生成 Prompt】 ===")
        print(prompts["article_prompt"])
        print("\n=== 【ASR 语义字面校对 Prompt】 ===")
        print(prompts["rectify_prompt"])


def cmd_note(args):
    info = _resolve_target_info(args.url, sessdata=args.sessdata)
    title = info["title"]
    part_title = ""
    target_cid = info["cid"]
    req_page = args.page if args.page is not None else (info.get("url_page") or 1)

    if info["has_multi_pages"] and req_page > 0:
        p_idx = max(1, min(req_page, len(info["parts"])))
        part_title = f"P{p_idx:02d} {info['parts'][p_idx - 1]['title']}"
        target_cid = info["parts"][p_idx - 1]["cid"]

    content = ""
    if args.transcript_file:
        t_path = Path(args.transcript_file).resolve()
        if t_path.exists():
            content = t_path.read_text(encoding="utf-8")
        else:
            print(f"[-] 转录文件未找到: {t_path}", file=sys.stderr)
            return
    else:
        # Try subtitle fallback if online
        sub_res = None
        if not info.get("is_local"):
            print(f"[*] 探测视频官方/AI字幕作为语料: {info['bvid']}...")
            sub_res = SubtitleFetcher.fetch_best_subtitle(info["bvid"], target_cid, sessdata=args.sessdata)
        if sub_res:
            content = sub_res["full_text"]
            print(f"[✓] 提取到字幕语料 ({sub_res['total_items']} 行)")
        else:
            print("[*] 无在线字幕，使用标题与视频元数据生成笔记骨架模板。")
            content = f"视频简介: {info.get('desc', '')}\n\n该视频时长 {info.get('duration', 0)} 秒，建议结合音频或切片转录生成完整笔记。"

    # Clean content if available
    if len(content) > 50:
        content = TextCleaner.clean(content)["cleaned_text"]

    note_md = DocumentBuilder.render_note(
        title=title,
        part_title=part_title,
        content=content,
        note_type=args.note_type,
        desc=info.get("desc", ""),
    )

    ws = TaskWorkspace.create(
        title=title,
        bvid=info["bvid"],
        custom_name=getattr(args, "task", None),
        base_dir=getattr(args, "base_dir", "output"),
    )

    out_dir = Path(args.output).resolve() if args.output else ws.notes_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    clean_title = "".join(c for c in title if c.isalnum() or c in (" ", "-", "_")).strip()
    out_file = out_dir / f"{info['bvid']}_{clean_title}_笔记.md"
    out_file.write_text(note_md, encoding="utf-8")
    print(f"[✓] 朴素 GitHub 风格笔记已生成: {out_file}")


def cmd_transcribe(args):
    # Check if target is a single local media file
    target_p = Path(args.target).resolve()
    if target_p.exists() and target_p.is_file():
        print(f"[*] 直接转录本地媒体: {target_p.name} (引擎策略: {args.engine})...")
        fallback_allowed = True if args.allow_local_fallback is None else args.allow_local_fallback
        res = AudioTranscriber.transcribe(
            target_p,
            engine=args.engine,
            model_size=args.model,
            language=args.lang,
            allow_local_fallback=fallback_allowed,
        )
        cleaned = TextCleaner.clean(res["full_text"])
        print(f"[✓] 转录完成 (引擎: {res.get('engine', 'unknown')}, 共 {res['total_segments']} 个片段)")
        if args.output:
            out_p = Path(args.output).resolve()
            out_p.parent.mkdir(parents=True, exist_ok=True)
            out_p.write_text(cleaned["cleaned_text"], encoding="utf-8")
            print(f"[✓] 清洗后文本已保存至: {out_p}")
        else:
            print("\n" + "-" * 50)
            print(cleaned["cleaned_text"][:500] + "...")
        return

    # Polymorphically resolve metadata (Local directory course or Bilibili URL/BVID)
    info = _resolve_target_info(args.target, sessdata=args.sessdata)
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

    clean_p_title = "".join([c for c in p_title if c.isalnum() or c in (" ", "-", "_")]).strip()
    audio_file = ws.audio_dir / f"P{target_part:02d}_{clean_p_title}.m4a"

    # Audio check or extraction/download
    if not audio_file.exists() or audio_file.stat().st_size < 10240:
        if info.get("is_local"):
            source_file = matched["filepath"] if info["has_multi_pages"] else info["source_path"]
            print(f"[*] 正在从本地视频提取 64kbps 纯音频...")
            LocalMediaParser.extract_audio(source_file, audio_file)
        else:
            print(f"[*] 音频未缓存，正在下载 P{target_part:02d} 音频...")
            stream_info = AudioFetcher.get_audio_stream_info(
                bvid,
                target_cid,
                sessdata=args.sessdata,
                prefer_quality=getattr(args, "quality", "low"),
            )
            AudioFetcher.download_audio(stream_info["best_stream_url"], str(audio_file), repackage_m4a=True)

    print(f"[*] 开始转录 P{target_part:02d}: {audio_file.name} (策略: {args.engine})...")
    fallback_allowed = True if args.allow_local_fallback is None else args.allow_local_fallback
    res = AudioTranscriber.transcribe(
        audio_file,
        engine=args.engine,
        model_size=args.model,
        language=args.lang,
        allow_local_fallback=fallback_allowed,
    )
    raw_txt_file = ws.subtitles_dir / f"P{target_part:02d}_{clean_p_title}_raw.txt"
    raw_txt_file.write_text(res["full_text"], encoding="utf-8")

    cleaned = TextCleaner.clean(res["full_text"])
    clean_txt_file = ws.subtitles_dir / f"P{target_part:02d}_{clean_p_title}_clean.txt"
    clean_txt_file.write_text(cleaned["cleaned_text"], encoding="utf-8")

    print(f"[✓] 转录与口语清洗完成 (引擎: {res.get('engine', 'unknown')})！")
    print(f"    - 原始转录语料: {raw_txt_file}")
    print(f"    - 清洗文本语料: {clean_txt_file}")


def cmd_pipeline(args):
    info = _resolve_target_info(args.url, sessdata=args.sessdata)
    bvid = info["bvid"]

    ws = TaskWorkspace.create(
        title=info["title"],
        bvid=bvid,
        custom_name=args.task,
        base_dir=args.base_dir,
    )
    print("=" * 65)
    print(f"[*] 全流程处理流水线启动 (Task Workspace: {ws.root_dir.name})")
    print("=" * 65)

    engine_desc = "对话大模型优先 (异常时暂停询问本地模型)" if getattr(args, "engine", "auto") == "auto" else args.engine
    print(f"[*] 转录引擎策略: {engine_desc} | 本地备用规格: whisper-{args.model}")

    if args.all or args.range:
        all_parts = info["parts"]
        if args.range:
            target_indices = _parse_range_string(args.range, len(all_parts))
            selected_parts = [all_parts[i - 1] for i in target_indices]
        else:
            selected_parts = all_parts
    elif info["has_multi_pages"]:
        req_page = args.page if args.page is not None else (info.get("url_page") or 1)
        p_idx = max(1, min(req_page, len(info["parts"])))
        selected_parts = [info["parts"][p_idx - 1]]
    else:
        selected_parts = [{
            "page": 1,
            "title": info["title"],
            "cid": info["cid"],
            "duration": info["duration"],
            "filepath": info.get("source_path", ""),
        }]

    total_episodes = len(selected_parts)
    print(f"[*] 待处理分集总数: {total_episodes}")

    manifest_entries = []
    for idx, p in enumerate(selected_parts, 1):
        p_num = p["page"]
        clean_p_title = "".join([c for c in p["title"] if c.isalnum() or c in (" ", "-", "_")]).strip()
        print(f"\n[{idx:02d}/{total_episodes:02d}] 开始处理 P{p_num:02d}: {p['title']}...")

        # 1. Audio Check or Extraction/Download
        audio_file = ws.audio_dir / f"P{p_num:02d}_{clean_p_title}.m4a"
        if not audio_file.exists() or audio_file.stat().st_size < 10240:
            if info.get("is_local"):
                print(f"    [1/4] 从本地视频提取通用 64kbps 纯音频...")
                LocalMediaParser.extract_audio(p.get("filepath", info.get("source_path")), audio_file)
            else:
                print(f"    [1/4] 下载轻量音频...")
                stream_info = AudioFetcher.get_audio_stream_info(
                    bvid,
                    p["cid"],
                    sessdata=args.sessdata,
                    prefer_quality=getattr(args, "quality", "low"),
                )
                AudioFetcher.download_audio(stream_info["best_stream_url"], str(audio_file), repackage_m4a=True)
        else:
            print(f"    [1/4] 音频已就绪: {audio_file.name} ({round(audio_file.stat().st_size / 1024 / 1024, 2)} MB)")

        # 2. Text Extraction
        transcript_clean_file = ws.subtitles_dir / f"P{p_num:02d}_{clean_p_title}_clean.txt"
        transcript_text = ""
        if transcript_clean_file.exists() and transcript_clean_file.stat().st_size > 50 and not args.force:
            print(f"    [2/4] 转录文本已存在，跳过 ASR: {transcript_clean_file.name}")
            transcript_text = transcript_clean_file.read_text(encoding="utf-8")
        else:
            # Try official subtitles if online
            sub_res = None
            if not info.get("is_local"):
                sub_res = SubtitleFetcher.fetch_best_subtitle(bvid, p["cid"], sessdata=args.sessdata)
            if sub_res:
                print(f"    [2/4] 命中官方/AI字幕，直接免转录抽取 ({sub_res['total_items']} 条)")
                transcript_text = sub_res["full_text"]
            else:
                print(f"    [2/4] 启动语音转录 (策略: {getattr(args, 'engine', 'auto')})...")
                fallback_allowed = True if args.allow_local_fallback is None else args.allow_local_fallback
                asr_res = AudioTranscriber.transcribe(
                    audio_path=audio_file,
                    engine=getattr(args, "engine", "auto"),
                    model_size=args.model,
                    language=args.lang,
                    allow_local_fallback=fallback_allowed,
                )
                transcript_text = asr_res["full_text"]
                engine_used = asr_res.get("engine", f"whisper-{args.model}")
                print(f"    [✓] 语音转录完成 ({engine_used})，共 {asr_res['total_segments']} 个片段")

            # 3. Safe typography normalization (non-destructive). Agent performs semantic rectification.
            cleaned = TextCleaner.clean(transcript_text)
            transcript_text = cleaned["cleaned_text"]
            transcript_clean_file.write_text(transcript_text, encoding="utf-8")

        # 4. Generate Single-Episode Tooling Artifacts (local baseline; Agent upgrades to video-replacement quality)
        article_file = ws.articles_dir / f"P{p_num:02d}_{clean_p_title}_精读文章.md"
        note_file = ws.notes_dir / f"P{p_num:02d}_{clean_p_title}_笔记.md"

        if article_file.exists() and article_file.stat().st_size > 1500 and not args.force:
            print(f"    [4/4] 本地基础文章已存在: {article_file.name} (Agent 可升级为替代视频级)")
        else:
            print(f"    [4/4] 生成本地基础文章 (Agent 将升级为替代视频级)...")
            article_md = DocumentBuilder.render_learning_article(
                title=info["title"],
                part_title=f"P{p_num:02d} {p['title']}",
                content=transcript_text,
            )
            article_file.write_text(article_md, encoding="utf-8")
            print(f"    [✓] 本地基础文章生成完毕: {article_file.name} ({len(article_md)} 字)")

        if not info["has_multi_pages"]:
            note_md = DocumentBuilder.render_note(
                title=info["title"],
                part_title=p["title"],
                content=transcript_text,
                note_type=args.note_type,
                desc=info.get("desc", ""),
            )
            note_file.write_text(note_md, encoding="utf-8")
            print(f"    [✓] 独立单集本地笔记生成完毕: {note_file.name} ({len(note_md)} 字) (Agent 可升级)")

        kernel_path = ws.subtitles_dir / "kernels" / f"P{p_num:02d}_{clean_p_title}_kernel.json"
        KernelExtractor.extract_single_kernel(p_num, p["title"], transcript_text, kernel_path=kernel_path)

        manifest_entries.append({
            "page": p_num,
            "title": p["title"],
            "cid": p["cid"],
            "audio": str(audio_file),
            "transcript": str(transcript_clean_file),
            "article": str(article_file),
            "asr_engine": asr_res.get("engine", f"whisper-{args.model}") if 'asr_res' in locals() else "official-subtitle",
            "doc_engine": "agent-native",
            "status": "success",
        })

    # Phase 2: Native Knowledge-Block Note Aggregation for Multi-P Collections
    if info["has_multi_pages"] and len(selected_parts) > 1:
        print("\n" + "=" * 65)
        print(f"[*] 阶段二：启动课程知识块智能聚合 (根据转录内容动态规划与合成大笔记)")
        print("=" * 65)

        # Collect transcript summaries to ground semantic topic planning in real spoken content
        summaries = {}
        for p in selected_parts:
            p_num = p["page"]
            clean_t = "".join([c for c in p["title"] if c.isalnum() or c in (" ", "-", "_")]).strip()
            clean_f = ws.subtitles_dir / f"P{p_num:02d}_{clean_t}_clean.txt"
            if clean_f.exists():
                summaries[p_num] = clean_f.read_text(encoding="utf-8")[:300]

        plan = SemanticTopicPlanner.plan(
            selected_parts,
            course_title=info["title"],
            ws=ws,
            transcript_summaries=summaries,
        )
        print(f"[✓] 课程知识块大纲规划完成，共聚合出 {len(plan)} 个逻辑知识块:")
        for b in plan:
            eps = b["episodes"]
            p_str = f"P{min(eps):02d}-P{max(eps):02d}" if len(eps) > 1 else f"P{eps[0]:02d}"
            print(f"    - 模块 {b['block_id']:02d} ({p_str}): {b['block_title']}")

        block_results = []
        for b in plan:
            eps = b["episodes"]
            block_parts = [p for p in selected_parts if p["page"] in eps]
            if not block_parts:
                continue
            kernels = KernelExtractor.extract_batch_kernels(block_parts, ws=ws, max_workers=min(len(block_parts), 5))
            res = BlockSynthesizer.synthesize_block(b, kernels, ws=ws)
            block_results.append(res)

        manifest_data = ws.load_manifest()
        manifest_data["knowledge_blocks_plan"] = plan
        manifest_data["knowledge_blocks_results"] = block_results
        ws.save_manifest(manifest_data)

    ws.save_manifest({
        "pipeline_completed": True,
        "processed_episodes": len(manifest_entries),
        "details": manifest_entries,
    })
    print("\n" + "=" * 65)
    print(f"[✓] 全流程流水线执行完毕！全部产物已按任务归档至: {ws.root_dir}")
    print("=" * 65)


def cmd_cluster_notes(args):
    info = _resolve_target_info(args.url, sessdata=args.sessdata)
    bvid = info["bvid"]
    ws = TaskWorkspace.create(title=info["title"], bvid=bvid, custom_name=args.task, base_dir=args.base_dir)

    print("=" * 65)
    print(f"[*] 启动知识块智能聚合重构流水线 (Knowledge-Block Aggregation)")
    print(f"[*] 课程标题: 《{info['title']}》 (共 {len(info['parts'])} 个分集)")
    print(f"[*] 任务工作区: {ws.root_dir}")
    print("=" * 65)

    # 1. Semantic Topic Planner (Pure LLM semantic reasoning, zero regex)
    print(f"\n[Phase 1/3] 启动大模型语义规划器，识别课程全局知识块边界...")
    plan = SemanticTopicPlanner.plan(info["parts"], course_title=info["title"], ws=ws, force=args.force_plan)
    print(f"[✓] 全局拓扑规划完成，共提炼出 {len(plan)} 个逻辑知识块:")
    for b in plan:
        eps = b["episodes"]
        p_str = f"P{min(eps):02d}-P{max(eps):02d}" if len(eps) > 1 else f"P{eps[0]:02d}"
        print(f"    - 模块 {b['block_id']:02d} ({p_str}): {b['block_title']}")

    # Clean old single-episode notes if replace requested
    if args.replace:
        old_single_notes = list(ws.notes_dir.glob("P[0-9][0-9]_*_笔记.md"))
        if old_single_notes:
            print(f"\n[*] 正在清理 {len(old_single_notes)} 篇旧版单集散碎笔记（原地替换为模块大笔记）...")
            for f in old_single_notes:
                try:
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

    # 2. Sub-Agent Kernel Extraction & Main Agent Block Synthesis
    print(f"\n[Phase 2/3 & 3/3] 并发抽取事实知识元并执行概念图谱融合 (待处理 {len(target_blocks)} 个知识块)...")
    block_results = []
    for b in target_blocks:
        b_id = b["block_id"]
        eps = b["episodes"]
        p_str = f"P{min(eps):02d}-P{max(eps):02d}" if len(eps) > 1 else f"P{eps[0]:02d}"
        print(f"\n▶ 正在处理模块 {b_id:02d} ({p_str}): 《{b['block_title']}》...")

        # Subagent parallel extraction
        block_parts = [p for p in info["parts"] if p["page"] in eps]
        kernels = KernelExtractor.extract_batch_kernels(block_parts, ws=ws, max_workers=min(len(block_parts), 5))
        print(f"    [✓] 子智能体已并发抽取 {len(kernels)} 集知识元（已剥离头尾客套与过渡噪声）")

        # Main agent synthesis
        res = BlockSynthesizer.synthesize_block(b, kernels, ws=ws, force=args.force)
        block_results.append(res)

    # Save manifest
    manifest = ws.load_manifest()
    manifest["knowledge_blocks_plan"] = plan
    manifest["knowledge_blocks_results"] = block_results
    ws.save_manifest(manifest)

    print("\n" + "=" * 65)
    print(f"[✓] 知识块聚合重构执行完毕！共生成 {len(block_results)} 篇体系化核心复习大笔记")
    print(f"[✓] 笔记存储目录: {ws.notes_dir}")
    print("=" * 65)


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
    p_audio.add_argument("--base-dir", default="./output", help="Base output directory for task workspaces")
    p_audio.add_argument("--force", action="store_true", help="Force re-download/re-extraction even if audio file already exists")
    p_audio.add_argument("--sessdata", help="Optional SESSDATA cookie", default=None)
    p_audio.add_argument("--url-only", action="store_true", help="Only print stream URL without downloading")
    p_audio.add_argument("--output", default=None, help="Optional explicit output directory override")
    p_audio.add_argument("--chunk-minutes", type=int, default=10, help="Split audio into balanced chunks of ~N minutes (0=disabled)")
    p_audio.add_argument("--json", action="store_true", help="Output in JSON format")

    # subtitle
    p_sub = subparsers.add_parser("subtitle", help="Fetch official or AI subtitle fallback")
    p_sub.add_argument("url", help="Bilibili URL or BV ID")
    p_sub.add_argument("--page", type=int, default=None, help="Page/Part index (auto-detects ?p=X from URL if omitted)")
    p_sub.add_argument("--task", default=None, help="Custom task workspace folder name")
    p_sub.add_argument("--base-dir", default="./output", help="Base output directory for task workspaces")
    p_sub.add_argument("--sessdata", help="Optional SESSDATA cookie", default=None)
    p_sub.add_argument("--output", help="Save subtitle to explicit file or directory", default=None)

    # clean
    p_clean = subparsers.add_parser("clean", help="Clean transcript text")
    p_clean.add_argument("file", help="Raw transcript file path")
    p_clean.add_argument("--output", help="Cleaned output file path", default=None)

    # prompt
    p_prompt = subparsers.add_parser("prompt", help="Render Agent prompt templates")
    p_prompt.add_argument("url", help="Bilibili URL/BV ID or local media path")
    p_prompt.add_argument("--page", type=int, default=None, help="Page index (auto-detects ?p=X from URL if omitted)")
    p_prompt.add_argument("--transcript-file", help="Path to transcript file")
    p_prompt.add_argument("--type", choices=["note", "article", "rectify", "both"], default="both")
    p_prompt.add_argument("--note-type", choices=["auto", "study", "news", "general"], default="auto", help="Adaptive note category")
    p_prompt.add_argument("--sessdata", help="Optional SESSDATA cookie", default=None)

    # note
    p_note = subparsers.add_parser("note", help="Generate and save sober GitHub-styled note directly")
    p_note.add_argument("url", help="Bilibili URL/BV ID or local media path")
    p_note.add_argument("--page", type=int, default=None, help="Page index (auto-detects ?p=X from URL if omitted)")
    p_note.add_argument("--task", default=None, help="Custom task workspace folder name")
    p_note.add_argument("--base-dir", default="./output", help="Base output directory for task workspaces")
    p_note.add_argument("--transcript-file", help="Path to transcript file", default=None)
    p_note.add_argument("--note-type", choices=["auto", "study", "news", "general"], default="auto", help="Adaptive note category")
    p_note.add_argument("--output", default=None, help="Optional explicit output directory override")
    p_note.add_argument("--sessdata", help="Optional SESSDATA cookie", default=None)

    # transcribe
    p_tr = subparsers.add_parser("transcribe", help="Transcribe audio or video to clean text")
    p_tr.add_argument("target", help="Bilibili URL/BVID, local audio file, or local video file")
    p_tr.add_argument("--page", type=int, default=None, help="Page index for Bilibili video or local course (auto-detects ?p=X from URL if omitted)")
    p_tr.add_argument("--engine", choices=["auto", "agent", "local"], default="auto", help="Transcription engine: auto(prioritize dialogue model, halt & prompt on lack of audio), agent(dialogue model only), local(whisper only)")
    p_tr.add_argument("--allow-local-fallback", action="store_true", default=None, help="Directly allow local whisper fallback if dialogue model cannot read audio without interactive prompt")
    p_tr.add_argument("--model", default="base", choices=["tiny", "base", "small", "medium"], help="Local whisper model size (used when falling back to local)")
    p_tr.add_argument("--lang", default="zh", help="Language code (defaults to zh)")
    p_tr.add_argument("--task", default=None, help="Custom task workspace folder name")
    p_tr.add_argument("--base-dir", default="./output", help="Base output directory for task workspaces")
    p_tr.add_argument("--output", default=None, help="Optional custom output path for cleaned text")
    p_tr.add_argument("--sessdata", help="Optional SESSDATA cookie", default=None)

    # pipeline
    p_pipe = subparsers.add_parser("pipeline", help="Execute complete automated pipeline (Audio -> ASR -> Notes & Articles)")
    p_pipe.add_argument("url", help="Bilibili URL/BV ID, local video file, or local course directory")
    p_pipe.add_argument("--page", type=int, default=None, help="Page/Part index (auto-detects ?p=X from URL if omitted)")
    p_pipe.add_argument("--all", action="store_true", help="Process all episodes in multi-P collection or local course directory")
    p_pipe.add_argument("--range", default=None, help="Episode range to process (e.g. 1-10, 1,3,5)")
    p_pipe.add_argument("--engine", choices=["auto", "agent", "local"], default="auto", help="Transcription engine: auto(prioritize dialogue model, halt & prompt on lack of audio), agent(dialogue model only), local(whisper only)")
    p_pipe.add_argument("--allow-local-fallback", action="store_true", default=None, help="Directly allow local whisper fallback if dialogue model cannot read audio without interactive prompt")
    p_pipe.add_argument("--quality", choices=["low", "medium", "high"], default="low", help="Audio quality (low=64k speech default, medium=132k, high=192k)")
    p_pipe.add_argument("--model", default="base", choices=["tiny", "base", "small", "medium"], help="Local whisper model size (used when falling back to local)")
    p_pipe.add_argument("--lang", default="zh", help="Language code (defaults to zh)")
    p_pipe.add_argument("--note-type", choices=["auto", "study", "news", "general"], default="auto", help="Note category")
    p_pipe.add_argument("--task", default=None, help="Custom task workspace folder name")
    p_pipe.add_argument("--base-dir", default="./output", help="Base output directory for task workspaces")
    p_pipe.add_argument("--force", action="store_true", help="Force re-transcribing and re-generating even if exists")
    p_pipe.add_argument("--sessdata", help="Optional SESSDATA cookie", default=None)

    # cluster-notes
    p_cl = subparsers.add_parser("cluster-notes", help="Cluster multi-P course into coherent knowledge block notes")
    p_cl.add_argument("url", help="Bilibili URL or BV ID")
    p_cl.add_argument("--block-id", type=int, default=None, help="Process specific block ID only")
    p_cl.add_argument("--start-block", type=int, default=None, help="Start block ID")
    p_cl.add_argument("--end-block", type=int, default=None, help="End block ID")
    p_cl.add_argument("--task", default=None, help="Custom task workspace folder name")
    p_cl.add_argument("--base-dir", default="./output", help="Base output directory for task workspaces")
    p_cl.add_argument("--replace", action="store_true", default=False, help="Replace old single-episode notes in notes/ directory")
    p_cl.add_argument("--force", action="store_true", help="Force re-synthesizing even if block note exists")
    p_cl.add_argument("--force-plan", action="store_true", help="Force re-generating semantic topic plan")
    p_cl.add_argument("--sessdata", help="Optional SESSDATA cookie", default=None)

    args = parser.parse_args()
    if not args.subcommand:
        parser.print_help()
        sys.exit(1)

    dispatch = {
        "parse": cmd_parse,
        "audio": cmd_audio,
        "subtitle": cmd_subtitle,
        "clean": cmd_clean,
        "prompt": cmd_prompt,
        "note": cmd_note,
        "transcribe": cmd_transcribe,
        "pipeline": cmd_pipeline,
        "cluster-notes": cmd_cluster_notes,
    }
    dispatch[args.subcommand](args)


if __name__ == "__main__":
    main()
