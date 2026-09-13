"""博主主页：解析 sec_uid、分页抓取全部作品、按合集归类。

接口
----
* 用户资料：``/aweme/v1/web/user/profile/other/``
* 作品列表：``/aweme/v1/web/aweme/post/``（游标 ``max_cursor`` + ``has_more``）

反爬说明
--------
匿名（不带 Cookie）时作品列表通常只能翻到约 41 条；配置 Cookie 后可完整翻页。
每个作品节点的 ``mix_info`` 字段标记了它所属的合集，据此即可完成合集归类。
"""

from __future__ import annotations

import re
from collections import OrderedDict
from typing import Any, Dict, Iterator, List, Optional, Tuple

import requests

from .client import DouyinClient
from .config import MOBILE_UA
from .utils import extract_first_url, get_logger, safe_int

PROFILE_PATH = "/aweme/v1/web/user/profile/other/"
POST_PATH = "/aweme/v1/web/aweme/post/"

_SEC_UID_RE = re.compile(r"(MS4wLjABAAAA[A-Za-z0-9_\-]+)")
_USER_PATH_RE = re.compile(r"/user/([A-Za-z0-9_\-]+)")

UNCLASSIFIED = "未分类"


class UserError(RuntimeError):
    pass


def extract_sec_uid(session: requests.Session, text: str, timeout: int = 15,
                    proxies: Optional[Dict[str, str]] = None) -> str:
    """从主页链接 / 分享文本 / 短链中解析 ``sec_uid``。"""
    url = extract_first_url(text) or text.strip()

    match = _SEC_UID_RE.search(url)
    if match:
        return match.group(1)

    match = _USER_PATH_RE.search(url)
    if match:
        return match.group(1)

    if "v.douyin.com" in url or "douyin.com" in url:
        resp = session.get(
            url, timeout=timeout, allow_redirects=True,
            headers={"User-Agent": MOBILE_UA},
            proxies=proxies,
        )
        final_url = str(resp.url)
        match = _SEC_UID_RE.search(final_url) or _USER_PATH_RE.search(final_url)
        if match:
            return match.group(1)

    raise UserError(f"未能解析出 sec_uid，请使用形如 https://www.douyin.com/user/MS4wLjABAAAA... 的主页链接：{text}")


def get_user_profile(client: DouyinClient, sec_uid: str) -> Dict[str, Any]:
    """获取博主资料（昵称等），失败时返回空字典。"""
    try:
        data = client.web_get(PROFILE_PATH, {"sec_user_id": sec_uid, "publish_video_strategy_type": "2"})
    except Exception as exc:  # noqa: BLE001 - 资料非必需，失败降级
        get_logger().warning("获取博主资料失败（忽略）：%s", exc)
        return {}
    user = data.get("user") or {}
    return {
        "nickname": user.get("nickname") or "",
        "sec_uid": user.get("sec_uid") or sec_uid,
        "unique_id": user.get("unique_id") or "",
        "signature": user.get("signature") or "",
        "aweme_count": safe_int(user.get("aweme_count")),
    }


def iter_user_posts(client: DouyinClient, sec_uid: str,
                    max_pages: int = 0) -> Iterator[Dict[str, Any]]:
    """分页迭代博主发布的作品节点。

    :param max_pages: 最大页数，0 表示直到 ``has_more`` 为 0。
    """
    log = get_logger()
    cursor = 0
    page = 0
    seen_cursors = set()

    while True:
        page += 1
        if max_pages and page > max_pages:
            log.info("已达 max_pages=%s，停止翻页", max_pages)
            break

        params = {
            "sec_user_id": sec_uid,
            "max_cursor": str(cursor),
            "locate_query": "false",
            "show_live_replay_strategy": "1",
            "need_time_list": "1",
            "time_list_query": "0",
            "whale_cut_token": "",
            "cut_version": "1",
            "count": str(client.cfg.count_per_page),
            "publish_video_strategy_type": "2",
            "from_user_page": "1",
        }
        data = client.web_get(POST_PATH, params)

        aweme_list = data.get("aweme_list") or []
        has_more = safe_int(data.get("has_more"))
        next_cursor = safe_int(data.get("max_cursor"), cursor)

        log.info("第 %s 页：%s 个作品，has_more=%s", page, len(aweme_list), has_more)
        for aweme in aweme_list:
            if isinstance(aweme, dict):
                yield aweme

        if not has_more or not aweme_list:
            break
        if next_cursor == cursor or next_cursor in seen_cursors:
            log.warning("游标未推进（cursor=%s），提前结束以避免死循环", next_cursor)
            break
        seen_cursors.add(cursor)
        cursor = next_cursor


def mix_key(aweme: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    """返回作品所属的 ``(合集ID, 合集名)``；不属于任何合集时返回 ``(None, None)``。"""
    mix_info = aweme.get("mix_info")
    if not isinstance(mix_info, dict):
        return None, None
    mix_id = mix_info.get("mix_id")
    mix_name = (mix_info.get("mix_name") or "").strip()
    if not mix_id or str(mix_id) in ("0", ""):
        return None, None
    return str(mix_id), mix_name or f"合集_{mix_id}"


def group_by_mix(awemes: List[Dict[str, Any]]) -> "OrderedDict[str, List[Dict[str, Any]]]":
    """按合集分组，保持出现顺序；不属于合集的作品归入 ``未分类``。"""
    groups: "OrderedDict[str, List[Dict[str, Any]]]" = OrderedDict()
    for aweme in awemes:
        _, name = mix_key(aweme)
        bucket = name or UNCLASSIFIED
        groups.setdefault(bucket, []).append(aweme)
    return groups


def collect_awemes_by_mix(client: DouyinClient, sec_uid: str, max_pages: int = 0,
                          enrich_mix: bool = True) -> Tuple[Dict[str, Any], "OrderedDict[str, List[Dict[str, Any]]]"]:
    """抓全部作品并按合集分组。

    :param enrich_mix: 是否额外调用合集接口补全（对主页只能返回前 41 条的情况有用）。
    """
    log = get_logger()
    profile = get_user_profile(client, sec_uid)
    awemes = list(iter_user_posts(client, sec_uid, max_pages=max_pages))
    log.info("共抓取作品 %s 个", len(awemes))

    groups = group_by_mix(awemes)

    if enrich_mix:
        groups = _enrich_with_mix_api(client, groups)

    return profile, groups


def _enrich_with_mix_api(client: DouyinClient,
                         groups: "OrderedDict[str, List[Dict[str, Any]]]") -> "OrderedDict[str, List[Dict[str, Any]]]":
    """对已识别出的合集，尝试调用合集接口补全其全部作品。"""
    from .mix_crawler import iter_mix_awemes  # 局部导入，避免循环依赖

    log = get_logger()
    enriched: "OrderedDict[str, List[Dict[str, Any]]]" = OrderedDict()
    for name, items in groups.items():
        mix_ids = set()
        for aweme in items:
            mix_id, _ = mix_key(aweme)
            if mix_id:
                mix_ids.add(mix_id)
        if not mix_ids:
            enriched[name] = items
            continue

        merged: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()
        for aweme in items:
            merged[str(aweme.get("aweme_id"))] = aweme

        for mix_id in mix_ids:
            try:
                extra = list(iter_mix_awemes(client, mix_id))
            except Exception as exc:  # noqa: BLE001 - 补全失败则忽略
                log.debug("合集 %s 补全失败（忽略）：%s", mix_id, exc)
                continue
            for aweme in extra:
                merged.setdefault(str(aweme.get("aweme_id")), aweme)

        enriched[name] = list(merged.values())
    return enriched
