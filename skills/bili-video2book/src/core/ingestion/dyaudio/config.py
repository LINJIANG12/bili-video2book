"""运行配置：cookie / 代理 / 限速 / 输出目录 / 音频来源等。

优先级：命令行参数 > 环境变量 > 配置文件(config.json) > 内置默认值。
配置文件默认读取 ``douyin/config.json``（可用 ``--config`` 指定）。
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any, Dict, Optional

# 默认桌面 UA，需与签名时使用的 UA 保持一致
DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0"
)

MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
)

# 工作区根与产物根绑定
try:
    from src.core import paths as _paths
    PKG_ROOT = _paths.home_root()
    DEFAULT_OUTPUT_DIR = _paths.products_root()
except Exception:
    PKG_ROOT = Path(__file__).resolve().parents[4]
    DEFAULT_OUTPUT_DIR = PKG_ROOT / "output"

_ENV_PREFIX = "DYAUDIO_"


@dataclass
class Config:
    """全部可调参数。"""

    # --- 身份与网络 ---
    cookie: str = ""                       # 浏览器复制的完整 Cookie 串（可选但强烈建议）
    user_agent: str = DEFAULT_UA
    proxy: str = ""                        # 例如 http://127.0.0.1:7890
    ms_token: str = ""                     # 浏览器 Cookie 中的 msToken（留空则自动生成）
    verify_fp: str = ""                    # 浏览器 Cookie 中的 s_v_web_id（留空则自动生成）

    # --- 输出 ---
    output_dir: str = ""                   # 默认 douyin/output
    audio_source: str = "video"            # video=从视频提取音轨（保真）/ music=直接下载原声
    audio_format: str = "m4a"              # m4a | mp3（music 源固定为原始格式）
    keep_video: bool = False               # video 源提取后是否保留临时视频
    flat: bool = False                     # True=所有音频放同一目录（不按合集分文件夹）

    # --- 抓取节奏与重试（反爬） ---
    min_delay: float = 1.0
    max_delay: float = 3.0
    max_retries: int = 3
    request_timeout: int = 15
    download_timeout: int = 60
    count_per_page: int = 18
    max_pages: int = 0                     # 0 = 不限页数
    use_random_ms_token: bool = True

    # --- 运行时覆盖（不写入配置文件） ---
    verbose: bool = False
    config_path: str = field(default="", repr=False)

    def to_public_dict(self) -> Dict[str, Any]:
        data = {}
        for f in fields(self):
            if f.name in ("cookie", "config_path"):
                continue
            data[f.name] = getattr(self, f.name)
        return data

    @property
    def resolved_output_dir(self) -> Path:
        return Path(self.output_dir).expanduser().resolve() if self.output_dir \
            else DEFAULT_OUTPUT_DIR


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("1", "true", "yes", "on", "y")


def _coerce(field_name: str, value: Any) -> Any:
    if value is None:
        return None
    if field_name in ("keep_video", "flat", "use_random_ms_token", "verbose"):
        return _as_bool(value)
    if field_name in (
        "max_retries", "request_timeout", "download_timeout",
        "count_per_page", "max_pages",
    ):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
    if field_name in ("min_delay", "max_delay"):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
    return value


def load_config(config_path: Optional[str] = None, **overrides: Any) -> Config:
    """加载配置。

    :param config_path: 配置文件路径，缺省 ``douyin/config.json``。
    :param overrides: 命令行覆盖项（值为 None 时忽略）。
    """
    cfg = Config()

    # 1) 默认配置文件
    path = Path(config_path) if config_path else (PKG_ROOT / "config.json")
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            for key, value in data.items():
                if hasattr(cfg, key) and key != "config_path":
                    coerced = _coerce(key, value)
                    if coerced is not None:
                        setattr(cfg, key, coerced)
            cfg.config_path = str(path)
        except (json.JSONDecodeError, OSError) as exc:
            raise ValueError(f"配置文件解析失败：{path}（{exc}）") from exc

    # 2) 环境变量
    env_map = {
        "DYAUDIO_COOKIE": "cookie",
        "DYAUDIO_USER_AGENT": "user_agent",
        "DYAUDIO_PROXY": "proxy",
        "DYAUDIO_OUTPUT_DIR": "output_dir",
        "DYAUDIO_AUDIO_SOURCE": "audio_source",
        "DYAUDIO_AUDIO_FORMAT": "audio_format",
        "DYAUDIO_MS_TOKEN": "ms_token",
        "DYAUDIO_MAX_PAGES": "max_pages",
        "DYAUDIO_MIN_DELAY": "min_delay",
        "DYAUDIO_MAX_DELAY": "max_delay",
    }
    for env_key, field_name in env_map.items():
        if env_key in os.environ:
            coerced = _coerce(field_name, os.environ[env_key])
            if coerced is not None:
                setattr(cfg, field_name, coerced)

    # 3) 显式覆盖
    for key, value in overrides.items():
        if value is None:
            continue
        if hasattr(cfg, key):
            setattr(cfg, key, value)

    # 归一化
    if cfg.audio_source not in ("video", "music"):
        cfg.audio_source = "video"
    if cfg.audio_format not in ("m4a", "mp3"):
        cfg.audio_format = "m4a"
    if cfg.min_delay < 0:
        cfg.min_delay = 0.0
    if cfg.max_delay < cfg.min_delay:
        cfg.max_delay = cfg.min_delay
    if cfg.count_per_page <= 0 or cfg.count_per_page > 20:
        cfg.count_per_page = 18

    return cfg


def save_cookie(cookie: str, config_path: Optional[str] = None) -> Path:
    """把 cookie 持久化到配置文件（保留其它已有字段）。"""
    path = Path(config_path) if config_path else (PKG_ROOT / "config.json")
    data: Dict[str, Any] = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {}
    data["cookie"] = cookie
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
