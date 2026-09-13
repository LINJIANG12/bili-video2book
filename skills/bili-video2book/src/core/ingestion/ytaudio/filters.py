"""类型过滤：只处理普通视频。

YouTube 一个频道下可能混着多种内容，本模块统一挡在门外：

* Shorts 短视频 —— 链接形态为 /shorts/<id>
* 直播 / 回放 / 预约 —— live_status 为 is_live / is_upcoming / was_live
* 非视频条目 —— 播放列表、频道卡片等（_type 不是视频）
* 过短视频 —— 由 min_duration 配置（默认 0，即不启用）
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from .config import Config
from .utils import get_logger

LIVE_STATUSES = ("is_live", "is_upcoming", "was_live", "post_live")

# YouTube 自动生成的播放列表（不是用户创建的主题合集），归类时应忽略
AUTO_PLAYLIST_TITLES = (
    "上传的视频", "上傳的影片", "Uploads",
    "热门视频", "熱門影片", "Popular videos",
    "直播回放", "直播", "Live streams", "Lives",
    "短视频", "Shorts", "短影音",
    "最新视频", "Latest videos",
)


def _entry_url(entry: Dict[str, Any]) -> str:
    return str(entry.get("url") or entry.get("webpage_url") or "")


def is_shorts(entry: Dict[str, Any]) -> bool:
    """是否为 Shorts 短视频。"""
    return "/shorts/" in _entry_url(entry)


def is_live(entry: Dict[str, Any]) -> bool:
    """是否为直播/回放/预约直播。"""
    if entry.get("live_status") in LIVE_STATUSES:
        return True
    return entry.get("was_live") is True


def is_regular_video(entry: Dict[str, Any], cfg: Optional[Config] = None) -> Tuple[bool, str]:
    """判断是否应纳入下载。

    :return: ``(是否保留, 被拒绝的原因)``；保留时原因为空串。
    """
    if not isinstance(entry, dict):
        return False, "非条目对象"

    entry_type = entry.get("_type")
    if entry_type not in (None, "url", "video", "url_transparent", "multi_video"):
        return False, f"非视频条目(_type={entry_type})"

    if not entry.get("id"):
        return False, "缺少视频 ID"

    if is_shorts(entry):
        return False, "短视频(Shorts)"

    if is_live(entry):
        return False, "直播/回放"

    if cfg is not None:
        min_duration = getattr(cfg, "min_duration", 0) or 0
        if min_duration > 0:
            try:
                duration = int(entry.get("duration") or 0)
            except (TypeError, ValueError):
                duration = 0
            if 0 < duration < min_duration:
                return False, f"时长过短({duration}s)"

    return True, ""


def is_auto_playlist(title: str) -> bool:
    """是否为 YouTube 自动生成的播放列表（不应视作合集）。"""
    if not title:
        return False
    return title.strip() in AUTO_PLAYLIST_TITLES


def make_match_filter(cfg: Config):
    """构造 yt-dlp 的 match_filter：下载阶段再兜一道类型过滤。

    返回非 None 的字符串表示跳过该条，字符串作为原因写入日志。
    """

    def match_filter(info: Dict[str, Any], *args, **kwargs) -> Optional[str]:
        incomplete = kwargs.get("incomplete", False)
        entry = dict(info or {})
        if incomplete:
            if is_shorts(entry):
                return "短视频(Shorts)"
            return None

        keep, reason = is_regular_video(entry, cfg)
        if keep:
            return None
        get_logger().debug("跳过 %s：%s", entry.get("id"), reason)
        return reason

    return match_filter
