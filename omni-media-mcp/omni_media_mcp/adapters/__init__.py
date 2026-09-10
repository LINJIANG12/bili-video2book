"""Host adapters for OpenCode, ZCode, DeepSeek Harness, Codex, and Antigravity."""

from .antigravity import AntigravityAdapter
from .base import BaseHostAdapter
from .codex import CodexAdapter
from .dsh import DshAdapter
from .opencode import OpenCodeAdapter
from .registry import get_adapter, get_all_adapters, list_supported_targets
from .zcode import ZCodeAdapter

__all__ = [
    "BaseHostAdapter",
    "OpenCodeAdapter",
    "ZCodeAdapter",
    "DshAdapter",
    "CodexAdapter",
    "AntigravityAdapter",
    "get_adapter",
    "get_all_adapters",
    "list_supported_targets",
]
