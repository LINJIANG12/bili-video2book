"""通用工具：链接提取、文件名清洗、日志、可读体积等。"""

from __future__ import annotations

import logging
import re
import sys
import unicodedata

# 分享口令里的链接：排除空白与常见中英文标点
_URL_RE = re.compile(r"https?://[^\s，。！？、；：“”‘’（）【】《》]+")
_PURE_NUM_RE = re.compile(r"^(\d{15,})$")
_ILLEGAL_FS = re.compile(r'[\\/:*?"<>|\r\n\t]')
_MULTI_SPACE = re.compile(r"\s+")

_LOGGER_NAME = "dyaudio"


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


def extract_first_url(text: str) -> str:
    """从任意文本（分享口令 / 纯链接）中提取第一个 URL。"""
    if not text:
        return ""
    text = text.strip()
    if text.startswith("http://") or text.startswith("https://"):
        # 仍可能带空格后接描述，统一走正则
        pass
    match = _URL_RE.search(text)
    return match.group(0) if match else ""


def sanitize_filename(name: str, max_len: int = 80) -> str:
    """清洗为跨平台安全的文件名（保留中文），过长则截断。"""
    if not name:
        return "untitled"
    name = unicodedata.normalize("NFC", name)
    name = _ILLEGAL_FS.sub("_", name)
    name = _MULTI_SPACE.sub(" ", name).strip()
    name = name.strip(" .")
    if len(name) > max_len:
        name = name[:max_len].rstrip(" .")
    return name or "untitled"


def format_bytes(num: float) -> str:
    """人类可读的体积。"""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}"
        num /= 1024.0
    return f"{num:.1f}PB"


def is_numeric_id(text: str) -> bool:
    return bool(_PURE_NUM_RE.match(text.strip()))


def safe_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
