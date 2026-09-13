"""下载与音频提取。

两种音频来源：

* ``audio_source="music"``：直接下载作品的原声（``music.play_url``），体积小、速度快；
* ``audio_source="video"``：下载无水平台码流后，用 ffmpeg 抽出音轨（与视频完全一致），
  需要系统安装 ffmpeg，默认输出 ``.m4a``。

若目标文件已存在则跳过（支持断点续跑）。
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests

from .config import Config
from .share_parser import parse_single_aweme
from .utils import format_bytes, get_logger, sanitize_filename

_CHUNK = 1024 * 256
_CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


# ---------------------------------------------------------------------- #
# ffmpeg
# ---------------------------------------------------------------------- #
def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def extract_audio(video_path: Path, out_path: Path, fmt: str = "m4a") -> bool:
    """用 ffmpeg 从视频中提取音轨。"""
    log = get_logger()
    if not ffmpeg_available():
        log.error("未找到 ffmpeg，无法从视频提取音轨（可改用 --source music）")
        return False

    if fmt == "mp3":
        codec_args = ["-c:a", "libmp3lame", "-q:a", "2"]
    else:
        codec_args = ["-c:a", "copy"]  # 无损直拷；失败时下方重试转码

    def _run(args: List[str]) -> bool:
        cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
               "-i", str(video_path), "-vn", *args, str(out_path)]
        try:
            from src.core.proc import run_quiet
            result = run_quiet(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=600)
            return result.returncode == 0 and out_path.exists()
        except OSError as exc:
            log.error("调用 ffmpeg 失败：%s", exc)
            return False

    if _run(codec_args):
        return True
    if fmt != "mp3":
        log.debug("直拷失败，尝试重编码为 AAC")
        if _run(["-c:a", "aac", "-b:a", "192k"]):
            return True
    return False


# ---------------------------------------------------------------------- #
# 下载
# ---------------------------------------------------------------------- #
def _guess_ext_from_url(url: str, default: str) -> str:
    path = urlparse(url).path
    for ext in (".mp3", ".m4a", ".aac", ".wav", ".mp4", ".flv"):
        if path.lower().endswith(ext):
            return ext
    return default


def download_file(session: requests.Session, url: str, dest: Path, cfg: Config,
                  referer: str = "https://www.douyin.com/",
                  headers: Optional[Dict[str, str]] = None) -> bool:
    """流式下载到 ``dest``，失败返回 False。"""
    log = get_logger()
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")

    req_headers = {"Referer": referer, "Accept": "*/*"}
    if headers:
        req_headers.update(headers)

    try:
        with session.get(
            url,
            headers=req_headers,
            stream=True,
            timeout=cfg.download_timeout,
            allow_redirects=True,
            proxies=({"http": cfg.proxy, "https": cfg.proxy} if cfg.proxy else None),
        ) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get("Content-Length") or 0)
            written = 0
            last_report = time.time()
            with open(tmp, "wb") as fh:
                for chunk in resp.iter_content(chunk_size=_CHUNK):
                    if not chunk:
                        continue
                    fh.write(chunk)
                    written += len(chunk)
                    if time.time() - last_report >= 3:
                        if total:
                            log.info("  下载中 %s / %s", format_bytes(written), format_bytes(total))
                        else:
                            log.info("  下载中 %s", format_bytes(written))
                        last_report = time.time()

        tmp.replace(dest)
        log.info("  已保存 %s（%s）", dest.name, format_bytes(dest.stat().st_size))
        return True
    except (requests.RequestException, OSError) as exc:
        log.error("  下载失败：%s", exc)
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
        return False


# ---------------------------------------------------------------------- #
# 单作品音频落盘
# ---------------------------------------------------------------------- #
def _build_basename(info: Dict[str, Any]) -> str:
    ts = info.get("create_time") or 0
    if ts:
        time_str = datetime.fromtimestamp(ts).strftime("%Y%m%d")
    else:
        time_str = "unknown"
    desc = sanitize_filename(info.get("desc") or "", max_len=60)
    aweme_id = info.get("aweme_id") or ""
    return sanitize_filename(f"{time_str}_{desc}_{aweme_id}", max_len=120)


def _unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem, suffix = path.stem, path.suffix
    for i in range(1, 1000):
        candidate = path.with_name(f"{stem} ({i}){suffix}")
        if not candidate.exists():
            return candidate
    return path


def download_audio_for_aweme(info: Dict[str, Any], dest_dir: Path,
                             session: requests.Session, cfg: Config) -> Optional[Path]:
    """下载单个作品的音频，返回落盘路径（失败返回 None）。"""
    log = get_logger()
    dest_dir.mkdir(parents=True, exist_ok=True)
    basename = _build_basename(info)

    # 跳过已下载（同名前缀的任意音频）
    for existing in dest_dir.glob(f"{basename}.*"):
        if existing.suffix.lower() in (".m4a", ".mp3", ".aac", ".wav"):
            log.info("  已存在，跳过：%s", existing.name)
            return existing

    desc = (info.get("desc") or "")[:40]
    log.info("处理 [%s] %s", info.get("aweme_id"), desc)

    prefer_music = cfg.audio_source == "music"
    music_urls = info.get("music_urls") or []
    video_urls = info.get("video_urls") or []

    # 1) music 源：直接下载原声
    if prefer_music and music_urls:
        ext = _guess_ext_from_url(music_urls[0], ".mp3")
        out = _unique_path(dest_dir / f"{basename}{ext}")
        if download_file(session, music_urls[0], out, cfg):
            return out
        log.warning("  原声下载失败，回退到视频提取")

    # 2) video 源（或 music 回退）：下载视频并抽音轨
    if video_urls:
        if not ffmpeg_available():
            log.error("  未安装 ffmpeg，无法提取音轨。请安装 ffmpeg 或改用 --source music")
            return None

        video_path = dest_dir / f"{basename}.mp4"
        if not download_file(session, video_urls[0], video_path, cfg):
            return None

        out = _unique_path(dest_dir / f"{basename}.{cfg.audio_format}")
        ok = extract_audio(video_path, out, cfg.audio_format)
        if not cfg.keep_video:
            try:
                video_path.unlink()
            except OSError:
                pass
        if ok:
            log.info("  已提取音频 %s（%s）", out.name, format_bytes(out.stat().st_size))
            return out
        log.error("  音频提取失败")
        return None

    # 3) 兜底：只有原声可用
    if music_urls:
        ext = _guess_ext_from_url(music_urls[0], ".mp3")
        out = _unique_path(dest_dir / f"{basename}{ext}")
        if download_file(session, music_urls[0], out, cfg):
            return out

    log.error("  没有可用的音频/视频地址")
    return None


def normalize_aweme(aweme: Dict[str, Any]) -> Dict[str, Any]:
    """把原始作品节点（主页接口返回）归一化为统一下载结构。"""
    return parse_single_aweme(aweme)
