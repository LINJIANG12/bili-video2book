"""带请求签名、反爬处理、限速与重试的抖音 Web 客户端。

要点
----
* 每个 Web 接口请求都会：
  - 注入一批固定的浏览器环境参数（device_platform / aid / screen_* 等）；
  - 用 :class:`~dyaudio.abogus.ABogus` 计算 ``a_bogus`` 并追加到查询串；
  - 携带 ``Cookie``（若配置）与随机 ``msToken`` / ``verifyFp`` 指纹；
  - 请求之间随机 sleep，失败（412/429/风控状态码）时指数退避重试。
* 首次运行时可选地引导拿一个 ``ttwid`` cookie，提升匿名成功率。
"""

from __future__ import annotations

import json
import random
import string
import time
from typing import Any, Dict, Optional
from urllib.parse import quote, urlencode

import requests

from .abogus import ABogus, BrowserFingerprintGenerator
from .config import Config
from .utils import get_logger

# 会让请求被风控/失败的 JSON 业务状态码
RISK_STATUS = {8, 10000, 2154, 10111, 20000, 40000}

# 固定的浏览器环境参数（顺序即签名顺序，保持稳定）
_BASE_PARAMS = [
    ("device_platform", "webapp"),
    ("aid", "6383"),
    ("channel", "channel_pc_web"),
]

_BROWSER_PARAMS = [
    ("pc_client_type", "1"),
    ("pc_libra_divert", "Windows"),
    ("update_version_code", "170400"),
    ("support_h265", "1"),
    ("support_dash", "0"),
    ("version_code", "290100"),
    ("version_name", "29.1.0"),
    ("cookie_enabled", "true"),
    ("screen_width", "1920"),
    ("screen_height", "1080"),
    ("browser_language", "zh-CN"),
    ("browser_platform", "Win32"),
    ("browser_name", "Edge"),
    ("browser_version", "131.0.0.0"),
    ("browser_online", "true"),
    ("engine_name", "Blink"),
    ("engine_version", "131.0.0.0"),
    ("os_name", "Windows"),
    ("os_version", "10"),
    ("cpu_core_num", "12"),
    ("device_memory", "8"),
    ("platform", "PC"),
    ("downlink", "10"),
    ("effective_type", "4g"),
    ("round_trip_time", "50"),
]

WEB_BASE = "https://www.douyin.com"
TTWID_URL = "https://ttwid.bytedance.com/ttwid/union/register/"


class APIError(RuntimeError):
    """接口返回了非 0 业务状态码。"""

    def __init__(self, status_code: int, status_msg: str, url: str):
        super().__init__(f"接口异常 status_code={status_code} msg={status_msg!r} url={url}")
        self.status_code = status_code
        self.status_msg = status_msg
        self.url = url


class RiskControlError(RuntimeError):
    """命中风控（HTTP 412/429/403 或风控业务码），重试后仍失败。"""


def _random_ms_token(length: int = 107) -> str:
    alphabet = string.ascii_letters + string.digits + "-_"
    return "".join(random.choice(alphabet) for _ in range(length))


def _random_verify_fp() -> str:
    hex_chars = string.hexdigits.lower()[:16]
    body = "".join(random.choice(hex_chars) for _ in range(32))
    return f"verify_l{body}"


class DouyinClient:
    """抖音 Web 接口客户端。"""

    def __init__(self, cfg: Config, session: Optional[requests.Session] = None):
        self.cfg = cfg
        self.log = get_logger()
        self.session = session or requests.Session()

        self.ms_token = cfg.ms_token or (
            _random_ms_token() if cfg.use_random_ms_token else ""
        )
        self.verify_fp = cfg.verify_fp or _random_verify_fp()

        self.signer = ABogus(
            user_agent=cfg.user_agent,
            fp=BrowserFingerprintGenerator.generate_fingerprint("Edge"),
        )
        self._last_request_ts = 0.0

        self.session.headers.update({
            "User-Agent": cfg.user_agent,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": "https://www.douyin.com/",
            "Origin": "https://www.douyin.com",
        })
        if cfg.cookie:
            self.session.headers["Cookie"] = cfg.cookie
        else:
            self._bootstrap_ttwid()

    # ------------------------------------------------------------------ #
    # 反爬：限速
    # ------------------------------------------------------------------ #
    def _throttle(self) -> None:
        min_delay = self.cfg.min_delay
        max_delay = self.cfg.max_delay
        if max_delay <= 0:
            return
        elapsed = time.time() - self._last_request_ts
        wait = random.uniform(min_delay, max_delay) - elapsed
        if wait > 0:
            time.sleep(wait)

    def _mark_request(self) -> None:
        self._last_request_ts = time.time()

    def sleep(self, seconds: Optional[float] = None) -> None:
        if seconds is None:
            seconds = random.uniform(self.cfg.min_delay, self.cfg.max_delay)
        if seconds > 0:
            time.sleep(seconds)

    # ------------------------------------------------------------------ #
    # 反爬：匿名身份引导
    # ------------------------------------------------------------------ #
    def _bootstrap_ttwid(self) -> None:
        """尝试无登录态获取一个 ttwid cookie（失败则静默跳过）。"""
        try:
            payload = {
                "region": "cn",
                "aid": 1768,
                "needFid": False,
                "service": "www.ixigua.com",
                "migrate_info": {"ticket": "", "source": "node"},
                "cbUrlProtocol": "https",
                "union": True,
            }
            resp = self.session.post(
                TTWID_URL,
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"},
                timeout=self.cfg.request_timeout,
                proxies=self._proxies(),
            )
            ttwid = resp.cookies.get("ttwid")
            if ttwid:
                self.session.cookies.set("ttwid", ttwid, domain=".douyin.com")
                self.log.debug("已获取匿名 ttwid")
            else:
                self.log.debug("未从响应中拿到 ttwid，继续匿名请求")
        except requests.RequestException as exc:
            self.log.debug("ttwid 引导失败（忽略）：%s", exc)

    def _proxies(self) -> Optional[Dict[str, str]]:
        if not self.cfg.proxy:
            return None
        return {"http": self.cfg.proxy, "https": self.cfg.proxy}

    # ------------------------------------------------------------------ #
    # 签名 & 请求
    # ------------------------------------------------------------------ #
    def _build_signed_url(self, url: str, params: Dict[str, Any]) -> str:
        merged = list(_BASE_PARAMS) + _BROWSER_PARAMS + list(params.items())
        # 指纹类参数放最后，贴近浏览器真实请求顺序
        if self.ms_token:
            merged.append(("msToken", self.ms_token))
        if self.verify_fp:
            merged.append(("verifyFp", self.verify_fp))
            merged.append(("fp", self.verify_fp))

        query = urlencode(merged)
        a_bogus = self.signer.sign(query)
        return f"{url}?{query}&a_bogus={quote(a_bogus, safe='')}"

    def web_get(
        self,
        path: str,
        params: Dict[str, Any],
        *,
        sign: bool = True,
        expect_status: bool = True,
    ) -> Dict[str, Any]:
        """请求 Web JSON 接口。

        :param path: 以 ``/`` 开头的接口路径，或完整 URL。
        :param params: 业务查询参数。
        :param sign: 是否附加 a_bogus 签名。
        :param expect_status: 是否校验 ``status_code`` 业务码。
        """
        url = path if path.startswith("http") else f"{WEB_BASE}{path}"
        last_exc: Optional[Exception] = None

        for attempt in range(1, self.cfg.max_retries + 1):
            self._throttle()
            try:
                if sign:
                    request_url = self._build_signed_url(url, params)
                else:
                    query = urlencode(list(_BASE_PARAMS) + list(params.items()))
                    request_url = f"{url}?{query}"

                resp = self.session.get(
                    request_url,
                    timeout=self.cfg.request_timeout,
                    proxies=self._proxies(),
                )
                self._mark_request()

                if resp.status_code in (412, 429, 403, 500, 502, 503):
                    raise RiskControlError(f"HTTP {resp.status_code}")

                resp.raise_for_status()
                data = resp.json()

                status = data.get("status_code", 0)
                if expect_status and status not in (0, None):
                    if status in RISK_STATUS:
                        raise RiskControlError(f"风控业务码 {status}: {data.get('status_msg', '')}")
                    raise APIError(status, str(data.get("status_msg", "")), url)
                return data

            except (requests.RequestException, ValueError, RiskControlError, APIError) as exc:
                last_exc = exc
                if isinstance(exc, APIError):
                    raise  # 业务码错误重试无意义
                backoff = min(2 ** attempt + random.random(), 30)
                self.log.warning(
                    "请求失败(%s/%s)：%s —— %.1fs 后重试",
                    attempt, self.cfg.max_retries, exc, backoff,
                )
                time.sleep(backoff)

        raise RiskControlError(f"多次重试仍失败：{last_exc}")

    def raw_get(self, url: str, **kwargs) -> requests.Response:
        """不签名、不解析的裸 GET（用于下载媒体与分享页）。"""
        headers = kwargs.pop("headers", {})
        merged_headers = {"Referer": "https://www.douyin.com/"}
        merged_headers.update(headers)
        return self.session.get(
            url,
            headers=merged_headers,
            timeout=kwargs.pop("timeout", self.cfg.request_timeout),
            proxies=self._proxies(),
            **kwargs,
        )

    def close(self) -> None:
        self.session.close()

    def __enter__(self) -> "DouyinClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
