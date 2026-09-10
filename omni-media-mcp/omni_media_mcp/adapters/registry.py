"""Registry of Host Adapters."""

from __future__ import annotations

from typing import Dict, List, Type

from .antigravity import AntigravityAdapter
from .base import BaseHostAdapter
from .codex import CodexAdapter
from .dsh import DshAdapter
from .opencode import OpenCodeAdapter
from .zcode import ZCodeAdapter

ADAPTER_MAP: Dict[str, Type[BaseHostAdapter]] = {
    "opencode": OpenCodeAdapter,
    "zcode": ZCodeAdapter,
    "dsh": DshAdapter,
    "codex": CodexAdapter,
    "antigravity": AntigravityAdapter,
}


def get_adapter(target: str, custom_config_path: str | None = None) -> BaseHostAdapter:
    """Returns an adapter instance by target ID."""
    key = target.lower().strip()
    adapter_cls = ADAPTER_MAP.get(key)
    if not adapter_cls:
        valid = ", ".join(ADAPTER_MAP.keys())
        raise ValueError(f"未知宿主目标: '{target}'。支持的目标: {valid}, all")
    return adapter_cls(custom_config_path=custom_config_path)


def list_supported_targets() -> List[str]:
    """Returns list of all supported target identifiers."""
    return list(ADAPTER_MAP.keys())


def get_all_adapters() -> List[BaseHostAdapter]:
    """Returns instances of all registered adapters."""
    return [cls() for cls in ADAPTER_MAP.values()]
