"""OpenAI Codex Host Adapter with MCP and Open Agent Skills Support."""

from __future__ import annotations

import copy
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from .base import BaseHostAdapter, get_default_env_vars


class CodexAdapter(BaseHostAdapter):
    """Adapter for OpenAI Codex CLI and Open Agent Skills ecosystem."""

    target_id = "codex"
    display_name = "OpenAI Codex"

    def __init__(
        self,
        custom_config_path: Optional[str | Path] = None,
        custom_skill_dir: Optional[str | Path] = None,
    ):
        super().__init__(custom_config_path=custom_config_path)
        self.custom_skill_dir = Path(custom_skill_dir).resolve() if custom_skill_dir else None

    def get_config_path(self) -> Path:
        if self.custom_path:
            return self.custom_path

        cwd_codex = Path.cwd() / ".codex" / "config.json"
        if cwd_codex.exists():
            return cwd_codex

        return Path.home() / ".codex" / "config.json"

    def get_skill_target_path(self) -> Path:
        """Determines target path for omni-media SKILL.md."""
        if self.custom_skill_dir:
            return self.custom_skill_dir / "SKILL.md"

        # Check local .agents/skills
        local_skills = Path.cwd() / ".agents" / "skills"
        if local_skills.exists():
            return local_skills / "omni-media" / "SKILL.md"

        # Default to user global ~/.agents/skills
        return Path.home() / ".agents" / "skills" / "omni-media" / "SKILL.md"

    def get_bundled_skill_path(self) -> Path:
        """Returns bundled SKILL.md in omni_media_mcp distribution."""
        return Path(__file__).resolve().parent.parent / "skills" / "omni-media" / "SKILL.md"

    def build_entry(self) -> Dict[str, Any]:
        env = get_default_env_vars()
        # Codex CLI works best with file-based media paths to avoid stdio buffer bursting
        # and unsupported binary content deserialization issues.
        env["OMNI_MEDIA_OUTPUT_MODE"] = "file"
        return {
            "command": sys.executable,
            "args": ["-m", "omni_media_mcp.server"],
            "env": env,
        }

    def is_registered(self) -> bool:
        data = self.read_config()
        servers = data.get("mcpServers", {})
        mcp_registered = isinstance(servers, dict) and "omni-media" in servers
        return mcp_registered

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

    def apply(self) -> Tuple[bool, str]:
        ok, msg = super().apply()
        # Install skill file
        bundled_skill = self.get_bundled_skill_path()
        target_skill = self.get_skill_target_path()
        if bundled_skill.exists():
            target_skill.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(bundled_skill, target_skill)
            msg += f" 并同步技能至: {target_skill}"
        return ok, msg

    def unapply(self) -> Tuple[bool, str]:
        ok, msg = super().unapply()
        target_skill = self.get_skill_target_path()
        if target_skill.exists():
            try:
                target_skill.unlink()
                if not any(target_skill.parent.iterdir()):
                    target_skill.parent.rmdir()
                msg += f" 并移除技能文件: {target_skill}"
            except Exception:
                pass
        return ok, msg
