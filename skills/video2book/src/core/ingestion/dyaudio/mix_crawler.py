"""合集（mix / 播放列表）接口 —— 尽力而为的补充抓取。

主页作品接口在匿名或合集条目较多时可能只返回部分作品，此时用合集接口
按 ``mix_id`` 拉全量。接口路径在不同版本可能变化，因此对多个候选路径依次尝试，
任一成功即返回；全部失败则抛错，由上层降级为「仅用主页作品列表」。
"""

from __future__ import annotations

from typing import Any, Dict, Iterator, List, Optional

from .client import DouyinClient
from .utils import get_logger, safe_int

# 候选合集作品列表接口（按可能性排序）
MIX_PATHS = [
    "/aweme/v1/web/mix/aweme/",
    "/aweme/v1/web/mix/detail/",
    "/aweme/v1/web/aweme/mix/",
]


def _extract_list(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    for key in ("aweme_list", "mix_aweme_list", "aweme_details", "aweme_list_detail"):
        value = data.get(key)
        if isinstance(value, list):
            return [x for x in value if isinstance(x, dict)]
    return []


def iter_mix_awemes(client: DouyinClient, mix_id: str, max_pages: int = 0) -> Iterator[Dict[str, Any]]:
    """迭代某个合集的全部作品。"""
    log = get_logger()
    last_error: Optional[Exception] = None

    for path in MIX_PATHS:
        try:
            yield from _iter_with_path(client, path, mix_id, max_pages)
            return
        except Exception as exc:  # noqa: BLE001 - 换下一个候选路径
            last_error = exc
            log.debug("合集接口 %s 不可用：%s", path, exc)

    raise RuntimeError(f"全部候选合集接口均失败：{last_error}")


def _iter_with_path(client: DouyinClient, path: str, mix_id: str,
                    max_pages: int) -> Iterator[Dict[str, Any]]:
    log = get_logger()
    cursor = 0
    page = 0
    seen_cursors = set()

    while True:
        page += 1
        if max_pages and page > max_pages:
            break

        params = {
            "mix_id": mix_id,
            "cursor": str(cursor),
            "count": str(max(client.cfg.count_per_page, 20)),
            "locate_query": "false",
            "show_live_replay_strategy": "1",
        }
        data = client.web_get(path, params)

        items = _extract_list(data)
        has_more = safe_int(data.get("has_more"))
        next_cursor = safe_int(data.get("cursor"), safe_int(data.get("max_cursor"), cursor))

        log.debug("合集 %s 第 %s 页：%s 条", mix_id, page, len(items))
        for item in items:
            yield item

        if not has_more or not items:
            break
        if next_cursor == cursor or next_cursor in seen_cursors:
            break
        seen_cursors.add(cursor)
        cursor = next_cursor
