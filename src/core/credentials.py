"""B 站登录凭证（SESSDATA）的本地持久化存储。

设计约束：
- 落盘位置固定为 <仓库根>/output/.sessdata.json：该目录已被 .gitignore 整体排除，
  且 .gitignore 另有一条显式规则兜底，绝不随代码进入版本库；
- 只存 SESSDATA 一项，不存任何其他 Cookie 或账号信息；
- 写入时尽力收紧文件权限（POSIX 0600），降低同机其他用户读取的可能；
- 命令行显式传入的 --sessdata 优先级永远高于本地存档。
"""

import json
import os
import time
from pathlib import Path
from typing import Optional

# 本文件位于 <仓库根>/src/core/ 下，向上两级即仓库根
_REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_STORE_NAME = ".sessdata.json"


def store_path() -> Path:
    """凭证存档的规范路径（恒定，不随当前所在目录变化）。"""
    return _REPO_ROOT / "output" / DEFAULT_STORE_NAME


class SessdataStore:
    """SESSDATA 的单文件读写与清除。"""

    @staticmethod
    def load(path: Optional[Path] = None) -> Optional[str]:
        """读取已保存的 SESSDATA；不存在、损坏或为空时返回 None。"""
        target = Path(path) if path else store_path()
        if not target.exists():
            return None
        try:
            data = json.loads(target.read_text(encoding="utf-8"))
        except Exception:
            return None
        value = data.get("sessdata") if isinstance(data, dict) else None
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    @staticmethod
    def save(sessdata: str, path: Optional[Path] = None) -> Path:
        """保存 SESSDATA（空值直接拒绝，避免写入无效凭证）。"""
        value = (sessdata or "").strip()
        if not value:
            raise ValueError("SESSDATA 不能为空。")

        target = Path(path) if path else store_path()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(
                {"sessdata": value, "saved_at": time.strftime("%Y-%m-%d %H:%M:%S")},
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

    @staticmethod
    def clear(path: Optional[Path] = None) -> bool:
        """清除本地存档；无存档时返回 False。"""
        target = Path(path) if path else store_path()
        if not target.exists():
            return False
        try:
            target.unlink()
            return True
        except OSError:
            return False

    @staticmethod
    def mask(value: Optional[str]) -> str:
        """脱敏展示：只保留长度与末 4 位，绝不回显完整凭证。"""
        if not value:
            return "（无）"
        if len(value) <= 8:
            return "*" * len(value)
        return f"{'*' * 8}{value[-4:]}（共 {len(value)} 字符）"


def resolve_sessdata(explicit: Optional[str] = None) -> Optional[str]:
    """凭证解析优先级：命令行显式传入 > 本地存档 > 无。"""
    if explicit and explicit.strip():
        return explicit.strip()
    return SessdataStore.load()
