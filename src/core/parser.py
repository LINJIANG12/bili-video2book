"""视频地址解析与稿件结构分类器。

分类：
1. 单稿单集：单个独立视频
2. 分集选集：同一稿件下多分集
3. 合集系列：投稿者创建的合集
4. 复合类型：多分集且归属合集
"""

import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

from .wbi import WbiSigner


class BilibiliParser:
    """视频解析器（详情接口强制签名请求）。"""

    VIEW_API = "https://api.bilibili.com/x/web-interface/wbi/view"

    DEFAULT_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.bilibili.com/",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Origin": "https://www.bilibili.com",
        "Connection": "keep-alive",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
    }

    @staticmethod
    def _解析密钥路径(密钥文件: Optional[Any] = None, 工作区: Optional[Any] = None) -> Optional[str]:
        """解析签名密钥文件路径（优先使用工作区提供的路径）。"""
        try:
            if 工作区 is not None and hasattr(工作区, "wbi_keys_file"):
                return str(工作区.wbi_keys_file)
        except Exception:
            pass
        if 密钥文件 is not None:
            return str(密钥文件)
        return None

    @staticmethod
    def extract_bvid(url_or_bvid: str) -> Optional[str]:
        """从原始字符串、链接或短链中提取合法稿件号。"""
        text = url_or_bvid.strip()
        bv_pattern = re.compile(r"(BV[a-zA-Z0-9]{10})", re.IGNORECASE)
        match = bv_pattern.search(text)
        if match:
            return match.group(1)

        # 处理短链（跟随跳转）
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
        """从链接中提取分集序号（无则返回空）。"""
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
    def fetch_video_view(
        cls,
        bvid: str,
        sessdata: Optional[str] = None,
        wbi_keys_file: Optional[str] = None,
        workspace: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """请求详情接口并返回原始元数据（强制签名，区分导航失败与详情失败）。"""
        # 密钥路径由工作区提供，含有效期，过期由签名器重取
        密钥路径 = cls._解析密钥路径(密钥文件=wbi_keys_file, 工作区=workspace)

        # 详情参数必须经签名器加签
        try:
            签名参数 = WbiSigner.enc_wbi({"bvid": bvid}, sessdata=sessdata, keys_file=密钥路径)
        except RuntimeError as 错误:
            文本 = str(错误)
            if "[风控]" in 文本 or "[网络]" in 文本:
                raise RuntimeError(
                    f"[导航失败]{文本}"
                    "建议动作：检查登录凭证有效性，等待后降低频率重试。"
                ) from 错误
            raise RuntimeError(
                f"[签名]导航阶段签名失败：{错误}。"
                "建议动作：删除过期密钥文件后重试；仍失败请检查网络。"
            ) from 错误
        except Exception as 错误:
            raise RuntimeError(
                f"[签名]导航阶段签名失败：{错误}。"
                "建议动作：删除过期密钥文件后重试；仍失败请检查网络。"
            ) from 错误

        params = urllib.parse.urlencode(签名参数)
        url = f"{cls.VIEW_API}?{params}"
        headers = dict(cls.DEFAULT_HEADERS)
        if sessdata:
            headers["Cookie"] = f"SESSDATA={sessdata}"

        # 复用集中限速，避免高频触发风控
        WbiSigner.wait_rate_limit()
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as 错误:
            if 错误.code == 412:
                raise RuntimeError(
                    "[风控]详情接口被风控拦截（412），签名可能过期或频率过高。"
                    "建议动作：携带有效登录凭证、删除过期密钥文件后降频重试。"
                ) from 错误
            if 500 <= 错误.code <= 599:
                raise RuntimeError(
                    f"[网络]详情接口服务端异常（{错误.code}）。"
                    "建议动作：等待后退避重试。"
                ) from 错误
            raise RuntimeError(
                f"[网络]详情接口请求失败（{错误.code}）。"
                "建议动作：检查网络后重试。"
            ) from 错误
        except Exception as 错误:
            raise RuntimeError(
                f"[网络]详情接口请求失败：{错误}。"
                "建议动作：检查网络连接或代理后重试。"
            ) from 错误

        if data.get("code") != 0:
            编码 = data.get("code")
            信息 = data.get("message")
            if 编码 == -412:
                raise RuntimeError(
                    f"[风控]详情接口返回风控拦截：code={编码}，msg={信息}。"
                    "建议动作：携带有效登录凭证、删除过期密钥文件并降频重试。"
                )
            if 编码 in (-403, -404, 62002, 62004):
                raise RuntimeError(
                    f"[风控]详情接口访问受限：code={编码}，msg={信息}。"
                    "建议动作：确认稿件可见性与凭证权限后重试。"
                )
            raise RuntimeError(
                f"[风控]详情接口返回异常：code={编码}，msg={信息}。"
                "建议动作：确认稿件号正确、凭证有效后重试。"
            )
        return data["data"]

    @classmethod
    def parse_video(
        cls,
        url_or_bvid: str,
        sessdata: Optional[str] = None,
        wbi_keys_file: Optional[str] = None,
        workspace: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """分析稿件结构并返回分类与分集信息。"""
        bvid = cls.extract_bvid(url_or_bvid)
        if not bvid:
            raise ValueError(f"Could not extract a valid BVID from input: {url_or_bvid}")

        raw = cls.fetch_video_view(bvid, sessdata=sessdata, wbi_keys_file=wbi_keys_file, workspace=workspace)

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

        # 构建干净分集列表
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

        # 构建合集选集列表
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

        _ = Path  # 保持路径工具可用性标记
        return {
            "bvid": bvid,
            "aid": raw.get("aid"),
            "cid": selected_cid,  # 链接含分集序号时取对应分集，否则取首集
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

    # 别名入口
    parse = parse_video
