"""登录凭证的本地持久化存储（B 站 `SESSDATA` / 抖音 Cookie）。

两种凭证的结构完全同构（单文件、单键、加一个保存时间戳），因此共用下面三个私有读写
helper，各自只提供一层薄类——避免把同一段读写逻辑复制两遍。

设计约束：
- 落盘位置固定为**产物根**下的单文件 JSON（默认 `<cwd>/output/`）：
  三域分离后产物根位于代码仓库之外，凭证**不可能**随代码进入版本库；两仓库的 .gitignore
  另有一条显式规则兜底，防止有人把产物根搬回仓库内；
- 每种凭证一个文件，只存那一项，不存任何其他 Cookie 或账号信息；
- 写入时尽力收紧文件权限（POSIX 0600），降低同机其他用户读取的可能；
- 命令行显式传入的值优先级永远高于本地存档。
"""

import json
import os
import time
from pathlib import Path
from typing import Optional

from . import paths as _paths

DEFAULT_STORE_NAME = ".sessdata.json"
DEFAULT_DOUYIN_STORE_NAME = ".douyin_cookie.json"


def store_path() -> Path:
    """SESSDATA 存档的规范路径（恒定，不随当前所在目录变化）。"""
    return _paths.products_root() / DEFAULT_STORE_NAME


def douyin_store_path() -> Path:
    """抖音 Cookie 存档的规范路径（恒定，不随当前所在目录变化）。"""
    return _paths.products_root() / DEFAULT_DOUYIN_STORE_NAME


def _target_for(filename: str, path: Optional[Path]) -> Path:
    """显式 path 优先（供自检注入临时文件），否则落到产物根下的规范路径。"""
    return Path(path) if path else (_paths.products_root() / filename)


def _load(filename: str, key: str, path: Optional[Path] = None) -> Optional[str]:
    """读取单值存档；不存在、损坏或为空时返回 None（绝不凭空造值）。"""
    target = _target_for(filename, path)
    if not target.exists():
        return None
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except Exception:
        return None
    value = data.get(key) if isinstance(data, dict) else None
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _save(filename: str, key: str, value: str, path: Optional[Path] = None) -> Path:
    """写入单值存档（空值直接拒绝，避免落一个无效凭证文件）。"""
    cleaned = (value or "").strip()
    if not cleaned:
        raise ValueError("凭证内容不能为空。")

    target = _target_for(filename, path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(
            {key: cleaned, "saved_at": time.strftime("%Y-%m-%d %H:%M:%S")},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    try:
        os.chmod(target, 0o600)  # POSIX 下收紧为仅属主可读写；Windows 上尽力而为
    except Exception:
        pass
    return target


def _clear(filename: str, path: Optional[Path] = None) -> bool:
    """删除单值存档；无存档时返回 False。"""
    target = _target_for(filename, path)
    if not target.exists():
        return False
    try:
        target.unlink()
        return True
    except OSError:
        return False


def _mask(value: Optional[str]) -> str:
    """脱敏展示：只保留长度与末 4 位，绝不回显完整凭证。"""
    if not value:
        return "（无）"
    if len(value) <= 8:
        return "*" * len(value)
    return f"{'*' * 8}{value[-4:]}（共 {len(value)} 字符）"


class SessdataStore:
    """B 站 SESSDATA 的单文件读写与清除。"""

    @staticmethod
    def load(path: Optional[Path] = None) -> Optional[str]:
        return _load(DEFAULT_STORE_NAME, "sessdata", path)

    @staticmethod
    def save(sessdata: str, path: Optional[Path] = None) -> Path:
        return _save(DEFAULT_STORE_NAME, "sessdata", sessdata, path)

    @staticmethod
    def clear(path: Optional[Path] = None) -> bool:
        return _clear(DEFAULT_STORE_NAME, path)

    @staticmethod
    def mask(value: Optional[str]) -> str:
        return _mask(value)


class DouyinCookieStore:
    """抖音 Cookie 的单文件读写与清除。

    为什么需要它：抖音对**匿名**访问施加了作品列表硬窗口（实测某博主真实 216 条、
    匿名只放行 21 条，且翻页在第二页直接返回空列表），所有免 cookie 的旁路
    （合集接口 / 主页 SSR 内联数据）都拿不到更多。配置登录态 Cookie 是唯一可行途径。
    """

    @staticmethod
    def load(path: Optional[Path] = None) -> Optional[str]:
        return _load(DEFAULT_DOUYIN_STORE_NAME, "cookie", path)

    @staticmethod
    def save(cookie: str, path: Optional[Path] = None) -> Path:
        return _save(DEFAULT_DOUYIN_STORE_NAME, "cookie", cookie, path)

    @staticmethod
    def clear(path: Optional[Path] = None) -> bool:
        return _clear(DEFAULT_DOUYIN_STORE_NAME, path)

    @staticmethod
    def mask(value: Optional[str]) -> str:
        return _mask(value)


def resolve_sessdata(explicit: Optional[str] = None) -> Optional[str]:
    """B 站凭证解析优先级：命令行显式传入 > 本地存档 > 无。"""
    if explicit and explicit.strip():
        return explicit.strip()
    return SessdataStore.load()


def resolve_douyin_cookie(explicit: Optional[str] = None) -> Optional[str]:
    """抖音凭证解析优先级：命令行显式传入 > 环境变量 > 本地存档 > 无。

    比 SESSDATA 多一条环境变量来源，因为抖音 cookie 串很长、不适合反复粘贴到命令行。
    """
    if explicit and explicit.strip():
        return explicit.strip()
    env_value = os.environ.get("DYAUDIO_COOKIE", "").strip()
    if env_value:
        return env_value
    return DouyinCookieStore.load()
