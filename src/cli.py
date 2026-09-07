#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Command-Line Interface for Bilibili Audio & Knowledge Extraction.

Commands:
  parse     - Parse URL/BVID, classify video type, and inspect sub-videos
  audio     - Fetch audio stream URL, download m4a, and optionally chunk via ffmpeg
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
from src.core.workspace import TaskWorkspace
from src.core.transcriber import AudioTranscriber
from src.core.kernel_extractor import KernelExtractor
from src.generator.cleaner import TextCleaner
from src.generator.doc_builder import DocumentBuilder
from src.generator.topic_planner import SemanticTopicPlanner
from src.generator.block_synthesizer import BlockSynthesizer


# 中文注释：状态文件记录上次 412/熔断，无则 info 显示“无记录”
_STATUS_FILE = PROJECT_ROOT / "output" / ".cli_status.json"
# 中文注释：manifest 中需要相对路径化的路径键集合
_PATH_KEYS = {"audio", "transcript", "task_prompt", "article", "audio_file", "filepath", "source_path"}


def _to_relative_str(val):
    """中文注释：绝对路径转仓库相对路径，非路径原样返回。"""
    if not isinstance(val, str) or not val:
        return val
    try:
        p = Path(val)
        if not p.is_absolute():
            return val
        try:
            return p.relative_to(PROJECT_ROOT).as_posix()
        except Exception:
            pass
        try:
            return p.relative_to(Path.cwd()).as_posix()
        except Exception:
            return val
    except Exception:
        return val


def _to_absolute_str(val):
    """中文注释：仓库相对路径转回绝对路径，绝对路径原样返回。"""
    if not isinstance(val, str) or not val:
        return val
    try:
        p = Path(val)
        if p.is_absolute():
            return str(p)
        # 中文注释：相对路径视为仓库相对，拼回绝对路径
        return str((PROJECT_ROOT / val).resolve())
    except Exception:
        return val


def _relativize_obj(obj):
    """中文注释：递归将 manifest 内路径键转为相对路径，保持按 page 合并兼容。"""
    if isinstance(obj, dict):
        return {k: (_to_relative_str(v) if k in _PATH_KEYS else _relativize_obj(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_relativize_obj(x) for x in obj]
    return obj


def _absolutize_obj(obj):
    """中文注释：递归将 manifest 内路径键转回绝对路径供使用处读取。"""
    if isinstance(obj, dict):
        return {k: (_to_absolute_str(v) if k in _PATH_KEYS else _absolutize_obj(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_absolutize_obj(x) for x in obj]
    return obj


def _save_manifest_rel(ws, data):
    """中文注释：保存前统一相对路径化。"""
    ws.save_manifest(_relativize_obj(data))


def _load_manifest_abs(ws):
    """中文注释：加载后统一转回绝对路径。"""
    return _absolutize_obj(ws.load_manifest())


def _is_412(err):
    """中文注释：判断是否为 412 风控拦截。"""
    return "412" in str(err)


def _record_412_status(err):
    """中文注释：记录 412/熔断状态到状态文件供 info 读取。"""
    try:
        import time as _time
        _STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
        _STATUS_FILE.write_text(
            json.dumps({"last_412": _time.strftime("%Y-%m-%d %H:%M:%S"),
                        "error": str(err)[:500]}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass


def _format_412(err, resume_hint=None):
    """中文注释：412 三要素文案：定性+可复制动作+预期。"""
    hint = resume_hint or 'python src/cli.py pipeline "<链接>" --all --sessdata YOUR_SESSDATA'
    return (
        f"[412 风控拦截] {err}\n"
        "①定性：B 站风控拦截（请求过频/缺登录态），非视频删除。\n"
        "②可复制动作：浏览器登录 bilibili.com → F12 → 应用/存储 → Cookie → 复制 SESSDATA，"
        f"然后运行：python src/cli.py pipeline \"<链接>\" --all --sessdata YOUR_SESSDATA\n"
        f"③预期：等待 30-60 分钟后再试；跑 python src/cli.py info 验证状态；断点续跑：{hint}"
    )


def _enrich_network_error(err, resume_hint=None):
    """中文注释：区分 412 与普通网络错误，412 走三要素文案并落盘状态。"""
    if _is_412(err):
        _record_412_status(err)
        return _format_412(err, resume_hint)
    return f"[网络/接口异常] {err}（非 412：建议检查网络后重试；频繁失败可补 --sessdata 后重跑）"


def _get_audio_stream(bvid, cid, sessdata=None, prefer_quality="low", resume_hint=None):
    """中文注释：音频流获取统一入口，412  enriched 后抛出。"""
    try:
        return AudioFetcher.get_audio_stream_info(bvid, cid, sessdata=sessdata, prefer_quality=prefer_quality)
    except Exception as err:
        raise RuntimeError(_enrich_network_error(err, resume_hint)) from err


def _export_transcribe_task(ws, page_num, clean_title, audio_file, title="", cid=0):
    """Export Agent-native TRANSCRIBE_TASK file. No env vars, no network calls."""
    import re as _re
    from src.generator.prompt_templates import AUDIO_TRANSCRIPTION_PROMPT
    # Avoid double prefix when the stem already carries one (e.g. local-file direct transcribe).
    prefix = "" if _re.match(r"^P\d{2}_", clean_title) else f"P{page_num:02d}_"
    task_file = ws.articles_dir / f"{prefix}{clean_title}_TRANSCRIBE_TASK.md"
    task_file.parent.mkdir(parents=True, exist_ok=True)
    content = (
        f"# P{page_num:02d} {clean_title} 转录任务书（TRANSCRIBE_TASK）\n\n"
        f"> 状态：need-agent-transcribe | 请宿主 Agent 原生转录落盘\n\n"
        f"## 输入\n\n- 音频：{audio_file}\n- 标题：{title}\n- CID：{cid}\n\n"
        f"## 分片清单（占位）\n\n- [ ] P{page_num:02d} 全片（{audio_file}，00:00 起）待 Agent 逐段转录\n"
        f"- [ ] 若音频过长，Agent 自行按自然语义切片并逐片落盘后再合并\n\n"
        f"## 转录提示词（引用 src/generator/prompt_templates.py AUDIO_TRANSCRIPTION_PROMPT）\n\n"
        f"{AUDIO_TRANSCRIPTION_PROMPT}\n"
    )
    task_file.write_text(content, encoding="utf-8")
    return task_file


def _resolve_target_info(target: str, sessdata: Optional[str] = None) -> Dict[str, Any]:
    """中文注释：多态解析本地媒体或 B 站元数据，412 走三要素文案。"""
    if LocalMediaParser.is_local_media(target):
        return LocalMediaParser.parse(target)
    try:
        return BilibiliParser.parse_video(target, sessdata=sessdata)
    except Exception as err:
        raise RuntimeError(_enrich_network_error(err)) from err


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
                    # 中文注释：统一走 412 富化入口
                    stream_info = _get_audio_stream(
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
        # 中文注释：统一走 412 富化入口
        stream_info = _get_audio_stream(
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
        # 中文注释：字幕已移除；无语料时指引跑 pipeline 转录
        print("[*] 未提供转录文件，字幕直取已移除，统一走转录。")
        print("[*] 请先跑 pipeline 生成转录语料后再合成笔记。")
        content = f"视频简介: {info.get('desc', '')}\n\n该视频时长 {info.get('duration', 0)} 秒，建议跑 pipeline 转录后再生成完整笔记。"

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
    engine = getattr(args, "engine", "auto")
    fallback_allowed = bool(getattr(args, "allow_local_fallback", False))
    # Check if target is a single local media file
    target_p = Path(args.target).resolve()
    if target_p.exists() and target_p.is_file():
        print(f"[*] 直接转录本地媒体: {target_p.name} (引擎策略: {engine})...")
        if engine in ("agent", "auto") and not (engine == "auto" and fallback_allowed):
            if engine == "auto" and fallback_allowed:
                pass
            else:
                from src.generator.prompt_templates import AUDIO_TRANSCRIPTION_PROMPT  # noqa: F401 确认常量名存在
                ws0 = TaskWorkspace.create(title=target_p.stem, bvid="", custom_name=args.task, base_dir=args.base_dir)
                tf = _export_transcribe_task(ws0, 1, target_p.stem, target_p, title=target_p.stem)
                print(f"[✓] 已导出转录任务书待 Agent 原生转录: {tf} (status=need-agent-transcribe)")
                return
        res = AudioTranscriber.transcribe(
            target_p,
            model_size=args.model,
            language=args.lang,
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
            # 中文注释：统一走 412 富化入口
            stream_info = _get_audio_stream(
                bvid,
                target_cid,
                sessdata=args.sessdata,
                prefer_quality=getattr(args, "quality", "low"),
            )
            AudioFetcher.download_audio(stream_info["best_stream_url"], str(audio_file), repackage_m4a=True)

    print(f"[*] 开始转录 P{target_part:02d}: {audio_file.name} (策略: {engine})...")
    if engine == "agent":
        tf = _export_transcribe_task(ws, target_part, clean_p_title, audio_file, title=info["title"], cid=target_cid)
        print(f"[✓] 已导出转录任务书待 Agent 原生转录: {tf} (status=need-agent-transcribe)")
        return
    if engine == "auto":
        # 中文注释：字幕直取已移除；无兜底授权导出任务书，有兜底走 whisper
        if not fallback_allowed:
            tf = _export_transcribe_task(ws, target_part, clean_p_title, audio_file, title=info["title"], cid=target_cid)
            print(f"[✓] 已导出转录任务书待 Agent 原生转录: {tf} (status=need-agent-transcribe)")
            return
    res = AudioTranscriber.transcribe(
        audio_file,
        model_size=args.model,
        language=args.lang,
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

    # 中文注释：pipeline 内 --allow-local-fallback 失效，显式传也只告警一次并忽略
    if bool(getattr(args, "allow_local_fallback", False)):
        print("[warn] --allow-local-fallback 在 pipeline 内已失效，已忽略（对话模型优先；如需本地转录请显式 --engine local）")
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

    # 断点续派过滤：manifest 中 status==success 的 page 跳过（--force 时不过滤）
    if not getattr(args, "force", False):
        try:
            # 中文注释：加载时转回绝对路径使用
            _done_pages = {d.get("page") for d in _load_manifest_abs(ws).get("details", []) if d.get("status") == "success"}
        except Exception:
            _done_pages = set()
        if _done_pages:
            kept = []
            for p in selected_parts:
                if p.get("page") in _done_pages:
                    print(f"[skip] P{p.get('page'):02d} {p.get('title')} 已完成，跳过")
                else:
                    kept.append(p)
            selected_parts = kept
            total_episodes = len(selected_parts)
            print(f"[*] 断点续派后待处理: {total_episodes}")
    else:
        print("[*] --force 已指定，不过滤已完成分集")

    from concurrent.futures import ThreadPoolExecutor
    import time as _time_mod

    prefetch_workers = max(1, int(getattr(args, "prefetch_workers", 12) or 1))
    tx_workers = max(1, int(getattr(args, "transcribe_episodes", 2) or 1))
    print(f"[*] 并发配置: 音频预取 {prefetch_workers} 线程 | 分集转录并行 {tx_workers} 集（块级并发另计）")

    def _audio_paths(p):
        clean_p_title = "".join([c for c in p["title"] if c.isalnum() or c in (" ", "-", "_")]).strip()
        return ws.audio_dir / f"P{p['page']:02d}_{clean_p_title}.m4a", clean_p_title

    def _classify_audio_error(err):
        # 中文注释：失败分类：412 风控/缺登录态/网络超时/其他
        msg = str(err)
        if "412" in msg:
            return "412风控拦截"
        low = msg.lower()
        if any(k in msg for k in ("SESSDATA", "sessdata", "401", "403", "登录", "Cookie", "cookie")):
            return "缺登录态/权限"
        if any(k in low for k in ("timeout", "timed out", "connection", "network", "dns", "reset", "超时", "网络", "连接")):
            return "网络超时"
        return "其他下载异常"

    def _ensure_audio_once(p):
        # 中文注释：单次音频收齐尝试，命中缓存直接返回
        audio_file, _ = _audio_paths(p)
        if audio_file.exists() and audio_file.stat().st_size >= 10240 and not getattr(args, "force", False):
            return audio_file
        if info.get("is_local"):
            print(f"    [prefetch] P{p['page']:02d} 本地提取音频...")
            LocalMediaParser.extract_audio(p.get("filepath", info.get("source_path")), audio_file)
        else:
            print(f"    [prefetch] P{p['page']:02d} 下载轻量音频...")
            # 中文注释：元数据 API 保持现有令牌桶，不动 fetcher；此处统一走 412 富化入口
            stream_info = _get_audio_stream(
                bvid, p["cid"], sessdata=args.sessdata, prefer_quality=getattr(args, "quality", "low"),
            )
            AudioFetcher.download_audio(stream_info["best_stream_url"], str(audio_file), repackage_m4a=True)
        print(f"    [prefetch] P{p['page']:02d} 音频就绪: {audio_file.name}")
        return audio_file

    def _ensure_audio_with_retry(p):
        # 中文注释：单集下载失败退避重试 3 次（共 4 次尝试），退避 1/2/4 秒
        last_err = None
        for attempt in range(4):
            try:
                return _ensure_audio_once(p)
            except Exception as err:
                last_err = err
                if attempt < 3:
                    print(f"    [retry] P{p['page']:02d} 第{attempt + 1}次失败，退避重试 ({_classify_audio_error(err)}): {str(err)[:120]}")
                    try:
                        _time_mod.sleep(2 ** attempt)
                    except Exception:
                        pass
        raise last_err

    # 中文注释：阶段一“音频收齐”：ThreadPoolExecutor 并发下载全部选中集音频
    print("=" * 65)
    print("[*] 阶段一：音频收齐（全部选中集并发下载/提取）")
    print("=" * 65)
    audio_failed = []
    audio_ready = {}
    with ThreadPoolExecutor(max_workers=prefetch_workers) as prefetch_pool:
        fut_map = {p["page"]: prefetch_pool.submit(_ensure_audio_with_retry, p) for p in selected_parts}
        for p in selected_parts:
            try:
                audio_ready[p["page"]] = fut_map[p["page"]].result()
            except Exception as err:
                audio_failed.append({
                    "page": p["page"], "title": p["title"], "cid": p["cid"],
                    "error": str(err), "category": _classify_audio_error(err), "status": "failed",
                })
    # 中文注释：阶段一结束后写检查点 parts.json + manifest
    try:
        _clean_parts = [{k: v for k, v in p.items() if not k.startswith("_")} for p in selected_parts]
        ws.save_parts(_clean_parts)
    except Exception:
        pass
    _save_manifest_rel(ws, {
        "audio_stage": {"total": len(selected_parts), "ready": len(audio_ready), "failed": len(audio_failed)},
        "audio_failed_episodes": [{k: v for k, v in d.items()} for d in audio_failed],
    })
    skip_failed_opt = bool(getattr(args, "skip_failed", False))
    skipped_entries = []
    if audio_failed:
        if skip_failed_opt:
            # 中文注释：显式 opt-in 豁免：记入 manifest 跳过名单，不进转录
            skipped_entries = list(audio_failed)
            audio_failed = []
            print(f"[*] --skip-failed 已指定，豁免 {len(skipped_entries)} 集（不进转录）")
            _save_manifest_rel(ws, {
                "skipped_episodes": skipped_entries,
                "skipped_pages": [d.get("page") for d in skipped_entries],
            })
        else:
            # 中文注释：任一集最终失败则严格终止报告并 sys.exit 非零
            print("\n" + "=" * 65, file=sys.stderr)
            print("[✗] 阶段一终止：音频收齐失败（硬切分门禁，未进入转录）", file=sys.stderr)
            print(f"失败集清单（共 {len(audio_failed)} 集）：", file=sys.stderr)
            for f_ep in audio_failed:
                print(f"    - P{f_ep['page']:02d} {f_ep['title']} [{f_ep.get('category')}]：{str(f_ep['error'])[:160]}", file=sys.stderr)
            print("失败分类统计：", file=sys.stderr)
            _cats = {}
            for f_ep in audio_failed:
                _cats[f_ep.get("category", "其他下载异常")] = _cats.get(f_ep.get("category", "其他下载异常"), 0) + 1
            for _c, _n in _cats.items():
                print(f"    - {_c} × {_n}", file=sys.stderr)
            print("三选项：①删集重跑（缩小 --range 剔除失败集后重跑）②补--sessdata（浏览器复制 SESSDATA 后重跑）③加--skip-failed跳过（豁免失败集，仅转录成功集）", file=sys.stderr)
            print("=" * 65, file=sys.stderr)
            sys.exit(2)
    # 中文注释：阶段二仅阶段一全绿（或失败集全部被豁免）才启动
    _skip_pages = {d.get("page") for d in skipped_entries}
    effective_parts = [p for p in selected_parts if p.get("page") not in _skip_pages]
    # 中文注释：阶段二入口校验音频 100% 就绪，否则拒绝并指去向
    _missing = []
    for p in effective_parts:
        _af, _ = _audio_paths(p)
        if not (_af.exists() and _af.stat().st_size >= 10240):
            _missing.append(p)
    if _missing:
        print("\n" + "=" * 65, file=sys.stderr)
        print("[✗] 阶段二拒绝启动：音频未 100% 就绪（请回阶段一排查音频目录）", file=sys.stderr)
        for _m in _missing:
            _af, _ = _audio_paths(_m)
            print(f"    - P{_m['page']:02d} {_m['title']} 缺失/过小：{_af}", file=sys.stderr)
        print(f"去向：检查 {ws.audio_dir} 与 parts.json，补齐后重跑 pipeline（断点续派自动跳过已完成集）", file=sys.stderr)
        print("=" * 65, file=sys.stderr)
        sys.exit(2)
    print("=" * 65)
    print(f"[*] 阶段二：批量转录（共 {len(effective_parts)} 集，并发 {tx_workers} 集）")
    print("=" * 65)

    def _extract_text(p):
        p_num = p["page"]
        audio_file, clean_p_title = _audio_paths(p)
        transcript_clean_file = ws.subtitles_dir / f"P{p_num:02d}_{clean_p_title}_clean.txt"
        if transcript_clean_file.exists() and transcript_clean_file.stat().st_size > 50 and not args.force:
            print(f"    [P{p_num:02d}] 转录文本已存在，跳过 ASR: {transcript_clean_file.name}")
            return transcript_clean_file.read_text(encoding="utf-8"), "cached"
        engine = getattr(args, "engine", "auto")
        # 中文注释：pipeline 内删除自动 whisper 兜底；--engine local 显式指定才走 whisper
        if engine == "local":
            print(f"    [P{p_num:02d}] 本地引擎转录 (whisper-{args.model})...")
            asr_res = AudioTranscriber.transcribe(audio_path=audio_file, model_size=args.model, language=args.lang)
            raw_text = asr_res["full_text"]
            engine_used = asr_res.get("engine", f"whisper-{args.model}")
            print(f"    [P{p_num:02d}] [✓] 本地转录完成 ({engine_used})，共 {asr_res['total_segments']} 个片段")
            cleaned = TextCleaner.clean(raw_text)["cleaned_text"]
            transcript_clean_file.parent.mkdir(parents=True, exist_ok=True)
            transcript_clean_file.write_text(cleaned, encoding="utf-8")
            return cleaned, engine_used
        # 中文注释：engine=auto/agent 只走对话模型原生，导出 TRANSCRIBE_TASK
        try:
            tf = _export_transcribe_task(ws, p_num, clean_p_title, audio_file, title=info["title"], cid=p["cid"])
        except Exception as err:
            # 中文注释：对话模型不可用则终止任务 + 结构化报告，非零退出
            print("\n" + "=" * 65, file=sys.stderr)
            print(f"[✗] 对话模型不可用，终止任务：P{p_num:02d} TRANSCRIBE_TASK 导出失败：{err}", file=sys.stderr)
            print("原因：对话模型原生转录通道不可用（任务书落盘失败）", file=sys.stderr)
            print("①排障重跑：检查 articles 目录写权限与磁盘空间后重跑 pipeline", file=sys.stderr)
            print("②显式--engine local：改用本地 whisper 转录（离线兜底）", file=sys.stderr)
            print("③中止：放弃本趟转录，已收齐音频保留在 audio/ 可稍后重跑", file=sys.stderr)
            print("=" * 65, file=sys.stderr)
            sys.exit(3)
        print(f"    [P{p_num:02d}] 已导出 TRANSCRIBE_TASK 待 Agent 原生转录: {tf.name} (status=need-agent-transcribe)")
        return "", "need-agent-transcribe"

    manifest_entries = []
    failed_entries = []
    with ThreadPoolExecutor(max_workers=tx_workers) as tx_pool:
        for p in effective_parts:
            p["_text_future"] = tx_pool.submit(_extract_text, p)

        for idx, p in enumerate(effective_parts, 1):
            p_num = p["page"]
            audio_file, clean_p_title = _audio_paths(p)
            print(f"\n[{idx:02d}/{len(effective_parts):02d}] 汇总落盘 P{p_num:02d}: {p['title']}...")
            try:
                transcript_text, engine_used = p["_text_future"].result()
            except SystemExit:
                raise
            except Exception as err:
                print(f"    [✗] P{p_num:02d} 处理失败: {err}", file=sys.stderr)
                failed_entries.append({
                    "page": p_num, "title": p["title"], "cid": p["cid"],
                    "error": str(err), "status": "failed",
                })
                continue

            transcript_clean_file = ws.subtitles_dir / f"P{p_num:02d}_{clean_p_title}_clean.txt"

            if engine_used == "need-agent-transcribe":
                tr_task = ws.articles_dir / f"P{p_num:02d}_{clean_p_title}_TRANSCRIBE_TASK.md"
                if not tr_task.exists():
                    tr_task = _export_transcribe_task(ws, p_num, clean_p_title, audio_file, title=info["title"], cid=p["cid"])
                print(f"    [agent] P{p_num:02d} 待 Agent 原生转录: {tr_task.name}")
                manifest_entries.append({
                    "page": p_num, "title": p["title"], "cid": p["cid"],
                    "audio": str(audio_file), "transcript": str(transcript_clean_file),
                    "task_prompt": str(tr_task), "article": "",
                    "asr_engine": engine_used, "doc_engine": "agent-native",
                    "status": "need-agent-transcribe",
                })
                continue

            # Export standard Task Prompt for Agent to execute natively
            prompts = DocumentBuilder.render_prompts(
                title=info["title"],
                part_title=f"P{p_num:02d} {p['title']}",
                content=transcript_text,
                desc=info.get("desc", ""),
            )
            task_file = ws.articles_dir / f"P{p_num:02d}_{clean_p_title}_TASK.md"
            task_file.write_text(prompts["article_prompt"], encoding="utf-8")

            # Single-Episode Tooling Artifacts (local baseline; Agent upgrades to video-replacement quality)
            article_file = ws.articles_dir / f"P{p_num:02d}_{clean_p_title}_精读文章.md"
            note_file = ws.notes_dir / f"P{p_num:02d}_{clean_p_title}_笔记.md"

            if article_file.exists() and article_file.stat().st_size > 1500 and not args.force:
                print(f"    [artifact] 本地基础文章已存在: {article_file.name} (Agent 可升级为替代视频级)")
            else:
                article_md = DocumentBuilder.render_learning_article(
                    title=info["title"],
                    part_title=f"P{p_num:02d} {p['title']}",
                    content=transcript_text,
                )
                article_file.write_text(article_md, encoding="utf-8")
                print(f"    [artifact] 本地基础文章生成完毕: {article_file.name} ({len(article_md)} 字)")

            if not info["has_multi_pages"]:
                note_md = DocumentBuilder.render_note(
                    title=info["title"],
                    part_title=p["title"],
                    content=transcript_text,
                    note_type=args.note_type,
                    desc=info.get("desc", ""),
                )
                note_file.write_text(note_md, encoding="utf-8")
                print(f"    [artifact] 独立单集本地笔记生成完毕: {note_file.name} ({len(note_md)} 字) (Agent 可升级)")

            kernel_path = ws.subtitles_dir / "kernels" / f"P{p_num:02d}_{clean_p_title}_kernel.json"
            KernelExtractor.extract_single_kernel(p_num, p["title"], transcript_text, kernel_path=kernel_path)

            manifest_entries.append({
                "page": p_num,
                "title": p["title"],
                "cid": p["cid"],
                "audio": str(audio_file),
                "transcript": str(transcript_clean_file),
                "task_prompt": str(task_file),
                "article": str(article_file),
                "asr_engine": engine_used,
                "doc_engine": "agent-native",
                "status": "success",
            })

    if failed_entries:
        print("\n" + "=" * 65)
        print(f"[!] 本趟共 {len(failed_entries)} 集处理失败（下载/转录/质检），已显式记入 manifest，重跑 pipeline --all 自动补齐：")
        for f_ep in failed_entries:
            print(f"    - P{f_ep['page']:02d} {f_ep['title']}: {str(f_ep['error'])[:160]}")
        print("=" * 65)

    # 中文注释：知识块聚合仅基于有效集（含转录成功与待 Agent 转录），豁免集不参与
    # Phase 3: Native Knowledge-Block Note Aggregation for Multi-P Collections
    if info["has_multi_pages"] and len(effective_parts) > 1:
        print("\n" + "=" * 65)
        print("[*] 阶段三：启动课程知识块智能聚合 (根据转录内容动态规划与合成大笔记)")
        print("=" * 65)

        # Collect transcript summaries to ground semantic topic planning in real spoken content
        summaries = {}
        for p in effective_parts:
            p_num = p["page"]
            clean_t = "".join([c for c in p["title"] if c.isalnum() or c in (" ", "-", "_")]).strip()
            clean_f = ws.subtitles_dir / f"P{p_num:02d}_{clean_t}_clean.txt"
            if clean_f.exists():
                summaries[p_num] = clean_f.read_text(encoding="utf-8")[:300]

        plan = SemanticTopicPlanner.plan(
            effective_parts,
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
            block_parts = [p for p in effective_parts if p["page"] in eps]
            if not block_parts:
                continue
            kernels = KernelExtractor.extract_batch_kernels(block_parts, ws=ws, max_workers=min(len(block_parts), 5))
            res = BlockSynthesizer.synthesize_block(b, kernels, ws=ws)

            # Export Synthesis Task Prompt for Agent to execute natively
            clean_b_title = "".join(c for c in b["block_title"] if c.isalnum() or c in (" ", "-", "_")).strip()
            synthesis_prompt = BlockSynthesizer.build_synthesis_prompt(b, kernels)
            b_task_file = ws.notes_dir / f"模块{b['block_id']:02d}_{clean_b_title}_TASK.md"
            b_task_file.write_text(synthesis_prompt, encoding="utf-8")
            res["task_prompt"] = str(b_task_file)

            block_results.append(res)

        # 中文注释：加载转绝对、使用后保存转相对
        manifest_data = _load_manifest_abs(ws)
        manifest_data["knowledge_blocks_plan"] = plan
        manifest_data["knowledge_blocks_results"] = block_results
        _save_manifest_rel(ws, manifest_data)

    _existing = _load_manifest_abs(ws)
    _merged = {d.get("page"): d for d in _existing.get("details", []) if isinstance(d, dict)}
    for d in manifest_entries:
        _merged[d.get("page")] = d
    _failed_merged = {d.get("page"): d for d in _existing.get("failed_episodes", []) if isinstance(d, dict)}
    for d in failed_entries:
        _failed_merged[d.get("page")] = d
    # 中文注释：按 page 合并后相对路径化保存，豁免集记入跳过名单
    _save_manifest_rel(ws, {
        "pipeline_completed": True,
        "processed_episodes": sum(1 for d in _merged.values() if d.get("status") == "success"),
        "details": [_merged[k] for k in sorted(_merged)],
        "failed_episodes": [_failed_merged[k] for k in sorted(_failed_merged)],
        "skipped_episodes": skipped_entries,
        "skipped_pages": [d.get("page") for d in skipped_entries],
    })
    print("\n" + "=" * 65)
    print(f"[✓] 工具层流水线执行完毕！语料与任务书已归档至: {ws.root_dir}")
    print("【★ 宿主 Agent 接管指南】：")
    print(f"  1. 单集精读文章任务书: {ws.articles_dir}/*_TASK.md")
    if info["has_multi_pages"] and len(effective_parts) > 1:
        print(f"  2. 知识块聚合笔记任务书: {ws.notes_dir}/*_TASK.md")
    print("  3. 请主程序以 5 个并发通道（Task 子代理或并行会话）直接领跑任务书，执行真正的认知写作！")
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

    # 中文注释：加载转绝对、保存转相对
    manifest = _load_manifest_abs(ws)
    manifest["knowledge_blocks_plan"] = plan
    manifest["knowledge_blocks_results"] = block_results
    _save_manifest_rel(ws, manifest)

    print("\n" + "=" * 65)
    print(f"[✓] 知识块聚合重构执行完毕！共生成 {len(block_results)} 篇体系化核心复习大笔记")
    print(f"[✓] 笔记存储目录: {ws.notes_dir}")
    print("=" * 65)


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
    try:
        import faster_whisper
        print(f"• faster-whisper : 已就绪 (v{faster_whisper.__version__}) - 100% 离线本地转录 (无需任何 Key)")
    except ImportError:
        print("• faster-whisper : 未安装 (可运行 pip install faster-whisper)")
    print("• 架构模式      : 宿主 Agent 原生派发模式（零环境变量、零网络代理绑定）")
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
    # 中文注释：sessdata 只显示有/无，脱敏不打印值
    sess = getattr(args, "sessdata", None)
    print(f"• SESSDATA：{'有（已传入，脱敏不显示）' if sess else '无（未传入 --sessdata）'}")
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
    print("1. 物理层跑批: python src/cli.py pipeline \"<链接>\" --all")
    print("2. 语料与任务书自动生成于 output/<任务名>/")
    print("   - articles/PXX_*_TASK.md: 单集精读文章提示词")
    print("   - notes/模块XX_*_TASK.md: 知识块聚合复习笔记提示词")
    print("3. 宿主 Agent 主程序以 5 个并发通道（Task子代理或并行生成）读取任务书，直接撰写落盘！")
    print("=" * 65)
    print("【可复制的断点续跑命令示例】：")
    print('python src/cli.py pipeline "<链接>" --all --sessdata YOUR_SESSDATA')
    print('python src/cli.py pipeline "<链接>" --range 1-10 --sessdata YOUR_SESSDATA')
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
    p_audio.add_argument("--base-dir", default="./output", help="Base output directory for task workspaces")
    p_audio.add_argument("--force", action="store_true", help="Force re-download/re-extraction even if audio file already exists")
    p_audio.add_argument("--sessdata", help="Optional SESSDATA cookie", default=None)
    p_audio.add_argument("--url-only", action="store_true", help="Only print stream URL without downloading")
    p_audio.add_argument("--output", default=None, help="Optional explicit output directory override")
    p_audio.add_argument("--chunk-minutes", type=int, default=10, help="Split audio into balanced chunks of ~N minutes (0=disabled)")
    p_audio.add_argument("--json", action="store_true", help="Output in JSON format")

    # 中文注释：subtitle 子命令已移除，统一走转录；subtitles/ 目录仅作转录语料存储
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
    p_pipe.add_argument("--prefetch-workers", type=int, default=12, help="Parallel audio prefetch (download/extract) threads")
    p_pipe.add_argument("--transcribe-episodes", type=int, default=2, help="Episodes transcribed concurrently (each uses chunk-level pool internally)")
    p_pipe.add_argument("--skip-failed", action="store_true", default=False, help="Explicit opt-in: exempt failed episodes from transcription gate (recorded in manifest skip list)")
    p_pipe.add_argument("--sessdata", help="Optional SESSDATA cookie", default=None)

    # info / agent-info
    p_info = subparsers.add_parser("info", aliases=["agent-info"], help="Show environment & toolchain readiness status")
    p_info.add_argument("--refresh", action="store_true", help="Clear cached status")
    # 中文注释：sessdata 仅判有/无，脱敏不打印
    p_info.add_argument("--sessdata", help="Optional SESSDATA cookie (only shows 有/无)", default=None)

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
        "clean": cmd_clean,
        "prompt": cmd_prompt,
        "note": cmd_note,
        "transcribe": cmd_transcribe,
        "pipeline": cmd_pipeline,
        "cluster-notes": cmd_cluster_notes,
        "agent-info": cmd_agent_info,
        "info": cmd_info,
    }
    dispatch[args.subcommand](args)


if __name__ == "__main__":
    main()
