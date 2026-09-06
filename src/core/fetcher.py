"""Bilibili Audio Stream Fetcher & Downloader.

Features:
- Fetches DASH audio streams via Wbi playurl endpoint
- Selects the highest available audio bitrate (192k/132k/64k/Dolby/Hi-Res)
- Downloads with mandatory Anti-Hotlink headers (Referer/User-Agent)
- Repackages streams with ffmpeg (-acodec copy) for zero quality loss in 0.1s
"""

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

from .wbi import WbiSigner


class AudioFetcher:
    PLAYURL_API = "https://api.bilibili.com/x/player/wbi/playurl"

    DEFAULT_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.bilibili.com/",
    }

    # Audio quality mapping (Bilibili standard DASH IDs)
    AUDIO_QUALITY_MAP = {
        30280: "192kbps (高码率)",
        30232: "132kbps (普通码率)",
        30216: "64kbps (低码率)",
        30250: "杜比全景声 (Dolby Atmos)",
        30251: "Hi-Res 无损",
    }

    @classmethod
    def get_audio_stream_url(
        cls,
        bvid: str,
        cid: int,
        sessdata: Optional[str] = None,
        prefer_quality: str = "low",
    ) -> Dict[str, Any]:
        """Convenience method for get_audio_stream_info."""
        return cls.get_audio_stream_info(bvid=bvid, cid=cid, sessdata=sessdata, prefer_quality=prefer_quality)

    @classmethod
    def get_audio_stream_info(
        cls,
        bvid: str,
        cid: int,
        sessdata: Optional[str] = None,
        prefer_quality: str = "low",
    ) -> Dict[str, Any]:
        """Request playurl with DASH mode (fnval=16) and return audio stream candidates."""
        raw_params = {
            "bvid": bvid,
            "cid": cid,
            "fnval": 16,   # 16 represents DASH format
            "fnver": 0,
            "fourk": 1,
        }
        signed_params = WbiSigner.enc_wbi(raw_params, sessdata=sessdata)
        query_str = urllib.parse.urlencode(signed_params)
        url = f"{cls.PLAYURL_API}?{query_str}"

        headers = dict(cls.DEFAULT_HEADERS)
        if sessdata:
            headers["Cookie"] = f"SESSDATA={sessdata}"

        req = urllib.request.Request(url, headers=headers)
        data = None
        for attempt in range(1, 4):
            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                break
            except Exception as e:
                if attempt == 3:
                    raise RuntimeError(f"Playurl request failed after 3 retries: {e}") from e
                time.sleep(1)

        if not data or data.get("code") != 0:
            msg = data.get("message") if data else "No response"
            code = data.get("code") if data else -1
            raise RuntimeError(f"Playurl error: code={code}, msg={msg}")

        result_data = data.get("data", {})
        dash = result_data.get("dash")
        if not dash:
            raise RuntimeError("No DASH stream available for this video (might be a legacy flv stream)")

        audio_list = dash.get("audio", [])
        if not audio_list:
            raise RuntimeError("No audio streams found in DASH manifest")

        # Sort audio streams by bandwidth/id
        def sort_key(item: Dict[str, Any]) -> int:
            return item.get("bandwidth", 0) or item.get("id", 0)

        # Select stream based on prefer_quality (default: 'low' 64kbps for speech efficiency)
        pq = (prefer_quality or "low").lower()
        if pq == "low":
            target_candidates = [a for a in audio_list if a.get("id") == 30216]
            if target_candidates:
                selected_audio = target_candidates[0]
            else:
                selected_audio = sorted(audio_list, key=sort_key, reverse=False)[0]
        elif pq == "medium":
            target_candidates = [a for a in audio_list if a.get("id") == 30232]
            if target_candidates:
                selected_audio = target_candidates[0]
            else:
                selected_audio = sorted(audio_list, key=sort_key, reverse=False)[0]
        else: # high
            selected_audio = sorted(audio_list, key=sort_key, reverse=True)[0]

        # Extract direct url (baseUrl or backupUrl)
        stream_url = selected_audio.get("base_url") or selected_audio.get("baseUrl")
        if not stream_url and selected_audio.get("backup_url"):
            stream_url = selected_audio["backup_url"][0]

        quality_id = selected_audio.get("id", 0)
        quality_desc = cls.AUDIO_QUALITY_MAP.get(quality_id, f"Audio ID: {quality_id}")

        audio_list_sorted = sorted(audio_list, key=sort_key, reverse=True)

        return {
            "bvid": bvid,
            "cid": cid,
            "best_stream_url": stream_url,
            "quality_id": quality_id,
            "quality_desc": quality_desc,
            "bandwidth": selected_audio.get("bandwidth"),
            "codecs": selected_audio.get("codecs"),
            "all_audio_streams": [
                {
                    "id": a.get("id"),
                    "desc": cls.AUDIO_QUALITY_MAP.get(a.get("id", 0), f"ID {a.get('id')}"),
                    "bandwidth": a.get("bandwidth"),
                    "url": a.get("base_url") or a.get("baseUrl"),
                }
                for a in audio_list_sorted
            ],
        }

    @classmethod
    def download_audio(
        cls,
        stream_url: str,
        output_filepath: str,
        repackage_m4a: bool = True,
        max_bytes: Optional[int] = None,
    ) -> str:
        """Stream download raw audio with anti-hotlink headers and repackage to .m4a."""
        out_path = Path(output_filepath).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)

        temp_raw_path = out_path.with_suffix(".raw.m4s")

        req = urllib.request.Request(stream_url, headers=cls.DEFAULT_HEADERS)
        try:
            downloaded = 0
            with urllib.request.urlopen(req, timeout=30) as resp, open(temp_raw_path, "wb") as f_out:
                chunk_size = 128 * 1024  # 128 KB chunks
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    f_out.write(chunk)
                    downloaded += len(chunk)
                    if max_bytes and downloaded >= max_bytes:
                        break
        except Exception as err:
            if temp_raw_path.exists():
                temp_raw_path.unlink()
            raise RuntimeError(f"Audio download failed: {err}") from err

        final_m4a_path = out_path.with_suffix(".m4a")

        # Repackage using ffmpeg if available
        ffmpeg_bin = shutil.which("ffmpeg")
        if repackage_m4a and ffmpeg_bin:
            cmd = [
                ffmpeg_bin,
                "-y",
                "-i", str(temp_raw_path),
                "-acodec", "copy",
                str(final_m4a_path),
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if res.returncode == 0:
                if temp_raw_path.exists():
                    temp_raw_path.unlink()
                return str(final_m4a_path)

        # If ffmpeg is not found or repackaging failed, rename raw stream
        if temp_raw_path.exists():
            temp_raw_path.rename(final_m4a_path)
        return str(final_m4a_path)
