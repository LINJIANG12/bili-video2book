"""Abstract Base Class for Multimodal Model Providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from ..core.limits import MAX_INLINE_BYTES


@dataclass
class ProcessingResult:
    text: str
    provider_name: str
    model_name: str
    tokens_consumed: Optional[int] = None
    cost_usd_estimate: Optional[float] = None
    media_duration_seconds: Optional[float] = None


def _extract_text_content(content: object) -> str:
    """Normalizes a provider's chat-completion ``message.content`` into ``str``.

    Several upstreams (MiniMax, MiMo, Qwen, DeepSeek, OpenAI) return content as
    either a plain ``str``, ``None``, or a list of content blocks
    (e.g. ``[{"type": "text", "text": "..."}, ...]``).  Accessing
    ``data["choices"][0]["message"]["content"]`` raw can therefore yield
    ``None`` or a ``list`` and crash callers downstream.  This helper guarantees
    a ``str`` return, raising a clear error only when no textual content exists.
    """
    if content is None:
        raise RuntimeError("模型返回了空的 message.content（无文本输出）。")
    if isinstance(content, str):
        return content
    if isinstance(content, (list, tuple)):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                # Prefer the standard text key; fall back to 'text'-typed blocks.
                text = block.get("text") or block.get("content")
                if isinstance(text, str) and text.strip():
                    parts.append(text)
            elif isinstance(block, str) and block.strip():
                parts.append(block)
        joined = "\n".join(parts).strip()
        if joined:
            return joined
        raise RuntimeError("模型返回了空的内容列表，无法提取文本。")
    if isinstance(content, dict):
        for key in ("text", "content"):
            val = content.get(key)
            if isinstance(val, str) and val.strip():
                return val
    raise RuntimeError(f"无法解析模型返回的 message.content 类型: {type(content).__name__}")


def _ensure_inline_media_size(media_path: Path) -> None:
    """Raises a clear error when a file exceeds the safe in-memory base64 cap.

    Providers that read the whole file and base64-encode it inline (OpenAI,
    MiniMax, MiMo, Qwen, DeepSeek) can exhaust memory on very large inputs.
    Callers should route such files to an upload path or slice them first.
    """
    size = Path(media_path).stat().st_size
    if size > MAX_INLINE_BYTES:
        raise ValueError(
            f"媒体文件过大 ({size / (1024 * 1024):.1f} MiB) 不适合内联发送，"
            f"上限为 {MAX_INLINE_BYTES / (1024 * 1024):.0f} MiB。"
            f"请先切片/压缩，或使用支持文件上传的 provider。"
        )
    return size


def _require_media_file(media_path: Path) -> Path:
    """Resolves and verifies a media path exists and is a file."""
    target = Path(media_path).resolve()
    if not target.exists():
        raise FileNotFoundError(f"媒体文件不存在: {target}")
    if not target.is_file():
        raise ValueError(f"路径不是文件: {target}")
    return target


class BaseMultimodalProvider(ABC):
    """Abstract interface defining uniform media processing across vendors."""

    name: str = "base"
    default_model: str = "default"

    @abstractmethod
    def is_available(self) -> bool:
        """Returns True if the provider is configured (e.g. API key present)."""
        pass

    @abstractmethod
    async def process(
        self,
        media_path: Path,
        prompt: str,
        visual: bool = False,
        on_progress: Optional[Callable[[float, str], None]] = None,
    ) -> ProcessingResult:
        """Processes the media file using the provider's multimodal API."""
        pass
