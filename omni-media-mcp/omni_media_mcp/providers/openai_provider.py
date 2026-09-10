"""OpenAI Audio & Vision Multimodal Provider (GPT-4o Audio / GPT-5 Series)."""

from __future__ import annotations

import asyncio
import base64
import os
from pathlib import Path
from typing import Callable, Optional

import httpx

from ..core.preprocessor import MediaPreprocessor
from ..core.temp_manager import ManagedTempDir
from .base import (
    BaseMultimodalProvider,
    ProcessingResult,
    _ensure_inline_media_size,
    _extract_text_content,
    _require_media_file,
)


class OpenAIProvider(BaseMultimodalProvider):
    name = "openai"
    default_model = "gpt-4o-audio-preview"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.base_url = base_url or os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1"
        self.model = model or os.environ.get("OPENAI_MODEL") or self.default_model

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def process(
        self,
        media_path: Path,
        prompt: str,
        visual: bool = False,
        on_progress: Optional[Callable[[float, str], None]] = None,
    ) -> ProcessingResult:
        if not self.is_available():
            raise ValueError("未检测到 OPENAI_API_KEY，请在环境变量或配置中提供。")

        target_path = _require_media_file(media_path)

        # Case 1: Audio only mode (Default speech / lecture)
        if not visual:
            # Guard against unbounded in-memory base64 of huge audio files.
            _ensure_inline_media_size(target_path)
            if on_progress:
                on_progress(0.2, "准备 OpenAI input_audio 格式音频载荷...")

            # OpenAI input_audio only accepts mp3/wav. Anything else (notably the
            # .m4a produced by read_audio) must be genuinely transcoded: sending
            # m4a bytes while declaring format="mp3" corrupts the payload.
            fmt = target_path.suffix.lstrip(".").lower()
            if fmt in ("mp3", "wav"):
                with open(target_path, "rb") as f:
                    b64_audio = base64.b64encode(f.read()).decode("utf-8")
            else:
                if on_progress:
                    on_progress(0.3, f"OpenAI 仅接受 mp3/wav，正在从 .{fmt} 真实转码为 mp3...")
                with ManagedTempDir(prefix="openai_audio_") as tmp_dir:
                    mp3_path = tmp_dir / f"{target_path.stem}.mp3"
                    await asyncio.to_thread(
                        MediaPreprocessor.extract_optimized_audio,
                        input_file=target_path,
                        output_file=mp3_path,
                        codec="libmp3lame",
                    )
                    if not mp3_path.exists() or mp3_path.stat().st_size == 0:
                        raise RuntimeError(f"OpenAI 音频转码失败：未生成 {mp3_path.name}")
                    b64_audio = base64.b64encode(mp3_path.read_bytes()).decode("utf-8")
                fmt = "mp3"

            payload = {
                "model": self.model,
                "modalities": ["text"],
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "input_audio",
                                "input_audio": {"data": b64_audio, "format": fmt},
                            },
                        ],
                    }
                ],
            }

        # Case 2: Visual mode (Sampled video frames + audio)
        else:
            # Frame extraction is bounded (fps=1.0, max_frames=60) but the source
            # is still decoded by ffmpeg, so it must run off the event loop.
            if on_progress:
                on_progress(0.2, "视频画面模式：正在进行 1 FPS 抽帧...")

            with ManagedTempDir(prefix="openai_frames_") as tmp_dir:
                frames = await asyncio.to_thread(
                    MediaPreprocessor.extract_video_keyframes,
                    target_path, output_dir=tmp_dir, fps=1.0, max_frames=60,
                )

                content_parts = [{"type": "text", "text": prompt}]
                for frame in frames:
                    with open(frame, "rb") as f:
                        b64_img = base64.b64encode(f.read()).decode("utf-8")
                    content_parts.append(
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"},
                        }
                    )

                payload = {
                    "model": self.model,
                    "messages": [{"role": "user", "content": content_parts}],
                }

        if on_progress:
            on_progress(0.6, f"OpenAI 正在进行多模态理解与文本生成...")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self.base_url.rstrip('/')}/chat/completions",
                headers=headers,
                json=payload,
            )

        if resp.status_code != 200:
            raise RuntimeError(f"OpenAI API 请求失败 ({resp.status_code}): {resp.text}")

        data = resp.json()
        text_out = _extract_text_content(data["choices"][0]["message"]["content"])

        if on_progress:
            on_progress(1.0, "OpenAI 多模态整理完成！")

        return ProcessingResult(
            text=text_out,
            provider_name="OpenAI",
            model_name=self.model,
        )
