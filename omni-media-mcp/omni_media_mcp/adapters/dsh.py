"""DeepSeek Harness (dsh) Host Adapter for MCP Configuration."""

from __future__ import annotations

import copy
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from .base import BaseHostAdapter, get_default_env_vars


class DshAdapter(BaseHostAdapter):
    """Adapter for DeepSeek Harness (dsh) runtime."""

    target_id = "dsh"
    display_name = "DeepSeek Harness (dsh)"

    def get_config_path(self) -> Path:
        if self.custom_path:
            return self.custom_path

        # 1. Project level dsh.config.json or .dsh/config.json
        cwd_dsh = Path.cwd() / "dsh.config.json"
        if cwd_dsh.exists():
            return cwd_dsh
        cwd_dot = Path.cwd() / ".dsh" / "config.json"
        if cwd_dot.exists():
            return cwd_dot

        # 2. Global ~/.dsh/config.json
        return Path.home() / ".dsh" / "config.json"

    def build_entry(self) -> Dict[str, Any]:
        return {
            "command": sys.executable,
            "args": ["-m", "omni_media_mcp.server"],
            "env": get_default_env_vars(),
        }

    def is_registered(self) -> bool:
        data = self.read_config()
        servers = data.get("mcpServers", {})
        return isinstance(servers, dict) and "omni-media" in servers

    def build_applied_config(self, current_data: Dict[str, Any]) -> Dict[str, Any]:
        data = copy.deepcopy(current_data)
        if "mcpServers" not in data or not isinstance(data["mcpServers"], dict):
            data["mcpServers"] = {}
        data["mcpServers"]["omni-media"] = self.build_entry()
        return data

    def build_unapplied_config(self, current_data: Dict[str, Any]) -> Dict[str, Any]:
        data = copy.deepcopy(current_data)
        if "mcpServers" in data and isinstance(data["mcpServers"], dict) and "omni-media" in data["mcpServers"]:
            del data["mcpServers"]["omni-media"]
        return data
