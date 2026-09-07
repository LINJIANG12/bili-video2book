"""High-Performance Local Audio Transcriber using faster-whisper.

Philosophy:
- transcribe() = 纯本地 faster-whisper 离线转录 (CPU int8 or CUDA float16).
- 转录原则：优先对话模型（Agent 原生），whisper 仅兜底。
- 零环境变量、零端口：本工具不读写任何环境变量、不绑定端口。
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


class AudioTranscriber:
    _cached_models: Dict[str, Any] = {}

    @classmethod
    def get_model(
        cls,
        model_size: str = "base",
        device: str = "auto",
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

        # 零环境变量原则：本工具绝不写入 os.environ。
        # 如需加速模型下载，用户可在 Shell 中按需自设镜像，例如：
        #   $env:HF_ENDPOINT="https://hf-mirror.com"  (PowerShell) /
        #   export HF_ENDPOINT="https://hf-mirror.com"  (bash)

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
        engine: str = "local",
        model_size: str = "base",
        language: str = "zh",
        device: str = "auto",
        compute_type: Optional[str] = None,
        beam_size: int = 1,
        initial_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Transcribe an audio file using pure-local faster-whisper (offline).

        engine 仅保留 local；传 agent/auto 时不做任何网络调用，直接提示：
        “转录由 Agent 原生执行，工具层仅导出任务书”。
        """
        if engine in ("agent", "auto"):
            raise RuntimeError(
                "转录由 Agent 原生执行，工具层仅导出任务书"
                "（transcribe() 为纯本地 faster-whisper 离线转录，engine 仅支持 local）。"
            )
        if engine != "local":
            raise ValueError(f"未知 engine: {engine!r}，仅支持 local。")

        path_obj = Path(audio_path).resolve()
        if not path_obj.exists():
            raise FileNotFoundError(f"Audio file not found: {path_obj}")

        # If input is a video file, automatically extract 64kbps 16kHz mono AAC audio first
        from .local_media import SUPPORTED_VIDEO_EXTS, LocalMediaParser
        if path_obj.suffix.lower() in SUPPORTED_VIDEO_EXTS:
            extracted_audio = path_obj.parent / f"{path_obj.stem}.m4a"
            if not extracted_audio.exists() or extracted_audio.stat().st_size == 0:
                print(f"[*] 检测到输入为视频文件 ({path_obj.suffix})，自动抽取轻量 64kbps 纯音频...")
                LocalMediaParser.extract_audio(path_obj, extracted_audio)
            path_obj = extracted_audio

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

    # Alias for backward compatibility
    transcribe_local = transcribe

    @staticmethod
    def format_seconds(seconds: float) -> str:
        s = int(round(seconds))
        hours = s // 3600
        minutes = (s % 3600) // 60
        secs = s % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
