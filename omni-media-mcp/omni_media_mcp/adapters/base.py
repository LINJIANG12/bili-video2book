"""Base Host Adapter for FastCtx-style MCP configuration management."""

from __future__ import annotations

import difflib
import json
import os
import re
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


def strip_json_comments(text: str) -> str:
    """Strips single-line and multi-line comments from JSONC text while preserving string literals."""
    pattern = r'("(?:\\.|[^"\\])*")|(/\*[\s\S]*?\*/|//[^\r\n]*)'

    def replace(match):
        if match.group(1):
            return match.group(1)
        return ""

    return re.sub(pattern, replace, text)


def get_default_env_vars() -> Dict[str, str]:
    """Returns active provider API keys and environment variables."""
    keys = [
        "GEMINI_API_KEY",
        "MIMO_API_KEY",
        "OPENAI_API_KEY",
        "DASHSCOPE_API_KEY",
        "DEEPSEEK_API_KEY",
        "MINIMAX_API_KEY",
    ]
    env_vars: Dict[str, str] = {}
    for k in keys:
        v = os.environ.get(k)
        if v:
            env_vars[k] = v
    # Inject PYTHONPATH to current module's root
    proj_root = str(Path(__file__).resolve().parent.parent.parent)
    env_vars["PYTHONPATH"] = proj_root
    return env_vars


# JSON lines that assign an API_KEY env var, e.g.  "OPENAI_API_KEY": "sk-..."
# Optional leading diff prefix ([+- ]) is allowed because these diffs are
# rendered through unified_diff which prefixes every content line.
_SECRET_ENV_LINE_RE = re.compile(
    r'(^[+\- ]*\s*"[A-Z0-9_]*API_KEY"\s*:\s*)"([^"\\]*(?:\\.[^"\\]*)*)"',
    re.MULTILINE,
)


def _mask_secrets_in_diff(diff: str) -> str:
    """Redacts provider API-key values inside a unified-diff text.

    ``preview_apply``/``preview_unapply`` render the new host JSONC (which injects
    real provider API keys into the env block).  Returning that raw to the caller
    would echo secrets to the terminal/agent.  This masks any ``*_API_KEY`` value
    while preserving the surrounding diff structure.
    """
    if not diff:
        return diff
    return _SECRET_ENV_LINE_RE.sub(r'\1"***REDACTED***"', diff)


class BaseHostAdapter(ABC):
    """Abstract Base Class for host MCP integrations."""

    target_id: str = "base"
    display_name: str = "Base Host"

    def __init__(self, custom_config_path: Optional[str | Path] = None):
        self.custom_path = Path(custom_config_path).resolve() if custom_config_path else None

    @abstractmethod
    def get_config_path(self) -> Path:
        """Returns the target configuration file path."""
        pass

    def read_config(self) -> Dict[str, Any]:
        """Reads and parses current configuration safely."""
        path = self.get_config_path()
        if not path.exists():
            return {}
        try:
            raw = path.read_text(encoding="utf-8")
            cleaned = strip_json_comments(raw).strip()
            if not cleaned:
                return {}
            return json.loads(cleaned)
        except Exception:
            return {}

    def write_config(self, data: Dict[str, Any]) -> None:
        """Atomically writes configuration data to target path."""
        path = self.get_config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        content = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
        path.write_text(content, encoding="utf-8")

    @abstractmethod
    def build_entry(self) -> Dict[str, Any]:
        """Builds the server configuration entry for this host."""
        pass

    @abstractmethod
    def is_registered(self) -> bool:
        """Checks if omni-media is currently registered in this host configuration."""
        pass

    @abstractmethod
    def build_applied_config(self, current_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generates new configuration dictionary with omni-media injected."""
        pass

    @abstractmethod
    def build_unapplied_config(self, current_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generates new configuration dictionary with omni-media removed."""
        pass

    def preview_apply(self) -> Tuple[bool, str, Dict[str, Any]]:
        """Previews the diff of applying the configuration.

        Returns:
            (has_changes, diff_text, new_config)
        """
        current = self.read_config()
        new_data = self.build_applied_config(current)

        old_str = json.dumps(current, indent=2, ensure_ascii=False) + "\n" if current else "{\n}\n"
        new_str = json.dumps(new_data, indent=2, ensure_ascii=False) + "\n"

        if old_str == new_str:
            return False, "", new_data

        diff = "".join(
            difflib.unified_diff(
                old_str.splitlines(keepends=True),
                new_str.splitlines(keepends=True),
                fromfile=f"a/{self.get_config_path().name}",
                tofile=f"b/{self.get_config_path().name}",
            )
        )
        return True, _mask_secrets_in_diff(diff), new_data

    def preview_unapply(self) -> Tuple[bool, str, Dict[str, Any]]:
        """Previews the diff of removing omni-media configuration.

        Returns:
            (has_changes, diff_text, new_config)
        """
        current = self.read_config()
        if not self.is_registered():
            return False, "", current

        new_data = self.build_unapplied_config(current)
        old_str = json.dumps(current, indent=2, ensure_ascii=False) + "\n"
        new_str = json.dumps(new_data, indent=2, ensure_ascii=False) + "\n"

        diff = "".join(
            difflib.unified_diff(
                old_str.splitlines(keepends=True),
                new_str.splitlines(keepends=True),
                fromfile=f"a/{self.get_config_path().name}",
                tofile=f"b/{self.get_config_path().name}",
            )
        )
        return True, _mask_secrets_in_diff(diff), new_data

    def apply(self) -> Tuple[bool, str]:
        """Applies registration to host configuration."""
        has_change, diff, new_data = self.preview_apply()
        if not has_change:
            return True, "配置已是最新，无需修改。"
        self.write_config(new_data)
        return True, f"成功配置到 {self.display_name} ({self.get_config_path()})"

    def unapply(self) -> Tuple[bool, str]:
        """Removes omni-media entry from host configuration."""
        if not self.is_registered():
            return True, f"{self.display_name} 中未检测到 omni-media 配置，跳过。"
        has_change, diff, new_data = self.preview_unapply()
        self.write_config(new_data)
        return True, f"成功从 {self.display_name} 移除配置。"

    def check_status(self) -> Dict[str, Any]:
        """Checks configuration status and returns standard diagnostic report."""
        path = self.get_config_path()
        file_exists = path.exists()
        registered = self.is_registered()

        if registered:
            status = "PASS"
            msg = f"已正确挂载 ({path})"
        elif file_exists:
            status = "INFO"
            msg = f"配置文件存在，但未挂载 omni-media ({path})"
        else:
            status = "INFO"
            msg = f"未检测到宿主配置文件 ({path})"

        return {
            "target": self.target_id,
            "display_name": self.display_name,
            "path": str(path),
            "file_exists": file_exists,
            "registered": registered,
            "status": status,
            "detail": msg,
        }
