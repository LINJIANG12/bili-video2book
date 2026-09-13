#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Local filesystem media provider."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

from src.core.local_media import LocalMediaParser
from .base import BaseMediaProvider, IngestionError


class LocalMediaProvider(BaseMediaProvider):
    name = "local"
    display_name = "本地音视频"

    def match(self, target: str) -> bool:
        return LocalMediaParser.is_local_media(target)

    def probe(self, target: str, **kwargs: Any) -> Dict[str, Any]:
        info = LocalMediaParser.parse(target)
        info["source_type"] = "local"
        return info

    def fetch_audio(
        self,
        episode: Dict[str, Any],
        output_file: Path,
        *,
        force: bool = False,
        progress_cb: Optional[Callable[[Dict[str, Any]], None]] = None,
        **kwargs: Any,
    ) -> Path:
        src_path = episode.get("filepath") or kwargs.get("source_path")
        if not src_path:
            raise IngestionError(f"本地分集缺少源文件路径: {episode.get('title')}")
        output_file.parent.mkdir(parents=True, exist_ok=True)
        LocalMediaParser.extract_audio(src_path, output_file)
        if progress_cb:
            progress_cb({"status": "downloaded", "file": str(output_file)})
        return output_file

    def check_readiness(self) -> Tuple[bool, str]:
        ffmpeg_bin = shutil.which("ffmpeg")
        if ffmpeg_bin:
            return True, f"就绪 ({ffmpeg_bin})"
        return False, "缺少 ffmpeg，无法提取本地音轨"
