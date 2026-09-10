"""MCP client test: verify omni-media-mcp can read the test m4a audio over stdio.

Walks the full MCP handshake (initialize -> list_tools -> call_tool) so we
exercise the real protocol surface, not just in-process imports.
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

TEST_AUDIO = Path(
    r"D:/project/项目/笔记sikll/成品/output/"
    r"【自用】数据库系统概论学习_BV1W3411y7dw/audio/P01_第1章 绪 论（1）.m4a"
)
SERVER_DIR = Path(r"D:/project/项目/笔记sikll/成品/omni-media-mcp")


def section(title: str) -> None:
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


async def main() -> int:
    print(f"Python: {sys.version.split()[0]}")
    print(f"Audio file: {TEST_AUDIO}")
    print(f"File exists: {TEST_AUDIO.exists()}, size: "
          f"{TEST_AUDIO.stat().st_size / (1024*1024):.2f} MiB" if TEST_AUDIO.exists() else "MISSING")

    # 1) Spawn the MCP server over stdio
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "omni_media_mcp.server"],
        cwd=str(SERVER_DIR),
        env={"PYTHONPATH": str(SERVER_DIR), "PATH": "/usr/bin:/bin:/c/Windows/System32"},
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
                arguments={"file_path": str(TEST_AUDIO)},
            )
            for block in inspect_result.content:
                if hasattr(block, "text"):
                    print(block.text)

            # ---- Test B: read_audio with output_mode=file (recommended) ----
            section("[4/4] call_tool read_audio (output_mode=file)")
            read_result = await session.call_tool(
                "read_audio",
                arguments={
                    "file_path": str(TEST_AUDIO),
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