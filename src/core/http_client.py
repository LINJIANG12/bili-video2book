"""统一 HTTP 请求与自适应退避重试组件。

提供针对 B站 API 及流媒体下载的标准请求客户端：
- 支持统一的 User-Agent 与防盗链 Referer
- 内置针对 412 风控拦截、429 限流、5xx 服务端错误及超时的带抖动指数退避重试
- 优先支持响应头中的 Retry-After 字段
- 维护复用连接的 Cookie 会话
"""

import json
import random
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional, Tuple, Union

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

DEFAULT_HEADERS = {
    "User-Agent": DEFAULT_USER_AGENT,
    "Referer": "https://www.bilibili.com",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

_SESSION_OPENER: Optional[urllib.request.OpenerDirector] = None


def get_session_opener() -> urllib.request.OpenerDirector:
    """获取带全局 Cookie 处理器的单例 Opener。"""
    global _SESSION_OPENER
    if _SESSION_OPENER is None:
        cookie_handler = urllib.request.HTTPCookieProcessor()
        _SESSION_OPENER = urllib.request.build_opener(cookie_handler)
    return _SESSION_OPENER


def compute_backoff(
    attempt: int,
    base_backoff: float = 1.5,
    max_backoff: float = 60.0,
    jitter_min: float = 0.1,
    jitter_max: float = 0.5,
) -> float:
    """计算带抖动（jitter）的指数退避等待时间。"""
    calculated = base_backoff * (2 ** (attempt - 1)) + random.uniform(jitter_min, jitter_max)
    return min(calculated, max_backoff)


def parse_retry_after(headers: Any) -> Optional[float]:
    """从 HTTP 响应头中提取并解析 Retry-After 延迟秒数。"""
    if not headers:
        return None
    header_val = headers.get("Retry-After") if hasattr(headers, "get") else None
    if not header_val:
        return None
    try:
        return float(header_val)
    except (ValueError, TypeError):
        return None


def is_risk_control_error(err: Any) -> bool:
    """检查是否属于 412 风控拦截异常。"""
    msg = str(err)
    return "412" in msg or "风控" in msg


def request_with_retry(
    url: str,
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 15.0,
    max_retries: int = 3,
    base_backoff: float = 1.5,
    max_backoff: float = 60.0,
    opener: Optional[urllib.request.OpenerDirector] = None,
) -> bytes:
    """发送 HTTP GET 请求，内置指数退避重试与风控识别。

    Args:
        url: 请求目标 URL
        headers: 自定义请求头（默认混入 DEFAULT_HEADERS）
        timeout: 单次超时秒数
        max_retries: 最大重试次数
        base_backoff: 基础退避时间（秒）
        max_backoff: 最大退避上限（秒）
        opener: 可选的自定义 Opener

    Returns:
        响应的字节流 (bytes)

    Raises:
        RuntimeError: 当遇到 412 且重试耗尽，或不可恢复的网络/服务错误
    """
    req_headers = dict(DEFAULT_HEADERS)
    if headers:
        req_headers.update(headers)

    active_opener = opener or get_session_opener()

    for attempt in range(1, max_retries + 1):
        try:
            req = urllib.request.Request(url, headers=req_headers)
            with active_opener.open(req, timeout=timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as http_err:
            status_code = getattr(http_err, "code", None)

            # 412: 触发风控拦截，尝试退避重试或直接暴露建议
            if status_code == 412 or is_risk_control_error(http_err):
                if attempt < max_retries:
                    retry_after = parse_retry_after(getattr(http_err, "headers", None))
                    wait_sec = retry_after if retry_after is not None else compute_backoff(attempt, base_backoff, max_backoff)
                    time.sleep(wait_sec)
                    continue
                raise RuntimeError(
                    f"[网络] 触发 B 站 412 风控拦截：请求过频或需要登录验证凭据。"
                    f"建议动作：配置 Cookie (SESSDATA) 或等待后重试。"
                ) from http_err

            # 429 或 5xx 服务端暂时性故障：退避重试
            if status_code in (429, 500, 502, 503, 504) and attempt < max_retries:
                retry_after = parse_retry_after(getattr(http_err, "headers", None))
                wait_sec = retry_after if retry_after is not None else compute_backoff(attempt, base_backoff, max_backoff)
                time.sleep(wait_sec)
                continue

            # 其他 HTTP 状态码直接抛出
            raise RuntimeError(
                f"[网络] HTTP 请求失败 ({status_code})：{http_err}。URL: {url}"
            ) from http_err

        except (urllib.error.URLError, TimeoutError, OSError) as net_err:
            if attempt < max_retries:
                wait_sec = compute_backoff(attempt, base_backoff, max_backoff)
                time.sleep(wait_sec)
                continue
            raise RuntimeError(
                f"[网络] 连接超时或网络故障：{net_err}。URL: {url}"
            ) from net_err

    raise RuntimeError(f"[网络] 超过最大重试次数 ({max_retries})，请求失败。URL: {url}")


def request_json_with_retry(
    url: str,
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 15.0,
    max_retries: int = 3,
    base_backoff: float = 1.5,
    max_backoff: float = 60.0,
    opener: Optional[urllib.request.OpenerDirector] = None,
) -> Dict[str, Any]:
    """发送 HTTP GET 请求并解析 JSON 结果，内置重试与异常封装。"""
    raw_bytes = request_with_retry(
        url=url,
        headers=headers,
        timeout=timeout,
        max_retries=max_retries,
        base_backoff=base_backoff,
        max_backoff=max_backoff,
        opener=opener,
    )
    try:
        data = json.loads(raw_bytes.decode("utf-8"))
    except Exception as parse_err:
        raise RuntimeError(f"[网络] 接口响应非合法 JSON：{parse_err}") from parse_err
    if not isinstance(data, dict):
        raise RuntimeError(f"[网络] 接口返回非预期 JSON 字典结构：{type(data)}")
    return data

