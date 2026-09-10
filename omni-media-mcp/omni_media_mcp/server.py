"""OmniMedia FastMCP Server: High-performance Multimodal Media Understanding for AI Agents."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
from pathlib import Path
from typing import Annotated, Optional, Union

from pydantic import Field

try:
    from mcp.server.mcpserver import Audio, Context, MCPServer
except ImportError:
    from mcp.server.fastmcp import Audio, Context, FastMCP as MCPServer

from .benchmarks.probe import BenchmarkProber
from .core.inspector import MediaInspector
from .core.limits import (
    DEFAULT_SAFE_SLICE_MINUTES,
    MAX_CONCURRENT_FFMPEG,
    MAX_INLINE_BYTES,
    MAX_ONESHOT_MINUTES,
    MAX_SAFE_INLINE_BYTES,
    MEDIA_EXTS,
    MODE_WHITELIST,
    OUTPUT_MODE_WHITELIST,
    VIDEO_EXTS,
    get_slices_cache_dir,
)
from .core.preprocessor import MediaPreprocessor
from .core.temp_manager import ManagedTempDir
from .prompts import PROMPT_QA, PROMPT_SUMMARIZE, PROMPT_TRANSCRIBE, PROMPT_VISUAL_QA
from .providers.router import MultimodalRouter

# Concurrency semaphore to throttle ffmpeg processes across async tasks
_ASYNC_FFMPEG_SEMAPHORE = asyncio.Semaphore(MAX_CONCURRENT_FFMPEG)

# Initialize MCPServer
mcp = MCPServer(
    "OmniMedia-Server",
    instructions="通用反重力式多模态音视频直读 MCP 服务。原生支持全模态大模型对音频、视频直接进行理解、长文重构与抗幻觉问答。",
)

router = MultimodalRouter()

# Progress milestones (kept as module constants instead of scattered literals).
_PCT_START = 0.05
_PCT_PREP = 0.15
_PCT_DONE = 1.0

# Prompt templates per mode. 'custom' intentionally has no canned prompt: it
# relies entirely on the caller-supplied instruction.
_MODE_PROMPTS = {
    "transcribe": PROMPT_TRANSCRIBE,
    "summarize": PROMPT_SUMMARIZE,
    "qa": PROMPT_QA,
}
_CUSTOM_FALLBACK_PROMPT = "请详细分析并提炼此音视频的核心内容。"


def _mode_prompt(mode: str, visual: bool) -> str:
    """Return the base prompt for a validated mode, prepending the visual QA
    preamble when visual analysis is requested."""
    base = _MODE_PROMPTS.get(mode, _CUSTOM_FALLBACK_PROMPT)
    if visual:
        base = f"{PROMPT_VISUAL_QA}\n\n{base}"
    return base


def _pagination_note(start_sec: float, end_sec: float, total_duration: float) -> str:
    """Build the human-readable continuation hint appended after a slice read.

    Returns an empty string when nothing was sliced.
    """
    if total_duration <= 0:
        return ""
    start_fmt = MediaPreprocessor.format_time_str(start_sec)
    end_fmt = MediaPreprocessor.format_time_str(end_sec)
    total_fmt = MediaPreprocessor.format_time_str(total_duration)
    if end_sec < total_duration:
        return (
            f"\n\n---\n"
            f"> ⏱️ **分页状态**: 已读取分卷 `[{start_fmt} - {end_fmt}]` / 总时长 `{total_fmt}`\n"
            f"> 💡 **续读下一分卷参数**: `start_time=\"{end_fmt}\"`"
        )
    return (
        f"\n\n---\n"
        f"> ⏱️ **分页状态**: 已读取分卷 `[{start_fmt} - {end_fmt}]` / 总时长 `{total_fmt}` (全篇已读完)"
    )


@mcp.tool()
async def read_media(
    file_path: Annotated[str, Field(description="本地音视频文件的绝对路径")],
    instruction: Annotated[
        Optional[str], Field(description="自定义附加提示词（可选）；custom 模式下为必填")
    ] = None,
    mode: Annotated[
        str, Field(description="任务预设: 'transcribe' | 'summarize' | 'qa' | 'custom'")
    ] = "transcribe",
    provider: Annotated[
        str, Field(description="模型提供商: 'auto' | 'gemini' | 'mimo' | 'openai' | 'qwen' | 'deepseek' | 'minimax'")
    ] = "auto",
    visual: Annotated[bool, Field(description="是否分析视频画面（需视频文件；音频文件请保持 False）")] = False,
    start_time: Annotated[
        Optional[str], Field(description="分页切片起始时间戳，如 '00:15:00' 或秒数（可选）")
    ] = None,
    duration_minutes: Annotated[
        Optional[float], Field(description="本次读取时长预算（分钟，可选，需 > 0）")
    ] = None,
    ctx: Context = None,
) -> str:
    """【云端委托代读模式】读取本地音视频文件，委托外部大模型 API 进行转录或总结。

    提示：若宿主模型本身具备原生音频多模态能力（如 Gemini、GPT-4o Audio、Codex），
    请优先调用 `read_audio` 工具，以获得零外部 API 凭证消耗、低延迟的原生听音感知。

    Args:
        file_path: 本地音视频绝对路径（支持 mp4/mkv/mov/avi/flv/webm/mp3/wav/m4a/aac/flac 等）。
        instruction: 自定义附加提示词（可选）。mode='custom' 时必须提供。
        mode: 任务预设 — 'transcribe'(逐字稿) / 'summarize'(教材级大笔记) / 'qa'(问答) / 'custom'(纯自定义指令)。
        provider: 模型提供商 — 'auto' 自动优选，或显式 'gemini'/'mimo'/'openai'/'qwen'/'deepseek'/'minimax'。
        visual: 是否分析视频画面（黑板/PPT/屏幕代码）。默认 False（提取 16kHz 纯人声）；对纯音频文件置 True 会报错。
        start_time: 分页切片起始时间戳（如 '00:00:00' / '00:15:00' 或秒数）。
        duration_minutes: 本次读取时长预算（分钟）。超出自动分卷并在文末生成下一分卷续读参数。

    Returns:
        Provider 生成的文本内容，含来源标注与（若切片）分页续读提示。

    Raises:
        ValueError: 参数非法（不支持的 mode、非文件路径、非媒体扩展名、负数时间等）。
        FileNotFoundError: 媒体文件不存在。
        RuntimeError: 处理过程失败（含底层原因链）。
    """
    # ---- Input validation: illegal inputs raise so the framework flags isError ----
    mode_key = (mode or "transcribe").strip().lower()
    if mode_key not in MODE_WHITELIST:
        raise ValueError(
            f"不支持的 mode: '{mode}'。支持: {sorted(MODE_WHITELIST)}"
        )
    if mode_key == "custom" and not (instruction and instruction.strip()):
        raise ValueError("mode='custom' 时需提供非空 instruction。")

    path = Path(file_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"媒体文件不存在: `{file_path}`")
    if not path.is_file():
        raise ValueError(f"路径不是文件: `{file_path}`")
    if path.suffix.lower() not in MEDIA_EXTS:
        raise ValueError(
            f"不支持的文件类型: '{path.suffix}'。支持: {sorted(MEDIA_EXTS)}"
        )

    if duration_minutes is not None and duration_minutes <= 0:
        raise ValueError(f"duration_minutes 必须 > 0，收到: {duration_minutes}")
    # parse_time_str raises ValueError on negative/invalid timestamps.
    start_sec = MediaPreprocessor.parse_time_str(start_time) or 0.0

    base_prompt = _mode_prompt(mode_key, visual)
    if instruction and instruction.strip():
        full_prompt = f"{base_prompt}\n\n【用户专属指示】：\n{instruction}"
    else:
        full_prompt = base_prompt

    # Progress helper (context is optional; ignored when injected ctx is absent)
    def progress_callback(pct: float, msg: str):
        if ctx:
            asyncio.create_task(ctx.report_progress(progress=pct, total=1.0))
            ctx.info(f"[{int(pct * 100)}%] {msg}")

    progress_callback(_PCT_START, f"开始分析媒体: {path.name}")

    try:
        chosen_provider = router.get_provider(provider)
        # Media probing spawns ffprobe/ffmpeg subprocesses -> keep off the loop.
        meta = await asyncio.to_thread(MediaInspector.probe, path)
        total_duration = meta.duration_seconds

        if visual and not meta.has_video:
            raise ValueError(
                "visual=True 需要含视频轨道的文件；当前媒体未检测到视频画面。"
                "对纯音频文件请改用 visual=False。"
            )

        # Parse slicing parameters
        is_sliced = False
        slice_dur_sec = None
        if duration_minutes is not None:
            slice_dur_sec = float(duration_minutes) * 60.0
            end_sec = min(total_duration, start_sec + slice_dur_sec) if total_duration > 0 else start_sec + slice_dur_sec
            is_sliced = True
        elif start_sec > 0:
            end_sec = total_duration
            if total_duration > start_sec:
                slice_dur_sec = total_duration - start_sec
            is_sliced = True
        else:
            end_sec = total_duration

        is_video_container = path.suffix.lower() in VIDEO_EXTS

        with ManagedTempDir(prefix="omni_proc_") as tmp_dir:
            if is_sliced:
                if not visual:
                    progress_callback(_PCT_PREP, f"提取切片音频 [{MediaPreprocessor.format_time_str(start_sec)} - {MediaPreprocessor.format_time_str(end_sec)}]...")
                    proc_audio = tmp_dir / f"{path.stem}_slice_{int(start_sec)}_{int(end_sec)}.m4a"
                    await asyncio.to_thread(
                        MediaPreprocessor.extract_optimized_audio,
                        path,
                        output_file=proc_audio,
                        start_time=start_sec,
                        duration_seconds=slice_dur_sec,
                    )
                    res = await chosen_provider.process(
                        media_path=proc_audio,
                        prompt=full_prompt,
                        visual=False,
                        on_progress=progress_callback,
                    )
                else:
                    progress_callback(_PCT_PREP, f"切片视频画面 [{MediaPreprocessor.format_time_str(start_sec)} - {MediaPreprocessor.format_time_str(end_sec)}]...")
                    proc_video = tmp_dir / f"{path.stem}_slice_{int(start_sec)}_{int(end_sec)}.mp4"
                    await asyncio.to_thread(
                        MediaPreprocessor.slice_video,
                        path,
                        output_file=proc_video,
                        start_time=start_sec,
                        duration_seconds=slice_dur_sec,
                    )
                    res = await chosen_provider.process(
                        media_path=proc_video,
                        prompt=full_prompt,
                        visual=True,
                        on_progress=progress_callback,
                    )
            elif not visual and is_video_container:
                progress_callback(_PCT_PREP, "极速提取 16kHz 单声道纯人声音频...")
                audio_file = tmp_dir / f"{path.stem}_16k.m4a"
                await asyncio.to_thread(
                    MediaPreprocessor.extract_optimized_audio,
                    path,
                    audio_file,
                )
                res = await chosen_provider.process(
                    media_path=audio_file,
                    prompt=full_prompt,
                    visual=False,
                    on_progress=progress_callback,
                )
            else:
                res = await chosen_provider.process(
                    media_path=path,
                    prompt=full_prompt,
                    visual=visual,
                    on_progress=progress_callback,
                )

        pagination_note = _pagination_note(start_sec, end_sec, total_duration) if is_sliced else ""

        header = f"<!-- OmniMedia: Provider={res.provider_name} | Model={res.model_name} -->\n\n"
        return f"{header}{res.text}{pagination_note}"

    except ValueError:
        # Validation/domain errors (unsupported provider, pure-audio+visual,
        # empty result) surface as-is so clients can recover.
        raise
    except Exception as e:
        raise RuntimeError(f"媒体处理失败: {e}") from e


@mcp.tool()
async def read_audio(
    file_path: Annotated[str, Field(description="本地音频或视频文件的绝对路径")],
    start_time: Annotated[
        Optional[str], Field(description="切片起始时间戳，如 '00:00:00'、'00:15:00' 或秒数（可选，默认从头开始）")
    ] = None,
    duration_minutes: Annotated[
        Optional[float], Field(description="本次切片读取时长预算（分钟，可选，需 > 0。超长媒体未传时自动安全分卷）")
    ] = None,
    output_mode: Annotated[
        str, Field(description="回传通道: 'auto'(智能兼顾) | 'file'(输出本地切片文件绝对路径，推荐 Codex 等终端 Agent) | 'inline'(MCP 原生 Audio 数据块)")
    ] = "auto",
    ctx: Context = None,
) -> Union[Audio, str]:
    """直接读取本地音视频文件的音频流，返回原生音频数据或切片文件供当前对话模型直接聆听与分析。

    无需任何第三方 API 凭证，直接借用宿主多模态对话模型（如 Gemini、GPT-4o Audio、Codex）的听音算力。

    Args:
        file_path: 本地音视频文件的绝对路径。
        start_time: 分页切片起始时间戳（如 '00:00:00'、'00:15:00' 或秒数，可选）。
        duration_minutes: 本次切片读取时长预算（分钟，可选，需 > 0。未传且媒体过长时将自动安全分卷）。
        output_mode: 回传通道 — 'auto'(根据大小与环境智能选择) / 'file'(生成 16kHz 优化切片并返回本地文件路径，适合 Codex/终端 Agent) / 'inline'(返回 MCP 原生 Audio 数据块)。

    Returns:
        MCP 原生 Audio 数据块 (inline 模式)，或包含本地切片绝对路径与续读指南的结构化 Markdown (file 模式)。

    Raises:
        FileNotFoundError: 媒体文件不存在。
        ValueError: 路径不是文件、扩展名不支持或参数非法。
        RuntimeError: 切片或音频提取失败。
    """
    path = Path(file_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"媒体文件不存在: `{file_path}`")
    if not path.is_file():
        raise ValueError(f"路径不是文件: `{file_path}`")
    ext = path.suffix.lower()
    if ext not in MEDIA_EXTS:
        raise ValueError(f"不支持的文件扩展名: '{ext}'。支持的媒体扩展名: {sorted(MEDIA_EXTS)}")

    mode_key = (output_mode or "auto").strip().lower()
    if mode_key not in OUTPUT_MODE_WHITELIST:
        raise ValueError(f"不支持的 output_mode: '{output_mode}'。支持: {sorted(OUTPUT_MODE_WHITELIST)}")

    env_default_mode = os.environ.get("OMNI_MEDIA_OUTPUT_MODE", "").strip().lower()
    if mode_key == "auto" and env_default_mode in ("file", "inline"):
        mode_key = env_default_mode

    if duration_minutes is not None and duration_minutes <= 0:
        raise ValueError(f"duration_minutes 必须大于 0，收到: {duration_minutes}")

    start_sec = MediaPreprocessor.parse_time_str(start_time)
    if start_sec is not None and start_sec < 0:
        raise ValueError(f"start_time 不能为负数: {start_time}")
    if start_sec is None:
        start_sec = 0.0

    # Probe duration (soft probe, fallback to 0.0 on synthetic/mock files).
    # `meta` must be bound even when probing fails: `_produce_file_channel`
    # below reads it as a closure variable.
    meta = None
    try:
        meta = await asyncio.to_thread(MediaInspector.probe, path)
        total_duration = meta.duration_seconds
    except Exception:
        total_duration = 0.0

    is_video = ext in VIDEO_EXTS

    # Slicing calculation with self-healing auto-clamping & One-Shot support
    if duration_minutes is not None:
        slice_dur_sec = duration_minutes * 60.0
        is_sliced = True
        mode_tag = "chunked"
    elif total_duration > 0 and (total_duration - start_sec) > (MAX_ONESHOT_MINUTES * 60.0):
        # Media exceeds 75 minutes, auto-clamp to 30-minute chunks to prevent context explosion
        slice_dur_sec = 30.0 * 60.0
        is_sliced = True
        mode_tag = "chunked"
    elif start_sec > 0:
        slice_dur_sec = (total_duration - start_sec) if total_duration > start_sec else None
        is_sliced = True
        mode_tag = "chunked"
    else:
        # Files <= 75 minutes: One-Shot full lecture
        slice_dur_sec = total_duration if total_duration > 0 else None
        is_sliced = False
        mode_tag = "oneshot"

    end_sec = start_sec + slice_dur_sec if slice_dur_sec is not None else total_duration
    if total_duration > 0:
        end_sec = min(total_duration, end_sec)

    # Channel resolution
    if mode_key == "file":
        target_channel = "file"
    elif mode_key == "inline":
        target_channel = "inline"
    else:  # "auto"
        # In auto mode, route to file if the raw file is large, video, or slice is long (>10m)
        if path.stat().st_size > MAX_SAFE_INLINE_BYTES or is_video or (slice_dur_sec and slice_dur_sec > 10 * 60):
            target_channel = "file"
        else:
            target_channel = "inline"

    # Helper function to generate file slice text
    async def _produce_file_channel() -> str:
        # Check if source file is already 16kHz mono pure audio and no slicing is needed
        is_source_16k_mono = False
        if not is_video and not is_sliced and meta and getattr(meta, "streams", None):
            audio_streams = [s for s in meta.streams if s.get("codec_type") == "audio"]
            if audio_streams:
                s0 = audio_streams[0]
                if s0.get("sample_rate") == 16000 and s0.get("channels") == 1:
                    is_source_16k_mono = True

        if is_source_16k_mono:
            out_slice_file = path
        else:
            path_hash = hashlib.md5(str(path.resolve()).encode("utf-8")).hexdigest()[:8]
            start_tag = int(start_sec)
            end_tag = int(end_sec) if end_sec > 0 else "end"
            out_slice_file = get_slices_cache_dir() / f"{path.stem}_{path_hash}_slice_{start_tag}_{end_tag}.m4a"

            if not out_slice_file.exists() or out_slice_file.stat().st_size == 0:
                async with _ASYNC_FFMPEG_SEMAPHORE:
                    if is_sliced or is_video:
                        await asyncio.to_thread(
                            MediaPreprocessor.extract_optimized_audio,
                            input_file=path,
                            output_file=out_slice_file,
                            start_time=start_sec,
                            duration_seconds=slice_dur_sec,
                        )
                    else:
                        await asyncio.to_thread(
                            MediaPreprocessor.extract_optimized_audio,
                            input_file=path,
                            output_file=out_slice_file,
                        )

        if not out_slice_file.exists() or out_slice_file.stat().st_size == 0:
            raise RuntimeError(f"音频切片生成失败: `{out_slice_file}`")

        slice_size_mb = out_slice_file.stat().st_size / (1024 * 1024)
        start_fmt = MediaPreprocessor.format_time_str(start_sec)
        end_fmt = MediaPreprocessor.format_time_str(end_sec)
        total_fmt = MediaPreprocessor.format_time_str(total_duration) if total_duration > 0 else "未知"
        effective_dur_min = duration_minutes or (30.0 if mode_tag == "chunked" else DEFAULT_SAFE_SLICE_MINUTES)

        has_next = total_duration > 0 and end_sec < total_duration
        if has_next:
            next_hint = f"> ⏱️ **续读下一分卷参数**: `start_time=\"{end_fmt}\", duration_minutes={effective_dur_min}`"
        else:
            next_hint = "> ⏱️ **分页状态**: 全篇音频已就绪 (One-Shot 完成)。" if mode_tag == "oneshot" else "> ⏱️ **分页状态**: 全篇音频已切片完毕。"

        status_payload = {
            "status": "COMPLETED" if not has_next else "IN_PROGRESS",
            "mode": mode_tag,
            "is_finished": not has_next,
            "start_time": start_fmt,
            "end_time": end_fmt,
            "total_duration": total_fmt,
        }
        if has_next:
            status_payload["next_start_time"] = end_fmt
            status_payload["next_duration_minutes"] = effective_dur_min

        status_comment = f"<!-- OMNI_STATUS: {json.dumps(status_payload, ensure_ascii=False)} -->\n\n"

        return (
            f"{status_comment}"
            f"### 🎙️ OmniMedia 原生音频切片就绪\n\n"
            f"- **切片本地绝对路径**: `{out_slice_file.as_posix()}`\n"
            f"- **切片时间区间**: `[{start_fmt} - {end_fmt}]` (本卷时长: {int(end_sec - start_sec)} 秒 / 总时长: {total_fmt})\n"
            f"- **音频规格**: 16kHz 单声道 AAC/m4a (高保真人声优化, 体积: {slice_size_mb:.2f} MiB)\n\n"
            f"{next_hint}\n\n"
            f"> 💡 **宿主 Agent 听音指引**: 切片已保存至本地。请使用您的原生文件查看工具（如 Codex/Antigravity 的 `view_file`）直接读取该切片文件路径，底层多模态内核即可直接感知并聆听音频内容。"
        )

    if target_channel == "file":
        try:
            return await _produce_file_channel()
        except Exception as e:
            raise RuntimeError(f"生成本地音频切片失败: {e}") from e

    # target_channel == "inline"
    if is_sliced or is_video:
        try:
            with ManagedTempDir() as tmp_dir:
                slice_path = tmp_dir / f"{path.stem}_slice.m4a"
                async with _ASYNC_FFMPEG_SEMAPHORE:
                    await asyncio.to_thread(
                        MediaPreprocessor.extract_optimized_audio,
                        input_file=path,
                        output_file=slice_path,
                        start_time=start_sec,
                        duration_seconds=slice_dur_sec,
                    )
                if not slice_path.exists():
                    raise RuntimeError(f"音频提取/切片生成失败: `{slice_path}`")

                # If auto mode and exceeds safe inline limit, gracefully fall back to file channel
                if mode_key == "auto" and slice_path.stat().st_size > MAX_SAFE_INLINE_BYTES:
                    return await _produce_file_channel()

                if slice_path.stat().st_size > MAX_INLINE_BYTES:
                    raise ValueError(
                        f"切片音频体积 ({slice_path.stat().st_size / (1024*1024):.1f} MiB) 超过单次内联限制 "
                        f"({MAX_INLINE_BYTES / (1024*1024):.0f} MiB)，请调小 duration_minutes 或改用 output_mode='file' 分卷读取。"
                    )
                with open(slice_path, "rb") as f:
                    audio_bytes = f.read()
            return Audio(data=audio_bytes, format="mp4")
        except (ValueError, FileNotFoundError):
            raise
        except Exception as e:
            raise RuntimeError(f"音频切片处理失败: {e}") from e
    else:
        # Direct audio file reading
        if mode_key == "auto" and path.stat().st_size > MAX_SAFE_INLINE_BYTES:
            return await _produce_file_channel()

        if path.stat().st_size > MAX_INLINE_BYTES:
            raise ValueError(
                f"音频文件体积 ({path.stat().st_size / (1024*1024):.1f} MiB) 超过单次内联限制 "
                f"({MAX_INLINE_BYTES / (1024*1024):.0f} MiB)，请使用 start_time 与 duration_minutes 或改用 output_mode='file' 分卷读取。"
            )
        try:
            with open(path, "rb") as f:
                audio_bytes = f.read()
            fmt = "mp4" if ext == ".m4a" else ext.lstrip(".")
            return Audio(data=audio_bytes, format=fmt)
        except Exception as e:
            raise RuntimeError(f"读取音频数据失败: {e}") from e



@mcp.tool()
async def inspect_media(
    file_path: Annotated[str, Field(description="本地音视频文件绝对路径")],
) -> str:
    """毫秒级探测音视频媒体文件的时长、编码、轨道、体积，以及在各类多模态模型下的 Token 预估。

    Args:
        file_path: 本地音视频文件绝对路径。

    Raises:
        FileNotFoundError: 文件不存在。
        ValueError: 路径不是文件或扩展名不支持。
        RuntimeError: 探测过程失败。
    """
    path = Path(file_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"媒体文件不存在: `{file_path}`")
    if not path.is_file():
        raise ValueError(f"路径不是文件: `{file_path}`")

    try:
        meta = await asyncio.to_thread(MediaInspector.probe, path)
        return meta.to_markdown()
    except ValueError:
        raise
    except Exception as e:
        raise RuntimeError(f"探测失败: {e}") from e


@mcp.tool()
async def ask_media(
    file_path: Annotated[str, Field(description="本地音视频文件绝对路径")],
    question: Annotated[str, Field(description="针对音视频内容的提问（非空）")],
    provider: Annotated[
        str, Field(description="模型提供商: 'auto' | 'gemini' | 'mimo' | 'openai' | 'qwen' | 'deepseek' | 'minimax'")
    ] = "auto",
    visual: Annotated[bool, Field(description="是否需要看视频画面回答（需视频文件）")] = False,
    ctx: Context = None,
) -> str:
    """基于音视频内容进行抗幻觉事实精准问答（Strict Grounding）。

    Args:
        file_path: 本地音视频文件绝对路径。
        question: 您想向音视频提出的具体问题（例如：“第15分钟推导的核心结论是什么？”）。
        provider: 模型提供商（'auto' 或显式厂商）。
        visual: 是否需要看视频画面回答。

    Raises:
        ValueError: question 为空，或参数非法。
        FileNotFoundError: 文件不存在。
        RuntimeError: 处理过程失败。
    """
    if not (question and question.strip()):
        raise ValueError("question 不能为空。")
    prompt = f"【用户提问】：\n{question}"
    return await read_media(
        file_path=file_path,
        instruction=prompt,
        mode="qa",
        provider=provider,
        visual=visual,
        ctx=ctx,
    )


@mcp.tool()
async def probe_models(
    category: Annotated[
        str, Field(description="要查看的模型类别: 'all' | 'audio' | 'video'")
    ] = "all",
) -> str:
    """查看主流多模态模型的音视频能力静态基准快照与本地 API Key 激活状态。

    注：本工具基于内置静态基准数据（源自 Video-MME / Artificial Analysis /
    厂商官方规格的**非实时快照**），不执行网络探测；"激活状态"为本地实时读取。

    Args:
        category: 类别 — 'all'（全部）/ 'audio'（能处理音频）/ 'video'（能处理视频）。

    Raises:
        ValueError: category 不在支持范围内。
    """
    return BenchmarkProber.generate_report(category=category)


# ==========================================
# Resources
# ==========================================


@mcp.resource("media://supported-models")
def get_supported_models_resource() -> str:
    """获取所有受支持的多模态模型规格与参数配置清单。"""
    return BenchmarkProber.generate_report()


@mcp.resource("media://system-status")
def get_system_status_resource() -> str:
    """获取本地 FFmpeg 状态及已配置激活的 API 凭证列表。"""
    env_status = BenchmarkProber.get_live_environment_status()
    active_keys = [k for k, v in env_status.items() if v]
    missing_keys = [k for k, v in env_status.items() if not v]

    return f"""### 🛠️ OmniMedia 系统运行环境诊断:
- **已激活环境变量**: {', '.join(active_keys) if active_keys else '无 (建议设置 GEMINI_API_KEY)'}
- **未配置环境变量**: {', '.join(missing_keys)}
- **可用 Provider 列表**: {', '.join(router.list_available_providers())}
"""


# ==========================================
# Prompts
# ==========================================


@mcp.prompt("transcribe-lecture")
def prompt_transcribe_lecture() -> str:
    """技术网课/学术讲座高保真逐字转录模板。"""
    return PROMPT_TRANSCRIBE


@mcp.prompt("generate-cheatsheet")
def prompt_generate_cheatsheet() -> str:
    """考前速查/架构复习大笔记重构模板。"""
    return PROMPT_SUMMARIZE


def main():
    """Run FastMCP Server on stdio transport."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
