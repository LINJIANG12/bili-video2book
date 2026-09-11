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
from src.generator.topic_planner import SemanticTopicPlanner
from src.generator.block_synthesizer import BlockSynthesizer
from src.generator.prompt_templates import ArticlePromptTypeError

# 仓库根目录（状态文件与断点续跑提示的换算基准）
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# 状态文件记录上次 412/熔断，无则 info 显示“无记录”
# 优先保存在当前工作目录的 output/ 下，其次保存在包根目录
def _resolve_status_file() -> Path:
    cwd_path = Path.cwd() / "output" / ".cli_status.json"
    if cwd_path.exists():
        return cwd_path
    root_path = PROJECT_ROOT / "output" / ".cli_status.json"
    if root_path.exists():
        return root_path
    return cwd_path

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
    """导出单集精读文章任务书（零中间逐字稿：听音后直接撰写 articles/）。

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

    # 自动执行微切片（单片 <= 10 分钟，受控在 4MB 以内），供 Antigravity view_file 及 ChatGPT 附件挂载
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

    content = (
        f"# P{page_num:02d} {clean_title} 单集精读文章任务书（ARTICLE_TASK）\n\n"
        f"> 状态：need-agent-article | 零中间逐字稿：听音后直接撰写精读长文\n"
        f"> 长文风格：{resolved['label']}（{resolved['key']}）\n"
        f"> 深度支持平台：Antigravity（Gemini 多模态内核）与 ChatGPT（GPT-4o Audio / Codex 内核）\n\n"
        f"## 1. 任务输入与待听音切片清单\n\n"
        f"- 课程全称：{title}\n"
        f"- 分集序号：P{page_num:02d} {clean_title}\n"
        f"- 完整音频：`{audio_file}`\n"
        f"- 目标长文落盘路径：`{target_article}`\n\n"
        f"### 待听音切片清单（共 {len(slices) if slices else 1} 个切片）：\n\n"
        f"{slices_section}\n\n"
        f"---\n\n"
        f"## 2. 宿主 Agent 执行指引（零中间逐字稿）\n\n"
        f"1. **取切片**：对清单中的切片调用 MCP 工具 `omni-media:read_audio`（`output_mode=\"file\"`）取得本地切片绝对路径；\n"
        f"2. **原生听音**：调用宿主原生 `view_file` 工具读取该切片路径，直接聆听讲师原声、例题与板书讲解；\n"
        f"3. **撰写长文**：依据聆听所得的真实讲解内容，按下方【文章撰写提示词】撰写深入技术长文；\n"
        f"4. **落盘**：调用 `write_to_file` 将长文写入上方目标长文落盘路径（严格保留，模块整编时不得删除）。\n\n"
        f"---\n\n"
        f"## 3. 文章撰写提示词\n\n"
        f"{article_prompt}\n"
    )
    task_file.write_text(content, encoding="utf-8")
    return task_file


def resolve_target_info(
    target: str,
    sessdata: Optional[str] = None,
    custom_task: Optional[str] = None,
    base_dir: str = "output",
) -> Dict[str, Any]:
    """多态解析本地媒体或 B 站元数据；网络失败且存在本地 parts.json 缓存时自动离线自愈。"""
    if LocalMediaParser.is_local_media(target):
        return LocalMediaParser.parse(target)
    try:
        return BilibiliParser.parse_video(target, sessdata=sessdata)
    except Exception as err:
        # 离线自愈：接口被风控或网络中断时，优先加载本地保存的分集拓扑离线运行
        bvid = BilibiliParser.extract_bvid(target)
        if bvid:
            out_base = Path(base_dir).resolve() if Path(base_dir).is_absolute() else (Path.cwd() / str(base_dir)).resolve()
            cand_dirs = []
            if custom_task:
                cand_dirs.append(out_base / TaskWorkspace.sanitize_name(custom_task))
            if out_base.exists():
                cand_dirs.extend([p for p in out_base.glob(f"*{bvid}*") if p.is_dir()])
            for cd in cand_dirs:
                parts_file = cd / "parts.json"
                if parts_file.exists() and parts_file.stat().st_size > 20:
                    try:
                        cached_parts = json.loads(parts_file.read_text(encoding="utf-8"))
                        if cached_parts and isinstance(cached_parts, list):
                            print(f"\n[!] B站元数据接口受阻（{err}），已自动从本地缓存加载分集拓扑离线运行: {parts_file.name}")
                            title = cd.name.split("_")[0]
                            manifest_f = cd / "manifest.json"
                            if manifest_f.exists():
                                try:
                                    m_data = json.loads(manifest_f.read_text(encoding="utf-8"))
                                    title = m_data.get("title", title)
                                except Exception:
                                    pass
                            return {
                                "video_type": "multi_page" if len(cached_parts) > 1 else "single",
                                "title": title,
                                "bvid": bvid,
                                "owner": "",
                                "owner_mid": 0,
                                "desc": "",
                                "duration": sum(p.get("duration", 0) for p in cached_parts),
                                "pic": "",
                                "has_multi_pages": len(cached_parts) > 1,
                                "parts": cached_parts,
                                "cid": cached_parts[0]["cid"] if cached_parts else 0,
                                "url_page": BilibiliParser.extract_page_index(target),
                                "is_cached_offline": True,
                            }
                    except Exception:
                        pass
        raise RuntimeError(enrich_network_error(err)) from err


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
        base_dir: str = "output",
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
        )
        print("=" * 65)
        print(f"[*] 全流程处理流水线启动 (Task Workspace: {ws.root_dir.name})")
        print("=" * 65)

        print("[*] 阶段一策略: 零中间逐字稿（听音后直接撰写 articles/；长文已存在即视为完成）")

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
            if info.get("is_local"):
                print(f"    [prefetch] P{p['page']:02d} 本地提取音频...")
                LocalMediaParser.extract_audio(p.get("filepath", info.get("source_path")), audio_file)
            else:
                print(f"    [prefetch] P{p['page']:02d} 下载轻量音频...")
                # 元数据 API 保持现有令牌桶，不动 fetcher；此处统一走 412 富化入口
                stream_info = get_audio_stream(
                    bvid, p["cid"], sessdata=sessdata, prefer_quality=quality,
                )
                AudioFetcher.download_audio(stream_info["best_stream_url"], str(audio_file), repackage_m4a=True)
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
                print("三选项：①删集重跑（缩小 --range 剔除失败集后重跑）②补--sessdata（浏览器复制 SESSDATA 后重跑）③人工语料外挂：将人工整理文本放至 subtitles/PXX_*_clean.txt 后重跑", file=sys.stderr)
                print("=" * 65, file=sys.stderr)
                raise PipelineGateError(2)

        # ===== 阶段二「单集精读文章任务书派发」：零中间逐字稿，直接产出 articles/ =====
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
        print(f"[*] 阶段二：派发单集精读文章任务书（共 {len(effective_parts)} 集，零中间逐字稿）")
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

        # ===== 阶段三「知识块聚合」：规划与知识元均由宿主 Agent 产出后才合成笔记 =====
        plan = None
        block_results: List[Dict[str, Any]] = []
        if process_all:
            # 语料摘要：优先取 Agent 已撰写的单集长文，兼容历史工作区的 _clean.txt
            summaries = {}
            for p in info["parts"]:
                p_num = p["page"]
                art = KernelExtractor.find_article(ws, p_num)
                if art is not None:
                    try:
                        summaries[p_num] = art.read_text(encoding="utf-8")[:400]
                    except Exception:
                        pass
            for p in info["parts"]:
                p_num = p["page"]
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
                print("[*] 阶段三：课程知识块聚合（规划与知识元均由宿主 Agent 产出）")
                print("=" * 65)

                plan = SemanticTopicPlanner.plan(
                    info["parts"],
                    course_title=info["title"],
                    ws=ws,
                    transcript_summaries=summaries,
                )
                if not plan:
                    print("[*] 阶段三后置：已导出知识块规划任务书，待宿主 Agent 产出 topic_plan.json 后重跑。")
                    print(f"[*] 任务书: {ws.root_dir / 'topic_plan_TASK.md'}")
                else:
                    print(f"[✓] 知识块规划已就绪，共 {len(plan)} 个逻辑知识块:")
                    for b in plan:
                        eps = b["episodes"]
                        p_str = f"P{min(eps):02d}-P{max(eps):02d}" if len(eps) > 1 else f"P{eps[0]:02d}"
                        print(f"    - 模块 {b['block_id']:02d} ({p_str}): {b['block_title']}")

                    for b in plan:
                        eps = b["episodes"]
                        block_parts = [p for p in info["parts"] if p["page"] in eps]
                        if not block_parts:
                            continue
                        # 门禁：本模块各集单集精读长文齐备才导出笔记任务书（知识元降级为可选索引）
                        articles, missing = BlockSynthesizer.collect_block_articles(block_parts, ws)
                        if missing:
                            _missing_str = ", ".join(f"P{m:02d}" for m in missing)
                            print(f"    [gate] 模块 {b['block_id']:02d}: {len(missing)} 集尚无单集精读长文"
                                  f"（{_missing_str}），跳过本模块笔记派发")
                            continue
                        # 笔记只有一种风格（文章直供 + 只写结论），无需再指定风格
                        res = BlockSynthesizer.synthesize_block(b, articles, ws=ws)
                        block_results.append(res)
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
        ws.save_manifest(_existing)
        print("\n" + "=" * 65)
        print(f"[✓] 工具层流水线执行完毕！语料与任务书已归档至: {ws.root_dir}")
        print("【★ 宿主 Agent 接管指南】：")
        print(f"  1. 单集精读文章任务书: {ws.articles_dir}/*_TASK.md")
        if process_all:
            print(f"  2. 知识块聚合笔记任务书: {ws.notes_dir}/*_TASK.md")
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
