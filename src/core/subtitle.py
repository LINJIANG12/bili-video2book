"""Bilibili Official Subtitle Fetcher & Parser (Fallback Path).

Fetches official AI-generated or human-uploaded subtitles from Bilibili player v2 API.
Used as an instant fallback when:
- The AI Agent is operating in a text-only model mode
- Multimodal audio parsing is disabled
- Network or compute constraints require zero-audio transcription
"""

import json
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional


class SubtitleFetcher:
    PLAYER_V2_API = "https://api.bilibili.com/x/player/v2"

    DEFAULT_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.bilibili.com/",
    }

    @classmethod
    def get_subtitles_list(
        cls,
        bvid: str,
        cid: int,
        sessdata: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Query player v2 API to list all available subtitles for a specific cid."""
        params = urllib.parse.urlencode({"bvid": bvid, "cid": cid})
        url = f"{cls.PLAYER_V2_API}?{params}"

        headers = dict(cls.DEFAULT_HEADERS)
        if sessdata:
            headers["Cookie"] = f"SESSDATA={sessdata}"

        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        if data.get("code") != 0:
            raise RuntimeError(f"Player v2 API error: code={data.get('code')}, msg={data.get('message')}")

        subtitles_meta = ((data.get("data") or {}).get("subtitle") or {}).get("subtitles") or []
        return subtitles_meta

    @classmethod
    def download_subtitle_content(
        cls,
        subtitle_url: str,
    ) -> List[Dict[str, Any]]:
        """Download subtitle JSON body containing time-stamped dialog entries."""
        # Ensure scheme is https
        if subtitle_url.startswith("//"):
            subtitle_url = f"https:{subtitle_url}"

        req = urllib.request.Request(subtitle_url, headers=cls.DEFAULT_HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        return data.get("body") or []

    @classmethod
    def fetch_best_subtitle(
        cls,
        bvid: str,
        cid: int,
        preferred_lang: str = "zh-CN",
        sessdata: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch the best matching subtitle (AI or human) and return structured text.
        """
        subs = cls.get_subtitles_list(bvid, cid, sessdata=sessdata)
        if not subs:
            return None

        # Prioritize specified lang, then first available
        target_sub = None
        for s in subs:
            if preferred_lang.lower() in s.get("lan", "").lower():
                target_sub = s
                break
        if not target_sub and subs:
            target_sub = subs[0]

        sub_url = target_sub.get("subtitle_url", "")
        if not sub_url:
            return None

        body = cls.download_subtitle_content(sub_url)

        # Build full text and formatted text with timestamps
        lines = []
        raw_paragraphs = []
        for item in body:
            content = item.get("content", "").strip()
            if not content:
                continue
            f_sec = item.get("from", 0.0)
            t_sec = item.get("to", 0.0)
            lines.append(f"[{cls.format_time(f_sec)} -> {cls.format_time(t_sec)}] {content}")
            raw_paragraphs.append(content)

        full_text = " ".join(raw_paragraphs)
        timestamped_text = "\n".join(lines)

        return {
            "language": target_sub.get("lan"),
            "language_doc": target_sub.get("lan_doc"),
            "is_ai": target_sub.get("ai_type", 0) != 0,
            "subtitle_url": sub_url,
            "total_items": len(body),
            "full_text": full_text,
            "timestamped_text": timestamped_text,
        }

    @staticmethod
    def format_time(seconds: float) -> str:
        s = int(round(seconds))
        return f"{s // 3600:02d}:{(s % 3600) // 60:02d}:{s % 60:02d}"
