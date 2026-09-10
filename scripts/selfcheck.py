#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Minimal runnable self-check for the bili-video2book + omni-media-mcp toolchain.

Not a test framework: a flat sequence of assertions covering the invariants that
matter after the architecture refactor (Agent-native kernel/plan chain, zero
intermediate transcript, no dead modules, MCP error contract).

Run: python scripts/selfcheck.py
"""

import asyncio
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

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
    import src.core.pipeline  # noqa: F401
    import src.core.kernel_extractor  # noqa: F401
    import src.core.workspace  # noqa: F401
    import src.generator.topic_planner  # noqa: F401
    import src.generator.integrator  # noqa: F401
    import src.generator.block_synthesizer  # noqa: F401
    import omni_media_mcp.server  # noqa: F401


def check_cli_help():
    for sub in ("parse", "audio", "transcribe",
                "pipeline", "cluster-notes", "cluster-articles", "dedup",
                "login", "logout", "info"):
        res = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "src" / "cli.py"), sub, "--help"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=60,
        )
        assert res.returncode == 0, f"`{sub} --help` 退出码 {res.returncode}: {res.stderr[:200]}"


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

    text = (PROJECT_ROOT / "src" / "generator" / "integrator.py").read_text(encoding="utf-8")
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
    import src.core.audio_chunker as ac
    import src.core.local_media as lm

    assert lm.PROBE_TIMEOUT_SEC > 0 and lm.TRANSCODE_TIMEOUT_SEC > 0
    assert ac.PROBE_TIMEOUT_SEC == lm.PROBE_TIMEOUT_SEC
    assert ac.TRANSCODE_TIMEOUT_SEC == lm.TRANSCODE_TIMEOUT_SEC

    for rel in ("src/core/local_media.py", "src/core/audio_chunker.py"):
        text = (PROJECT_ROOT / rel).read_text(encoding="utf-8")
        for line in text.splitlines():
            if "subprocess.run(" in line:
                assert "timeout=" in line, f"{rel} 存在无超时的 subprocess.run: {line.strip()}"


def check_mcp_tool_contract():
    """MCP 工具契约：非法入参抛类型化异常，且废弃的云端委托链路必须已彻底移除。"""
    from omni_media_mcp import server
    from omni_media_mcp.core.limits import PROBE_TIMEOUT_SEC

    assert PROBE_TIMEOUT_SEC > 0

    # 云端委托（需 API Key 的 read_media/ask_media/probe_models 及 provider/benchmark 层）
    # 已废弃：宿主模型原生听音取代了它，这些入口必须不复存在。
    for gone in ("read_media", "ask_media", "probe_models"):
        assert not hasattr(server, gone), f"{gone} 属废弃的云端委托链路，应已移除"
    for live in ("read_audio", "inspect_media"):
        assert hasattr(server, live), f"{live} 是当前唯一入口，不得缺失"

    missing = str(PROJECT_ROOT / "definitely-missing.m4a")
    non_media = str(PROJECT_ROOT / "pyproject.toml")

    async def _run():
        cases = [
            (server.read_audio(file_path=missing), FileNotFoundError),
            (server.read_audio(file_path=non_media), ValueError),
            (server.read_audio(file_path=non_media, output_mode="bogus"), ValueError),
            (server.inspect_media(file_path=missing), FileNotFoundError),
            (server.inspect_media(file_path=non_media), ValueError),
        ]
        for coro, expected in cases:
            try:
                await coro
            except expected:
                continue
            except Exception as err:
                raise AssertionError(f"期望 {expected.__name__}，实际 {type(err).__name__}: {err}")
            raise AssertionError(f"非法入参未抛出 {expected.__name__}")

    asyncio.run(_run())


def check_dead_modules_removed():
    for rel in (
        "src/core/http_client.py",
        "src/generator/cleaner.py",
        "src/generator/classifier.py",
        "src/generator/doc_builder.py",
        "omni-media-mcp/omni_media_mcp/installer.py",
        "omni-media-mcp/omni_media_mcp/providers",
        "omni-media-mcp/omni_media_mcp/benchmarks",
        "omni-media-mcp/omni_media_mcp/prompts.py",
        "tests",
        "omni-media-mcp/tests",
        "MCP_TOOL_AUDIT_REPORT.md",
        "config.example.json",
        "scripts/validate_skill.py",
    ):
        assert not (PROJECT_ROOT / rel).exists(), f"{rel} 应已删除"


def check_host_artifacts_ignored():
    """宿主/编辑器旁路目录必须被 .gitignore 覆盖且从未入库。

    .workbuddy、.zcode 这类目录由编辑器在会话中自动写入（含对话记忆），
    既不该被"必须不存在"式断言约束（宿主会重建），也绝不能进入版本库。
    """
    import subprocess as _sp

    ignore = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")
    for name in (".workbuddy", ".aide", ".zcode", "output", ".sessdata.json"):
        assert name in ignore, f"{name} 未被 .gitignore 覆盖"

    tracked = _sp.run(
        ["git", "ls-files", "--", ".workbuddy", ".aide", ".zcode"],
        cwd=str(PROJECT_ROOT), stdout=_sp.PIPE, stderr=_sp.PIPE, text=True,
    )
    assert not tracked.stdout.strip(), f"宿主旁路目录已被纳入版本控制: {tracked.stdout.strip()}"


def check_skill_copies_in_sync():
    """两份 SKILL.md 及 references 必须保持一致（validate_skill.py 已移除，靠本检查兜底）。"""
    pairs = [
        ("SKILL.md", ".agents/skills/bili-video2book/SKILL.md"),
        ("references/delivery_matrix.md", ".agents/skills/bili-video2book/references/delivery_matrix.md"),
    ]
    for a, b in pairs:
        pa, pb = PROJECT_ROOT / a, PROJECT_ROOT / b
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

    sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
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

    # 默认存档路径必须被 .gitignore 覆盖，且绝不能已进入版本库
    assert DEFAULT_STORE_NAME in (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8"), \
        f"{DEFAULT_STORE_NAME} 未被 .gitignore 覆盖"
    tracked = _sp.run(
        ["git", "ls-files", "--", DEFAULT_STORE_NAME],
        cwd=str(PROJECT_ROOT), stdout=_sp.PIPE, stderr=_sp.PIPE, text=True,
    )
    assert not tracked.stdout.strip(), f"凭证存档已被纳入版本控制: {tracked.stdout.strip()}"
    assert store_path().name == DEFAULT_STORE_NAME


def check_cache_paths_anchored():
    """缓存/凭证文件路径必须锚定仓库根，不得随当前所在目录漂移。"""
    from src.core.credentials import store_path
    from src.core.wbi import WbiSigner

    for label, p in (("WBI 密钥", WbiSigner._解析密钥文件路径()), ("凭证存档", store_path())):
        assert p.is_absolute(), f"{label}路径不是绝对路径: {p}"
        assert PROJECT_ROOT in p.parents, f"{label}路径未锚定仓库根: {p}"


def main():
    print("=" * 62)
    print("bili-video2book / omni-media-mcp 自检")
    print("=" * 62)
    check("模块导入无 ImportError", check_imports)
    check("CLI 全部子命令 --help 可用", check_cli_help)
    check("KernelExtractor 契约（无本地伪造抽取）", check_kernel_extractor_contract)
    check("SemanticTopicPlanner 契约（无启发式聚类）", check_topic_planner_contract)
    check("ArticleIntegrator 无硬编码课程数据", check_integrator_no_hardcoded_course)
    check("零中间逐字稿入口切换", check_zero_transcript_pipeline)
    check("子进程硬超时就位", check_subprocess_timeouts)
    check("MCP 工具契约与废弃链路移除", check_mcp_tool_contract)
    check("任务书导出门禁端到端", check_task_file_export_end_to_end)
    check("阶段一门禁不误认任务书", check_stage1_gate_ignores_task_files)
    check("重复分集免字幕复用", check_dedup_reuses_without_subtitles)
    check("SESSDATA 存档安全（脱敏/不入库）", check_sessdata_store_safety)
    check("缓存与凭证路径锚定仓库根", check_cache_paths_anchored)
    check("宿主旁路目录不入库", check_host_artifacts_ignored)
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
