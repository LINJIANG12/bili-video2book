"""通用工具：频道 URL 归一化、文件名清洗、日志、可读体积。"""

from __future__ import annotations

import logging
import re
import sys
import unicodedata

_LOGGER_NAME = "ytaudio"

_CHANNEL_RE = re.compile(
    r"(https?://(?:www\.|m\.)?youtube\.com/"
    r"(?:channel/|c/|user/|@)[^/?#\s]+)",
    re.IGNORECASE,
)

_TAB_SUFFIX_RE = re.compile(
    r"/(?:videos|shorts|live|streams|playlists|community|about|featured|releases|podcasts|store|channels|search)/?$",
    re.IGNORECASE,
)

_VIDEO_ID_RE = re.compile(r"(?:v=|/shorts/|/embed/|/live/|youtu\.be/)([0-9A-Za-z_-]{11})")

_ILLEGAL_FS = re.compile(r'[\\/:*?"<>|\r\n\t]')
_MULTI_SPACE = re.compile(r"\s+")


def setup_logger(verbose: bool = False) -> logging.Logger:
    """配置并返回全局 logger（幂等）。"""
    logger = logging.getLogger(_LOGGER_NAME)
    if logger.handlers:
        logger.setLevel(logging.DEBUG if verbose else logging.INFO)
        return logger

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%H:%M:%S")
    )
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.propagate = False
    return logger


def get_logger() -> logging.Logger:
    return logging.getLogger(_LOGGER_NAME)


def extract_video_id(url: str) -> str:
    """从各类视频链接中提取 11 位视频 ID。"""
    match = _VIDEO_ID_RE.search(url or "")
    return match.group(1) if match else ""


def is_video_url(url: str) -> bool:
    """判断是否为单个视频链接（而非频道/播放列表主页）。"""
    if not url:
        return False
    if re.search(r"/(?:channel|c|user)/|youtube\.com/@", url, re.IGNORECASE):
        return False
    return bool(_VIDEO_ID_RE.search(url))


def normalize_channel_base(url: str) -> str:
    """把频道主页链接归一化为不带标签页的基地址。"""
    if not url:
        return ""
    match = _CHANNEL_RE.search(url)
    if not match:
        return ""
    base = match.group(1).rstrip("/")
    return _TAB_SUFFIX_RE.sub("", base)


def channel_urls(base: str) -> tuple:
    """返回 (视频列表URL, 播放列表URL, 短视频URL)。"""
    return base + "/videos", base + "/playlists", base + "/shorts"


def sanitize_filename(name: str, max_len: int = 80) -> str:
    """清洗为跨平台安全的文件名（保留中文）。"""
    if not name:
        return "untitled"
    name = unicodedata.normalize("NFC", name)
    name = _ILLEGAL_FS.sub("_", name)
    name = _MULTI_SPACE.sub(" ", name).strip()
    name = name.strip(" .")
    if len(name) > max_len:
        name = name[:max_len].rstrip(" .")
    return name or "untitled"


def slugify(name: str, max_len: int = 60) -> str:
    """生成安全的目录/文件名片段。"""
    if not name:
        return "unknown"
    out = []
    for ch in unicodedata.normalize("NFC", name):
        if ch.isalnum() or ch in ("-", "_", "."):
            out.append(ch)
        elif ch.isspace():
            out.append("_")
    text = "".join(out).strip("_.")
    return text[:max_len].rstrip("_.") or "unknown"


def format_bytes(num: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}"
        num /= 1024.0
    return f"{num:.1f}PB"


def safe_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
