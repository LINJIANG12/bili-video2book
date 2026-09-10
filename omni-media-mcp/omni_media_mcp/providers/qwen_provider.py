"""Alibaba Qwen Multimodal Provider (Qwen2.5-VL / Qwen3-Omni)."""

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


class QwenProvider(BaseMultimodalProvider):
    name = "qwen"
    default_model = "qwen2.5-vl-72b-instruct"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = api_key or os.environ.get("DASHSCOPE_API_KEY") or os.environ.get("QWEN_API_KEY")
        self.base_url = (
            base_url
            or os.environ.get("DASHSCOPE_BASE_URL")
            or "https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        self.model = model or os.environ.get("QWEN_MODEL") or self.default_model

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
            raise ValueError("未检测到 DASHSCOPE_API_KEY，请在环境变量或配置中提供。")

        target_path = _require_media_file(media_path)

        if on_progress:
            on_progress(0.2, f"正在为通义千问 ({self.model}) 准备多模态数据载荷...")

        # If visual or video container
        if visual or target_path.suffix.lower() in [".mp4", ".mkv", ".webm"]:
            with ManagedTempDir(prefix="qwen_frames_") as tmp_dir:
                frames = await asyncio.to_thread(
                    MediaPreprocessor.extract_video_keyframes,
                    target_path, output_dir=tmp_dir, fps=1.0, max_frames=80,
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
        else:
            # Audio mode: bound the in-memory base64 payload size.
            _ensure_inline_media_size(target_path)
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
        }

        if on_progress:
            on_progress(0.6, f"通义千问大模型正在进行多模态时空理解与公式推导演算...")

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
            raise RuntimeError(f"DashScope Qwen API 请求失败 ({resp.status_code}): {resp.text}")

        data = resp.json()
        text_out = _extract_text_content(data["choices"][0]["message"]["content"])

        if on_progress:
            on_progress(1.0, "通义千问整理完成！")

        return ProcessingResult(
            text=text_out,
            provider_name="Alibaba Qwen",
            model_name=self.model,
        )
