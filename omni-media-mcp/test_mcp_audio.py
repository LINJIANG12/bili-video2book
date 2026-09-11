"""MCP client test: verify omni-media-mcp can read a local m4a audio over stdio.

Walks the full MCP handshake (initialize -> list_tools -> call_tool) so we
exercise the real protocol surface, not just in-process imports.

Usage (paths must be supplied, nothing is hardcoded to one machine):
    set OMNI_TEST_AUDIO=D:/courses/xx/audio/P01_intro.m4a
    python test_mcp_audio.py

    # or as positional arguments
    python test_mcp_audio.py "<audio file>" "<omni-media-mcp dir>"
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

HERE = Path(__file__).resolve().parent


def _resolve_audio() -> Path:
    """测试音频路径：命令行 > 环境变量 OMNI_TEST_AUDIO，均缺失时明确报错。"""
    raw = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("OMNI_TEST_AUDIO", "")
    if not raw:
        raise SystemExit(
            "未提供测试音频路径。用法：\n"
            '  python test_mcp_audio.py "<音频文件绝对路径>" ["<omni-media-mcp 目录>"]\n'
            "  或先设置环境变量 OMNI_TEST_AUDIO=<音频文件绝对路径>"
        )
    path = Path(raw).expanduser().resolve()
    if not path.is_file():
        raise SystemExit(f"测试音频不存在: {path}")
    return path


def _resolve_server_dir() -> Path:
    """MCP 服务目录：命令行 > 环境变量 OMNI_TEST_SERVER_DIR > 本文件所在目录。"""
    raw = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("OMNI_TEST_SERVER_DIR", "")
    server_dir = Path(raw).expanduser().resolve() if raw else HERE
    if not (server_dir / "omni_media_mcp" / "server.py").is_file():
        raise SystemExit(f"该目录下未找到 omni_media_mcp/server.py: {server_dir}")
    return server_dir


def section(title: str) -> None:
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


async def main() -> int:
    test_audio = _resolve_audio()
    server_dir = _resolve_server_dir()

    print(f"Python: {sys.version.split()[0]}")
    print(f"Audio file: {test_audio}")
    print(f"Server dir: {server_dir}")
    print(f"File exists: {test_audio.exists()}, size: "
          f"{test_audio.stat().st_size / (1024*1024):.2f} MiB" if test_audio.exists() else "MISSING")

    # 1) Spawn the MCP server over stdio
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "omni_media_mcp.server"],
        cwd=str(server_dir),
        env={"PYTHONPATH": str(server_dir), "PATH": os.environ.get("PATH", "")},
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            section("[1/4] MCP initialize handshake")
            init_result = await session.initialize()
            print(f"  server_name: {init_result.server_info.name}")
            print(f"  server_version: {init_result.server_info.version}")
            print(f"  protocol_version: {init_result.protocol_version}")

            section("[2/4] List tools exposed by the server")
            tools = await session.list_tools()
            for t in tools.tools:
                print(f"  - {t.name}: {t.description.splitlines()[0][:90]}")

            # ---- Test A: inspect_media ----
            section("[3/4] call_tool inspect_media")
            inspect_result = await session.call_tool(
                "inspect_media",
                arguments={"file_path": str(test_audio)},
            )
            for block in inspect_result.content:
                if hasattr(block, "text"):
                    print(block.text)

            # ---- Test B: read_audio with output_mode=file (recommended) ----
            section("[4/4] call_tool read_audio (output_mode=file)")
            read_result = await session.call_tool(
                "read_audio",
                arguments={
                    "file_path": str(test_audio),
                    "output_mode": "file",
                    # explicitly request a 5-min slice to exercise slicing path
                    "duration_minutes": 5.0,
                },
            )
            for block in read_result.content:
                if hasattr(block, "text"):
                    print(block.text)

    print("\n*** ALL MCP CALLS SUCCEEDED ***")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))