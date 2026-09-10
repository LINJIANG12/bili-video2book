"""DeepSeek Vision Multimodal Provider (DeepSeek-V4-Flash-Vision-Exp)."""

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


class DeepSeekProvider(BaseMultimodalProvider):
    name = "deepseek"
    default_model = "deepseek-v4-flash-vision-exp"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        self.base_url = (
            base_url
            or os.environ.get("DEEPSEEK_BASE_URL")
            or "https://api.deepseek.com/v1"
        )
        self.model = model or os.environ.get("DEEPSEEK_MODEL") or self.default_model

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
            raise ValueError("未检测到 DEEPSEEK_API_KEY，请在环境变量或配置中提供。")

        target_path = _require_media_file(media_path)

        # Video / visual path: sample keyframes into bounded JPEG payload.
        # (Original code always frame-extracted even for audio-only files, which
        #  produced 0 frames and silently degenerated to text-only. Route pure
        #  audio through an inline audio payload instead.)
        if visual or target_path.suffix.lower() in [".mp4", ".mkv", ".mov", ".webm", ".avi"]:
            if on_progress:
                on_progress(0.2, f"正在为 DeepSeek 视觉模型 ({self.model}) 准备高清时序关键帧...")

            with ManagedTempDir(prefix="deepseek_frames_") as tmp_dir:
                frames = await asyncio.to_thread(
                    MediaPreprocessor.extract_video_keyframes,
                    target_path, output_dir=tmp_dir, fps=1.0, max_frames=50,
                )

                content_parts = [{"type": "text", "text": prompt}]
                for f in frames:
                    with open(f, "rb") as img_f:
                        b64_img = base64.b64encode(img_f.read()).decode("utf-8")
                    content_parts.append(
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"},
                        }
                    )

            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": content_parts}],
                "temperature": 0.2,
            }
        else:
            # Audio-only path: guard in-memory base64 and send inline audio.
            _ensure_inline_media_size(target_path)
            if on_progress:
                on_progress(0.2, f"正在为 DeepSeek ({self.model}) 准备音频载荷...")
            with open(target_path, "rb") as af:
                b64_audio = base64.b64encode(af.read()).decode("utf-8")
            fmt = target_path.suffix.lstrip(".").lower()
            content_parts = [
                {"type": "text", "text": prompt},
                {
                    "type": "input_audio",
                    "input_audio": {"data": b64_audio, "format": fmt},
                },
            ]
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": content_parts}],
                "temperature": 0.2,
            }

        if on_progress:
            on_progress(0.6, "DeepSeek 正在执行多模态理解与整理...")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(
                f"{self.base_url.rstrip('/')}/chat/completions",
                headers=headers,
                json=payload,
            )

        if resp.status_code != 200:
            raise RuntimeError(f"DeepSeek API 请求失败 ({resp.status_code}): {resp.text}")

        data = resp.json()
        text_out = _extract_text_content(data["choices"][0]["message"]["content"])

        if on_progress:
            on_progress(1.0, "DeepSeek 整理完成！")

        return ProcessingResult(
            text=text_out,
            provider_name="DeepSeek",
            model_name=self.model,
        )
