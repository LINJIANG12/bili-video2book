"""Bilibili URL Parser & Video Topology Classifier.

Classifies videos into:
1. single: Single independent video (1 P, no UGC season)
2. multi_page: Multi-part video collection in one submission (P1, P2...)
3. ugc_season: Series / collection of separate videos created by an uploader
4. hybrid: Multi-part video that also belongs to an uploader's UGC season
"""

import json
import re
import sys
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional


class BilibiliParser:
    VIEW_API = "https://api.bilibili.com/x/web-interface/view"

    DEFAULT_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.bilibili.com/",
    }

    @staticmethod
    def extract_bvid(url_or_bvid: str) -> Optional[str]:
        """Extract valid 12-char BVID from raw strings, URLs, or b23.tv short links."""
        text = url_or_bvid.strip()
        bv_pattern = re.compile(r"(BV[a-zA-Z0-9]{10})", re.IGNORECASE)
        match = bv_pattern.search(text)
        if match:
            return match.group(1)

        # Handle b23.tv short links (follow 302 redirect)
        if "b23.tv" in text:
            short_url_match = re.search(r"https?://b23\.tv/[a-zA-Z0-9]+", text)
            if short_url_match:
                try:
                    req = urllib.request.Request(
                        short_url_match.group(0),
                        headers=BilibiliParser.DEFAULT_HEADERS,
                    )
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        final_match = bv_pattern.search(resp.geturl())
                        if final_match:
                            return final_match.group(1)
                except Exception as err:
                    print(f"[Warn] Failed to resolve b23.tv redirect: {err}", file=sys.stderr)

        return None

    @staticmethod
    def extract_page_index(url_or_bvid: str) -> Optional[int]:
        """Extract page index (?p=N or &p=N) from URL if present."""
        try:
            parsed = urllib.parse.urlparse(url_or_bvid.strip())
            qs = urllib.parse.parse_qs(parsed.query)
            if "p" in qs and qs["p"]:
                val = int(qs["p"][0])
                if val >= 1:
                    return val
        except Exception:
            pass
        return None

    @classmethod
    def fetch_video_view(cls, bvid: str, sessdata: Optional[str] = None) -> Dict[str, Any]:
        """Fetch raw view metadata from Bilibili API."""
        params = urllib.parse.urlencode({"bvid": bvid})
        url = f"{cls.VIEW_API}?{params}"
        headers = dict(cls.DEFAULT_HEADERS)
        if sessdata:
            headers["Cookie"] = f"SESSDATA={sessdata}"

        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("code") != 0:
                    raise RuntimeError(
                        f"Bilibili API error: code={data.get('code')}, msg={data.get('message')}"
                    )
                return data["data"]
        except Exception as err:
            raise RuntimeError(f"Failed to fetch video view for {bvid}: {err}") from err

    @classmethod
    def parse_video(cls, url_or_bvid: str, sessdata: Optional[str] = None) -> Dict[str, Any]:
        """Analyze video structure and return structured classification & episodes."""
        bvid = cls.extract_bvid(url_or_bvid)
        if not bvid:
            raise ValueError(f"Could not extract a valid BVID from input: {url_or_bvid}")

        raw = cls.fetch_video_view(bvid, sessdata=sessdata)

        title = raw.get("title", "")
        owner = raw.get("owner", {}).get("name", "")
        owner_mid = raw.get("owner", {}).get("mid", 0)
        desc = raw.get("desc", "")
        duration = raw.get("duration", 0)
        pic = raw.get("pic", "")
        pages: List[Dict[str, Any]] = raw.get("pages", [])
        ugc_season: Optional[Dict[str, Any]] = raw.get("ugc_season")

        has_multi_pages = len(pages) > 1
        has_ugc_season = bool(ugc_season)

        if not has_multi_pages and not has_ugc_season:
            video_type = "single"
            type_desc = "单个独立视频（单P，无合集）"
        elif has_multi_pages and not has_ugc_season:
            video_type = "multi_page"
            type_desc = f"分P选集视频（稿件内包含 {len(pages)} 个视频选集）"
        elif not has_multi_pages and has_ugc_season:
            video_type = "ugc_season"
            season_title = ugc_season.get("title", "")
            type_desc = f"合集/系列视频（UGC Season，合集名: {season_title}）"
        else:
            video_type = "hybrid"
            season_title = ugc_season.get("title", "")
            type_desc = f"复合型视频（本稿件含 {len(pages)} 个分P，且属于合集【{season_title}】）"

        # Build clean part list
        parts = []
        for p in pages:
            p_num = p.get("page", 1)
            parts.append({
                "page": p_num,
                "title": p.get("part", ""),
                "cid": p.get("cid"),
                "duration": p.get("duration", 0),
                "url": f"https://www.bilibili.com/video/{bvid}?p={p_num}",
            })

        # Build season episodes list
        season_episodes = []
        season_info = None
        if has_ugc_season and ugc_season:
            season_info = {
                "season_id": ugc_season.get("id"),
                "title": ugc_season.get("title"),
                "cover": ugc_season.get("cover"),
                "intro": ugc_season.get("intro"),
                "ep_count": ugc_season.get("ep_count", 0),
            }
            sections = ugc_season.get("sections", [])
            for sec_idx, sec in enumerate(sections, 1):
                sec_title = sec.get("title", f"第{sec_idx}部分")
                for ep_idx, ep in enumerate(sec.get("episodes", []), 1):
                    ep_bvid = ep.get("bvid", "")
                    season_episodes.append({
                        "section_title": sec_title,
                        "episode_index": ep_idx,
                        "bvid": ep_bvid,
                        "aid": ep.get("aid"),
                        "cid": ep.get("cid"),
                        "title": ep.get("title", ""),
                        "url": f"https://www.bilibili.com/video/{ep_bvid}?season_id={ugc_season.get('id')}",
                        "pages_count": len(ep.get("pages", [])),
                    })

        url_page = cls.extract_page_index(url_or_bvid)
        selected_cid = raw.get("cid", 0)
        selected_title = title
        if url_page and 1 <= url_page <= len(parts):
            matched_part = parts[url_page - 1]
            selected_cid = matched_part["cid"]
            selected_title = matched_part["title"]

        return {
            "bvid": bvid,
            "aid": raw.get("aid"),
            "cid": selected_cid,  # Default to selected cid if p=X present, else P1 cid
            "title": title,
            "desc": desc,
            "cover": pic,
            "duration": duration,
            "owner": {"name": owner, "mid": owner_mid},
            "video_type": video_type,
            "type_desc": type_desc,
            "has_multi_pages": has_multi_pages,
            "has_ugc_season": has_ugc_season,
            "page_count": len(pages),
            "parts": parts,
            "season_info": season_info,
            "season_episodes": season_episodes,
            "url_page": url_page,
            "selected_cid": selected_cid,
            "selected_title": selected_title,
        }

    # Alias for convenience
    parse = parse_video
