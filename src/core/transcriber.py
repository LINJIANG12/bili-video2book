"""Multimodal Audio Transcriber: Dialogue Model Priority & Local Fallback.

Architecture:
- Priority 1: Direct multimodal audio ingestion by the active dialogue model
  (e.g. Gemini 3.8 Flash High via AgentModelClient).
- Failure & Fallback Gate: If the dialogue model does not support audio modality or is unavailable,
  the tool halts, reports the issue clearly, and prompts the user whether to permit fallback
  to the local faster-whisper model.
"""

import os
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

from .agent_client import AgentModelClient


class AudioTranscriber:
    _cached_models: Dict[str, Any] = {}

    @classmethod
    def get_model(
        cls,
        model_size: str = "base",
        device: str = "cpu",
        compute_type: Optional[str] = None,
    ):
        """Retrieve or instantiate a cached faster-whisper model."""
        try:
            from faster_whisper import WhisperModel
        except ImportError as err:
            raise RuntimeError(
                "faster-whisper is not installed. Please install it via `pip install faster-whisper`"
            ) from err

        if device == "auto":
            device = "cpu"
        compute_type = compute_type or ("float16" if device == "cuda" else "int8")

        # Ensure reliable model download in restricted networks
        if "HF_ENDPOINT" not in os.environ:
            os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

        cache_key = f"{model_size}_{device}_{compute_type}"
        if cache_key not in cls._cached_models:
            num_threads = min(8, os.cpu_count() or 4) if device == "cpu" else 4
            cls._cached_models[cache_key] = WhisperModel(
                model_size_or_path=model_size,
                device=device,
                compute_type=compute_type,
                cpu_threads=num_threads,
            )
        return cls._cached_models[cache_key]

    @classmethod
    def transcribe(
        cls,
        audio_path: Union[str, Path],
        engine: str = "auto",
        model_size: str = "base",
        language: str = "zh",
        device: str = "cpu",
        compute_type: Optional[str] = None,
        beam_size: int = 1,
        initial_prompt: Optional[str] = None,
        allow_local_fallback: Optional[bool] = None,
        fallback_callback: Optional[Callable[[], bool]] = None,
    ) -> Dict[str, Any]:
        """
        Transcribe an audio file to text.
        Priority:
        1. Dialogue Model (AgentModelClient) if engine in ('auto', 'agent') and model supports audio.
        2. If dialogue model lacks audio capability or fails:
           HALTS and asks user whether to fallback to local faster-whisper.
        """
        path_obj = Path(audio_path).resolve()
        if not path_obj.exists():
            raise FileNotFoundError(f"Audio file not found: {path_obj}")

        # Path 1: Priority Dialogue Model
        if engine in ("auto", "agent"):
            cfg = AgentModelClient.discover_config()
            can_audio = AgentModelClient.can_transcribe_audio()
            available = AgentModelClient.is_available()

            if can_audio and available:
                model_name = cfg.get("model", "dialogue-model") if cfg else "dialogue-model"
                print(f"[*] 【优先路径】调用宿主对话大模型 ({model_name}) 执行原生多模态语音转录...")
                try:
                    return AgentModelClient.transcribe_audio(
                        audio_path=path_obj,
                        chunk_minutes=10,
                        initial_prompt=initial_prompt,
                    )
                except Exception as err:
                    print(f"[-] 对话大模型多模态转录请求异常: {err}")
                    if engine == "agent":
                        raise

            # Dialogue model cannot handle audio or is unreachable
            reason = []
            if not can_audio:
                reason.append(f"当前配置的模型 ({cfg.get('model') if cfg else 'unknown'}) 不具备音频 (audio) 输入模态")
            if not available:
                reason.append(f"本地网关 ({cfg.get('base_url') if cfg else 'unknown'}) 探测无响应或不可达")

            problem_desc = "；".join(reason) if reason else "对话模型服务未就绪"
            print(f"\n[!] 警告：当前对话大模型无法执行音频转录（原因: {problem_desc}）。")

            if engine == "agent":
                raise RuntimeError(
                    f"当前指定了 --engine agent，但对话大模型无法读取音频（{problem_desc}），任务已中止。"
                )

            # Auto mode: Halt and ask user whether to fallback to local Whisper
            should_fallback = False
            if allow_local_fallback is True:
                should_fallback = True
                print("[*] 检测到预授权参数，已确认切换至本地 faster-whisper 引擎兜底...")
            elif allow_local_fallback is False:
                should_fallback = False
            elif fallback_callback is not None:
                should_fallback = fallback_callback()
            elif sys.stdin.isatty():
                try:
                    ans = input("\n[?] 是否切换为本地 faster-whisper 模型进行离线转录兜底？[y/N]: ").strip().lower()
                    should_fallback = ans in ("y", "yes")
                except (EOFError, KeyboardInterrupt):
                    should_fallback = False
            else:
                should_fallback = False

            if not should_fallback:
                raise RuntimeError(
                    f"对话大模型不具备音频读取能力（{problem_desc}），且未授权使用本地模型，任务已主动中止。"
                )

            print(f"[*] 用户已授权：切换为本地 whisper-{model_size} 执行兜底声学转录...")

        # Path 2: Local faster-whisper
        return cls.transcribe_local(
            audio_path=path_obj,
            model_size=model_size,
            language=language,
            device=device,
            compute_type=compute_type,
            beam_size=beam_size,
            initial_prompt=initial_prompt,
        )

    @classmethod
    def transcribe_local(
        cls,
        audio_path: Union[str, Path],
        model_size: str = "base",
        language: str = "zh",
        device: str = "cpu",
        compute_type: Optional[str] = None,
        beam_size: int = 1,
        initial_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Transcribe an audio file using local faster-whisper."""
        path_obj = Path(audio_path).resolve()
        if not path_obj.exists():
            raise FileNotFoundError(f"Audio file not found: {path_obj}")

        model = cls.get_model(
            model_size=model_size,
            device=device,
            compute_type=compute_type,
        )

        segments_gen, info = model.transcribe(
            str(path_obj),
            language=language,
            beam_size=beam_size,
            initial_prompt=initial_prompt,
        )

        segments_list = []
        raw_text_pieces = []
        timestamped_lines = []

        for seg in segments_gen:
            clean_t = seg.text.strip()
            if not clean_t:
                continue
            start_str = cls.format_seconds(seg.start)
            end_str = cls.format_seconds(seg.end)
            segments_list.append({
                "start": round(seg.start, 2),
                "end": round(seg.end, 2),
                "start_fmt": start_str,
                "end_fmt": end_str,
                "text": clean_t,
            })
            raw_text_pieces.append(clean_t)
            timestamped_lines.append(f"[{start_str} -> {end_str}] {clean_t}")

        full_text = " ".join(raw_text_pieces)
        timestamped_text = "\n".join(timestamped_lines)

        return {
            "full_text": full_text,
            "timestamped_text": timestamped_text,
            "segments": segments_list,
            "total_segments": len(segments_list),
            "language": info.language,
            "language_probability": round(info.language_probability, 4),
            "duration": round(info.duration, 2),
            "engine": f"local-whisper-{model_size}",
        }

    @staticmethod
    def format_seconds(seconds: float) -> str:
        s = int(round(seconds))
        hours = s // 3600
        minutes = (s % 3600) // 60
        secs = s % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
