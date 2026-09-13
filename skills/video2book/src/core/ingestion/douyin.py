#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Douyin media provider using in-process dyaudio engine."""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from .base import BaseMediaProvider, IngestionError


class DouyinProvider(BaseMediaProvider):
    name = "douyin"
    display_name = "抖音 (Douyin)"

    def match(self, target: str) -> bool:
        if not target or not isinstance(target, str):
            return False
        low = target.lower()
        if "douyin.com" in low or "iesdouyin.com" in low:
            return True
        if "v.douyin.com" in low:
            return True
        # 兼容纯数字 aweme_id（18-19位数字）
        if target.strip().isdigit() and len(target.strip()) >= 15:
            return True
        return False

    def _get_client(self, **kwargs: Any) -> Any:
        from .dyaudio.client import DouyinClient
        from .dyaudio.config import Config, load_config

        cfg_path = kwargs.get("config_path")
        cfg = load_config(cfg_path)
        if "cookie" in kwargs and kwargs["cookie"]:
            cfg.cookie = str(kwargs["cookie"])
        if "proxy" in kwargs and kwargs["proxy"]:
            cfg.proxy = str(kwargs["proxy"])
        if "audio_source" in kwargs and kwargs["audio_source"]:
            cfg.audio_source = str(kwargs["audio_source"])
        return DouyinClient(cfg), cfg

    def probe(self, target: str, **kwargs: Any) -> Dict[str, Any]:
        from .dyaudio.share_parser import ParseError, parse_share_url
        from .dyaudio.user_crawler import (
            UserError,
            collect_awemes_by_mix,
            extract_sec_uid,
            get_user_profile,
        )
        from .dyaudio.utils import sanitize_filename

        client, cfg = self._get_client(**kwargs)
        clean_target = target.strip()

        with client:
            # 1. 判定是否为用户主页
            is_user = "/user/" in clean_target or "sec_uid" in clean_target
            if is_user:
                try:
                    sec_uid = extract_sec_uid(client.session, clean_target)
                except Exception as err:
                    raise IngestionError(f"未能解析抖音用户主页: {err}") from err

                profile, groups = collect_awemes_by_mix(client, sec_uid, max_pages=cfg.max_pages)
                author_name = profile.get("nickname") or sec_uid
                safe_author = sanitize_filename(author_name, max_len=60)

                parts: List[Dict[str, Any]] = []
                page_idx = 1
                total_duration = 0

                for mix_name, awemes in groups.items():
                    for aweme in awemes:
                        aweme_id = str(aweme.get("aweme_id") or "")
                        if not aweme_id:
                            continue
                        desc = str(aweme.get("desc") or aweme_id)
                        dur = int(aweme.get("duration") or 0)
                        if dur > 1000:
                            dur = dur // 1000  # 毫秒转秒
                        total_duration += dur

                        display_title = f"[{mix_name}] {desc}" if mix_name != "未分类" and len(groups) > 1 else desc
                        parts.append({
                            "page": page_idx,
                            "title": display_title,
                            "cid": f"dy_{aweme_id}",
                            "duration": dur,
                            "url": f"https://www.douyin.com/video/{aweme_id}",
                            "filepath": "",
                            "_raw_aweme": aweme,
                        })
                        page_idx += 1

                if not parts:
                    raise IngestionError(f"未从抖音博主主页中获取到有效作品: {clean_target}")

                return {
                    "bvid": f"dy_u_{safe_author[:20]}",
                    "title": author_name,
                    "desc": f"抖音博主: {author_name}",
                    "duration": total_duration,
                    "owner": {"name": author_name, "mid": 0},
                    "video_type": "multi_page" if len(parts) > 1 else "single",
                    "type_desc": f"抖音作品合集 (共 {len(parts)} P)",
                    "cid": parts[0]["cid"],
                    "has_multi_pages": len(parts) > 1,
                    "has_ugc_season": False,
                    "season_episodes": [],
                    "parts": parts,
                    "is_local": False,
                    "source_type": "douyin",
                    "source_path": clean_target,
                }

            # 2. 单视频解析
            try:
                info = parse_share_url(client.session, clean_target)
            except Exception as err:
                raise IngestionError(f"抖音单视频解析失败: {err}") from err

            aweme_id = str(info.get("aweme_id") or "")
            desc = str(info.get("desc") or aweme_id)
            author = str(info.get("author") or "抖音作者")
            duration = int(info.get("duration") or 0)
            if duration > 1000:
                duration = duration // 1000

            parts = [{
                "page": 1,
                "title": desc,
                "cid": f"dy_{aweme_id}",
                "duration": duration,
                "url": f"https://www.douyin.com/video/{aweme_id}",
                "filepath": "",
                "_raw_aweme": info,
            }]

            return {
                "bvid": f"dy_{aweme_id}",
                "title": desc,
                "desc": f"抖音作品: {desc}",
                "duration": duration,
                "owner": {"name": author, "mid": 0},
                "video_type": "single",
                "type_desc": "抖音单视频",
                "cid": f"dy_{aweme_id}",
                "has_multi_pages": False,
                "has_ugc_season": False,
                "season_episodes": [],
                "parts": parts,
                "is_local": False,
                "source_type": "douyin",
                "source_path": clean_target,
            }

    def fetch_audio(
        self,
        episode: Dict[str, Any],
        output_file: Path,
        *,
        force: bool = False,
        progress_cb: Optional[Callable[[Dict[str, Any]], None]] = None,
        **kwargs: Any,
    ) -> Path:
        from .dyaudio.downloader import download_audio_for_aweme, normalize_aweme
        from .dyaudio.share_parser import parse_share_url

        output_file = Path(output_file).resolve()
        output_file.parent.mkdir(parents=True, exist_ok=True)

        if output_file.exists() and output_file.stat().st_size >= 10240 and not force:
            if progress_cb:
                progress_cb({"status": "cached", "file": str(output_file)})
            return output_file

        client, cfg = self._get_client(**kwargs)

        # 准备 aweme 信息字典
        raw_aweme = episode.get("_raw_aweme")
        with client:
            if not raw_aweme:
                url = episode.get("url")
                if not url:
                    cid = str(episode.get("cid") or "")
                    if cid.startswith("dy_"):
                        url = f"https://www.douyin.com/video/{cid[3:]}"
                    else:
                        raise IngestionError(f"缺少抖音作品链接: {episode.get('title')}")
                raw_aweme = parse_share_url(client.session, url)

            norm_info = normalize_aweme(raw_aweme) if "aweme_id" in raw_aweme and "video" in raw_aweme else raw_aweme

            # 下载到临时目录然后移至目标 output_file
            temp_dir = output_file.parent / ".dy_tmp"
            temp_dir.mkdir(parents=True, exist_ok=True)
            saved_file = download_audio_for_aweme(norm_info, temp_dir, client.session, cfg)

            if not saved_file or not saved_file.exists() or saved_file.stat().st_size == 0:
                raise IngestionError(f"抖音音频下载失败: {episode.get('title')}")

            # 移动/重命名为预期的 output_file
            if saved_file != output_file:
                shutil.move(str(saved_file), str(output_file))

            # 清理临时目录
            try:
                if temp_dir.exists() and not any(temp_dir.iterdir()):
                    temp_dir.rmdir()
            except Exception:
                pass

        if progress_cb:
            progress_cb({"status": "downloaded", "file": str(output_file)})
        return output_file

    def check_readiness(self) -> Tuple[bool, str]:
        try:
            import requests
            req_ver = getattr(requests, "__version__", "已安装")
        except ImportError:
            return False, "缺少 requests 依赖 (pip install requests)"

        ffmpeg_bin = shutil.which("ffmpeg")
        status = f"就绪 (requests {req_ver})"
        if ffmpeg_bin:
            status += f", ffmpeg: {ffmpeg_bin}"
        else:
            status += ", 未检测到 ffmpeg (从视频抽音轨需 ffmpeg)"
        return True, status
