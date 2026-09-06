"""Batch Processor Worker for Course Episodes (Pure Tooling).

Division of labor (mature host agent architecture):
- This script (tooling): audio download -> local whisper transcription -> safe normalization ->
  baseline article -> knowledge kernels -> per-block planning + synthesis prompts + local fallback notes.
- The host Agent (dialogue model): executes the exported prompts to perform semantic rectification,
  video-replacement article writing, and knowledge-block note synthesis.

Features checkpoint resume & per-episode isolation.
"""

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# Enable real-time line buffering
try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.parser import BilibiliParser
from src.core.fetcher import AudioFetcher
from src.core.workspace import TaskWorkspace
from src.core.transcriber import AudioTranscriber
from src.core.kernel_extractor import KernelExtractor
from src.generator.cleaner import TextCleaner
from src.generator.doc_builder import DocumentBuilder
from src.generator.topic_planner import SemanticTopicPlanner
from src.generator.block_synthesizer import BlockSynthesizer


def process_episode(
    ws: TaskWorkspace,
    info: dict,
    part: dict,
    total_count: int,
    engine: str = "auto",
    model_size: str = "base",
    allow_local_fallback: Optional[bool] = None,
) -> dict:
    p_num = part["page"]
    clean_title = "".join(c for c in part["title"] if c.isalnum() or c in (" ", "-", "_")).strip()
    prefix = f"[{p_num:02d}/{total_count:02d}]"

    article_file = ws.articles_dir / f"P{p_num:02d}_{clean_title}_精读文章.md"
    clean_txt_file = ws.subtitles_dir / f"P{p_num:02d}_{clean_title}_clean.txt"
    audio_file = ws.audio_dir / f"P{p_num:02d}_{clean_title}.m4a"

    if article_file.exists() and article_file.stat().st_size > 1000:
        print(f"{prefix} P{p_num:02d} 《{part['title']}》产物已存在，跳过。")

    # 1. Ensure audio is downloaded
    if not audio_file.exists() or audio_file.stat().st_size < 10240:
        print(f"{prefix} [1/3] 下载 64kbps 音频...")
        stream_info = AudioFetcher.get_audio_stream_info(info["bvid"], part["cid"], prefer_quality="low")
        AudioFetcher.download_audio(stream_info["best_stream_url"], str(audio_file), repackage_m4a=True)
    else:
        print(f"{prefix} [1/3] 音频已就绪: {audio_file.name} ({round(audio_file.stat().st_size / 1024 / 1024, 2)} MB)")

    # 2. Priority dialogue model or local whisper transcription + safe normalization
    if clean_txt_file.exists() and clean_txt_file.stat().st_size > 500:
        print(f"{prefix} [2/3] 转录文本已存在，直接复用: {clean_txt_file.name}")
        transcript_text = clean_txt_file.read_text(encoding="utf-8")
        engine_used = "cached"
    else:
        print(f"{prefix} [2/3] 启动语音转录 (策略: {engine})...")
        asr_res = AudioTranscriber.transcribe(
            audio_path=audio_file,
            engine=engine,
            model_size=model_size,
            allow_local_fallback=allow_local_fallback,
        )
        transcript_text = TextCleaner.clean(asr_res["full_text"])["cleaned_text"]
        clean_txt_file.write_text(transcript_text, encoding="utf-8")
        engine_used = asr_res.get("engine", "unknown")
        print(f"{prefix}    [✓] 转录完成 ({engine_used})，共 {len(transcript_text)} 字符")

    # 3. Baseline article (host Agent upgrades to video-replacement quality via prompt)
    if not article_file.exists() or article_file.stat().st_size < 1000:
        print(f"{prefix} [3/3] 生成 baseline 文章与知识元 (供 Agent 深度合成)...")
        article_md = DocumentBuilder.render_learning_article(
            title=info["title"],
            part_title=f"P{p_num:02d} {part['title']}",
            content=transcript_text,
        )
        article_file.write_text(article_md, encoding="utf-8")
    kernel_path = ws.subtitles_dir / "kernels" / f"P{p_num:02d}_{clean_title}_kernel.json"
    KernelExtractor.extract_single_kernel(p_num, part["title"], transcript_text, kernel_path=kernel_path)

    return {
        "page": p_num,
        "title": part["title"],
        "cid": part["cid"],
        "audio": str(audio_file),
        "transcript": str(clean_txt_file),
        "article": str(article_file),
        "kernel": str(kernel_path),
        "status": "success",
    }


def main():
    import threading

    parser = argparse.ArgumentParser(description="Batch Course Processor Worker (Tooling)")
    parser.add_argument("--bvid", required=True, help="Bilibili BV ID or URL")
    parser.add_argument("--start", type=int, default=1, help="Start page index (1-based)")
    parser.add_argument("--end", type=int, default=34, help="End page index (1-based)")
    parser.add_argument("--concurrency", type=int, default=2, help="Number of concurrent episode workers")
    parser.add_argument("--engine", default="auto", choices=["auto", "agent", "local"], help="Transcription engine strategy")
    parser.add_argument("--allow-local-fallback", action="store_true", default=None, help="Allow local fallback if dialogue model lacks audio capability")
    parser.add_argument("--model", default="base", choices=["tiny", "base", "small", "medium"], help="Local whisper model size")
    args = parser.parse_args()

    info = BilibiliParser.parse_video(args.bvid)
    ws = TaskWorkspace.create(title=info["title"], bvid=info["bvid"])

    all_parts = info.get("parts", [])
    total_parts = len(all_parts)
    start_idx = max(1, min(args.start, total_parts))
    end_idx = max(start_idx, min(args.end, total_parts))

    print("=" * 65)
    print(f"[*] 并发批量处理任务: 《{info['title']}》 (P{start_idx:02d} 至 P{end_idx:02d}, 并发数: {args.concurrency})")
    print(f"[*] 任务工作区: {ws.root_dir}")
    print(f"[*] 转录引擎策略: {args.engine} (优先对话大模型，异常询问本地模型) | 本地兜底规格: whisper-{args.model}")
    print("=" * 65)

    manifest_lock = threading.Lock()
    selected_parts = all_parts[start_idx - 1:end_idx]

    def _worker(p):
        res = process_episode(
            ws,
            info,
            p,
            total_parts,
            engine=args.engine,
            model_size=args.model,
            allow_local_fallback=args.allow_local_fallback,
        )
        with manifest_lock:
            manifest = ws.load_manifest()
            details = manifest.get("details", [])
            details = [d for d in details if d.get("page") != res["page"]]
            details.append(res)
            ws.save_manifest({"details": details})
        return res

    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        results = list(executor.map(_worker, selected_parts))

    # Plan knowledge blocks + export Agent-ready synthesis prompts
    plan = SemanticTopicPlanner.plan(all_parts, course_title=info["title"], ws=ws)
    prompt_tasks = []
    for b in plan:
        eps = b["episodes"]
        block_parts = [p for p in all_parts if p["page"] in eps]
        kernels = []
        for bp in block_parts:
            clean_t = "".join(c for c in bp["title"] if c.isalnum() or c in (" ", "-", "_")).strip()
            k_path = ws.subtitles_dir / "kernels" / f"P{bp['page']:02d}_{clean_t}_kernel.json"
            if k_path.exists():
                try:
                    kernels.append(json.loads(k_path.read_text(encoding="utf-8")))
                except Exception:
                    pass
        if not kernels:
            continue
        prompt = BlockSynthesizer.build_synthesis_prompt(b, kernels)
        task_file = ws.notes_dir / f"模块{b['block_id']:02d}_AGENT_TASK.md"
        task_file.write_text(prompt, encoding="utf-8")
        prompt_tasks.append(str(task_file))

    ws.save_manifest({
        "knowledge_blocks_plan": plan,
        "agent_prompt_tasks": prompt_tasks,
        "pipeline_completed": True,
    })

    print("\n" + "=" * 65)
    print(f"[✓] 当前批次 (P{start_idx:02d} - P{end_idx:02d}) 并发执行完毕！")
    print(f"[✓] 知识块规划完成: {len(plan)} 个模块；Agent 合成任务书已导出至 notes/模块XX_AGENT_TASK.md")
    print("=" * 65)


if __name__ == "__main__":
    main()
