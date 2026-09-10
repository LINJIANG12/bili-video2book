"""Xiaomi MiMo Omnimodal Provider (MiMo-V2.5 / MiMo-V2.5-Pro)."""

from __future__ import annotations

import asyncio
import base64
import os
from pathlib import Path
from typing import Callable, Optional

import httpx

from .base import (
    BaseMultimodalProvider,
    ProcessingResult,
    _ensure_inline_media_size,
    _extract_text_content,
    _require_media_file,
)


class MiMoProvider(BaseMultimodalProvider):
    """Xiaomi MiMo 2.5 Omnimodal Engine (1M context, MoE architecture)."""

    name = "mimo"
    default_model = "mimo-v2.5"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = api_key or os.environ.get("MIMO_API_KEY") or os.environ.get("XIAOMI_API_KEY")
        self.base_url = (
            base_url
            or os.environ.get("MIMO_BASE_URL")
            or "https://api.mimo.xiaomi.com/v1"
        )
        self.model = model or os.environ.get("MIMO_MODEL") or self.default_model

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
            raise ValueError("未检测到 MIMO_API_KEY，请在环境变量或配置中提供。")

        target_path = _require_media_file(media_path)
        _ensure_inline_media_size(target_path)
        file_size = target_path.stat().st_size

        if on_progress:
            on_progress(0.2, f"正在为小米 MiMo 全模态通道读取媒体 ({file_size / 1024:.1f} KB)...")

        with open(target_path, "rb") as f:
            raw_bytes = f.read()

        b64_data = base64.b64encode(raw_bytes).decode("utf-8")
        fmt = target_path.suffix.lstrip(".").lower()
        if fmt == "m4a":
            fmt = "aac"

        # Construct Omnimodal request payload (OpenAI-compatible multimodal format)
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "input_audio" if not visual else "video",
                            "input_audio": {"data": b64_data, "format": fmt} if not visual else None,
                            "video": {"data": b64_data, "format": fmt} if visual else None,
                        },
                    ],
                }
            ],
            "temperature": 0.2,
        }

        # Clean None values in message content
        for msg in payload["messages"]:
            msg["content"] = [
                {k: v for k, v in item.items() if v is not None}
                for item in msg["content"]
            ]

        if on_progress:
            on_progress(0.6, f"小米 MiMo 核心 ({self.model}) 正在进行端到端全模态时序推理...")

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
            raise RuntimeError(f"MiMo API 请求失败 ({resp.status_code}): {resp.text}")

        data = resp.json()
        text_out = _extract_text_content(data["choices"][0]["message"]["content"])

        if on_progress:
            on_progress(1.0, "小米 MiMo 全模态重构完成！")

        return ProcessingResult(
            text=text_out,
            provider_name="Xiaomi MiMo",
            model_name=self.model,
        )
