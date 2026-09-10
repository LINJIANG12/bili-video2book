"""FastCtx-style Command Line Interface for OmniMedia MCP."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

from .adapters.registry import ADAPTER_MAP, get_adapter, get_all_adapters, list_supported_targets
from .core.inspector import MediaInspector
from .server import mcp


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
    """Diagnoses environment, tools and target host configurations."""
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

    # 2. Native listening requires no credentials whatsoever
    print()
    print("[ 凭证需求 ]")
    print(f"  {TAG_PASS} 无需任何 API Key：音频由宿主多模态模型原生聆听 (read_audio)，零外部凭证消耗。")

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
    p_status = subparsers.add_parser("status", help="诊断环境、依赖与宿主接入状态")
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
