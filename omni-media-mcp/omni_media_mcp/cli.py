"""FastCtx-style Command Line Interface for OmniMedia MCP."""

from __future__ import annotations

import argparse
import asyncio
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

from .adapters.registry import ADAPTER_MAP, get_adapter, get_all_adapters, list_supported_targets
from .benchmarks.probe import BenchmarkProber
from .core.inspector import MediaInspector
from .server import ask_media, mcp, read_media


def color_text(text: str, color_code: str) -> str:
    """Wraps text in ANSI escape sequence if stdout supports color."""
    if sys.stdout.isatty():
        return f"\033[{color_code}m{text}\033[0m"
    return text


TAG_PASS = color_text("[PASS]", "32")  # Green
TAG_INFO = color_text("[INFO]", "36")  # Cyan
TAG_FAIL = color_text("[FAIL]", "31")  # Red
TAG_WARN = color_text("[WARN]", "33")  # Yellow


def cmd_serve(args: argparse.Namespace) -> int:
    """Starts MCP stdio transport server."""
    mcp.run(transport="stdio")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Diagnoses environment, tools, API keys, and target host configurations."""
    print("=" * 65)
    print("📊 OmniMedia 系统运行与宿主挂载状态诊断")
    print("=" * 65)

    # 1. Binaries and Environment
    print("\n[ 系统与依赖诊断 ]")
    # Python
    py_ver = sys.version.split()[0]
    print(f"  {TAG_PASS} Python: {py_ver} ({sys.executable})")

    # MCP library
    try:
        import mcp as mcp_pkg
        mcp_ver = getattr(mcp_pkg, "__version__", ">=1.0.0")
        print(f"  {TAG_PASS} MCP SDK: {mcp_ver}")
    except Exception as e:
        print(f"  {TAG_FAIL} MCP SDK: 未正确加载 ({e})")

    # FFmpeg
    ffmpeg_bin = shutil.which("ffmpeg")
    if ffmpeg_bin:
        try:
            res = subprocess.run([ffmpeg_bin, "-version"], stdout=subprocess.PIPE, text=True, timeout=5)
            first_line = res.stdout.splitlines()[0] if res.stdout else "unknown version"
            print(f"  {TAG_PASS} FFmpeg: {first_line.split('Copyright')[0].strip()} ({ffmpeg_bin})")
        except Exception:
            print(f"  {TAG_PASS} FFmpeg: 可用 ({ffmpeg_bin})")
    else:
        print(f"  {TAG_FAIL} FFmpeg: 系统 PATH 中未找到 ffmpeg 可执行文件")

    # FFprobe
    ffprobe_bin = shutil.which("ffprobe")
    if ffprobe_bin:
        print(f"  {TAG_PASS} FFprobe: 可用 ({ffprobe_bin})")
    else:
        print(f"  {TAG_WARN} FFprobe: 未找到独立 ffprobe（将回退使用 ffmpeg 探测）")

    # 2. Providers API Keys
    print("\n[ 多模态模型凭证状态 ]")
    env_keys = [
        ("GEMINI_API_KEY", "Google Gemini 2.5/3.0 全模态 (推荐主力)"),
        ("MIMO_API_KEY", "Xiaomi MiMo-V2.5 1M 长文本全模态"),
        ("OPENAI_API_KEY", "OpenAI GPT-4o / GPT-5 input_audio"),
        ("DASHSCOPE_API_KEY", "Alibaba Qwen2.5-VL / Qwen-Omni"),
        ("DEEPSEEK_API_KEY", "DeepSeek-V4-Flash 视觉多模态"),
        ("MINIMAX_API_KEY", "MiniMax H3 / abab 7 音频模型"),
    ]

    for key, desc in env_keys:
        val = os.environ.get(key)
        if val:
            masked = f"{val[:4]}...{val[-4:]}" if len(val) > 8 else "***"
            print(f"  {TAG_PASS} {key}: 已配置 ({masked}) - {desc}")
        else:
            print(f"  {TAG_INFO} {key}: 未配置 - {desc}")

    # 3. Host Adapters
    print("\n[ 宿主工具箱接入状态 ]")
    adapters = get_all_adapters()
    for ad in adapters:
        st = ad.check_status()
        status_tag = TAG_PASS if st["status"] == "PASS" else TAG_INFO
        print(f"  {status_tag} {ad.display_name} [{ad.target_id}]: {st['detail']}")

    print("\n💡 提示: 执行 `omni-media apply --target <host>` 可显式接入指定宿主。")
    print("=" * 65)
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    """Applies MCP registration to target host configuration with diff preview."""
    target = args.target.lower().strip()
    yes = args.yes

    if target == "all":
        targets_to_apply = list_supported_targets()
    else:
        if target not in ADAPTER_MAP:
            print(f"{TAG_FAIL} 未知目标: '{target}'。支持的目标: {', '.join(list_supported_targets())}, all")
            return 1
        targets_to_apply = [target]

    for t in targets_to_apply:
        adapter = get_adapter(t, custom_config_path=args.config)
        has_change, diff, _ = adapter.preview_apply()

        print("\n" + "-" * 60)
        print(f"目标宿主: {adapter.display_name} ({adapter.get_config_path()})")
        print("-" * 60)

        if not has_change:
            print(f"{TAG_PASS} 配置已是最新，无需修改。")
            continue

        print("即将写入的配置 Diff 预览:")
        print(color_text(diff, "33"))

        if not yes:
            # The registered host config embeds provider API keys in its env
            # block so the spawned MCP server can read them (it does not inherit
            # this shell's env). Warn the user before writing keys to disk.
            print(color_text(
                f"{TAG_WARN} 注意: 本次接入会把已配置的 provider API Key 明文写入 {adapter.get_config_path()}，"
                "请确保该文件不纳入版本控制。",
                "33",
            ))
            try:
                ans = input(f"是否确认将 omni-media 接入 {adapter.display_name}? [y/N]: ").strip().lower()
            except (KeyboardInterrupt, EOFError):
                print("\n操作已取消。")
                return 1
            if ans not in ("y", "yes"):
                print(f"跳过 {adapter.display_name}。")
                continue

        ok, msg = adapter.apply()
        if ok:
            print(f"{TAG_PASS} {msg}")
        else:
            print(f"{TAG_FAIL} {msg}")

    return 0


def cmd_unapply(args: argparse.Namespace) -> int:
    """Removes omni-media registration from target host configuration."""
    target = args.target.lower().strip()
    yes = args.yes

    if target == "all":
        targets_to_unapply = list_supported_targets()
    else:
        if target not in ADAPTER_MAP:
            print(f"{TAG_FAIL} 未知目标: '{target}'。支持的目标: {', '.join(list_supported_targets())}, all")
            return 1
        targets_to_unapply = [target]

    for t in targets_to_unapply:
        adapter = get_adapter(t, custom_config_path=args.config)
        has_change, diff, _ = adapter.preview_unapply()

        print("\n" + "-" * 60)
        print(f"目标宿主: {adapter.display_name} ({adapter.get_config_path()})")
        print("-" * 60)

        if not has_change:
            print(f"{TAG_INFO} 宿主中未检测到可撤销的 omni-media 配置。")
            continue

        print("即将移除的配置 Diff 预览:")
        print(color_text(diff, "31"))

        if not yes:
            try:
                ans = input(f"是否确认从 {adapter.display_name} 移除 omni-media 配置? [y/N]: ").strip().lower()
            except (KeyboardInterrupt, EOFError):
                print("\n操作已取消。")
                return 1
            if ans not in ("y", "yes"):
                print(f"跳过 {adapter.display_name}。")
                continue

        ok, msg = adapter.unapply()
        if ok:
            print(f"{TAG_PASS} {msg}")
        else:
            print(f"{TAG_FAIL} {msg}")

    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    """Inspects media file metadata and token estimation."""
    try:
        meta = MediaInspector.probe(args.file)
        print(meta.to_markdown())
        return 0
    except Exception as e:
        print(f"{TAG_FAIL} 探测失败: {e}", file=sys.stderr)
        return 1


def cmd_read(args: argparse.Namespace) -> int:
    """Directly reads media file via multimodal models in terminal."""
    async def _run():
        return await read_media(
            file_path=args.file,
            instruction=args.instruction,
            mode=args.mode,
            provider=args.provider,
            visual=args.visual,
            start_time=args.start_time,
            duration_minutes=args.duration_minutes,
        )

    try:
        res = asyncio.run(_run())
    except (ValueError, FileNotFoundError) as e:
        print(f"{TAG_FAIL} 参数/文件错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"{TAG_FAIL} 读取失败: {e}", file=sys.stderr)
        return 1
    print(res)
    return 0


def cmd_ask(args: argparse.Namespace) -> int:
    """Asks a specific question against media file in terminal."""
    async def _run():
        return await ask_media(
            file_path=args.file,
            question=args.question,
            provider=args.provider,
            visual=args.visual,
        )

    try:
        res = asyncio.run(_run())
    except (ValueError, FileNotFoundError) as e:
        print(f"{TAG_FAIL} 参数/文件错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"{TAG_FAIL} 处理失败: {e}", file=sys.stderr)
        return 1
    print(res)
    return 0


def cmd_probe(args: argparse.Namespace) -> int:
    """Prints multimodal models benchmark and capability matrix."""
    try:
        report = BenchmarkProber.generate_report(category=args.category)
    except ValueError as e:
        print(f"{TAG_FAIL} {e}", file=sys.stderr)
        return 1
    print(report)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="omni-media",
        description="OmniMedia: Universal Multimodal Audio/Video Native Reading CLI & MCP Server",
    )
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # 1. serve
    p_serve = subparsers.add_parser("serve", help="启动 MCP stdio 传输服务")
    p_serve.set_defaults(func=cmd_serve)

    # 2. status
    p_status = subparsers.add_parser("status", help="诊断环境、依赖、凭据与宿主接入状态")
    p_status.set_defaults(func=cmd_status)

    # 3. apply
    p_apply = subparsers.add_parser("apply", help="接入指定宿主配置 (支持 diff 预览与确认)")
    p_apply.add_argument(
        "--target",
        "-t",
        default="antigravity",
        help=f"目标宿主 ({', '.join(list_supported_targets())}, all，默认: antigravity)",
    )
    p_apply.add_argument("--yes", "-y", action="store_true", help="跳过交互确认直接写入")
    p_apply.add_argument("--config", "-c", default=None, help="自定义宿主配置文件路径")
    p_apply.set_defaults(func=cmd_apply)

    # 4. unapply
    p_unapply = subparsers.add_parser("unapply", help="撤销指定宿主中的 omni-media 接入配置")
    p_unapply.add_argument(
        "--target",
        "-t",
        default="antigravity",
        help=f"目标宿主 ({', '.join(list_supported_targets())}, all，默认: antigravity)",
    )
    p_unapply.add_argument("--yes", "-y", action="store_true", help="跳过交互确认直接移除")
    p_unapply.add_argument("--config", "-c", default=None, help="自定义宿主配置文件路径")
    p_unapply.set_defaults(func=cmd_unapply)

    # 5. inspect
    p_inspect = subparsers.add_parser("inspect", help="毫秒级探测音视频元数据与 Token 预估")
    p_inspect.add_argument("file", help="本地音视频文件路径")
    p_inspect.set_defaults(func=cmd_inspect)

    # 6. read
    p_read = subparsers.add_parser("read", help="终端直接调用多模态模型阅读音视频")
    p_read.add_argument("file", help="本地音视频文件路径")
    p_read.add_argument("--instruction", "-i", default=None, help="附加指示词")
    p_read.add_argument(
        "--mode",
        "-m",
        default="transcribe",
        choices=["transcribe", "summarize", "qa", "custom"],
        help="处理预设模式 (默认: transcribe)",
    )
    p_read.add_argument(
        "--provider",
        "-p",
        default="auto",
        choices=["auto", "gemini", "mimo", "openai", "qwen", "deepseek", "minimax"],
        help="模型提供商 (默认: auto)",
    )
    p_read.add_argument("--visual", "-v", action="store_true", help="开启视频画面理解分析")
    p_read.add_argument("--start-time", "-s", default=None, help="起始时间戳 (如 '00:15:00')")
    p_read.add_argument("--duration-minutes", "-d", type=float, default=None, help="读取时长预算 (分钟)")
    p_read.set_defaults(func=cmd_read)

    # 7. ask
    p_ask = subparsers.add_parser("ask", help="针对音视频内容进行抗幻觉问答")
    p_ask.add_argument("file", help="本地音视频文件路径")
    p_ask.add_argument("question", help="具体提问内容")
    p_ask.add_argument(
        "--provider",
        "-p",
        default="auto",
        choices=["auto", "gemini", "mimo", "openai", "qwen", "deepseek", "minimax"],
        help="模型提供商 (默认: auto)",
    )
    p_ask.add_argument("--visual", "-v", action="store_true", help="开启视频画面理解")
    p_ask.set_defaults(func=cmd_ask)

    # 8. probe
    p_probe = subparsers.add_parser("probe", help="查看多模态模型评测矩阵与官方基准")
    p_probe.add_argument(
        "--category",
        "-c",
        default="all",
        choices=["all", "audio", "video"],
        help="分类过滤 (all, audio, video)",
    )
    p_probe.set_defaults(func=cmd_probe)

    return parser


def main(args: Optional[List[str]] = None) -> int:
    parser = build_parser()
    parsed_args = parser.parse_args(args)
    if not hasattr(parsed_args, "func"):
        parser.print_help()
        return 0
    return parsed_args.func(parsed_args)


if __name__ == "__main__":
    sys.exit(main())
