"""yt-dlp 引擎封装：选项构造、签名与反爬参数、限速与重试。

YouTube 侧的「请求签名 / 反爬」由三层构成，本模块把它们统一装配进 yt-dlp：

1. **播放器签名（n-sig / cipher）** —— YouTube 把签名算法藏进 player JS，
   由 yt-dlp 负责解析与求解；我们通过 ``player_client`` 选择更不容易被限流的
   Innertube 客户端链（``web_safari`` / ``tv`` / ``web_embedded`` 等）。
2. **PO Token / visitorData** —— 部分客户端（web、mweb、android、ios 等）现在要求
   携带 Proof-of-Origin 令牌，否则取流返回 403。本模块把 ``po_token`` /
   ``visitor_data`` 透传给 yt-dlp 的 youtube extractor args。
3. **限速与重试** —— ``sleep_requests`` / ``sleep_interval`` 控制请求与下载间隔，
   ``retries`` / ``fragment_retries`` / ``extractor_retries`` 控制各级重试。
"""

from __future__ import annotations

import shutil
from typing import Any, Dict, List, Optional

from .config import Config
from .filters import make_match_filter
from .utils import get_logger


def yt_dlp_version() -> str:
    try:
        import yt_dlp
    except ImportError:
        return "（未安装）"
    return getattr(yt_dlp, "version", None) and yt_dlp.version.__version__ or "unknown"


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def _split_values(raw: str) -> List[str]:
    """把 ``"web_safari,tv"`` 解析为 ``["web_safari", "tv"]``。"""
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


class Engine:
    """构造 yt-dlp 选项并执行提取/下载。"""

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.log = get_logger()

    # ------------------------------------------------------------------ #
    def _extractor_args(self) -> Dict[str, Dict[str, List[str]]]:
        args: Dict[str, List[str]] = {}
        clients = _split_values(self.cfg.player_client)
        if clients:
            args["player_client"] = clients
        po_tokens = _split_values(self.cfg.po_token)
        if po_tokens:
            args["po_token"] = po_tokens
        if self.cfg.visitor_data.strip():
            args["visitor_data"] = [self.cfg.visitor_data.strip()]
        return {"youtube": args} if args else {}

    def base_opts(self) -> Dict[str, Any]:
        """公共选项。"""
        cfg = self.cfg
        opts: Dict[str, Any] = {
            "quiet": not cfg.verbose,
            "no_warnings": not cfg.verbose,
            "noprogress": not cfg.verbose,
            "ignoreerrors": True,
            "retries": cfg.retries,
            "fragment_retries": cfg.fragment_retries,
            "extractor_retries": cfg.extractor_retries,
            "concurrent_fragment_downloads": cfg.concurrent_fragments,
            "sleep_interval_requests": cfg.sleep_requests,
            "sleep_interval": cfg.sleep_interval,
            "max_sleep_interval": cfg.max_sleep_interval,
            "http_headers": {
                "User-Agent": cfg.user_agent,
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            },
            "match_filter": make_match_filter(cfg),
        }

        if cfg.proxy:
            opts["proxy"] = cfg.proxy

        cookiefile = cfg.resolved_cookiefile()
        if cookiefile:
            opts["cookiefile"] = str(cookiefile)
            self.log.debug("使用 Cookie 文件：%s", cookiefile)
        elif cfg.cookies_from_browser:
            # yt-dlp 期望 (browser, profile, keyring, container) 四元组
            opts["cookiesfrombrowser"] = (cfg.cookies_from_browser, None, None, None)
            self.log.debug("从浏览器读取 Cookie：%s", cfg.cookies_from_browser)

        extractor_args = self._extractor_args()
        if extractor_args:
            opts["extractor_args"] = extractor_args

        return opts

    # ------------------------------------------------------------------ #
    def list_opts(self, playlistend: Optional[int] = None) -> Dict[str, Any]:
        """列表/分页提取选项（不下载）。"""
        opts = self.base_opts()
        opts.update({
            "extract_flat": True,
            "noplaylist": False,
            "skip_download": True,
            "lazy_playlist": False,  # 立即展开全部分页，便于统计与切片
            "quiet": True,
            "noprogress": True,
        })
        if playlistend:
            opts["playlistend"] = playlistend
        return opts

    def download_opts(self, outtmpl: str, archive: Optional[str] = None) -> Dict[str, Any]:
        """下载选项（含音频提取后处理）。"""
        cfg = self.cfg
        opts = self.base_opts()
        opts.update({
            "format": "bestaudio/best",
            "outtmpl": outtmpl,
            "noplaylist": True,
            "trim_file_name": 180,
            "windowsfilenames": True,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": cfg.audio_format,
                "preferredquality": cfg.audio_quality,
            }],
        })
        if archive:
            opts["download_archive"] = archive
        if cfg.keep_video:
            opts["keepvideo"] = True
        return opts

    # ------------------------------------------------------------------ #
    def extract_list(self, url: str, playlistend: Optional[int] = None) -> List[Dict[str, Any]]:
        """扁平提取一个列表（频道 videos 标签 / 播放列表）的全部条目。"""
        import yt_dlp

        opts = self.list_opts(playlistend=playlistend)
        with yt_dlp.YoutubeDL(opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
            except Exception as exc:  # noqa: BLE001
                self.log.warning("列表提取失败：%s —— %s", url, exc)
                return []

        if not info:
            return []
        entries = info.get("entries") or []
        result = []
        for entry in entries:
            if isinstance(entry, dict) and entry.get("id"):
                result.append(entry)
        self.log.debug("列表 %s 解析出 %s 条", url, len(result))
        return result

    def extract_video_info(self, url: str) -> Optional[Dict[str, Any]]:
        """完整提取单个视频的元数据（不下载）。"""
        import yt_dlp

        opts = self.base_opts()
        opts.update({"noplaylist": True, "skip_download": True, "quiet": True, "noprogress": True})
        with yt_dlp.YoutubeDL(opts) as ydl:
            try:
                return ydl.extract_info(url, download=False)
            except Exception as exc:  # noqa: BLE001
                self.log.error("视频信息提取失败：%s", exc)
                return None

    def download(self, urls: List[str], outtmpl: str, archive: Optional[str] = None) -> int:
        """下载一批视频并提取音频。"""
        import yt_dlp

        opts = self.download_opts(outtmpl=outtmpl, archive=archive)
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download(list(urls))
        return 0
