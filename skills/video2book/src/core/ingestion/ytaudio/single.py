"""单视频：解析并下载音频。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from .config import Config
from .downloader import OUTTMPL, count_archive, ensure_archive
from .engine import Engine
from .filters import is_regular_video
from .utils import get_logger, sanitize_filename, slugify


def resolve_video(engine: Engine, cfg: Config, url: str) -> Optional[Dict[str, Any]]:
    """提取视频元数据并做类型校验（只处理普通视频）。"""
    log = get_logger()
    info = engine.extract_video_info(url)
    if not info:
        return None

    # 播放列表/频道误入时，取不到单视频条目
    if info.get("_type") == "playlist" or "entries" in info:
        log.error("这看起来是播放列表或频道链接，请改用：python main.py channel \"%s\"", url)
        return None

    keep, reason = is_regular_video(info, cfg)
    if not keep:
        log.error("已跳过：%s（%s）", url, reason)
        return None

    log.info("标题：%s", info.get("title"))
    log.info("频道：%s", info.get("uploader") or info.get("channel") or "未知")
    duration = info.get("duration")
    if duration:
        minutes, seconds = divmod(int(duration), 60)
        log.info("时长：%s 分 %s 秒", minutes, seconds)
    return info


def download_single(engine: Engine, cfg: Config, url: str) -> Optional[Path]:
    """下载单个视频的音频，返回落盘目录。"""
    log = get_logger()
    info = resolve_video(engine, cfg, url)
    if not info:
        return None

    uploader = info.get("uploader") or info.get("channel") or "unknown"
    dest_dir = cfg.resolved_output_dir / "singles" / sanitize_filename(str(uploader))
    dest_dir.mkdir(parents=True, exist_ok=True)

    video_id = str(info.get("id") or "")
    archive = ensure_archive(cfg.resolved_output_dir, f"single_{slugify(str(uploader))}")
    before = count_archive(archive)

    outtmpl = str(dest_dir / OUTTMPL)
    engine.download([url], outtmpl=outtmpl, archive=str(archive))

    if count_archive(archive) > before:
        log.info("完成，输出目录：%s", dest_dir)
        return dest_dir

    if video_id:
        matches = [p for p in dest_dir.glob(f"*{video_id}.*") if p.suffix.lower() != ".part"]
        if matches:
            log.info("已存在，跳过：%s", matches[0].name)
            return dest_dir

    log.error("未能完成下载：%s", url)
    return None
