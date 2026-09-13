"""单视频解析：走移动端分享页，**免 Cookie、免签名**。

流程：分享文本/链接 → 提取 aweme_id（短链跟跳） → 请求移动端分享页
→ 从 ``window._ROUTER_DATA`` 抠出 JSON（括号深度匹配，不依赖 HTML 解析库）
→ 递归定位作品节点 → 取无水平台码流地址与原声地址。

该通道不受 Web 接口风控（412 / invalid a_bogus）影响，是单视频下载的首选路径。
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

import requests

from .config import MOBILE_UA
from .utils import extract_first_url, get_logger

SHARE_VIDEO_URL = "https://www.iesdouyin.com/share/video/{aweme_id}/"
SHARE_NOTE_URL = "https://www.iesdouyin.com/share/note/{aweme_id}/"

_VIDEO_ID_RE = re.compile(r"/(?:video|note|slides)/(\d{8,})")
_ANY_ID_RE = re.compile(r"(\d{15,})")
_ROUTER_MARKER = "window._ROUTER_DATA = "
_ROUTER_MARKER_LOOSE = "_ROUTER_DATA"


class ParseError(RuntimeError):
    """分享页结构变化或请求失败导致无法解析。"""


def extract_aweme_id(session: requests.Session, text: str, timeout: int = 15,
                     proxies: Optional[Dict[str, str]] = None) -> str:
    """从分享文本 / 链接中提取作品 ID（支持 v.douyin.com 短链跳转）。"""
    url = extract_first_url(text) or text.strip()

    match = _VIDEO_ID_RE.search(url)
    if match:
        return match.group(1)

    if "douyin.com" not in url:
        # 也可能用户直接粘贴了纯数字 ID
        pure = _ANY_ID_RE.search(url)
        if pure and url.strip().isdigit():
            return pure.group(1)

    # 短链：跟随重定向拿最终地址
    resp = session.get(
        url, timeout=timeout, allow_redirects=True,
        headers={"User-Agent": MOBILE_UA,
                 "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"},
        proxies=proxies,
    )
    final_url = str(resp.url)
    match = _VIDEO_ID_RE.search(final_url) or _ANY_ID_RE.search(final_url)
    if not match:
        raise ParseError(f"未能从链接中解析出作品 ID：{url}")
    return match.group(1)


def fetch_share_page(session: requests.Session, aweme_id: str, timeout: int = 15,
                     proxies: Optional[Dict[str, str]] = None) -> str:
    """抓取移动端分享页 HTML。"""
    last_error: Optional[Exception] = None
    for url in (SHARE_VIDEO_URL.format(aweme_id=aweme_id),
                SHARE_NOTE_URL.format(aweme_id=aweme_id)):
        try:
            resp = session.get(
                url,
                timeout=timeout,
                allow_redirects=True,
                headers={
                    "User-Agent": MOBILE_UA,
                    "Referer": "https://www.iesdouyin.com/",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "zh-CN,zh;q=0.9",
                },
                proxies=proxies,
            )
            if resp.status_code == 200 and resp.text:
                return resp.text
            last_error = ParseError(f"分享页请求失败 HTTP {resp.status_code}")
        except requests.RequestException as exc:
            last_error = exc
    raise ParseError(f"无法获取分享页：{last_error}")


def extract_router_data(html: str) -> Optional[Any]:
    """从 HTML 中提取 ``window._ROUTER_DATA`` 对应的 JSON 对象。

    使用状态机做花括号深度匹配，正确处理字符串内的花括号与转义字符，
    因此不依赖正则的贪婪匹配，也不会被 JSON 字符串值里的 ``{}`` 截断。
    """
    start = html.find(_ROUTER_MARKER)
    if start == -1:
        start = html.find(_ROUTER_MARKER_LOOSE)
        if start == -1:
            return None
        eq = html.find("=", start)
        if eq == -1:
            return None
        start = eq + 1
    else:
        start = start + len(_ROUTER_MARKER)

    # 跳过等号后的空白，要求以 { 开头
    index = start
    while index < len(html) and html[index] in " \t\r\n":
        index += 1
    if index >= len(html) or html[index] != "{":
        return None

    depth = 0
    in_str = False
    escape = False
    for i in range(index, len(html)):
        ch = html[i]
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                blob = html[index:i + 1]
                try:
                    return json.loads(blob)
                except json.JSONDecodeError:
                    return None
    return None


def _deep_find(obj: Any, predicate) -> Optional[Any]:
    """深度优先查找第一个满足 predicate 的 dict 节点。"""
    if isinstance(obj, dict):
        if predicate(obj):
            return obj
        for value in obj.values():
            found = _deep_find(value, predicate)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = _deep_find(item, predicate)
            if found is not None:
                return found
    return None


def _looks_like_aweme(node: Dict[str, Any]) -> bool:
    return isinstance(node.get("video"), dict) and (
        "aweme_id" in node or "awemeId" in node or "desc" in node
    )


def _dedupe(urls: List[str]) -> List[str]:
    seen = set()
    out = []
    for u in urls:
        if not u or u in seen:
            continue
        seen.add(u)
        out.append(u)
    return out


def _downgrade_watermark(url: str) -> str:
    """把带水印的 ``playwm`` 路径替换为无水的 ``play``。"""
    return url.replace("/playwm/", "/play/").replace("playwm", "play")


def _collect_video_urls(aweme: Dict[str, Any]) -> List[str]:
    video = aweme.get("video") or {}
    urls: List[str] = []

    for key in ("play_addr", "play_addr_h264", "play_addr_265", "download_addr"):
        node = video.get(key)
        if isinstance(node, dict):
            urls.extend(node.get("url_list") or [])
        elif isinstance(node, list):
            for sub in node:
                if isinstance(sub, dict):
                    urls.extend(sub.get("url_list") or [])

    for br in video.get("bit_rate") or []:
        if isinstance(br, dict):
            pa = br.get("play_addr") or {}
            if isinstance(pa, dict):
                urls.extend(pa.get("url_list") or [])

    return _dedupe([_downgrade_watermark(u) for u in urls if u])


def _collect_music_urls(aweme: Dict[str, Any]) -> List[str]:
    music = aweme.get("music") or {}
    if not isinstance(music, dict):
        return []
    play_url = music.get("play_url")
    urls: List[str] = []
    if isinstance(play_url, dict):
        urls.extend(play_url.get("url_list") or [])
    elif isinstance(play_url, str):
        urls.append(play_url)
    # 部分分享页把原声放在 music.play_addr
    node = music.get("play_addr")
    if isinstance(node, dict):
        urls.extend(node.get("url_list") or [])
    return _dedupe([u for u in urls if u])


def _to_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def parse_single_aweme(aweme: Dict[str, Any]) -> Dict[str, Any]:
    """把原始作品节点归一化为统一结构。"""
    author = aweme.get("author") or {}
    video = aweme.get("video") or {}
    music = aweme.get("music") or {}
    images = aweme.get("images") or []

    return {
        "aweme_id": str(aweme.get("aweme_id") or aweme.get("awemeId") or ""),
        "desc": (aweme.get("desc") or "").strip(),
        "create_time": _to_int(aweme.get("create_time") or aweme.get("createTime")),
        "duration": _to_int(video.get("duration") or video.get("duration_ms")),
        "author": author.get("nickname") or "",
        "author_sec_uid": author.get("sec_uid") or "",
        "video_urls": _collect_video_urls(aweme),
        "music_urls": _collect_music_urls(aweme),
        "music_title": music.get("title") or "",
        "cover": _first_cover(video),
        "is_album": bool(images),
        "mix_info": aweme.get("mix_info") or None,
        "raw": aweme,
    }


def _first_cover(video: Dict[str, Any]) -> str:
    for key in ("cover", "origin_cover", "dynamic_cover"):
        node = video.get(key)
        if isinstance(node, dict):
            urls = node.get("url_list") or []
            if urls:
                return urls[0]
    return ""


def parse_share_url(session: requests.Session, text: str, timeout: int = 15,
                    proxies: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """一站式：分享文本/链接 → 归一化的作品信息（含音频/视频直链）。"""
    log = get_logger()
    aweme_id = extract_aweme_id(session, text, timeout=timeout, proxies=proxies)
    log.debug("解析到 aweme_id=%s", aweme_id)

    html = fetch_share_page(session, aweme_id, timeout=timeout, proxies=proxies)
    data = extract_router_data(html)
    if data is None:
        raise ParseError("无法从分享页提取 _ROUTER_DATA，抖音页面结构可能已变更")

    aweme = _deep_find(data, _looks_like_aweme)
    if aweme is None:
        raise ParseError("分享页中未找到作品数据节点")

    info = parse_single_aweme(aweme)
    if not info["aweme_id"]:
        info["aweme_id"] = aweme_id
    if not info["video_urls"] and not info["music_urls"]:
        raise ParseError("未能在作品数据中找到可下载的媒体地址")
    return info
