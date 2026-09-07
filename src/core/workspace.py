"""任务工作区管理器（按任务隔离输出目录）。

目录结构：
输出根目录/
└── <任务名>/
    ├── 音频目录/      # 提取的音频与切片文件
    ├── 笔记目录/      # 结构化笔记
    ├── 文章目录/      # 深度文章
    ├── 字幕目录/      # 字幕与转写文本
    ├── 分集缓存/      # 分集列表缓存
    └── 清单文件/      # 任务元数据
"""

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


def _探测仓库根目录() -> Path:
    """从本文件向上查找包含目录的祖先作为仓库根目录。"""
    try:
        当前 = Path(__file__).resolve()
        for 祖先 in 当前.parents:
            if (祖先 / "src").is_dir():
                return 祖先
        return Path.cwd()
    except Exception:
        return Path.cwd()


_仓库根目录 = _探测仓库根目录()


class TaskWorkspace:
    """任务工作区：隔离每个任务的输出文件。"""

    非法字符正则 = re.compile(r'[\\/*?:"<>|#\n\r\t]+')

    # 仓库根目录（相对路径换算基准）
    仓库根目录: Path = _仓库根目录
    REPO_ROOT: Path = _仓库根目录

    def __init__(self, task_name: str, base_dir: Union[str, Path] = "output"):
        """初始化工作区并确保子目录存在。"""
        self.task_name = self.sanitize_name(task_name)
        self.base_dir = Path(base_dir).resolve() if Path(base_dir).is_absolute() else (Path.cwd() / str(base_dir)).resolve()
        self.root_dir = self.base_dir / self.task_name
        self.audio_dir = self.root_dir / "audio"
        self.notes_dir = self.root_dir / "notes"
        self.articles_dir = self.root_dir / "articles"
        self.subtitles_dir = self.root_dir / "subtitles"
        # 分集列表缓存路径
        self.parts_cache_path = self.root_dir / "parts.json"
        self.manifest_file = self.root_dir / "manifest.json"

        self.ensure_dirs()

    @property
    def wbi_keys_file(self) -> Path:
        """签名密钥文件路径（供上层透传给签名器做文件级缓存）。"""
        return self.base_dir / ".wbi_keys.json"

    @classmethod
    def default_wbi_keys_path(cls, base_dir: Union[str, Path] = "output") -> Path:
        """在未创建工作区实例时计算默认密钥文件路径。"""
        基 = Path(base_dir)
        if not 基.is_absolute():
            基 = (Path.cwd() / str(基)).resolve()
        return 基 / ".wbi_keys.json"

    @classmethod
    def sanitize_name(cls, raw_name: str) -> str:
        """清理非法文件系统字符并限制长度。"""
        清理后 = cls.非法字符正则.sub("_", raw_name)
        清理后 = re.sub(r"_+", "_", 清理后).strip(" ._-")
        return 清理后[:100] if 清理后 else "task_unnamed"

    def ensure_dirs(self):
        """确保任务根目录与各分类子目录存在。"""
        for 目录 in [self.root_dir, self.audio_dir, self.notes_dir, self.articles_dir, self.subtitles_dir]:
            目录.mkdir(parents=True, exist_ok=True)

    @classmethod
    def create(
        cls,
        title: str,
        bvid: str = "",
        custom_name: Optional[str] = None,
        base_dir: Union[str, Path] = "output",
    ) -> "TaskWorkspace":
        """工厂方法：按标题与稿件号搭建任务工作区。"""
        if custom_name:
            task_name = custom_name
        else:
            安全标题 = cls.sanitize_name(title)
            task_name = f"{安全标题}_{bvid}" if bvid else 安全标题

        return cls(task_name=task_name, base_dir=base_dir)

    @classmethod
    def to_absolute(cls, path: Union[str, Path]) -> Path:
        """相对仓库根目录换算为绝对路径（绝对路径直接归一化返回）。"""
        路径 = Path(str(path))
        if 路径.is_absolute():
            return 路径.resolve()
        return (cls.REPO_ROOT / str(path)).resolve()

    @classmethod
    def to_relative(cls, path: Union[str, Path]) -> str:
        """绝对路径换算为相对仓库根目录的相对路径（便于入库与展示）。"""
        try:
            绝对 = Path(str(path))
            if not 绝对.is_absolute():
                绝对 = (Path.cwd() / str(path)).resolve()
            else:
                绝对 = 绝对.resolve()
            return 绝对.relative_to(cls.REPO_ROOT).as_posix()
        except Exception:
            try:
                return os.path.relpath(str(path), str(cls.REPO_ROOT)).replace(os.sep, "/")
            except Exception:
                return str(path).replace(os.sep, "/")

    def save_parts(self, parts: Union[List[Any], Dict[str, Any]]) -> Path:
        """原子写入分集列表缓存。"""
        目标 = self.parts_cache_path
        目标.parent.mkdir(parents=True, exist_ok=True)
        临时 = 目标.with_suffix(f".tmp.{os.getpid()}")
        with open(临时, "w", encoding="utf-8") as 写:
            json.dump(parts, 写, ensure_ascii=False, indent=2)
            写.flush()
            os.fsync(写.fileno())
        os.replace(临时, 目标)
        return 目标

    def load_parts(self) -> List[Any]:
        """读取分集列表缓存（缺失或损坏时返回空列表）。"""
        目标 = self.parts_cache_path
        if not 目标.exists():
            return []
        try:
            with open(目标, "r", encoding="utf-8") as 读:
                数据 = json.load(读)
            if isinstance(数据, list):
                return 数据
            return []
        except Exception:
            return []

    def save_manifest(self, data: Dict[str, Any]):
        """持久化或增量更新任务清单（原子写入）。"""
        已有 = {}
        if self.manifest_file.exists():
            try:
                with open(self.manifest_file, "r", encoding="utf-8") as 读:
                    已有 = json.load(读)
            except Exception:
                已有 = {}

        已有.update(data)
        临时 = self.manifest_file.with_suffix(f".tmp.{os.getpid()}")
        with open(临时, "w", encoding="utf-8") as 写:
            json.dump(已有, 写, ensure_ascii=False, indent=2)
            写.flush()
            os.fsync(写.fileno())
        os.replace(临时, self.manifest_file)

    def load_manifest(self) -> Dict[str, Any]:
        """读取清单，不存在或损坏时返回空字典。"""
        if not self.manifest_file.exists():
            return {}
        try:
            with open(self.manifest_file, "r", encoding="utf-8") as 读:
                return json.load(读)
        except Exception:
            return {}
