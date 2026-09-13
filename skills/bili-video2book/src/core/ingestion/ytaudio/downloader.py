"""按目录分组下载音频，支持断点续跑（yt-dlp download archive）。"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple

from .config import Config
from .engine import Engine
from .utils import get_logger

# 输出模板：日期_标题_视频ID.扩展名
OUTTMPL = "%(upload_date)s_%(title)s_%(id)s.%(ext)s"


def count_archive(path: Optional[Path]) -> int:
    """统计 download archive 中已记录的条目数。"""
    if not path or not path.exists():
        return 0
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            return sum(1 for line in fh if line.strip())
    except OSError:
        return 0


def ensure_archive(output_dir: Path, slug: str) -> Path:
    archive_dir = output_dir / ".archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    return archive_dir / f"{slug}.txt"


def download_group(engine: Engine, cfg: Config, urls: List[str], dest_dir: Path,
                   archive: Optional[Path], label: str) -> Tuple[int, int]:
    """下载一组视频到同一目录。

    :return: ``(新增成功数, 请求总数)``
    """
    log = get_logger()
    if not urls:
        return 0, 0

    dest_dir.mkdir(parents=True, exist_ok=True)
    before = count_archive(archive)
    outtmpl = str(dest_dir / OUTTMPL)

    log.info("「%s」开始下载 %s 条 → %s", label, len(urls), dest_dir)
    engine.download(urls, outtmpl=outtmpl, archive=str(archive) if archive else None)

    after = count_archive(archive)
    done = max(after - before, 0)
    skipped = len(urls) - done
    log.info("「%s」完成：新增 %s 条%s", label, done,
             f"（跳过/失败 {skipped} 条）" if skipped else "")
    return done, len(urls)


def list_audio_files(directory: Path) -> List[Path]:
    """列出目录下的音频文件。"""
    exts = {".m4a", ".mp3", ".opus", ".flac", ".wav", ".ogg", ".webm"}
    if not directory.exists():
        return []
    return sorted(p for p in directory.rglob("*") if p.suffix.lower() in exts)
