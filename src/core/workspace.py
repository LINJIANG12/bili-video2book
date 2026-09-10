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

    非法字符正则 = re.compile(r'[\\/*?:"<>|\n\r\t]+')

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
    def sanitize_name(cls, raw_name: str) -> str:
        """清理非法文件系统字符并限制任务文件夹长度（最大 80 字符，防 Windows MAX_PATH 溢出）。"""
        清理后 = cls.非法字符正则.sub("_", raw_name)
        清理后 = re.sub(r"_+", "_", 清理后).strip(" ._-")
        return 清理后[:80] if 清理后 else "task_unnamed"

    @classmethod
    def sanitize_title(cls, title: str) -> str:
        """用于文件名的分集或稿件标题转义：不执行字符过滤式清洗（保留 C++、C#、1.1、括号等原样符号），
        仅替换操作系统硬性禁止的非法字符并规范化空白与长度。"""
        cleaned = cls.非法字符正则.sub("_", title)
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" ._-")
        return cleaned[:80] if cleaned else "part"

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

    PATH_KEYS = {
        "audio", "transcript", "task_prompt", "task_file", "article",
        "audio_file", "filepath", "source_path", "target_path", "chunk_path", "chunk_file"
    }

    @classmethod
    def relativize_obj(cls, obj: Any) -> Any:
        """递归将字典/列表中属于路径键的值换算为相对仓库根目录的相对路径。"""
        if isinstance(obj, dict):
            return {
                k: (cls.to_relative(v) if k in cls.PATH_KEYS and isinstance(v, (str, Path)) else cls.relativize_obj(v))
                for k, v in obj.items()
            }
        if isinstance(obj, list):
            return [cls.relativize_obj(x) for x in obj]
        return obj

    @classmethod
    def absolutize_obj(cls, obj: Any) -> Any:
        """递归将字典/列表中属于路径键的值换算为绝对路径供程序内部安全读取。"""
        if isinstance(obj, dict):
            return {
                k: (str(cls.to_absolute(v)) if k in cls.PATH_KEYS and isinstance(v, (str, Path)) else cls.absolutize_obj(v))
                for k, v in obj.items()
            }
        if isinstance(obj, list):
            return [cls.absolutize_obj(x) for x in obj]
        return obj

    def save_manifest(self, data: Dict[str, Any], relative: bool = True):
        """持久化或增量更新任务清单（原子写入，默认转换为相对路径保持跨环境便携）。"""
        已有 = {}
        if self.manifest_file.exists():
            try:
                with open(self.manifest_file, "r", encoding="utf-8") as 读:
                    已有 = json.load(读)
            except Exception:
                已有 = {}

        payload = self.relativize_obj(data) if relative else data
        已有.update(payload)
        临时 = self.manifest_file.with_suffix(f".tmp.{os.getpid()}")
        with open(临时, "w", encoding="utf-8") as 写:
            json.dump(已有, 写, ensure_ascii=False, indent=2)
            写.flush()
            os.fsync(写.fileno())
        os.replace(临时, self.manifest_file)

    def load_manifest(self, absolute: bool = False) -> Dict[str, Any]:
        """读取清单，不存在或损坏时返回空字典；可选项转为绝对路径。"""
        if not self.manifest_file.exists():
            return {}
        try:
            with open(self.manifest_file, "r", encoding="utf-8") as 读:
                data = json.load(读)
            if absolute:
                return self.absolutize_obj(data)
            return data
        except Exception:
            return {}

    @staticmethod
    def compute_file_hash(filepath: Union[str, Path]) -> str:
        """计算指定文件的 SHA-256 摘要哈希。"""
        import hashlib
        p = Path(filepath)
        if not p.is_file():
            return ""
        h = hashlib.sha256()
        with open(p, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()

    def scan_audio_fingerprints(self) -> Dict[str, List[Dict[str, Any]]]:
        """扫描 audio 目录下所有分集音频的 SHA-256 指纹，按 hash 归组以识别重复分集。"""
        fingerprints: Dict[str, List[Dict[str, Any]]] = {}
        if not self.audio_dir.exists():
            return fingerprints

        for audio_file in sorted(self.audio_dir.glob("P*.*")):
            if audio_file.suffix.lower() not in (".m4a", ".mp3", ".wav", ".aac", ".flac"):
                continue
            m = re.match(r"P(\d+)", audio_file.name)
            page = int(m.group(1)) if m else None
            h = self.compute_file_hash(audio_file)
            if h not in fingerprints:
                fingerprints[h] = []
            fingerprints[h].append({
                "page": page,
                "file": audio_file,
                "name": audio_file.name,
                "size": audio_file.stat().st_size,
            })
        return fingerprints

    @staticmethod
    def _final_artifacts(directory: Path, page: int, tail: str) -> List[Path]:
        """定位某集已落盘的最终产物，排除任务书（*_TASK.md）。"""
        return [
            f for f in sorted(directory.glob(f"P{page:02d}_*{tail}"))
            if not f.name.endswith("_TASK.md")
        ]

    def sync_duplicate_assets(self, dry_run: bool = False) -> List[Dict[str, Any]]:
        """检测并自动复用重复音频的字幕与长文产物，实现 0 Token 零成本去重同步。

        零中间逐字稿链路的最终产物是 articles/ 长文，subtitles/ 字幕属历史遗留，
        因此字幕是有则顺带同步的可选产物，不再充当复用前提。
        """
        import shutil
        fingerprints = self.scan_audio_fingerprints()
        synced = []

        for h, items in fingerprints.items():
            if len(items) <= 1:
                continue
            items_sorted = sorted(items, key=lambda x: (x["page"] if x["page"] is not None else 9999))
            primary = items_sorted[0]
            p_page = primary["page"]
            if p_page is None:
                continue

            prim_art = self._final_artifacts(self.articles_dir, p_page, ".md")
            prim_sub = self._final_artifacts(self.subtitles_dir, p_page, "_clean.txt")

            if not prim_art and not prim_sub:
                continue

            src_art = prim_art[0] if prim_art else None
            src_sub = prim_sub[0] if prim_sub else None

            for dup in items_sorted[1:]:
                d_page = dup["page"]
                if d_page is None:
                    continue

                target_art = self._final_artifacts(self.articles_dir, d_page, ".md")
                target_sub = self._final_artifacts(self.subtitles_dir, d_page, "_clean.txt")

                need_art = src_art is not None and (not target_art or target_art[0].stat().st_size == 0)
                need_sub = src_sub is not None and (not target_sub or target_sub[0].stat().st_size == 0)

                if need_art or need_sub:
                    m_d = re.match(r"P\d+_(.*)\.[^.]+", dup["name"])
                    d_title = m_d.group(1) if m_d else f"P{d_page:02d}"

                    dst_sub = self.subtitles_dir / f"P{d_page:02d}_{d_title}_clean.txt"
                    dst_art = self.articles_dir / f"P{d_page:02d}_{d_title}_精读文章.md"

                    if not dry_run:
                        if need_sub:
                            shutil.copy2(src_sub, dst_sub)
                        if need_art:
                            content = src_art.read_text(encoding="utf-8")
                            dst_art.write_text(content, encoding="utf-8")

                    synced.append({
                        "src_page": p_page,
                        "dst_page": d_page,
                        "hash": h[:12],
                        "synced_sub": need_sub,
                        "synced_art": need_art,
                    })

        return synced



def sanitize_filename(name: str, max_len: int = 80) -> str:
    """清理用于文件名的分集或稿件标题（模块级快捷函数）。"""
    return TaskWorkspace.sanitize_title(name)[:max_len]

