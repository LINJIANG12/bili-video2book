"""Google Gemini Multimodal Provider (Gemini 2.5/3.0/3.8 Flash & Pro)."""

from __future__ import annotations

import asyncio
import mimetypes
import os
import time
from pathlib import Path
from typing import Callable, Optional

from ..core.limits import MAX_INLINE_BYTES, UPLOAD_POLL_TIMEOUT_SEC
from .base import (
    BaseMultimodalProvider,
    ProcessingResult,
    _extract_text_content,
    _require_media_file,
)


class GeminiProvider(BaseMultimodalProvider):
    name = "gemini"
    default_model = "gemini-2.5-flash"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        self.model = model or os.environ.get("GEMINI_MODEL") or self.default_model

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
            raise ValueError("未检测到 GEMINI_API_KEY，请在环境变量或配置中提供。")

        from google import genai
        from google.genai import types

        client = genai.Client(api_key=self.api_key)
        target_path = _require_media_file(media_path)
        file_size = target_path.stat().st_size
        mime_type, _ = mimetypes.guess_type(target_path.name)
        if not mime_type:
            mime_type = "audio/mp4" if target_path.suffix.lower() in [".m4a", ".mp4"] else "audio/mpeg"

        uploaded_file = None
        try:
            # Case 1: Small files (under the inline cap) -> Direct Inline Data
            if file_size < MAX_INLINE_BYTES:
                if on_progress:
                    on_progress(0.3, "正在以内存 InlineData 模式快速封包媒体...")
                with open(target_path, "rb") as f:
                    file_bytes = f.read()

                media_part = types.Part.from_bytes(data=file_bytes, mime_type=mime_type)
                contents = [media_part, prompt]

            # Case 2: Large files (>= 20MB) -> Gemini Files API with auto-cleanup
            else:
                if on_progress:
                    on_progress(0.2, f"大媒体文件 ({file_size / (1024*1024):.1f}MB)，通过 Gemini Files API 传输...")
                # Run synchronous upload in thread pool
                uploaded_file = await asyncio.to_thread(
                    client.files.upload,
                    file=target_path,
                )

                # Poll until ACTIVE, bounded by a hard deadline so a stuck remote
                # index never hangs the MCP event loop forever.
                if on_progress:
                    on_progress(0.5, "等待云端多模态索引激活...")
                deadline = time.monotonic() + UPLOAD_POLL_TIMEOUT_SEC
                while uploaded_file.state.name == "PROCESSING":
                    if time.monotonic() > deadline:
                        raise TimeoutError(
                            f"Gemini Files API 媒体索引超时（>{UPLOAD_POLL_TIMEOUT_SEC}s）："
                            f"{target_path.name} 长时间停留在 PROCESSING 状态。"
                        )
                    await asyncio.sleep(2)
                    uploaded_file = await asyncio.to_thread(client.files.get, name=uploaded_file.name)

                if uploaded_file.state.name == "FAILED":
                    raise RuntimeError(f"Gemini Files API 媒体处理失败: {uploaded_file.error}")

                contents = [uploaded_file, prompt]

            if on_progress:
                on_progress(0.7, f"Gemini 原生多模态核心 ({self.model}) 正在深度理解与推导...")

            response = await asyncio.to_thread(
                client.models.generate_content,
                model=self.model,
                contents=contents,
            )

            if on_progress:
                on_progress(1.0, "完成转录与结构化整理！")

            text_result = response.text or ""
            return ProcessingResult(
                text=text_result,
                provider_name="Google Gemini",
                model_name=self.model,
            )

        finally:
            # Guarantee remote file destruction
            if uploaded_file:
                try:
                    await asyncio.to_thread(client.files.delete, name=uploaded_file.name)
                except Exception:
                    pass
