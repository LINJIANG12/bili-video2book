"""MiniMax Multimodal Provider (MiniMax H3 / abab 7)."""

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


class MiniMaxProvider(BaseMultimodalProvider):
    name = "minimax"
    default_model = "minimax-h3"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = api_key or os.environ.get("MINIMAX_API_KEY")
        self.base_url = (
            base_url
            or os.environ.get("MINIMAX_BASE_URL")
            or "https://api.minimax.chat/v1"
        )
        self.model = model or os.environ.get("MINIMAX_MODEL") or self.default_model

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
            raise ValueError("未检测到 MINIMAX_API_KEY，请在环境变量或配置中提供。")

        target_path = _require_media_file(media_path)
        _ensure_inline_media_size(target_path)

        if on_progress:
            on_progress(0.2, f"正在为 MiniMax ({self.model}) 准备音视频载荷...")

        with open(target_path, "rb") as f:
            raw_bytes = f.read()

        b64_data = base64.b64encode(raw_bytes).decode("utf-8")
        fmt = target_path.suffix.lstrip(".").lower()

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "audio" if not visual else "video",
                            "data": b64_data,
                            "format": fmt,
                        },
                    ],
                }
            ],
        }

        if on_progress:
            on_progress(0.6, "MiniMax 原生视音频核心正在执行多模态理解...")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(
                f"{self.base_url.rstrip('/')}/text/chatcompletion_v2",
                headers=headers,
                json=payload,
            )

        if resp.status_code != 200:
            raise RuntimeError(f"MiniMax API 请求失败 ({resp.status_code}): {resp.text}")

        data = resp.json()
        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError(f"MiniMax 返回数据异常: {data}")

        text_out = _extract_text_content(choices[0]["message"]["content"])

        if on_progress:
            on_progress(1.0, "MiniMax 整理完成！")

        return ProcessingResult(
            text=text_out,
            provider_name="MiniMax",
            model_name=self.model,
        )
