"""ZCode (Z.ai) Host Adapter for MCP Configuration."""

from __future__ import annotations

import copy
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from .base import BaseHostAdapter, get_default_env_vars


class ZCodeAdapter(BaseHostAdapter):
    """Adapter for ZCode (Z.ai) coding agent."""

    target_id = "zcode"
    display_name = "ZCode (Z.ai)"

    def get_config_path(self) -> Path:
        if self.custom_path:
            return self.custom_path

        # 1. Project level .zcode/config.json or zcode.json
        cwd_zcode = Path.cwd() / ".zcode" / "config.json"
        if cwd_zcode.exists():
            return cwd_zcode
        cwd_json = Path.cwd() / "zcode.json"
        if cwd_json.exists():
            return cwd_json

        # 2. User level ~/.zcode/cli/config.json (canonical)
        cli_config = Path.home() / ".zcode" / "cli" / "config.json"
        if cli_config.exists() or (Path.home() / ".zcode" / "cli").exists():
            return cli_config

        # 3. Fallback to ~/.zcode/config.json or ~/.zcode/mcp_config.json
        legacy_config = Path.home() / ".zcode" / "config.json"
        if legacy_config.exists():
            return legacy_config

        return cli_config

    def build_entry(self) -> Dict[str, Any]:
        return {
            "type": "stdio",
            "command": sys.executable,
            "args": ["-m", "omni_media_mcp.server"],
            "env": get_default_env_vars(),
            "enabled": True,
        }

    def is_registered(self) -> bool:
        data = self.read_config()
        # Canonical schema: mcp.servers.<name>
        mcp = data.get("mcp", {})
        if isinstance(mcp, dict):
            servers = mcp.get("servers", {})
            if isinstance(servers, dict) and "omni-media" in servers:
                return True
        # Compatibility schema: mcpServers.<name>
        legacy_servers = data.get("mcpServers", {})
        if isinstance(legacy_servers, dict) and "omni-media" in legacy_servers:
            return True
        return False

    def build_applied_config(self, current_data: Dict[str, Any]) -> Dict[str, Any]:
        data = copy.deepcopy(current_data)
        if "mcp" not in data or not isinstance(data["mcp"], dict):
            data["mcp"] = {}
        if "servers" not in data["mcp"] or not isinstance(data["mcp"]["servers"], dict):
            data["mcp"]["servers"] = {}
        data["mcp"]["servers"]["omni-media"] = self.build_entry()
        return data

    def build_unapplied_config(self, current_data: Dict[str, Any]) -> Dict[str, Any]:
        data = copy.deepcopy(current_data)
        if "mcp" in data and isinstance(data["mcp"], dict) and "servers" in data["mcp"]:
            if isinstance(data["mcp"]["servers"], dict) and "omni-media" in data["mcp"]["servers"]:
                del data["mcp"]["servers"]["omni-media"]
        if "mcpServers" in data and isinstance(data["mcpServers"], dict) and "omni-media" in data["mcpServers"]:
            del data["mcpServers"]["omni-media"]
        return data
