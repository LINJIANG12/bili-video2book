#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pipeline Coordination Domain Service（流水线领域调度服务）。

职责：
1. 承载原 CLI 中 `cmd_pipeline` 的两阶段编排逻辑：
   阶段一「音频收齐」→ 阶段二「转录任务派发与落盘」→ 阶段三「知识块聚合」。
2. 收口跨命令共享的领域辅助函数（目标解析、412 富化、范围解析、任务书导出），
   供 CLI 的 audio / transcribe / note / cluster-notes 等命令复用。
3. 通过 PipelineGateError 表达硬门禁终止（等价于原实现中的 sys.exit 非零退出），
   CLI 层仅需捕获并转换为进程退出码。

设计约束：
- 不依赖 argparse 命名空间，参数全部显式传入，可独立单元测试；
- 输出行为与原 CLI 实现逐行一致，保证用户可感知行为零变化。
"""

import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from src.core.parser import BilibiliParser
from src.core.local_media import LocalMediaParser
from src.core.fetcher import AudioFetcher
from src.core.audio_chunker import AudioChunker
from src.core.workspace import TaskWorkspace, sanitize_filename
from src.core.kernel_extractor import KernelExtractor
from src.core import fsutil
from src.core import paths as _paths
from src.generator.block_synthesizer import BlockSynthesizer
from src.generator.prompt_templates import ArticlePromptTypeError

# 代码根（skill/）——仅用于断点续跑提示等展示；产物路径一律走 paths.products_root()
PROJECT_ROOT = _paths.code_root()


def _resolve_status_file() -> Path:
    """状态文件（记录上次 412/熔断）路径：产物根下唯一一份。

    三域分离后不再探测当前工作目录：在任意目录执行命令都写同一个状态文件，
    不会在别处凭空生成一个 output/。仅保留「读取旧 cwd/output 状态文件」的兼容探测。
    """
    current = _paths.products_root() / ".cli_status.json"
    if current.exists():
        return current
    legacy_cwd = Path.cwd() / "output" / ".cli_status.json"
    if legacy_cwd.exists():
        return legacy_cwd
    return current

_STATUS_FILE = _resolve_status_file()

# 412 断点续跑默认提示命令
_RESUME_HINT = 'bili-video2book pipeline "<链接>" --all --sessdata YOUR_SESSDATA'


class PipelineGateError(RuntimeError):
    """流水线硬门禁终止信号（CLI 层捕获后转换为 sys.exit(exit_code)）。"""

    def __init__(self, exit_code: int, message: str = ""):
        super().__init__(message or f"pipeline gate terminated (exit {exit_code})")
        self.exit_code = exit_code


def is_412(err: Any) -> bool:
    """判断异常是否为 412 风控拦截。"""
    return "412" in str(err)


def record_412_status(err: Any) -> None:
    """记录 412/熔断状态到状态文件供 info 读取。"""
    try:
        _STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
        _STATUS_FILE.write_text(
            json.dumps({"last_412": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "error": str(err)[:500]}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass


def format_412(err: Any, resume_hint: Optional[str] = None) -> str:
    """412 三要素文案：定性 + 可复制动作 + 预期。"""
    hint = resume_hint or _RESUME_HINT
    return (
        f"[412 风控拦截] {err}\n"
        "①定性：B 站风控拦截（请求过频/缺登录态），非视频删除。\n"
        "②可复制动作：浏览器登录 bilibili.com → F12 → 应用/存储 → Cookie → 复制 SESSDATA，"
        f"然后运行：python src/cli.py pipeline \"<链接>\" --all --sessdata YOUR_SESSDATA\n"
        f"③预期：等待 30-60 分钟后再试；跑 python src/cli.py info 验证状态；断点续跑：{hint}"
    )


def enrich_network_error(err: Any, resume_hint: Optional[str] = None) -> str:
    """区分 412 与普通网络错误，412 走三要素文案并落盘状态。"""
    if is_412(err):
        record_412_status(err)
        return format_412(err, resume_hint)
    return f"[网络/接口异常] {err}（非 412：建议检查网络后重试；频繁失败可补 --sessdata 后重跑）"


def get_audio_stream(
    bvid: str,
    cid: Any,
    sessdata: Optional[str] = None,
    prefer_quality: str = "low",
    resume_hint: Optional[str] = None,
) -> Dict[str, Any]:
    """音频流获取统一入口，412 富化后抛出。"""
    try:
        return AudioFetcher.get_audio_stream_info(bvid, cid, sessdata=sessdata, prefer_quality=prefer_quality)
    except Exception as err:
        raise RuntimeError(enrich_network_error(err, resume_hint)) from err


def resolve_article_type(article_type: str) -> Dict[str, str]:
    """解析长文提示词风格（供派发门禁与 manifest 记录复用）。"""
    from src.generator.prompt_templates import resolve_article_prompt

    return resolve_article_prompt(article_type)


def export_article_task(
    ws: TaskWorkspace,
    page_num: int,
    clean_title: str,
    audio_file: Any,
    title: str = "",
    cid: int = 0,
    chunk_minutes: int = 60,
    article_type: str = "",
) -> Path:
    """导出单集精读文章任务书（单集直出长文：听音后直接撰写 articles/）。

    长文写作提示词按 article_type 从提示词风格矩阵取用：风格未指定、拼写有误，
    或该类型尚无提示词时，一律抛 ArticlePromptTypeError（工具层不猜、不降级）。
    无外部 HTTP 依赖、无第三方 API Key 依赖，且不产出任何中间逐字稿。
    """
    import re as _re
    from src.core.audio_chunker import AudioChunker
    from src.generator.prompt_templates import resolve_article_prompt

    resolved = resolve_article_prompt(article_type)

    prefix = "" if _re.match(r"^P\d{2}_", clean_title) else f"P{page_num:02d}_"
    task_file = ws.articles_dir / f"{prefix}{clean_title}_TASK.md"
    task_file.parent.mkdir(parents=True, exist_ok=True)

    audio_path = Path(audio_file).resolve() if audio_file else None
    target_article = ws.articles_dir / f"{prefix}{clean_title}_精读文章.md"

    # 自动执行微切片（单片 <= 10 分钟，受控在 4MB 以内），供宿主的文件查看能力（原生多模态读文件）直接挂载
    slices = []
    if audio_path and audio_path.exists() and audio_path.stat().st_size > 1024:
        try:
            chunks_dir = ws.audio_dir / f"{prefix}{clean_title}_chunks"
            slices = AudioChunker.chunk_audio(str(audio_path), chunk_minutes=chunk_minutes, balanced=True, output_dir=str(chunks_dir))
        except Exception:
            slices = []

    # 生成分片清单文本
    if slices:
        slices_lines = []
        for s in slices:
            fp = s.get("filepath", str(audio_path))
            start_str = s.get("start_time_str", "00:00:00")
            end_str = s.get("end_time_str", "00:00:00")
            idx = s.get("chunk_index", 1)
            slices_lines.append(f"- [ ] 切片 {idx:02d} [{start_str} -> {end_str}]: `{fp}` (待听音)")
        slices_section = "\n".join(slices_lines)
    else:
        slices_section = f"- [ ] P{page_num:02d} 完整音频 (00:00 起): `{audio_file}`"

    article_prompt = (
        resolved["prompt"]
        .replace("{title}", title or clean_title)
        .replace("{part_title}", f"P{page_num:02d} {clean_title}")
        .replace(
            "{content}",
            "（本流程不产出中间逐字稿：请直接依据下方音频切片聆听所得的真实讲解内容撰写）\n\n"
            f"待听音切片清单：\n{slices_section}",
        )
    )

    # 本集预算（供子智能体判断上下文占用、供主 Agent 判断并发与打包粒度）
    from src.core import budget as _budget

    _时长秒 = 0.0
    if slices:
        try:
            _时长秒 = float(slices[-1].get("end_sec") or 0.0)
        except (TypeError, ValueError):
            _时长秒 = 0.0
    _系数 = _budget.audio_tokens_per_sec()
    _音频token = _budget.est_audio_tokens(_时长秒)
    _时长文本 = (
        f"{int(_时长秒 // 60):02d}:{int(_时长秒 % 60):02d}" if _时长秒 > 0 else "未知"
    )

    content = (
        f"# P{page_num:02d} {clean_title} 单集精读文章任务书（ARTICLE_TASK）\n\n"
        f"> 状态：need-agent-article | 单集直出长文：取到本集真实讲解内容后直接撰写精读长文\n"
        f"> 　　　　（通道 A 无中间产物，边听边写；通道 B 的逐字稿只是语料，不落盘成交付物）\n"
        f"> 长文风格：{resolved['label']}（{resolved['key']}）\n"
        f"> 执行者要求：由**子智能体**承担（一集一个；课程总时长 ≤ 60 分钟时主 Agent 可串行亲做）；\n"
        f"> 　　　　　　完成后只回报一行 `P{page_num:02d} | 文件路径 | 字节数 | 执行者`，**不回传正文**\n"
        f"> 本集预算：时长 {_时长文本} × {_系数:g} tok/s ≈ {_音频token:,} token 音频；切片 {len(slices) if slices else 1} 个\n"
        f"> 深度支持：宿主模型具备原生音频模态（可本地听音）\n\n"
        f"## 1. 任务输入与待听音切片清单\n\n"
        f"- 课程全称：{title}\n"
        f"- 分集序号：P{page_num:02d} {clean_title}\n"
        f"- 完整音频：`{audio_file}`\n"
        f"- 目标长文落盘路径：`{target_article}`\n\n"
        f"### 待听音切片清单（共 {len(slices) if slices else 1} 个切片）：\n\n"
        f"{slices_section}\n\n"
        f"---\n\n"
        f"## 2. 宿主 Agent 执行指引（单集直出长文）\n\n"
        f"1. **取音频并处理**：先看自己的工具列表，按原生音频能力二选一（两条通道的分页契约同构，续读循环可复用）：\n"
        f"   - **通道 A（工具列表里有 `read_audio`，优先）**：\n"
        f"     a. 对清单中的切片调用 `omni-media:read_audio`（`output_mode=\"file\"`）取得本地切片绝对路径；\n"
        f"     b. 用**宿主自己的文件查看能力**（能直接感知音频内容的那件工具；各平台工具名见技能内 references/host-tools/）打开该切片路径，直接聆听讲师原声、例题与板书讲解；\n"
        f"   - **通道 B（只有 `read_media`，宿主无原生音频）**：\n"
        f"     a. 对清单中的切片调用 `omni-media-ext:read_media`"
        f"（`mode=\"transcribe\"`，需要总结/问答时换 `mode`），直接取回文本；\n"
        f"     b. 返回文本首行的 `OMNI_STATUS` 注释若 `is_finished=false`，用 `start_time=next_start_time` 继续读下一卷；\n"
        f"     c. 注意 `mode` 在状态注释里指切片模式（`oneshot`/`chunked`），本次任务预设看 `task` 字段；\n"
        f"   - **共同要求**：不得跳过取音频这一步直接编造；正文须含讲师亲口讲的内容。\n"
        f"2. **撰写长文**：依据所得的真实讲解内容，按下方【文章撰写提示词】撰写深入技术长文；\n"
        f"3. **落盘**：用**宿主的文件写入能力**将长文写入上方目标长文落盘路径（严格保留，模块整编时不得删除）。\n\n"
        f"---\n\n"
        f"## 3. 文章撰写提示词\n\n"
        f"{article_prompt}\n"
    )
    task_file.write_text(content, encoding="utf-8")
    return task_file


def _offline_candidate_dirs(out_base: Path, bvid: str, custom_task: Optional[str] = None) -> List[Path]:
    """接口受阻时按 BV 号找回本地工作区目录（离线自愈的定位入口）。

    两级定位，越靠前越可信：

    1. `--task` 显式指定的目录；
    2. 目录名含完整 BV 号 / BV 号前缀——工作区名可能被 80 字符上限截断（如 `…_BV1P7b5z`）。

    只保留**确实有料**的目录（有 `parts.json` 或 `articles/` 下有长文）。
    """
    def _has_content(path: Path) -> bool:
        return (path / "parts.json").exists() or bool(_parts_from_articles(path))

    cands: List[Path] = []
    if custom_task:
        cands.append(out_base / TaskWorkspace.sanitize_name(custom_task))
    if out_base.exists():
        # 这里遍历的是**产物根第一层**：`Path.is_dir()` 遇到 Windows「不受信任的装入点」
        # 会抛 OSError，让离线自愈整体失败。走 fsutil 的安全判定，坏条目跳过即可。
        found = [p for p in out_base.glob(f"*{bvid}*") if fsutil.is_dir(p)]
        if not found and len(bvid) > 6:
            found = [p for p in out_base.glob(f"*{bvid[:6]}*") if fsutil.is_dir(p) and _has_content(p)]
        cands.extend(found)
    # 目录名里连 BV 号（或其前缀）都没有的工作区**无法**由 BV 号唯一确定：实测同一输出根下
    # 确有两个名字都不含 BV 号的 80 字符截断目录（NLP 课与另一门），任何按名字的猜法都会在
    # 它们之间摇摆。这类工作区请显式用 `--task "<工作区目录名>"` 指定——那条路是确定的。
    # 这里刻意不猜：猜错会静默读写到别的课的产物上，比自愈失败更糟。
    return cands


def _workspace_title(dir_path: Path, manifest: Optional[Dict[str, Any]] = None) -> str:
    """离线自愈时的课程标题：**目录名优先**，manifest 的 title 只作兜底。

    这里的标题会交给 `TaskWorkspace.create` 再推导一次工作区目录，所以它必须能还原出
    同一个目录——目录名是唯一满足这一点的事实。若改用 manifest 里可能被用户改短的 title，
    推导出的工作区就会指向别处（轻则空跑，重则 exit 2），而真正的成品就在旁边。
    """
    derived = dir_path.name.split("_")[0].strip()
    if derived:
        return derived
    return str((manifest or {}).get("title") or "").strip() or dir_path.name


def _parts_from_articles(dir_path: Path) -> List[Dict[str, Any]]:
    """拓扑缓存不可用时，从 `articles/` 已有长文的文件名反推集号（离线兜底）。

    为什么需要：`parts.json` 可能缺失或被写坏，而长文是 Agent 落盘的真实产物。
    没有集号就无法规划、也无法派发，一条本该跑完的命令会直接 traceback 退出。
    """
    parts: Dict[int, Dict[str, Any]] = {}
    articles_dir = dir_path / "articles"
    if not articles_dir.exists():
        return []
    for entry in sorted(articles_dir.glob("P*_*.md")):
        if entry.name.endswith("_TASK.md"):
            continue
        matched = re.match(r"^P(\d+)_(.*?)\.md$", entry.name)
        if not matched:
            continue
        title = matched.group(2)
        for suffix in ("_精读文章", "_精读", "_文章"):
            if title.endswith(suffix):
                title = title[: -len(suffix)]
        parts.setdefault(int(matched.group(1)), {"page": int(matched.group(1)), "title": title.strip()})
    return [parts[k] for k in sorted(parts)]


def resolve_target_info(
    target: str,
    sessdata: Optional[str] = None,
    custom_task: Optional[str] = None,
    base_dir: Optional[Any] = None,
    limit: Optional[int] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """多态解析本地媒体、B站、YouTube 或抖音元数据；网络失败时用本地缓存离线自愈。"""
    from src.core.ingestion import get_coordinator

    coordinator = get_coordinator()
    return coordinator.resolve_target_info(
        target,
        sessdata=sessdata,
        custom_task=custom_task,
        base_dir=base_dir,
        limit=limit,
        **kwargs,
    )


def resolve_scope_parts(info: Dict[str, Any], ws: Any) -> List[Dict[str, Any]]:
    """集号基准：**工作区 `parts.json` 优先**，缺失才用在线解析结果。

    为什么不能直接用 `info["parts"]`：在线解析永远返回课程**全集**。用户 `--range 9-87`
    建的工作区里只有 P09–P87，拿 185 集当基准会让规划任务书列错集号、让规划校验把
    用户自己的区间判成非法，甚至把整个阶段二卡死——集号是工作区的事实，工具无权放大它。

    在线解析只用于**首次建工作区**（`pipeline`），此后一律以工作区为准。
    """
    local = [
        p for p in (ws.load_parts() or [])
        if isinstance(p, dict) and p.get("page") is not None
    ]
    online = [p for p in (info.get("parts") or []) if isinstance(p, dict)]
    if not local:
        return online
    if online and {int(p["page"]) for p in online} != {int(p["page"]) for p in local}:
        print(
            f"[i] 集号基准取工作区 parts.json（{len(local)} 集，"
            f"P{min(int(p['page']) for p in local):02d}–P{max(int(p['page']) for p in local):02d}）；"
            f"在线全集为 {len(online)} 集——以工作区为准"
        )
    return sorted(local, key=lambda p: int(p["page"]))


def resolve_course_title(info: Dict[str, Any], ws: Any) -> str:
    """课程标题：manifest → parts.json 所属工作区名 → 在线解析（离线也拿得到）。

    标题会写进规划提示词与任务书抬头，取错了会让 Agent 对着别的课名做规划。
    """
    try:
        manifest_title = str((ws.load_manifest() or {}).get("title") or "").strip()
        if manifest_title:
            return manifest_title
    except Exception:
        pass
    online_title = str(info.get("title") or "").strip()
    if online_title:
        return online_title
    return ws.root_dir.name


def parse_range_string(range_str: str, max_val: int) -> List[int]:
    """解析范围字符串（'1-10' / '1,3,5' / '5-'）为 1 起始的分集页码列表。"""
    pages: Set[int] = set()
    if max_val <= 0:
        return []
    for part in range_str.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            if "-" in part:
                s_str, e_str = part.split("-", 1)
                start = int(s_str.strip()) if s_str.strip() else 1
                end = int(e_str.strip()) if e_str.strip() else max_val
                if start <= max_val and end >= 1:
                    for i in range(max(1, start), min(max_val, end) + 1):
                        pages.add(i)
            else:
                p = int(part)
                if 1 <= p <= max_val:
                    pages.add(p)
        except ValueError:
            continue
    return sorted(pages)


def classify_audio_error(err: Any) -> str:
    """失败分类：412 风控 / 缺登录态 / 网络超时 / 其他。"""
    msg = str(err)
    if "412" in msg:
        return "412风控拦截"
    low = msg.lower()
    if any(k in msg for k in ("SESSDATA", "sessdata", "401", "403", "登录", "Cookie", "cookie")):
        return "缺登录态/权限"
    if any(k in low for k in ("timeout", "timed out", "connection", "network", "dns", "reset", "超时", "网络", "连接")):
        return "网络超时"
    return "其他下载异常"


class PipelineCoordinator:
    """两阶段流水线调度器：音频收齐 → 转录任务派发（+可选知识块聚合）。"""

    def run(
        self,
        url: str,
        sessdata: Optional[str] = None,
        task: Optional[str] = None,
        base_dir: Optional[Any] = None,
        page: Optional[int] = None,
        range_str: Optional[str] = None,
        process_all: bool = False,
        force: bool = False,
        prefetch_workers: int = 12,
        skip_failed: bool = False,
        quality: str = "low",
        chunk_minutes: int = 60,
        article_type: str = "",
    ) -> Dict[str, Any]:
        """执行完整流水线；硬门禁失败时抛出 PipelineGateError（由 CLI 转换为退出码）。"""
        from concurrent.futures import ThreadPoolExecutor

        # 工作区参数必须一并传入：离线自愈按 base_dir/task 找 parts.json 缓存，
        # 漏传会退化成当前目录下的默认 output/，导致 --base-dir 指定时自愈失效。
        info = resolve_target_info(url, sessdata=sessdata, custom_task=task, base_dir=base_dir)
        bvid = info["bvid"]

        ws = TaskWorkspace.create(
            title=info["title"],
            bvid=bvid,
            custom_name=task,
            base_dir=base_dir,
            info_name=info.get("workspace_name"),
        )
        print("=" * 65)
        print(f"[*] 全流程处理流水线启动 (Task Workspace: {ws.root_dir.name})")
        print("=" * 65)

        print("[*] 阶段一策略: 单集直出长文（听音后直接撰写 articles/；长文已存在即视为完成）")

        if process_all or range_str:
            all_parts = info["parts"]
            if range_str:
                target_indices = parse_range_string(range_str, len(all_parts))
                selected_parts = [all_parts[i - 1] for i in target_indices]
            else:
                selected_parts = all_parts
        elif info["has_multi_pages"]:
            req_page = page if page is not None else (info.get("url_page") or 1)
            p_idx = max(1, min(req_page, len(info["parts"])))
            selected_parts = [info["parts"][p_idx - 1]]
        else:
            selected_parts = [{
                "page": 1,
                "title": info["title"],
                "cid": info["cid"],
                "duration": info["duration"],
                "filepath": info.get("source_path", ""),
            }]

        total_episodes = len(selected_parts)
        print(f"[*] 待处理分集总数: {total_episodes}")

        # 断点续派过滤：manifest 中 status==success 的 page 跳过（force 时不过滤）
        if not force:
            try:
                _done_pages = {
                    d.get("page") for d in ws.load_manifest(absolute=True).get("details", [])
                    if d.get("status") == "success"
                }
            except Exception:
                _done_pages = set()
            if _done_pages:
                kept = []
                for p in selected_parts:
                    if p.get("page") in _done_pages:
                        print(f"[skip] P{p.get('page'):02d} {p.get('title')} 已完成，跳过")
                    else:
                        kept.append(p)
                selected_parts = kept
                total_episodes = len(selected_parts)
                print(f"[*] 断点续派后待处理: {total_episodes}")
        else:
            print("[*] --force 已指定，不过滤已完成分集")

        prefetch_workers = max(1, int(prefetch_workers or 1))
        print(f"[*] 并发配置: 音频预取 {prefetch_workers} 线程")

        def _audio_paths(p: Dict[str, Any]):
            clean_p_title = sanitize_filename(p["title"])
            return ws.audio_dir / f"P{p['page']:02d}_{clean_p_title}.m4a", clean_p_title

        def _ensure_audio_once(p: Dict[str, Any]) -> Path:
            # 单次音频收齐尝试，命中缓存直接返回
            audio_file, _ = _audio_paths(p)
            if audio_file.exists() and audio_file.stat().st_size >= 10240 and not force:
                return audio_file

            source_type = info.get("source_type") or ("local" if info.get("is_local") else "bilibili")
            print(f"    [prefetch] P{p['page']:02d} 获取音频 ({source_type})...")

            from src.core.ingestion import get_coordinator
            coordinator = get_coordinator()
            coordinator.fetch_episode_audio(
                info,
                p,
                audio_file,
                force=force,
                sessdata=sessdata,
                quality=quality,
            )
            print(f"    [prefetch] P{p['page']:02d} 音频就绪: {audio_file.name}")
            return audio_file

        def _ensure_audio_with_retry(p: Dict[str, Any]) -> Path:
            # 单集下载失败退避重试 3 次（共 4 次尝试），退避 1/2/4 秒
            last_err: Optional[Exception] = None
            for attempt in range(4):
                try:
                    return _ensure_audio_once(p)
                except Exception as err:
                    last_err = err
                    if attempt < 3:
                        print(f"    [retry] P{p['page']:02d} 第{attempt + 1}次失败，退避重试 ({classify_audio_error(err)}): {str(err)[:120]}")
                        try:
                            time.sleep(2 ** attempt)
                        except Exception:
                            pass
            raise last_err  # type: ignore[misc]

        # ===== 阶段一「音频收齐」：并发下载/提取全部选中集音频 =====
        print("=" * 65)
        print("[*] 阶段一：音频收齐（全部选中集并发下载/提取）")
        print("=" * 65)
        audio_failed: List[Dict[str, Any]] = []
        audio_ready: Dict[int, Path] = {}
        with ThreadPoolExecutor(max_workers=prefetch_workers) as prefetch_pool:
            fut_map = {p["page"]: prefetch_pool.submit(_ensure_audio_with_retry, p) for p in selected_parts}
            for p in selected_parts:
                try:
                    audio_ready[p["page"]] = fut_map[p["page"]].result()
                except Exception as err:
                    audio_failed.append({
                        "page": p["page"], "title": p["title"], "cid": p["cid"],
                        "error": str(err), "category": classify_audio_error(err), "status": "failed",
                    })
        # 阶段一结束后写检查点 parts.json + manifest
        # 局部运行（--page/--range）只处理选中分集：必须与既有拓扑**合并**而非覆盖，
        # 否则会把分集拓扑缓存截断成子集（离线自愈与 sync 对账都会据此误判规模）。
        try:
            _clean_parts = [{k: v for k, v in p.items() if not k.startswith("_")} for p in selected_parts]
            ws.save_parts(TaskWorkspace.merge_parts(ws.load_parts(), _clean_parts))
        except Exception:
            pass
        ws.save_manifest({
            "audio_stage": {"total": len(selected_parts), "ready": len(audio_ready), "failed": len(audio_failed)},
            "audio_failed_episodes": [dict(d) for d in audio_failed],
        })
        skipped_entries: List[Dict[str, Any]] = []
        if audio_failed:
            if skip_failed:
                # 显式 opt-in 豁免：记入 manifest 跳过名单，不进转录
                skipped_entries = list(audio_failed)
                audio_failed = []
                print(f"[*] --skip-failed 已指定，豁免 {len(skipped_entries)} 集（不进转录）")
                ws.save_manifest({
                    "skipped_episodes": skipped_entries,
                    "skipped_pages": [d.get("page") for d in skipped_entries],
                })
            else:
                # 任一集最终失败则严格终止报告（硬切分门禁，未进入转录）
                print("\n" + "=" * 65, file=sys.stderr)
                print("[✗] 阶段一终止：音频收齐失败（硬切分门禁，未进入转录）", file=sys.stderr)
                print(f"失败集清单（共 {len(audio_failed)} 集）：", file=sys.stderr)
                for f_ep in audio_failed:
                    print(f"    - P{f_ep['page']:02d} {f_ep['title']} [{f_ep.get('category')}]：{str(f_ep['error'])[:160]}", file=sys.stderr)
                print("失败分类统计：", file=sys.stderr)
                _cats: Dict[str, int] = {}
                for f_ep in audio_failed:
                    _cats[f_ep.get("category", "其他下载异常")] = _cats.get(f_ep.get("category", "其他下载异常"), 0) + 1
                for _c, _n in _cats.items():
                    print(f"    - {_c} × {_n}", file=sys.stderr)
                print("三选项：①删集重跑（缩小 --range 剔除失败集后重跑）②补--sessdata（浏览器复制 SESSDATA 后重跑）③人工语料外挂：把人工整理的本集文本放至 <task>/subtitles/PXX_<标题>_clean.txt 后重跑（该目录是逐字稿与人工语料的正式存放位置）", file=sys.stderr)
                print("=" * 65, file=sys.stderr)
                raise PipelineGateError(2)

        # ===== 阶段二「单集精读文章任务书派发」：单集直出长文，直接产出 articles/ =====
        _skip_pages = {d.get("page") for d in skipped_entries}
        effective_parts = [p for p in selected_parts if p.get("page") not in _skip_pages]
        # 阶段二入口校验音频 100% 就绪，否则拒绝并指去向
        _missing = []
        for p in effective_parts:
            _af, _ = _audio_paths(p)
            if not (_af.exists() and _af.stat().st_size >= 10240):
                _missing.append(p)
        if _missing:
            print("\n" + "=" * 65, file=sys.stderr)
            print("[✗] 阶段二拒绝启动：音频未 100% 就绪（请回阶段一排查音频目录）", file=sys.stderr)
            for _m in _missing:
                _af, _ = _audio_paths(_m)
                print(f"    - P{_m['page']:02d} {_m['title']} 缺失/过小：{_af}", file=sys.stderr)
            print(f"去向：检查 {ws.audio_dir} 与 parts.json，补齐后重跑 pipeline（断点续派自动跳过已完成集）", file=sys.stderr)
            print("=" * 65, file=sys.stderr)
            raise PipelineGateError(2)
        print("=" * 65)
        print(f"[*] 阶段二：派发单集精读文章任务书（共 {len(effective_parts)} 集，单集直出长文）")
        print(f"[*] 长文提示词风格：{article_type or '未指定（将在派发时终止并给出风格菜单）'}")
        print("=" * 65)

        manifest_entries: List[Dict[str, Any]] = []
        for idx, p in enumerate(effective_parts, 1):
            p_num = p["page"]
            audio_file, clean_p_title = _audio_paths(p)
            article_file = ws.articles_dir / f"P{p_num:02d}_{clean_p_title}_精读文章.md"
            print(f"\n[{idx:02d}/{len(effective_parts):02d}] P{p_num:02d}: {p['title']}")

            # 复用判定走 KernelExtractor 的宽容定位：历史工作区存在无 _精读文章 后缀的长文，
            # 精确文件名匹配会误判为未写并要求重做。
            existing_article = None if force else KernelExtractor.find_article(ws, p_num)
            if existing_article is not None and existing_article.stat().st_size >= 1000:
                print(f"    [cached] 单集精读长文已存在，跳过派发: {existing_article.name}")
                manifest_entries.append({
                    "page": p_num, "title": p["title"], "cid": p["cid"],
                    "audio": str(audio_file), "article": str(existing_article),
                    "asr_engine": "agent-native", "doc_engine": "agent-native",
                    "status": "success",
                })
                continue

            # 长文风格门禁（二次防线）：CLI 层（cmd_pipeline）已在入口前确认风格并 exit 4；
            # 此处再校验一次，保证直接调用领域服务的调用方也拿不到未命中预设的提示词。
            try:
                _resolved_type = resolve_article_type(article_type)
            except ArticlePromptTypeError as err:
                print("\n" + err.report, file=sys.stderr)
                print("去向：主 Agent 先依课程标题与分集标题判定类型，再用 --article-type 重跑本命令。", file=sys.stderr)
                raise PipelineGateError(4, f"长文提示词风格门禁终止：{err.reason}") from err

            try:
                task_file = export_article_task(
                    ws, p_num, clean_p_title, audio_file,
                    title=info["title"], cid=p["cid"], chunk_minutes=chunk_minutes,
                    article_type=article_type,
                )
            except Exception as err:
                print("\n" + "=" * 65, file=sys.stderr)
                print(f"[✗] 文章任务书导出失败，终止任务：P{p_num:02d}：{err}", file=sys.stderr)
                print("①排障重跑：检查 articles 目录写权限与磁盘空间后重跑 pipeline", file=sys.stderr)
                print("②中止：已收齐音频保留在 audio/ 可稍后重跑", file=sys.stderr)
                print("=" * 65, file=sys.stderr)
                raise PipelineGateError(3)

            print(f"    [agent] 已导出文章任务书，待 Agent 听音撰写: {task_file.name}")
            manifest_entries.append({
                "page": p_num, "title": p["title"], "cid": p["cid"],
                "audio": str(audio_file), "task_prompt": str(task_file),
                "article": str(article_file), "article_type": _resolved_type["key"],
                "asr_engine": "agent-native", "doc_engine": "agent-native",
                "status": "need-agent-article",
            })

        # ===== 阶段三「两趟语义聚合」：模块规划与笔记归并均由宿主 Agent 产出后才派发 =====
        plan = None
        note_plan: List[Dict[str, Any]] = []
        block_results: List[Dict[str, Any]] = []
        if process_all:
            scope_parts = resolve_scope_parts(info, ws)
            # 语料摘要：优先取 Agent 已撰写的单集长文，其次 subtitles/ 下的逐字稿或人工语料
            summaries = {}
            for p in scope_parts:
                p_num = int(p["page"])
                art = KernelExtractor.find_article(ws, p_num)
                if art is not None:
                    try:
                        summaries[p_num] = art.read_text(encoding="utf-8")[:400]
                    except Exception:
                        pass
            for p in scope_parts:
                p_num = int(p["page"])
                if p_num in summaries:
                    continue
                clean_t = sanitize_filename(p["title"])
                clean_f = ws.subtitles_dir / f"P{p_num:02d}_{clean_t}_clean.txt"
                if clean_f.exists() and clean_f.stat().st_size > 50:
                    summaries[p_num] = clean_f.read_text(encoding="utf-8")[:300]

            # 语料就绪门禁：若没有任何语料落盘，阶段三后置挂起，防止透支生成空壳大笔记
            if not summaries:
                print("\n" + "=" * 65)
                print("[*] 阶段三后置：精读文章任务书已就绪，但尚无任何语料落盘。")
                print("[*] 待宿主 Agent 将长文写入 articles/ 后，重跑 pipeline --all 将自动聚合。")
                print("=" * 65)
            else:
                print("\n" + "=" * 65)
                print("[*] 阶段三：两趟语义聚合（模块规划 → 笔记归并，均由宿主 Agent 产出）")
                print("=" * 65)

                # 两趟规划 + 笔记派发的唯一实现；缺规划时用兜底继续，绝不终止
                outcome = BlockSynthesizer.dispatch_notes(
                    ws,
                    scope_parts,
                    course_title=resolve_course_title(info, ws),
                    force_plan=False,
                    transcript_summaries=summaries,
                )
                note_plan = outcome["notes"]
                block_results = outcome["results"]
                if outcome["block_status"] in ("placeholder", "unmerged"):
                    print("[*] 阶段三后置：已导出规划任务书，待宿主 Agent 产出 topic_plan.json（及 note_plan.json）后重跑。")
                    print(f"[*] 任务书: {ws.root_dir / 'topic_plan_TASK.md'}")
                else:
                    # planned / salvaged 都算「Agent 已给出模块边界」，可以收尾
                    plan = outcome["blocks"]
        elif info["has_multi_pages"]:
            print("[*] 分区间运行：聚合后置，待 --all 全量语料齐后统一规划")

        # ===== Manifest 按 page 合并落盘（工作区原生相对路径化） =====
        _existing = ws.load_manifest(absolute=True)
        _merged = {d.get("page"): d for d in _existing.get("details", []) if isinstance(d, dict)}
        for d in manifest_entries:
            _merged[d.get("page")] = d
        _failed_merged = {d.get("page"): d for d in _existing.get("failed_episodes", []) if isinstance(d, dict)}

        # 仅当所有有效分集转录成功（且无历史失败分集）时才标记全流程完毕
        # 说明：本趟的失败集在阶段一/阶段二就以 PipelineGateError 终止，不存在「本趟失败清单」，
        # 因此此处只继承 manifest 里的历史失败记录。
        _all_success = (
            len(_merged) >= len(effective_parts)
            and all(d.get("status") == "success" for d in _merged.values())
            and not _failed_merged
        )
        _existing["pipeline_completed"] = bool(_all_success and (not process_all or plan is not None))
        _existing["processed_episodes"] = sum(1 for d in _merged.values() if d.get("status") == "success")
        _existing["details"] = [_merged[k] for k in sorted(_merged)]
        _existing["failed_episodes"] = [_failed_merged[k] for k in sorted(_failed_merged)]
        _existing["skipped_episodes"] = skipped_entries
        _existing["skipped_pages"] = [d.get("page") for d in skipped_entries]
        if process_all and plan is not None:
            _existing["knowledge_blocks_plan"] = plan
            _existing["knowledge_blocks_results"] = block_results
            _existing["note_plan"] = note_plan
        ws.save_manifest(_existing)
        print("\n" + "=" * 65)
        print(f"[✓] 工具层流水线执行完毕！语料与任务书已归档至: {ws.root_dir}")
        print("【★ 宿主 Agent 接管指南】：")
        print(f"  1. 单集精读文章任务书: {ws.articles_dir}/*_TASK.md")
        if process_all:
            print(f"  2. 笔记任务书: {ws.notes_dir}/*_TASK.md")
        print("  3. 请主程序以 5 个并发通道（Task 子代理或并行会话）直接领跑任务书，执行真正的认知写作！")
        print("=" * 65)

        # ===== 任务书回收：成品已落盘的分集/模块任务书即时清场（每类保留 1 份范本） =====
        try:
            from .task_cleanup import cleanup_completed_tasks as _cleanup_tasks
            _reclaim = _cleanup_tasks(ws, keep_per_category=1)
            if _reclaim["deleted"]:
                print(f"[*] 已回收 {len(_reclaim['deleted'])} 份已完成任务书（每类保留 1 份范本供查阅提示词）")
        except Exception as _reclaim_err:  # 回收失败不得影响主流程
            print(f"[!] 任务书回收已跳过：{_reclaim_err}", file=sys.stderr)

        # ===== 账本对账：以磁盘产成为唯一真相回填 manifest（消除账本与产物脱节） =====
        try:
            from .state_sync import reconcile_workspace_manifest as _reconcile
            _sync = _reconcile(ws)
            print(f"[*] 账本对账：分集 {_sync['success']}/{_sync['total']} 集达标 | "
                  f"待办 {_sync['pending']} | 模块笔记 {_sync['notes']} 份 | "
                  f"教材 {_sync['textbooks']} 部 | "
                  f"pipeline_completed={_sync['pipeline_completed']}")
        except Exception as _sync_err:
            print(f"[!] 账本对账已跳过：{_sync_err}", file=sys.stderr)

        return {
            "workspace": ws,
            "manifest": _existing,
            "plan": plan,
            "block_results": block_results,
            "failed_entries": list(_failed_merged.values()),
        }
