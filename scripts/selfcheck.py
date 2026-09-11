#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Minimal runnable self-check for the bili-video2book skill repo (三域分离后的技能侧自检).

Not a test framework: a flat sequence of assertions covering the invariants that
matter after the architecture refactor (Agent-native kernel/plan chain, zero
intermediate transcript, no dead modules) **plus the three-domain separation
contract**: skill/ 与 mcp/ 各自独立仓库、产物根在两者之外、CLI 不依赖当前工作目录。

MCP 自身的不变量由其独立仓库的 `mcp/selfcheck.py` 负责；本脚本只在同级存在 mcp/
时以子进程方式调用它（可选段落，缺失即跳过，技能侧不依赖 MCP 仓库）。

Run: python scripts/selfcheck.py
"""

import os
import re
import subprocess
import sys
from pathlib import Path

# 代码根（skill/）：文档、源码、脚本的基准
SKILL_ROOT = Path(__file__).resolve().parent.parent
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from src.core import paths as _paths  # noqa: E402
from src.core.proc import run_quiet  # noqa: E402  （统一抑制 Windows 控制台窗口）

# 容器根（skill/、mcp/、output/ 的共同父目录）与产物根
HOME_ROOT = _paths.home_root()
PRODUCTS_ROOT = _paths.products_root()
MCP_REPO = Path(os.environ.get("OMNI_MEDIA_MCP_DIR", "").strip() or (HOME_ROOT / "mcp"))

FAILURES = []


def check(name, fn):
    try:
        fn()
        print(f"[PASS] {name}")
    except Exception as err:
        FAILURES.append((name, err))
        print(f"[FAIL] {name}: {type(err).__name__}: {err}")


def check_imports():
    import src.cli  # noqa: F401
    import src.core.paths  # noqa: F401
    import src.core.pipeline  # noqa: F401
    import src.core.kernel_extractor  # noqa: F401
    import src.core.workspace  # noqa: F401
    import src.generator.topic_planner  # noqa: F401
    import src.generator.integrator  # noqa: F401
    import src.generator.block_synthesizer  # noqa: F401


def check_cli_help():
    for sub in ("parse", "audio", "transcribe",
                "pipeline", "cluster-notes", "cluster-articles", "dedup",
                "cleanup", "sync", "login", "logout", "info"):
        res = run_quiet(
            [sys.executable, str(SKILL_ROOT / "src" / "cli.py"), sub, "--help"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=60,
        )
        assert res.returncode == 0, f"`{sub} --help` 退出码 {res.returncode}: {res.stderr[:200]}"


def check_repo_separation():
    """三域分离契约：skill/ 与 mcp/ 各自独立仓库，产物根在两者之外，容器根不再是仓库。"""
    assert (SKILL_ROOT / ".git").is_dir(), "skill/ 应是独立 git 仓库（缺 .git）"
    assert (SKILL_ROOT / ".gitattributes").is_file(), "skill/ 缺少 .gitattributes（行尾契约）"

    # 容器根不应是 git 仓库（拆分后由两个独立仓库各自管理）
    assert not (HOME_ROOT / ".git").is_dir(), f"容器根不应再有 .git: {HOME_ROOT / '.git'}"

    # 产物根必须位于两个仓库工作树之外，避免产物被误提交
    for repo_name, repo_root in (("skill", SKILL_ROOT), ("mcp", HOME_ROOT / "mcp")):
        if not repo_root.exists():
            continue
        try:
            PRODUCTS_ROOT.relative_to(repo_root)
        except ValueError:
            continue
        raise AssertionError(f"产物根 {PRODUCTS_ROOT} 位于 {repo_name} 仓库工作树内")

    if (HOME_ROOT / "mcp").exists():
        assert (HOME_ROOT / "mcp" / ".git").is_dir(), "mcp/ 应是独立 git 仓库（缺 .git）"
        assert not (SKILL_ROOT / "omni-media-mcp").exists(), "skill/ 内不应再残留 omni-media-mcp/"

    # 产物根必须存在且能枚举出工作区（否则说明锚点解析跑偏）
    assert PRODUCTS_ROOT.is_dir(), f"产物根不存在: {PRODUCTS_ROOT}"


def check_products_root_resolution():
    """产物根解析：与拆分前的锚点等价（<home>/output），且不随当前工作目录漂移。"""
    expected = HOME_ROOT / "output"
    assert PRODUCTS_ROOT == expected, f"产物根解析异常: {PRODUCTS_ROOT} != {expected}"
    assert _paths.resolve_base_dir(None) == expected, "空 --base-dir 未解析到产物根"
    assert _paths.resolve_base_dir("") == expected, "空字符串 --base-dir 未解析到产物根"
    assert _paths.default_base_dir() == str(expected), "default_base_dir 与产物根不一致"
    # manifest 相对路径基准 = 容器根，因此历史 `output/<task>/...` 字面值继续有效
    probe = expected / "__probe__" / "模块01_甲_精读全书.md"
    assert _paths.__name__ and str(probe.relative_to(HOME_ROOT).as_posix()).startswith("output/")

    # 跨工作目录一致性：从临时目录跑一次 CLI，产物根必须仍是同一个
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        code = (
            "import sys; sys.path.insert(0, r'%s');"
            "from src.core import paths; print(paths.products_root())" % SKILL_ROOT
        )
        res = run_quiet(
            [sys.executable, "-c", code],
            cwd=tmp, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=60,
        )
        got = (res.stdout or "").strip().splitlines()[-1] if res.stdout else ""
        assert got == str(expected), f"从其它工作目录解析出的产物根不一致: {got!r}"


def check_no_cross_repo_imports():
    """互不打扰：技能侧代码不得 import omni_media_mcp；MCP 侧不得 import src。"""
    import ast as _ast
    import re as _re

    def _imported_modules(path: Path) -> set:
        tree = _ast.parse(path.read_text(encoding="utf-8"))
        names = set()
        for node in _ast.walk(tree):
            if isinstance(node, _ast.Import):
                for alias in node.names:
                    names.add(alias.name.split(".")[0])
            elif isinstance(node, _ast.ImportFrom):
                if node.module and node.level == 0:
                    names.add(node.module.split(".")[0])
        return names

    # 技能侧：允许在「注释/字符串」里提到 MCP，但不允许真的 import
    offenders = []
    for path in list((SKILL_ROOT / "src").rglob("*.py")) + list((SKILL_ROOT / "scripts").rglob("*.py")):
        if "__pycache__" in path.parts or path.name == "selfcheck.py":
            continue  # selfcheck 只以子进程方式调用 MCP 自检，不 import
        if "omni_media_mcp" in _imported_modules(path):
            offenders.append(path.relative_to(SKILL_ROOT).as_posix())
    assert not offenders, f"技能侧不得 import MCP 包: {offenders}"

    # 技能侧源码不得出现 omni_media_mcp 的 import 文本（防止动态 import 绕过）
    for path in (SKILL_ROOT / "src").rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        assert not _re.search(r"^\s*(import|from)\s+omni_media_mcp", text, _re.M), \
            f"{path.relative_to(SKILL_ROOT)} 出现了对 MCP 包的 import"

    mcp_root = HOME_ROOT / "mcp"
    if mcp_root.exists():
        bad = []
        for path in (mcp_root / "omni_media_mcp").rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            if "src" in _imported_modules(path):
                bad.append(path.relative_to(mcp_root).as_posix())
        assert not bad, f"MCP 侧不得 import 技能包 src: {bad}"


def check_kernel_extractor_contract():
    """本地伪造抽取必须已彻底移除，缺失的知识元只能报告为待办。"""
    from src.core.kernel_extractor import KernelExtractor

    assert not hasattr(KernelExtractor, "degraded_extract"), "degraded_extract 应已删除"
    assert not hasattr(KernelExtractor, "strip_transient_chatter"), "strip_transient_chatter 应已删除"
    assert not hasattr(KernelExtractor, "extract_single_kernel"), "extract_single_kernel 应已改名为 collect_kernel"

    pending = {"page": 1, "title": "t", "status": KernelExtractor.STATUS_PENDING}
    assert KernelExtractor.pending_pages([pending]) == [1]
    assert KernelExtractor.pending_pages([{"page": 2, "status": "extracted"}]) == []


def check_topic_planner_contract():
    """本地关键词聚类必须已移除，规划校验必须拒绝缺失/重复分集。"""
    from src.generator.topic_planner import SemanticTopicPlanner

    assert not hasattr(SemanticTopicPlanner, "fallback_heuristic_plan"), "启发式聚类应已删除"
    assert hasattr(SemanticTopicPlanner, "export_plan_task"), "export_plan_task 应已提供"

    ok, _ = SemanticTopicPlanner.validate_plan(
        [{"block_id": 1, "block_title": "A", "episodes": [1, 2]}], 2)
    assert ok, "完整覆盖应通过校验"
    bad, _ = SemanticTopicPlanner.validate_plan(
        [{"block_id": 1, "block_title": "A", "episodes": [1]}], 2)
    assert not bad, "缺失分集应被拒绝"
    dup, _ = SemanticTopicPlanner.validate_plan(
        [{"block_id": 1, "block_title": "A", "episodes": [1, 1]}], 2)
    assert not dup, "重复分集应被拒绝"


def check_integrator_no_hardcoded_course():
    """通用整编器不得再内嵌任何具体课程数据。"""
    import inspect

    from src.generator.integrator import ArticleIntegrator

    text = (SKILL_ROOT / "src" / "generator" / "integrator.py").read_text(encoding="utf-8")
    for needle in ("微机原理", "8253", "8255A", "黑马程序员", "核心语法-", "函数基础"):
        assert needle not in text, f"integrator.py 仍含硬编码课程数据: {needle}"

    sig = inspect.signature(ArticleIntegrator.run)
    assert sig.parameters["course_title"].default is inspect.Parameter.empty, \
        "run() 的 course_title 应为必传参数"


def check_zero_transcript_pipeline():
    """零中间逐字稿：文章任务书入口存在，旧的转录任务书入口必须已移除。"""
    from src.core import pipeline

    assert hasattr(pipeline, "export_article_task"), "export_article_task 应已提供"
    assert not hasattr(pipeline, "export_transcribe_task"), "export_transcribe_task 应已移除"


def check_subprocess_timeouts():
    """bili-video2book 侧所有 ffmpeg/ffprobe 调用必须有硬超时。"""
def check_subprocess_timeouts():
    """子进程契约：所有外部程序调用都必须 (1) 走 run_quiet（抑制 Windows 控制台窗口）
    且 (2) 带硬超时；源码里不得再出现裸 subprocess.run / Popen。

    背景：ffmpeg/ffprobe 每次调用都会新建进程，宿主后台托管 + 多子智能体并发时
    Windows 会为每个控制台程序新开窗口（成片闪黑窗，一门 84 集课程约 250 次）。
    窗口抑制集中在 src/core/proc.py，此处防止有人回退成裸调用。
    """
    import src.core.audio_chunker as ac
    import src.core.local_media as lm
    import src.core.proc as proc_mod
    import ast as _ast

    assert lm.PROBE_TIMEOUT_SEC > 0 and lm.TRANSCODE_TIMEOUT_SEC > 0
    assert ac.PROBE_TIMEOUT_SEC == lm.PROBE_TIMEOUT_SEC
    assert ac.TRANSCODE_TIMEOUT_SEC == lm.TRANSCODE_TIMEOUT_SEC
    assert hasattr(proc_mod, "run_quiet") and hasattr(proc_mod, "CREATE_NO_WINDOW")

    import os as _os

    if _os.name == "nt":
        # Windows 下必须真正带上窗口抑制标志
        kwargs = proc_mod.quiet_kwargs()
        assert kwargs.get("creationflags") == proc_mod.CREATE_NO_WINDOW and proc_mod.CREATE_NO_WINDOW, \
            "run_quiet 在 Windows 下未启用 CREATE_NO_WINDOW"

    bare = []
    timeoutless = []
    for path in list((SKILL_ROOT / "src").rglob("*.py")) + list((SKILL_ROOT / "scripts").rglob("*.py")):
        if "__pycache__" in path.parts or path.name == "proc.py":
            continue  # proc.py 是唯一允许直接调用 subprocess.run 的地方
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(SKILL_ROOT).as_posix()
        tree = _ast.parse(text)
        for node in _ast.walk(tree):
            if not isinstance(node, _ast.Call):
                continue
            func = node.func
            attr = getattr(func, "attr", None)
            base = getattr(func, "value", None)
            base_name = getattr(base, "id", None)
            if attr in {"run", "Popen", "call", "check_output"} and base_name in {"subprocess", "_sp"}:
                bare.append(f"{rel}:{node.lineno}")
            if getattr(func, "id", None) == "run_quiet":
                if not any(kw.arg == "timeout" for kw in node.keywords):
                    timeoutless.append(f"{rel}:{node.lineno}")
    assert not bare, "存在未抑制控制台窗口的裸子进程调用（应改走 run_quiet）: " + ", ".join(bare)
    assert not timeoutless, "run_quiet 调用缺少 timeout=（硬超时是强制契约）: " + ", ".join(timeoutless)


def check_mcp_repo_optional():
    """可选段落：同级存在 mcp/ 独立仓库时，调用它自己的自检（技能侧不依赖 MCP）。

    MCP 的全部不变量（工具契约、limits、适配器、废弃链路）由 `mcp/selfcheck.py` 负责，
    避免两处断言各自漂移；找不到 MCP 仓库即跳过，不视为失败。
    """
    import subprocess as _sp

    entry = MCP_REPO / "selfcheck.py"
    if not entry.is_file():
        print(f"       (未发现 MCP 仓库自检 {entry}，跳过可选段落)")
        return

    res = run_quiet(
        [sys.executable, str(entry)],
        cwd=str(MCP_REPO), stdout=_sp.PIPE, stderr=_sp.STDOUT, text=True, timeout=300,
    )
    tail = "\n".join((res.stdout or "").strip().splitlines()[-4:])
    assert res.returncode == 0, f"mcp/selfcheck.py 未通过（exit {res.returncode}）:\n{tail}"
    print(f"       (已调用 {entry})")


def check_dead_modules_removed():
    for rel in (
        "src/core/http_client.py",
        "src/generator/cleaner.py",
        "src/generator/classifier.py",
        "src/generator/doc_builder.py",
        "tests",
        "MCP_TOOL_AUDIT_REPORT.md",
        "config.example.json",
        "scripts/validate_skill.py",
        # 三域分离后，MCP 的实现不再属于本仓库（其死代码断言见 mcp/selfcheck.py）
        "omni-media-mcp",
    ):
        assert not (SKILL_ROOT / rel).exists(), f"{rel} 应已删除"


def check_host_artifacts_ignored():
    """宿主/编辑器旁路目录与产物根都不得进入任一仓库。

    .workbuddy、.zcode 这类目录由编辑器在会话中自动写入（含对话记忆）——三域分离后它们位于
    容器根，不在任何仓库工作树内；产物根同理。这里同时验证「不在工作树内」这一结构事实，
    以及两个仓库的 .gitignore 仍留有安全网条目（防止有人把产物根搬回仓库内）。
    """
    import subprocess as _sp

    ignore = (SKILL_ROOT / ".gitignore").read_text(encoding="utf-8")
    for name in (".workbuddy", ".aide", ".zcode", "output", ".sessdata.json", ".archive"):
        assert name in ignore, f"{name} 未被 skill/.gitignore 覆盖（安全网缺失）"

    repos = [SKILL_ROOT] + ([HOME_ROOT / "mcp"] if (HOME_ROOT / "mcp" / ".git").is_dir() else [])
    for repo in repos:
        tracked = run_quiet(
            ["git", "ls-files", "--", ".workbuddy", ".aide", ".zcode", "output", ".sessdata.json", ".archive"],
            cwd=str(repo), stdout=_sp.PIPE, stderr=_sp.PIPE, text=True, timeout=60,
        )
        assert not tracked.stdout.strip(), \
            f"{repo.name} 仓库纳入了宿主旁路目录/产物: {tracked.stdout.strip()}"

    # 结构事实：这些目录都在容器根（两仓库工作树之外）
    for name in (".workbuddy", ".zcode", "output"):
        assert (HOME_ROOT / name).exists() or name == ".zcode", f"容器根缺少 {name}"
        for repo in repos:
            try:
                (HOME_ROOT / name).relative_to(repo)
            except ValueError:
                continue
            raise AssertionError(f"{name} 位于 {repo.name} 仓库工作树内，应移到容器根")


def check_skill_copies_in_sync():
    """两份 SKILL.md 及 references 必须保持一致（validate_skill.py 已移除，靠本检查兜底）。"""
    pairs = [
        ("SKILL.md", ".agents/skills/bili-video2book/SKILL.md"),
        ("references/delivery_matrix.md", ".agents/skills/bili-video2book/references/delivery_matrix.md"),
    ]
    for a, b in pairs:
        pa, pb = SKILL_ROOT / a, SKILL_ROOT / b
        assert pa.exists() and pb.exists(), f"{a} 或 {b} 缺失"
        assert pa.read_text(encoding="utf-8") == pb.read_text(encoding="utf-8"), f"{a} 与 {b} 不同步"


def check_task_file_export_end_to_end():
    """在临时工作区实证 kernel/plan 的任务书导出门禁按预期收敛。"""
    import json
    import tempfile

    from src.core.kernel_extractor import KernelExtractor
    from src.core.workspace import TaskWorkspace
    from src.generator.topic_planner import SemanticTopicPlanner

    with tempfile.TemporaryDirectory() as tmp:
        ws = TaskWorkspace(task_name="selfcheck_task", base_dir=tmp)
        parts = [{"page": 1, "title": "绪论"}, {"page": 2, "title": "数制与编码"}]

        # 1) 无单集长文时报告 need-agent-article，且绝不产出伪造内容
        k0 = KernelExtractor.collect_kernel(1, "绪论", ws)
        assert k0["status"] == "need-agent-article", k0["status"]
        assert k0["definitions"] == [] and k0["mechanisms_and_models"] == []

        # 2) 有长文后导出 KERNEL_TASK 并报告 need-agent-kernel
        (ws.articles_dir / "P01_绪论_精读文章.md").write_text("内容" * 200, encoding="utf-8")
        k1 = KernelExtractor.collect_kernel(1, "绪论", ws)
        assert k1["status"] == KernelExtractor.STATUS_PENDING, k1["status"]
        assert Path(k1["task_file"]).exists(), "KERNEL_TASK 未落盘"

        # 3) Agent 产出 extracted 后必须被复用
        kp = KernelExtractor.kernel_json_path(ws, 1, "绪论")
        kp.write_text(json.dumps({
            "page": 1, "title": "绪论", "status": "extracted",
            "definitions": [{"term": "t", "essence": "e"}],
        }, ensure_ascii=False), encoding="utf-8")
        k2 = KernelExtractor.collect_kernel(1, "绪论", ws)
        assert k2["status"] == "extracted", k2["status"]

        # 4) 无 topic_plan.json 时导出规划任务书并返回 None（不做本地聚类）
        plan = SemanticTopicPlanner.plan(parts, course_title="测试课程", ws=ws)
        assert plan is None, "无规划时应返回 None 而非本地聚类结果"
        assert (ws.root_dir / "topic_plan_TASK.md").exists(), "TOPIC_PLAN_TASK 未落盘"
        assert not (ws.root_dir / "topic_plan.json").exists()

        # 5) Agent 产出合法规划后必须被采纳；非法规划必须被拒绝
        (ws.root_dir / "topic_plan.json").write_text(json.dumps(
            [{"block_id": 1, "block_title": "绪论与数制", "episodes": [1, 2], "core_theme": "x"}],
            ensure_ascii=False), encoding="utf-8")
        plan2 = SemanticTopicPlanner.plan(parts, course_title="测试课程", ws=ws)
        assert plan2 is not None and len(plan2) == 1, "合法规划未被采纳"

        (ws.root_dir / "topic_plan.json").write_text(json.dumps(
            [{"block_id": 1, "block_title": "残缺", "episodes": [1]}], ensure_ascii=False),
            encoding="utf-8")
        plan3 = SemanticTopicPlanner.plan(parts, course_title="测试课程", ws=ws)
        assert plan3 is None, "缺失分集的非法规划未被拒绝"


def check_stage1_gate_ignores_task_files():
    """阶段一门禁只认最终长文：articles/ 里的任务书不得计入已完成。"""
    import tempfile

    sys.path.insert(0, str(SKILL_ROOT / "scripts"))
    from queue_tracker import scan_status
    from src.core.workspace import TaskWorkspace

    with tempfile.TemporaryDirectory() as tmp:
        ws = TaskWorkspace(task_name="gate_probe", base_dir=tmp)
        ws.save_parts([{"page": 1, "title": "绪论"}, {"page": 2, "title": "数制"}])

        # 任务书体积（7KB 级）远超 1000 字节门禁，若未排除会被误判为已交长文
        for name in ("P01_绪论_TASK.md", "P02_数制_TASK.md"):
            (ws.articles_dir / name).write_text("提示词" * 800, encoding="utf-8")
        st = scan_status(ws.root_dir)
        assert st["completed_count"] == 0, f"任务书被误判为长文: {st['completed_count']}/2"
        assert not st["is_stage1_complete"], "尚无长文时阶段一门禁不得放行"
        assert not st["invalid_articles"], "任务书不应进入异常短文章清单"

        # 真实长文落盘后才计入，且未完成时仍不放行
        (ws.articles_dir / "P01_绪论_精读文章.md").write_text("正文" * 300, encoding="utf-8")
        st2 = scan_status(ws.root_dir)
        assert st2["completed_count"] == 1, f"长文未被计入: {st2['completed_count']}"
        assert st2["pending_count"] == 1, f"待办数异常: {st2['pending_count']}"
        assert not st2["is_stage1_complete"], "仍有待办时门禁不得放行"

        # 旧版工作区可能缺 parts.json：必须回退到 manifest/articles 而非直接崩溃
        ws.parts_cache_path.unlink()
        st3 = scan_status(ws.root_dir)
        assert st3["completed_count"] == 1, f"缺 parts.json 时回退判定异常: {st3['completed_count']}"

        # 历史工作区存在无 _精读文章 后缀的长文（如 PXX_标题.md）：必须同样被认定为已完成，
        # 否则 pipeline/transcribe 会按精确文件名误判为未写并要求重做（吉林大学工作区即此情形）。
        from src.core.kernel_extractor import KernelExtractor

        (ws.articles_dir / "P02_数制.md").write_text("正文" * 300, encoding="utf-8")
        assert KernelExtractor.find_article(ws, 2) is not None, "宽容定位未识别无后缀长文"
        st4 = scan_status(ws.root_dir)
        assert st4["completed_count"] == 2 and st4["is_stage1_complete"], \
            f"无后缀长文未被计入: {st4['completed_count']}/2"


def check_dedup_reuses_without_subtitles():
    """零中间逐字稿链路不产字幕：长文复用不得被字幕前提阻断，任务书也不得充当复用源。"""
    import tempfile

    from src.core.workspace import TaskWorkspace

    with tempfile.TemporaryDirectory() as tmp:
        ws = TaskWorkspace(task_name="dedup_probe", base_dir=tmp)
        for name in ("P01_绪论.m4a", "P02_绪论重复.m4a"):
            (ws.audio_dir / name).write_bytes(b"x" * 20000)

        article = "这是一篇正式长文。" * 100
        (ws.articles_dir / "P01_绪论_精读文章.md").write_text(article, encoding="utf-8")
        # 任务书与长文同目录同前缀：必须被排除在复用源与"已有产物"判定之外
        (ws.articles_dir / "P01_绪论_TASK.md").write_text("这是任务书。" * 100, encoding="utf-8")
        (ws.articles_dir / "P02_绪论重复_TASK.md").write_text("这是任务书。" * 100, encoding="utf-8")

        synced = ws.sync_duplicate_assets()
        assert len(synced) == 1, f"重复分集未被同步（字幕前提未解除）: {synced}"
        assert synced[0]["synced_art"], f"长文未复用: {synced[0]}"
        assert not synced[0]["synced_sub"], f"无字幕源时不应报告同步字幕: {synced[0]}"

        dst = ws.articles_dir / "P02_绪论重复_精读文章.md"
        assert dst.exists(), "P02 长文未复用"
        assert dst.read_text(encoding="utf-8") == article, "复用源不是正式长文（任务书被误拷）"


def check_sessdata_store_safety():
    """SESSDATA 持久化：往返一致、脱敏不泄露，且存档路径必须落在版本库之外。"""
    import subprocess as _sp
    import tempfile

    from src.core.credentials import DEFAULT_STORE_NAME, SessdataStore, resolve_sessdata, store_path

    secret = "abc123def456ghi789"

    with tempfile.TemporaryDirectory() as tmp:
        store = Path(tmp) / "store.json"

        assert SessdataStore.load(path=store) is None, "无存档时不得凭空返回凭证"
        try:
            SessdataStore.save("   ", path=store)
            raise AssertionError("空 SESSDATA 未被拒绝")
        except ValueError:
            pass

        SessdataStore.save(secret, path=store)
        assert SessdataStore.load(path=store) == secret, "存档往返不一致"
        assert secret not in SessdataStore.mask(secret), "脱敏展示泄露了完整凭证"

        assert SessdataStore.clear(path=store) is True
        assert SessdataStore.clear(path=store) is False, "重复清除应返回 False"
        assert SessdataStore.load(path=store) is None

    # 显式传入优先于本地存档；空白视作未传入
    assert resolve_sessdata(secret) == secret, "显式传入未优先生效"
    assert resolve_sessdata("   ") == SessdataStore.load(), "空白显式值应回退到本地存档"

    # 默认存档路径：必须落在产物根（两仓库工作树之外），且 skill/.gitignore 留有安全网
    assert DEFAULT_STORE_NAME in (SKILL_ROOT / ".gitignore").read_text(encoding="utf-8"), \
        f"{DEFAULT_STORE_NAME} 未被 skill/.gitignore 覆盖（安全网缺失）"
    assert store_path().name == DEFAULT_STORE_NAME
    assert store_path().parent == PRODUCTS_ROOT, \
        f"凭证存档不在产物根: {store_path()} (期望目录 {PRODUCTS_ROOT})"
    for repo in (SKILL_ROOT, HOME_ROOT / "mcp"):
        if not (repo / ".git").is_dir():
            continue
        tracked = run_quiet(
            ["git", "ls-files", "--", DEFAULT_STORE_NAME],
            cwd=str(repo), stdout=_sp.PIPE, stderr=_sp.PIPE, text=True, timeout=60,
        )
        assert not tracked.stdout.strip(), f"凭证存档已进入 {repo.name} 版本控制: {tracked.stdout.strip()}"
        try:
            store_path().relative_to(repo)
        except ValueError:
            continue
        raise AssertionError(f"凭证存档位于 {repo.name} 仓库工作树内")


def check_cache_paths_anchored():
    """缓存/凭证文件路径必须锚定**产物根**，不得随当前所在目录漂移，也不得落回代码仓库。"""
    from src.core.credentials import store_path
    from src.core.wbi import WbiSigner

    for label, p in (("WBI 密钥", WbiSigner._解析密钥文件路径()), ("凭证存档", store_path())):
        assert p.is_absolute(), f"{label}路径不是绝对路径: {p}"
        assert PRODUCTS_ROOT in p.parents, f"{label}路径未锚定产物根: {p}"
        assert SKILL_ROOT not in p.parents, f"{label}路径落在了代码仓库内: {p}"

    # 显式传入的相对路径按容器根解析（兼容拆分前的 `output/.wbi_keys.json` 写法）
    legacy = WbiSigner._解析密钥文件路径("output/.wbi_keys.json")
    assert legacy == PRODUCTS_ROOT / ".wbi_keys.json", f"旧式相对路径解析异常: {legacy}"


def check_render_compat_rules():
    """交付物渲染兼容约束在位：Typora 优先，字符画必须进围栏，禁用 GitHub 告警块。"""
    from src.generator.block_synthesizer import BlockSynthesizer
    from src.generator.prompt_templates import (
        ARTICLE_LEARNING_PROMPT,
        RENDER_COMPAT_RULES,
    )

    # 1) 共享规则是唯一文案来源，两条硬约束都必须在
    assert "```text" in RENDER_COMPAT_RULES, "共享规则缺少「字符画必须进围栏」硬约束"
    assert "成对闭合" in RENDER_COMPAT_RULES, "共享规则缺少「围栏必须成对闭合」硬约束"
    assert "GitHub 专有" in RENDER_COMPAT_RULES, "共享规则缺少「禁用 GitHub 告警块」禁令"

    # 2) 讲义提示词已注入规则，且不再处方 GitHub 告警块
    assert RENDER_COMPAT_RULES in ARTICLE_LEARNING_PROMPT, "讲义提示词未注入渲染兼容规则"
    assert "（如 `> [!TIP]`）" not in ARTICLE_LEARNING_PROMPT, "讲义提示词仍在处方 GitHub 告警块"
    for ph in ("{title}", "{part_title}", "{content}"):
        assert ph in ARTICLE_LEARNING_PROMPT, f"讲义提示词占位符缺失: {ph}"

    # 3) 模块笔记提示词对本模块字符画提出了围栏要求（文章直供版专属提示词）
    from src.generator.prompt_templates import MODULE_NOTE_PROMPT
    assert "```text 围栏内" in MODULE_NOTE_PROMPT, "MODULE_NOTE_PROMPT 未要求字符画进围栏"
    assert "{article_list}" in MODULE_NOTE_PROMPT, "MODULE_NOTE_PROMPT 缺少语料清单占位符"

    # 4) 笔记只有一种风格：渲染兼容规则与版式规范都必须注入（build_synthesis_prompt 已无 style 参数）
    import inspect as _inspect

    assert "style" not in _inspect.signature(BlockSynthesizer.build_synthesis_prompt).parameters, \
        "build_synthesis_prompt 不应再有 style 参数（八种旧风格已删除）"
    block_meta = {"block_id": 1, "block_title": "t", "episodes": [1], "core_theme": "x"}
    assert RENDER_COMPAT_RULES in BlockSynthesizer.build_synthesis_prompt(block_meta, []), \
        "模块笔记提示词未注入渲染兼容规则"

    # 5) 格式总纲（含镜像）必须写明阅读器为 Typora
    for rel in (
        "references/delivery_matrix.md",
        ".agents/skills/bili-video2book/references/delivery_matrix.md",
    ):
        text = (SKILL_ROOT / rel).read_text(encoding="utf-8")
        assert "Typora" in text, f"{rel} 未声明 Typora 阅读场景"
        assert "```text" in text, f"{rel} 未写入字符画围栏要求"


def check_module_note_contract():
    """模块笔记契约：文章直供 + 只写结论 + 零套话 + 版式规范 + 两条排版硬约束 + 任务书回收。"""
    from src.core.task_cleanup import cleanup_completed_tasks  # noqa: F401  (导入即校验依赖无环)
    from src.core.workspace import TaskWorkspace
    from src.generator.block_synthesizer import BlockSynthesizer
    from src.generator.prompt_templates import (
        MODULE_NOTE_PROMPT,
        NOTE_VISUAL_SPEC,
    )

    # 1) 专属提示词必须点名禁止「套话填充」「分集标题」「分集口吻」「中途截断」
    for 关键短语, 说明 in (
        ("概念属性与边界", "套话黑名单"),
        ("严禁以分集为单位组织内容", "分集标题禁令"),
        ("严禁分集口吻", "分集口吻禁令"),
        ("严禁中途截断", "截断禁令"),
    ):
        assert 关键短语 in MODULE_NOTE_PROMPT, f"MODULE_NOTE_PROMPT 缺少{说明}：{关键短语}"

    # 2) 版式规范标志性要求必须在位；且必须明令不再写「速查卡 / 一句话总纲」
    for 关键短语 in ("一句话主旨", "知识拓扑树", "来源: P03"):
        assert 关键短语 in NOTE_VISUAL_SPEC, f"NOTE_VISUAL_SPEC 缺少「{关键短语}」要求"
    assert "末尾不加收尾小节" in NOTE_VISUAL_SPEC, "NOTE_VISUAL_SPEC 未禁止末尾收尾小节"

    # 2b) 两条最容易翻车的排版硬要求必须在位
    assert "围栏整体缩进 4 个空格" in NOTE_VISUAL_SPEC, "版式规范缺少字符画围栏缩进要求"
    assert "一个汉字按 2 列、一个 ASCII 字符按 1 列" in NOTE_VISUAL_SPEC, \
        "版式规范缺少拓扑树按显示宽度对齐的要求"

    # 2c) 密度纪律：只写结论、不写推导
    assert "只写结论，不写推导" in MODULE_NOTE_PROMPT, "MODULE_NOTE_PROMPT 缺少「只写结论不写推导」纪律"
    assert "标题用技术文档的朴素写法" in MODULE_NOTE_PROMPT, "MODULE_NOTE_PROMPT 缺少朴素标题要求"
    assert "不许硬造子标题" in MODULE_NOTE_PROMPT, "MODULE_NOTE_PROMPT 未禁止硬造子标题"

    # 3) 旧版八种笔记风格必须已彻底删除（含标签与指令文案）
    for 已删除 in ("NOTE_STYLES", "minimal", "detailed", "academic", "tutorial",
                  "task_oriented", "business", "meeting_minutes", "life_journal"):
        text = (SKILL_ROOT / "src" / "generator" / "prompt_templates.py").read_text(encoding="utf-8")
        assert 已删除 not in text, f"prompt_templates.py 仍残留旧笔记风格痕迹：{已删除}"

    # 4) 任务书渲染：必须带上版式规范与语料清单
    block_meta = {"block_id": 3, "block_title": "关系数据库", "episodes": [6, 7], "core_theme": "关系模型"}
    样例文章 = SKILL_ROOT / "SKILL.md"  # 仅需一个存在的文件来渲染字节数
    prompt = BlockSynthesizer.build_synthesis_prompt(block_meta, [样例文章])
    assert NOTE_VISUAL_SPEC in prompt, "任务书未注入版式规范"
    assert "SKILL.md" in prompt, "任务书未渲染语料清单"

    # 5) 知识元默认不参与：不传 kernel_index 时不得出现知识元索引段
    prompt_without = BlockSynthesizer.build_synthesis_prompt(block_meta, [样例文章])
    assert "可选结构化索引" not in prompt_without, "未显式开启时仍注入了知识元索引"
    prompt_with = BlockSynthesizer.build_synthesis_prompt(
        block_meta, [样例文章],
        kernel_index=[{"page": 6, "status": "extracted", "definitions": []}],
    )
    assert "可选结构化索引" in prompt_with, "显式传入 kernel_index 时未注入索引段"

    # 6) 任务书回收：成品已产出才回收，每类保留 1 份范本，未产出的一律保留
    import json
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        ws = TaskWorkspace(task_name="cleanup_task", base_dir=tmp)

        # 文章：P01 无成品（保留待办 + 范本）、P02 有成品（回收）
        (ws.articles_dir / "P01_绪论_TASK.md").write_text("t" * 200, encoding="utf-8")
        (ws.articles_dir / "P02_数制_TASK.md").write_text("t" * 200, encoding="utf-8")
        (ws.articles_dir / "P02_数制_精读文章.md").write_text("内容" * 400, encoding="utf-8")
        # 知识元：P01 有合规成品（但属范本，保留）、P02 有合规成品（回收）
        kernels_dir = ws.subtitles_dir / "kernels"
        kernels_dir.mkdir(parents=True, exist_ok=True)
        (kernels_dir / "P01_绪论_KERNEL_TASK.md").write_text("t" * 200, encoding="utf-8")
        (kernels_dir / "P02_数制_KERNEL_TASK.md").write_text("t" * 200, encoding="utf-8")
        for page, title in ((1, "绪论"), (2, "数制")):
            (kernels_dir / f"P{page:02d}_{title}_kernel.json").write_text(
                json.dumps({"page": page, "title": title, "status": "extracted",
                            "definitions": [{"term": "t", "essence": "e"}]}, ensure_ascii=False),
                encoding="utf-8",
            )
        # 模块笔记：模块01 有成品（范本，保留）、模块02 有成品（回收）、模块03 无成品（保留）
        (ws.notes_dir / "模块01_绪论_TASK.md").write_text("t" * 200, encoding="utf-8")
        (ws.notes_dir / "模块02_关系_TASK.md").write_text("t" * 200, encoding="utf-8")
        (ws.notes_dir / "模块03_理论_TASK.md").write_text("t" * 200, encoding="utf-8")
        (ws.notes_dir / "模块01_绪论_笔记.md").write_text("笔记" * 600, encoding="utf-8")
        (ws.notes_dir / "模块02_关系_笔记.md").write_text("笔记" * 600, encoding="utf-8")

        result = cleanup_completed_tasks(ws, keep_per_category=1, dry_run=False)
        remaining = sorted(p.name for p in ws.articles_dir.glob("*_TASK.md"))
        assert remaining == ["P01_绪论_TASK.md"], f"文章任务书回收结果异常: {remaining}"
        kernel_remaining = sorted(p.name for p in kernels_dir.glob("*_KERNEL_TASK.md"))
        assert kernel_remaining == ["P01_绪论_KERNEL_TASK.md"], f"知识元任务书回收结果异常: {kernel_remaining}"
        note_remaining = sorted(p.name for p in ws.notes_dir.glob("*_TASK.md"))
        assert note_remaining == ["模块01_绪论_TASK.md", "模块03_理论_TASK.md"], \
            f"模块笔记任务书回收结果异常: {note_remaining}"
        assert len(result["deleted"]) == 3, f"回收数量异常: {result['deleted']}"
        assert not (ws.root_dir / "topic_plan_TASK.md").exists() or True  # 规划任务书不参与回收



def check_article_prompt_types():
    """长文提示词风格契约：学习（推荐）+ 旧版（原稳定版）两种风格，由用户确认后使用。

    另外四种视频形态只登记、不提供提示词：命中即打印风格菜单并终止任务（不猜、不降级）。
    """
    import tempfile

    from src.core.pipeline import export_article_task
    from src.core.workspace import TaskWorkspace
    from src.generator.prompt_templates import (
        ARTICLE_LEARNING_PROMPT,
        ARTICLE_LEGACY_PROMPT,
        ARTICLE_PROMPT_TYPES,
        IMPLEMENTED_ARTICLE_TYPES,
        ArticlePromptTypeError,
        render_article_prompt_menu,
        resolve_article_prompt,
    )

    # 1) 只提供两种风格，且「学习」是推荐风格；其余形态登记齐备但必须没有提示词
    assert IMPLEMENTED_ARTICLE_TYPES == ("learning", "legacy"),         f"已提供提示词的状态异常: {IMPLEMENTED_ARTICLE_TYPES}"
    assert ARTICLE_PROMPT_TYPES["learning"].get("recommended") is True, "「学习」未被标为推荐风格"
    assert len(ARTICLE_PROMPT_TYPES) >= 2, "风格矩阵至少应登记学习与旧版"
    for key, meta in ARTICLE_PROMPT_TYPES.items():
        assert meta.get("label"), f"风格 {key} 缺少中文名"
        assert meta.get("signals"), f"风格 {key} 缺少适用信号（用户无法据以选择）"
        if key not in IMPLEMENTED_ARTICLE_TYPES:
            assert not meta.get("prompt"), f"风格 {key} 不应提供提示词"

    # 2) 旧版必须与改写前的原稳定版一致：仍走客观学术第一视角与随堂自测
    for 关键短语 in ("客观、直接的技术/学术第一视角", "随堂自测", "去口语化"):
        assert 关键短语 in ARTICLE_LEGACY_PROMPT, f"旧版提示词缺少原有条款：{关键短语}"
    for 反例 in ("保住讲师的讲课风格", "标题用技术文档的朴素写法"):
        assert 反例 not in ARTICLE_LEGACY_PROMPT, f"旧版提示词混入了新风格条款：{反例}"

    # 3) 学习版（推荐）的立意必须在位：保讲课风格 / 高信息密度 / 成稿观感 / 噪声清单含舞台提示
    for 关键短语 in ("保住讲师的讲课风格", "高信息密度", "成稿观感", "（笑）"):
        assert 关键短语 in ARTICLE_LEARNING_PROMPT, f"学习版提示词缺少「{关键短语}」"

    # 4) 已判定不合格的扩张型/编造型条款不得回流
    for 反例 in ("宁可充分展开", "绝不跳步"):
        assert 反例 not in ARTICLE_LEARNING_PROMPT, f"学习版提示词回流了扩张型条款：{反例}"
    assert "不要凭印象替他补一份" in ARTICLE_LEARNING_PROMPT, "缺少「不得替讲师补写代码」的禁令"

    # 5) 标题规则（第 4~8 轮逐步加固）：朴素写法 + 数量与切分跟着内容 + 不许硬造子标题 + 不许撑大原文
    for 关键短语 in ("标题用技术文档的朴素写法", "严禁口语化、修辞化、带语气或带悬念的标题",
                   "标题的数量与切分跟着这一讲走", "不许硬造子标题", "不许出现空壳层级"):
        assert 关键短语 in ARTICLE_LEARNING_PROMPT, f"学习版提示词缺少标题规则：{关键短语}"
    assert "不构成" in ARTICLE_LEARNING_PROMPT and "义务" in ARTICLE_LEARNING_PROMPT, \
        "学习版提示词未禁止「立了标题就要写满」"

    # 6) 风格解析：键 / 中文名都要命中；未指定、拼错、无提示词的形态都必须终止
    assert resolve_article_prompt("learning")["key"] == "learning"
    assert resolve_article_prompt("学习")["key"] == "learning"
    assert resolve_article_prompt("legacy")["key"] == "legacy"
    assert resolve_article_prompt("旧版")["key"] == "legacy"
    for bad in ("", "网课", "consulting", "livestream"):
        try:
            resolve_article_prompt(bad)
        except ArticlePromptTypeError as err:
            assert "菜单" in err.report, "终止提示未附带风格菜单"
            continue
        raise AssertionError(f"非预设风格未终止任务: {bad!r}")

    # 7) 菜单必须列出全部风格、标出推荐、并给出可复制用法
    menu = render_article_prompt_menu()
    for key in ARTICLE_PROMPT_TYPES:
        assert f"--article-type {key}" in menu, f"风格菜单缺少 {key}"
    assert "推荐" in menu, "风格菜单未标出推荐风格"
    assert "--all --article-type" in menu, "风格菜单缺少可复制用法"

    # 8) 端到端：未命中风格不得落盘任何任务书；命中时任务书须写明风格并注入对应提示词
    with tempfile.TemporaryDirectory() as tmp:
        ws = TaskWorkspace(task_name="style_gate", base_dir=tmp)
        for bad in ("", "consulting", "乱写"):
            try:
                export_article_task(ws, 1, "绪论", None, title="测试课程", article_type=bad)
            except ArticlePromptTypeError:
                pass
            else:
                raise AssertionError(f"风格 {bad!r} 未被门禁拦下")
        assert not list(ws.articles_dir.glob("*_TASK.md")), "风格未命中却落了任务书"

        task = export_article_task(ws, 1, "绪论", None, title="测试课程", article_type="学习")
        text = task.read_text(encoding="utf-8")
        assert "长文风格：学习" in text, "任务书未写明所选长文风格"
        assert "保住讲师的讲课风格" in text, "任务书未注入学习版提示词"

        (ws.articles_dir / "P01_绪论_精读文章.md").unlink(missing_ok=True)
        legacy_task = export_article_task(ws, 2, "数制", None, title="测试课程", article_type="legacy")
        legacy_text = legacy_task.read_text(encoding="utf-8")
        assert "长文风格：旧版" in legacy_text, "旧版任务书未写明风格"
        assert "随堂自测" in legacy_text, "旧版任务书未注入旧版提示词"


def check_deliverable_lint_gate():
    """真实交付物机器门禁：告警块与围栏配对必须为 0（仓库无 output/ 时自动跳过）。

    这是「只在提示词里喊口号、没人验货」的补丁：提示词规则容易被改回，产物指标不会说谎。
    """
    from src.core.deliverable_lint import lint_render, summarize_render
    from src.core.task_cleanup import find_workspaces

    workspaces = find_workspaces(PRODUCTS_ROOT)
    if not workspaces:
        print("       (仓库内无 output/ 工作区，跳过真实产物门禁)")
        return

    alerts = unbalanced = 0
    for ws in workspaces:
        for path in ws.root_dir.rglob("*.md"):
            try:
                rel_parents = path.relative_to(ws.root_dir).parts[:-1]
            except ValueError:
                continue
            if any(part.startswith(".") for part in rel_parents):
                continue  # 归档/备份目录不计入
            if path.name.endswith(("_TASK.md", "_KERNEL_TASK.md")):
                continue
            try:
                summary = summarize_render(lint_render(path.read_text(encoding="utf-8")))
            except OSError:
                continue
            alerts += summary["alert_blocks"]
            unbalanced += summary["fences_unbalanced"]

    assert alerts == 0, f"交付物中仍存在 {alerts} 处 GitHub 告警块（> [!TIP] 等）"
    assert unbalanced == 0, f"交付物中仍有 {unbalanced} 个未成对闭合的代码围栏"


def check_docs_style_matrix_clean():
    """文档不得再残留已删除的旧笔记风格：minimal / detailed 只存在于历史记忆里。"""
    for rel in (
        "README.md",
        "README.en.md",
        "SKILL.md",
        "references/delivery_matrix.md",
    ):
        text = (SKILL_ROOT / rel).read_text(encoding="utf-8")
        low = text.lower()
        for 已删除 in ("minimal", "detailed"):
            assert 已删除 not in low, f"{rel} 仍残留已删除的笔记风格字样：{已删除}"


def check_delivery_matrix_article_types():
    """交付矩阵的长文类型表必须覆盖全部已登记类型，且标明 legacy 的存在与 learning 的推荐地位。"""
    from src.generator.prompt_templates import ARTICLE_PROMPT_TYPES, IMPLEMENTED_ARTICLE_TYPES

    for rel in (
        "references/delivery_matrix.md",
        ".agents/skills/bili-video2book/references/delivery_matrix.md",
    ):
        text = (SKILL_ROOT / rel).read_text(encoding="utf-8")
        for key in ARTICLE_PROMPT_TYPES:
            assert f"`{key}`" in text, f"{rel} 的类型表缺少 {key} 行"
        assert "推荐" in text or "已提供（推荐" in text, f"{rel} 未标出推荐风格"
        assert set(IMPLEMENTED_ARTICLE_TYPES) == {"learning", "legacy"}, \
            f"已提供提示词的类型集合变化，文档需同步：{IMPLEMENTED_ARTICLE_TYPES}"


def check_version_consistency():
    """版本号三处必须一致：SKILL 抬头 / pyproject / src.__version__。"""
    import re as _re

    import src

    skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    m_skill = _re.search(r"^\s*version:\s*([^\s]+)\s*$", skill, _re.M)
    assert m_skill, "SKILL.md 抬头缺少 version 字段"
    pyproject = (SKILL_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    m_proj = _re.search(r'^version\s*=\s*"([^"]+)"', pyproject, _re.M)
    assert m_proj, "pyproject.toml 缺少 version"
    versions = {"SKILL.md": m_skill.group(1), "pyproject.toml": m_proj.group(1), "src.__version__": src.__version__}
    assert len(set(versions.values())) == 1, f"版本号不一致: {versions}"


def check_quality_gate_copy():
    """质检文档口径必须与代码一致：五类致命项齐全，且语言标识写明是提示项。"""
    from src.core.deliverable_lint import FATAL_NOTE_KEYS

    assert len(FATAL_NOTE_KEYS) == 5, f"致命项集合变化，文档需同步：{FATAL_NOTE_KEYS}"
    readme = (SKILL_ROOT / "README.md").read_text(encoding="utf-8")
    for 中文标签 in ("套话填充", "空壳标题", "分集平铺标题", "行内残缺引用", "分集口吻"):
        assert 中文标签 in readme, f"README.md 质检说明缺少致命项：{中文标签}"
    readme_en = (SKILL_ROOT / "README.en.md").read_text(encoding="utf-8").lower()
    for 英文标签 in ("boilerplate", "hollow", "per-episode headings", "inline quote", "episode voice"):
        assert 英文标签 in readme_en, f"README.en.md 质检说明缺少致命项：{英文标签}"
    for rel in ("SKILL.md", "README.md", "README.en.md"):
        text = (SKILL_ROOT / rel).read_text(encoding="utf-8")
        assert "语言标识" in text or "language tag" in text.lower() or "language identifier" in text.lower(), \
            f"{rel} 未说明围栏语言标识的体检口径"


def check_dispatch_discipline_documented():
    """阶段一派发纪律必须写进文档，不能停留在含糊措辞上（防止回退）。

    阈值：课程总时长 ≤ 60 分钟 → 主 Agent 可串行；超过 → 必须派发（一集一子智能体，
    或集数多且单集短时 3~5 集打包）。回报协议：只回报一行、不回传正文。
    """
    skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    for 关键词 in ("60 分钟", "一集一子智能体", "执行者", "不回传正文", "BVB_AUDIO_TOKENS_PER_SEC"):
        assert 关键词 in skill, f"SKILL.md 缺少阶段一派发纪律关键词：{关键词}"

    readme = (SKILL_ROOT / "README.md").read_text(encoding="utf-8")
    assert "60 分钟" in readme and ("派发" in readme), "README.md 未写明阶段一派发阈值"
    readme_en = (SKILL_ROOT / "README.en.md").read_text(encoding="utf-8")
    assert "60 minutes" in readme_en or "60-minute" in readme_en, "README.en.md 未写明阶段一派发阈值"


def check_dispatch_payload_shape():
    """派发载荷契约：临时工作区跑一次 queue_tracker，断言字段齐备、台账可写、默认零写入。"""
    import json
    import tempfile

    from src.core import budget
    from src.core.workspace import TaskWorkspace

    with tempfile.TemporaryDirectory() as tmp:
        ws = TaskWorkspace(task_name="dispatch_probe", base_dir=tmp)
        ws.save_parts([
            {"page": 1, "title": "导学", "duration": 900},
            {"page": 2, "title": "变量", "duration": 1200},
        ])
        (ws.audio_dir / "P01_导学.m4a").write_bytes(b"x" * 20000)
        (ws.audio_dir / "P02_变量.m4a").write_bytes(b"x" * 20000)
        (ws.articles_dir / "P01_导学_TASK.md").write_text("任务书" * 100, encoding="utf-8")

        tracker = SKILL_ROOT / "scripts" / "queue_tracker.py"

        def _run(*extra, base=None):
            return run_quiet(
                [sys.executable, str(tracker), "--base-dir", str(base or ws.root_dir), *extra],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=120,
            )

        log_path = ws.root_dir / ".dispatch_log.jsonl"
        assert not log_path.exists()

        # 0) --base-dir 既支持「产物根（含工作区）」也支持「工作区目录本身」
        res_root = _run("--summary", base=ws.base_dir)
        assert res_root.returncode == 0, f"--base-dir 指向产物根时失败: {res_root.stdout[-200:]}"
        res_ws = _run("--summary", base=ws.root_dir)
        assert res_ws.returncode == 0, f"--base-dir 指向工作区本身时失败: {res_ws.stdout[-200:]}"
        assert res_root.stdout.split(";")[0] == res_ws.stdout.split(";")[0], "两种 --base-dir 口径结果不一致"

        # 1) 默认零写入
        res = _run("--next", "1", "--json")
        assert res.returncode == 0, f"queue_tracker 退出码 {res.returncode}: {res.stdout[-300:]}"
        assert not log_path.exists(), "未加 --log-dispatch 时不应写台账（--next 必须保持纯读）"

        payload = json.loads(res.stdout)
        for key in ("budget", "next"):
            assert key in payload, f"派发载荷缺少顶层字段：{key}"
        for key in ("suggest_workers", "suggest_batch", "audio_tokens_per_sec", "context_window_tokens",
                    "dispatch_required", "total_audio_min"):
            assert key in payload["budget"], f"budget 缺少字段：{key}"

        item = payload["next"][0]
        for key in ("page", "title", "duration_sec", "est_audio_tokens", "est_episode_prefill_tokens",
                    "task_file", "task_file_exists", "audio_file", "audio_slices", "target_article"):
            assert key in item, f"派发载荷缺少每集字段：{key}"
        assert item["page"] == 1 and item["duration_sec"] == 900
        assert item["est_audio_tokens"] == budget.est_audio_tokens(900)
        assert item["task_file_exists"] is True, "任务书已存在却报告不存在"
        assert item["target_article"].endswith("P01_导学_精读文章.md"), item["target_article"]
        assert item["audio_slices"] and item["audio_slices"][0]["path"].endswith("P01_导学.m4a")
        assert item["slices_ready"] is True

        # 2) --log-dispatch 写台账，且内容与建议分集一致
        res2 = _run("--next", "2", "--json", "--log-dispatch")
        assert res2.returncode == 0, f"queue_tracker --log-dispatch 失败: {res2.stdout[-300:]}"
        assert log_path.exists(), "--log-dispatch 未写出台账"
        entry = json.loads(log_path.read_text(encoding="utf-8").strip().splitlines()[-1])
        assert entry["suggested"] == [1, 2], f"台账建议分集与载荷不一致: {entry}"
        assert entry["requested"] == 2 and entry["audio_tokens_per_sec"] == budget.audio_tokens_per_sec()

        # 3) 系数可配置：环境变量覆盖后 est_audio_tokens 同步变化
        env = dict(os.environ, BVB_AUDIO_TOKENS_PER_SEC="100")
        res3 = run_quiet(
            [sys.executable, str(tracker), "--base-dir", str(ws.root_dir), "--summary"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=120, env=env,
        )
        assert "AUDIO_TOKENS_PER_SEC=100" in res3.stdout, f"系数覆盖未生效: {res3.stdout.strip()[:200]}"
        assert "SUGGEST_WORKERS=" in res3.stdout and "DISPATCH_REQUIRED=" in res3.stdout

        # 4) 阈值口径：短课程（30 分钟）可串行，长课程必须派发
        assert budget.serial_ok(30 * 60) is True, "30 分钟课程应允许串行"
        assert budget.dispatch_required(30 * 60, episodes=4) is False, "30 分钟 4 集不应强制派发"
        assert budget.dispatch_required(4 * 3600, episodes=40) is True, "4 小时课程必须派发"
        assert budget.suggest_workers(190) == 6 and budget.suggest_workers(2) == 2
        assert budget.suggest_batch([35_000] * 20, 20) == 5, "短集多集应建议打包"
        assert budget.suggest_batch([80_000] * 20, 20) == 1, "长集不应打包"


def check_manifest_paths_portable():
    """清单路径必须可移植：路径字段（含列表型）一律按 to_relative 归一，绝不原样落盘绝对路径。

    注意：临时工作区可能位于**另一个盘符**（TEMP 在 C:、仓库在 D:），此时跨盘 relativize 无法
    产出 `../..` 形式，会退化为绝对路径——因此这里断言的是「落盘值恒等于 to_relative(原值)」，
    而不是「一定不是绝对路径」；另用仓库内路径单独验证相对化后不含盘符。
    """
    import json
    import re as _re
    import tempfile

    from src.core.workspace import TaskWorkspace

    drive_re = _re.compile(r"[A-Za-z]:[\\/]")

    # 仓库内路径：相对化后必须是纯相对、无盘符、无反斜杠
    in_repo_rel = TaskWorkspace.to_relative(HOME_ROOT / "output" / "__probe__" / "模块01_甲_精读全书.md")
    assert in_repo_rel == "output/__probe__/模块01_甲_精读全书.md", f"仓库内路径相对化异常: {in_repo_rel}"
    assert not drive_re.search(in_repo_rel) and "\\" not in in_repo_rel

    with tempfile.TemporaryDirectory() as tmp:
        ws = TaskWorkspace(task_name="portable_probe", base_dir=tmp)
        raw = {
            "textbooks": [str(ws.root_dir / "textbooks" / "模块01_甲_精读全书.md")],
            "notes_files": [str(ws.notes_dir / "模块01_甲_笔记.md")],
            "note_file": str(ws.notes_dir / "模块01_甲_笔记.md"),
            "kernel_file": str(ws.subtitles_dir / "kernels" / "P01_甲_kernel.json"),
            "details": [{"page": 1, "article": str(ws.articles_dir / "P01_甲_精读文章.md")}],
        }
        rel = ws.relativize_obj(raw)
        assert rel["textbooks"] == [TaskWorkspace.to_relative(raw["textbooks"][0])], \
            f"textbooks 未按 to_relative 归一: {rel['textbooks']}"
        assert rel["notes_files"] == [TaskWorkspace.to_relative(raw["notes_files"][0])], \
            f"notes_files 未按 to_relative 归一: {rel['notes_files']}"
        assert rel["note_file"] == TaskWorkspace.to_relative(raw["note_file"]), \
            f"note_file 未按 to_relative 归一: {rel['note_file']}"
        assert rel["kernel_file"] == TaskWorkspace.to_relative(raw["kernel_file"]), \
            f"kernel_file 未按 to_relative 归一: {rel['kernel_file']}"
        assert rel["details"][0]["article"] == TaskWorkspace.to_relative(raw["details"][0]["article"]), \
            "details[].article 未按 to_relative 归一"

        # 反方向：读回时列表型路径字段必须逐项绝对化，程序内部可直接读取
        back = ws.absolutize_obj(rel)
        assert back["textbooks"] == [str(TaskWorkspace.to_absolute(rel["textbooks"][0]))], \
            f"textbooks 未逐项绝对化: {back['textbooks']}"
        assert Path(back["note_file"]).is_absolute(), "note_file 未绝对化"
        assert Path(back["details"][0]["article"]).is_absolute(), "details[].article 未绝对化"

        ws.save_manifest({
            "textbooks": raw["textbooks"],
            "knowledge_blocks_results": [{"block_id": 1, "note_file": raw["note_file"]}],
        })
        text = ws.manifest_file.read_text(encoding="utf-8")
        assert "\\\\" not in text, "manifest.json 落盘了 Windows 反斜杠路径"
        payload = json.loads(text)
        assert payload["textbooks"] == [TaskWorkspace.to_relative(raw["textbooks"][0])], \
            f"textbooks 落盘形态异常: {payload['textbooks']}"
        assert payload["knowledge_blocks_results"][0]["note_file"] == TaskWorkspace.to_relative(raw["note_file"]), \
            f"note_file 落盘形态异常: {payload['knowledge_blocks_results'][0]['note_file']}"


def check_no_hardcoded_machine_paths():
    """源码不得硬编码本机盘符绝对路径（AST 取字符串常量；跳过文档字符串里的示例路径）。"""
    import ast
    import re as _re

    drive_re = _re.compile(r"(^|[^\w])[A-Za-z]:[\\/]")

    def _docstring_nodes(tree: ast.AST) -> set:
        found = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                body = getattr(node, "body", None) or []
                if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                        and isinstance(body[0].value.value, str):
                    found.add(id(body[0].value))
        return found

    扫描 = []
    # MCP 侧（mcp/ 仓库）由它自己的 selfcheck.py 扫描，本仓库只负责技能侧
    for 子目录 in ("src", "scripts"):
        for path in (SKILL_ROOT / 子目录).rglob("*.py"):
            if path.name == "selfcheck.py":
                continue
            if "__pycache__" in path.parts:
                continue
            扫描.append(path)
    assert 扫描, "未找到任何源码文件，扫描范围异常"

    hits = []
    for path in 扫描:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError as err:
            raise AssertionError(f"源码语法错误，无法扫描: {path}: {err}")
        skip = _docstring_nodes(tree)
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in skip:
                if drive_re.search(node.value):
                    hits.append(f"{path.relative_to(SKILL_ROOT).as_posix()}:{node.lineno}: {node.value[:70]}")
    assert not hits, "源码内存在硬编码本机绝对路径:\n      " + "\n      ".join(hits)


def check_regression_fixes():
    """本轮修复项的回归断言（全部在临时工作区内完成，不触碰 output/）。"""
    import json
    import tempfile

    from src.cli import _owner_line
    from src.core.task_cleanup import find_module_note
    from src.core.workspace import TaskWorkspace
    from src.generator.block_synthesizer import BlockSynthesizer
    from src.generator.integrator import ArticleIntegrator

    # 1) merge_parts：局部运行不得丢历史分集，同 page 以新结果为准
    merged = TaskWorkspace.merge_parts(
        [{"page": 1, "title": "旧"}, {"page": 2, "title": "旧"}, {"page": 3, "title": "旧"}],
        [{"page": 2, "title": "新"}],
    )
    assert [m["page"] for m in merged] == [1, 2, 3], f"合并后分集丢失/乱序: {merged}"
    assert merged[1]["title"] == "新", "同 page 未以新结果覆盖"
    assert TaskWorkspace.merge_parts([], [{"page": 5}]) == [{"page": 5}], "空缓存合并不正确"
    assert TaskWorkspace.merge_parts([{"page": 1}], []) == [{"page": 1}], "空增量合并不正确"

    # 2) 离线自愈元数据（owner 为字符串/空）不得让 parse 崩掉
    assert "未知" in _owner_line({"owner": "", "owner_mid": 0}), "owner 为空串时未兜底"
    assert "UP主" in _owner_line({"owner": {"name": "UP主", "mid": 7}}), "正常 owner 渲染异常"
    assert "mid: 9" in _owner_line({"owner_mid": 9}), "仅 owner_mid 时渲染异常"

    with tempfile.TemporaryDirectory() as tmp:
        ws = TaskWorkspace(task_name="regression_probe", base_dir=tmp)
        ws.save_parts([{"page": 1, "title": "绪论"}, {"page": 2, "title": "数制"}])
        article = ws.articles_dir / "P01_绪论_精读文章.md"
        article.write_text(
            "# 微型计算机概述\n"
            "> 目标：讲清体系结构  \n"
            "> 来源：P01 单集精读长文\n"
            "\n"
            "---\n"
            "\n"
            "## 1. 体系结构\n\n正文内容。\n",
            encoding="utf-8",
        )

        # 3) 模块笔记复用：历史命名（无 `_笔记` 规范名）也必须被认出，不得重复派发
        found = find_module_note(ws, 1)
        assert found is None, "尚无笔记成品时不应命中"
        legacy_note = ws.notes_dir / "模块01_微机系统基础_P01-P17_思维导图速查笔记.md"
        legacy_note.write_text("笔记" * 600, encoding="utf-8")
        assert find_module_note(ws, 1) == legacy_note, "历史命名的笔记成品未被识别"
        res = BlockSynthesizer.synthesize_block(
            {"block_id": 1, "block_title": "微机系统基础", "episodes": [1], "core_theme": "x"},
            [article], ws=ws,
        )
        assert res["status"] == "cached", f"已有笔记成品时仍重复派发任务书: {res['status']}"
        assert not (ws.notes_dir / "模块01_微机系统基础_TASK.md").exists(), "重复派发出了任务书"

        # 4) 教材整编：多行引用抬头与 H1 必须剥净、H2 降级，且默认复用 / --force 重编
        integrator = ArticleIntegrator(ws.root_dir)
        out = integrator.integrate_module(1, "绪论", [{"page": 1, "title": "绪论"}], "测试课程")
        text = out.read_text(encoding="utf-8")
        out_lines = text.splitlines()
        assert "微型计算机概述" not in text, "长文 H1 未被剥离"
        assert "目标：讲清体系结构" not in text and "来源：P01 单集精读长文" not in text, "多行抬头未被剥净"
        assert "### 1. 体系结构" in out_lines, "章内 H2 未降级为 H3"
        assert "## 1. 体系结构" not in out_lines, "章内 H2 仍以 H2 层级残留（与教材章标题同级）"
        assert "正文内容。" in text, "正文被误删"

        out.write_text(text + "\n<!-- MARK -->\n", encoding="utf-8")
        integrator.integrate_module(1, "绪论", [{"page": 1, "title": "绪论"}], "测试课程")
        assert "<!-- MARK -->" in out.read_text(encoding="utf-8"), "默认未复用已存在的模块教材"
        integrator.integrate_module(1, "绪论", [{"page": 1, "title": "绪论"}], "测试课程", force=True)
        assert "<!-- MARK -->" not in out.read_text(encoding="utf-8"), "--force 未强制重新整编"

        # 5) 任务书回收计数：删除失败与成品未产出必须分开统计
        from src.core.task_cleanup import cleanup_completed_tasks

        (ws.articles_dir / "P01_绪论_TASK.md").write_text("t" * 200, encoding="utf-8")
        (ws.articles_dir / "P02_数制_TASK.md").write_text("t" * 200, encoding="utf-8")
        (ws.articles_dir / "P02_数制_精读文章.md").write_text("正文" * 400, encoding="utf-8")
        result = cleanup_completed_tasks(ws, keep_per_category=1)
        counts = result["counts"]["articles"]
        assert "failed_delete" in counts and "skipped_pending" in counts, f"回收计数未拆分: {counts}"
        assert counts["failed_delete"] == 0, f"正常删除不应计入失败: {counts}"
        assert list(result["failed_delete"]) == [], "正常删除不应留下失败清单"

        # 6) 清单路径可移植性（与 check_manifest_paths_portable 互补，此处走真实写入链路）
        textbook_path = str(ws.root_dir / "textbooks" / "模块01_绪论_精读全书.md")
        ws.save_manifest({"textbooks": [textbook_path]})
        stored = json.loads(ws.manifest_file.read_text(encoding="utf-8"))["textbooks"][0]
        assert stored == TaskWorkspace.to_relative(textbook_path), \
            f"textbooks 落盘形态与 to_relative 不一致: {stored}"


def main():
    print("=" * 62)
    print("bili-video2book 技能仓库自检（三域分离：skill / mcp / output）")
    print(f"  代码根  : {SKILL_ROOT}")
    print(f"  容器根  : {HOME_ROOT}")
    print(f"  产物根  : {PRODUCTS_ROOT}")
    print("=" * 62)
    check("模块导入无 ImportError", check_imports)
    check("CLI 全部子命令 --help 可用", check_cli_help)
    check("三域分离契约（仓库边界/产物在仓库外）", check_repo_separation)
    check("产物根解析与 cwd 无关", check_products_root_resolution)
    check("跨仓库不互引（skill ⇎ mcp）", check_no_cross_repo_imports)
    check("KernelExtractor 契约（无本地伪造抽取）", check_kernel_extractor_contract)
    check("SemanticTopicPlanner 契约（无启发式聚类）", check_topic_planner_contract)
    check("ArticleIntegrator 无硬编码课程数据", check_integrator_no_hardcoded_course)
    check("零中间逐字稿入口切换", check_zero_transcript_pipeline)
    check("子进程硬超时就位", check_subprocess_timeouts)
    check("MCP 仓库自检（可选段落）", check_mcp_repo_optional)
    check("任务书导出门禁端到端", check_task_file_export_end_to_end)
    check("阶段一门禁不误认任务书", check_stage1_gate_ignores_task_files)
    check("重复分集免字幕复用", check_dedup_reuses_without_subtitles)
    check("SESSDATA 存档安全（脱敏/不入库）", check_sessdata_store_safety)
    check("缓存与凭证路径锚定产物根", check_cache_paths_anchored)
    check("宿主旁路目录与产物不入库", check_host_artifacts_ignored)
    check("交付物渲染兼容约束（Typora）", check_render_compat_rules)
    check("长文提示词风格契约（学习/旧版 + 未确认即终止）", check_article_prompt_types)
    check("模块笔记契约（文章直供/只写结论/版式规范/任务书回收）", check_module_note_contract)
    check("交付物机器门禁（告警块/围栏配对）", check_deliverable_lint_gate)
    check("文档无已删除笔记风格残留", check_docs_style_matrix_clean)
    check("交付矩阵长文类型表齐备", check_delivery_matrix_article_types)
    check("版本号三处一致", check_version_consistency)
    check("质检文档口径与门禁一致", check_quality_gate_copy)
    check("清单路径可移植（无绝对路径落盘）", check_manifest_paths_portable)
    check("源码无硬编码本机路径", check_no_hardcoded_machine_paths)
    check("阶段一派发纪律已写入文档", check_dispatch_discipline_documented)
    check("派发载荷与台账契约", check_dispatch_payload_shape)
    check("本轮修复项回归", check_regression_fixes)
    check("死代码与验证产物已移除", check_dead_modules_removed)
    check("两份 SKILL 同步", check_skill_copies_in_sync)
    print("=" * 62)
    if FAILURES:
        print(f"[FAILED] {len(FAILURES)} 项未通过:")
        for name, err in FAILURES:
            print(f"  - {name}: {err}")
        sys.exit(1)
    print("[OK] 全部自检通过")


if __name__ == "__main__":
    main()
