"""OpenCode Host Adapter for MCP Configuration."""

from __future__ import annotations

import copy
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from .base import BaseHostAdapter, get_default_env_vars


class OpenCodeAdapter(BaseHostAdapter):
    """Adapter for OpenCode AI coding assistant."""

    target_id = "opencode"
    display_name = "OpenCode"

    def get_config_path(self) -> Path:
        if self.custom_path:
            return self.custom_path

        # 1. Project level opencode.jsonc / opencode.json
        cwd_jsonc = Path.cwd() / "opencode.jsonc"
        if cwd_jsonc.exists():
            return cwd_jsonc
        cwd_json = Path.cwd() / "opencode.json"
        if cwd_json.exists():
            return cwd_json

        # 2. Global ~/.config/opencode/opencode.jsonc
        global_path = Path.home() / ".config" / "opencode" / "opencode.jsonc"
        if global_path.exists():
            return global_path

        # 3. Windows AppData fallback
        appdata = os.environ.get("APPDATA")
        if appdata:
            win_path = Path(appdata) / "opencode" / "opencode.json"
            if win_path.exists():
                return win_path

        return global_path

    def build_entry(self) -> Dict[str, Any]:
        return {
            "type": "local",
            "command": sys.executable,
            "args": ["-m", "omni_media_mcp.server"],
            "env": get_default_env_vars(),
            "enabled": True,
        }

    def is_registered(self) -> bool:
        data = self.read_config()
        mcp = data.get("mcp", {})
        return isinstance(mcp, dict) and "omni-media" in mcp

    def build_applied_config(self, current_data: Dict[str, Any]) -> Dict[str, Any]:
        data = copy.deepcopy(current_data)
        if "mcp" not in data or not isinstance(data["mcp"], dict):
            data["mcp"] = {}
        data["mcp"]["omni-media"] = self.build_entry()
        return data

    def build_unapplied_config(self, current_data: Dict[str, Any]) -> Dict[str, Any]:
        data = copy.deepcopy(current_data)
        if "mcp" in data and isinstance(data["mcp"], dict) and "omni-media" in data["mcp"]:
            del data["mcp"]["omni-media"]
        return data
