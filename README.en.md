<div align="center">

<a name="readme-top"></a>

<h1>Bili-Video2Book</h1>

<p>
  <strong>Batch-transform Bilibili videos and local course media into structured textbooks and review notes.</strong>
  <br />
  <em>Two-stage pipeline · Dual listening channels · Three deliverable tracks · Pre-delivery quality gate · Python 3.8+ standard library only</em>
</p>

<p>
  <a href="#quick-start"><img src="https://img.shields.io/badge/Install-4CAF50?style=for-the-badge" alt="Install" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge" alt="License: MIT" /></a>
</p>

<p>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python_3.8%2B-3776AB?style=flat&logo=python&logoColor=white" alt="Runtime: Python 3.8 or later" /></a>
</p>

<p>
  <a href="https://modelcontextprotocol.io/"><img src="https://img.shields.io/badge/MCP-3178C6?style=flat" alt="Listening channel: Model Context Protocol" /></a>
  <a href="https://docs.anthropic.com/en/docs/claude-code"><img src="https://img.shields.io/badge/Claude_Code-D97757?style=flat&logo=claude&logoColor=white" alt="Host: Claude Code" /></a>
  <a href="https://openai.com/codex/"><img src="https://img.shields.io/badge/Codex-000000?style=flat&logo=openai&logoColor=white" alt="Host: Codex" /></a>
  <a href="https://opencode.ai/"><img src="https://img.shields.io/badge/OpenCode-3178C6?style=flat" alt="Host: OpenCode" /></a>
</p>

<p>
  <a href="README.md">简体中文</a> ·
  <strong>English</strong>
</p>

</div>

> [!CAUTION]
> This tool batch-fetches Bilibili video metadata and audio streams, and can store your login credential. Use it only on content you are entitled to access, and comply with Bilibili's terms of service and applicable law. `SESSDATA` grants access to your account: do not copy, upload or share it.

## Table of Contents

- [What's Inside](#whats-inside)
- [Features](#features)
- [Quick Start](#quick-start)
- [How It Works](#how-it-works)
- [Usage](#usage)
- [Requirements](#requirements)
- [Configuration](#configuration)
- [Project Structure](#project-structure)
- [Commands](#commands)
- [Tech Stack](#tech-stack)
- [Security](#security)
- [License](#license)

## What's Inside

A course passes through three kinds of deliverables on its way from a link to a book, and the toolchain is organised around them.

### Deliverables

| Capability | What it does |
|---|---|
| Per-episode article | One full article per episode, written directly from the listening result |
| Modular book | Consolidates many episode articles into a chaptered book along knowledge boundaries |
| Mindmap notes | Review notes produced by two-pass semantic aggregation |

### Listening channels

| Capability | What it does |
|---|---|
| `read_audio` | Used when the host has an audio modality; requires no credential at all |
| `read_media` | Used when the host is text-only; transcribes through an external service that needs an endpoint configured |

## Features

| Feature | Description |
|---|---|
| One command per course | Give it a collection URL or a local course directory; it writes one article per episode, then consolidates them into a book and notes |
| Works if the host can hear | Hosts with an audio modality use `read_audio` with zero credentials; text-only hosts use `read_media`. Both channels share one pagination contract |
| Three tracks, separate folders | Articles land in `articles/`, modular books in `textbooks/`, notes in `notes/`, each usable on its own |
| Fatal patterns blocked pre-delivery | Boilerplate padding, hollow headings, per-episode headings, inline quote fragments and episode voice fail the gate. Fence language tag is a warning, counted only with `--require-lang` |
| Re-runs fill the gaps | Completed episodes are skipped by default; `--force` reprocesses them |
| No third-party runtime dependencies | Python standard library only, plus system `ffmpeg` |

<div align="right">

[![Back to top][badge-top]](#readme-top)

</div>

## Quick Start

### Prerequisites

```bash
python --version   # 3.8 及以上
ffmpeg -version    # 已加入 PATH
```

### Install

```bash
# 技能本体：复制这一个目录即可
cp -r skills/bili-video2book ~/.claude/skills/            # Claude Code
cp -r skills/bili-video2book ~/.codex/skills/             # Codex
cp -r skills/bili-video2book ~/.config/opencode/skills/   # OpenCode

# 可选：安装 CLI
pip install -e .

# 听音通道：两个音视频 MCP 服务同属配套仓库 omni-media
cd .. && git clone https://github.com/LINJIANG12/omni-media.git
cd omni-media/mcp && pip install -e .                     # 通道 A：宿主原生听音，零凭证
python -m omni_media_mcp.cli status                       # 诊断依赖与各宿主挂载状态
python -m omni_media_mcp.cli apply --target codex         # 写入该宿主的 MCP 配置
```

### Run

```bash
bili-video2book pipeline "https://www.bilibili.com/video/BV14VqVBrEhc" --all --article-type learning
```

Products land under `<products root>/<course workspace>/`: articles in `articles/`, modular books in `textbooks/`, notes in `notes/`.

<div align="right">

[![Back to top][badge-top]](#readme-top)

</div>

## How It Works

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'fontSize': '14px'}}}%%
flowchart TD
    A[Parse and audio extraction<br/>FFmpeg 16kHz mono slices] --> B{Course under 60 minutes}
    B -->|Yes| C[Main agent handles it serially]
    B -->|No| D[Dispatch subagents<br/>one per episode]
    C --> E[Stage 1 listening<br/>read_audio / read_media]
    D --> E
    E --> F[Per-episode articles<br/>articles/]
    F --> G[Stage 2 two-pass aggregation<br/>modules → notes]
    G --> H[Modular books and review notes<br/>textbooks/ · notes/]

    classDef start fill:#3B82F6,stroke:#2563EB,color:#fff,stroke-width:2px
    classDef process fill:#10B981,stroke:#059669,color:#fff,stroke-width:2px
    classDef decision fill:#F59E0B,stroke:#D97706,color:#fff,stroke-width:2px
    classDef data fill:#8B5CF6,stroke:#7C3AED,color:#fff,stroke-width:2px

    class A start
    class C,D,E,F,G process
    class B decision
    class H data
```

- Dispatch thresholds live in `src/core/budget.py`: a course under 60 minutes is handled serially by the main agent, and anything longer is dispatched to subagents, one per episode. When episodes are numerous and short, the tool suggests batching them.
- Stage 1 and stage 2 are decoupled, split on content boundaries, so a long course can also be resumed after an interruption.
- The tool layer produces task files, dispatch payloads and gates; the agent writes the articles and notes.

<div align="right">

[![Back to top][badge-top]](#readme-top)

</div>

## Usage

### Process a whole course

```bash
# B 站合集
bili-video2book pipeline "https://www.bilibili.com/video/BV14VqVBrEhc" --all --article-type learning

# 本地课程目录
bili-video2book pipeline "D:\courses\software_engineering\" --all --article-type learning
```

### Process selected episodes or a range

```bash
bili-video2book pipeline "https://www.bilibili.com/video/BV14VqVBrEhc" --page 1 --article-type learning
bili-video2book pipeline "https://www.bilibili.com/video/BV14VqVBrEhc" --range 2-5 --article-type learning
```

### Build modular books and review notes

```bash
bili-video2book cluster-articles "https://www.bilibili.com/video/BV14VqVBrEhc"
bili-video2book cluster-notes "https://www.bilibili.com/video/BV14VqVBrEhc"
```

### Quality gate and ledger reconciliation

```bash
python scripts/note_quality_check.py --strict      # 笔记成色
python scripts/render_compat_check.py --strict     # 渲染合规
bili-video2book sync                               # 以磁盘产物回填 manifest.json
```

<div align="right">

[![Back to top][badge-top]](#readme-top)

</div>

## Requirements

| Item | Requirement |
|---|---|
| Python | 3.8 or later, from `requires-python` in `pyproject.toml` |
| External binary | `ffmpeg`, on `PATH` |
| Listening channel | one of `read_audio` or `read_media` |
| Operating system | OS independent, per the classifiers in `pyproject.toml` |

<div align="right">

[![Back to top][badge-top]](#readme-top)

</div>

## Configuration

### Environment variables

| Variable | Description | Default | Required |
|---|---|---|---|
| `BVB_HOME` | Container root, the common parent of `skill/`, `omni-media/` and `output/` | located via the `.bvb-home` marker | no |
| `BVB_OUTPUT_DIR` | Products root | `<container root>/output` | no |
| `BVB_AUDIO_TOKENS_PER_SEC` | Audio token coefficient; set `100` for OpenAI pricing | `32` | no |
| `BVB_CONTEXT_WINDOW_TOKENS` | Context window budget | `1000000` | no |
| `OMNI_MEDIA_MCP_DIR` | Override for the host-native listening server directory | `<container root>/omni-media/mcp` | no |
| `BVB_DEBUG` | Set to `1` to re-raise errors with a stack trace | unset | no |

Set environment variables before the process starts. A single run can relocate the products root with `--base-dir <path>`; command-line flags take precedence over environment variables.

<div align="right">

[![Back to top][badge-top]](#readme-top)

</div>

## Project Structure

```
bili-video2book/
├── skills/bili-video2book/     # 技能本体，安装时只需这一个目录
│   ├── SKILL.md                # 技能契约，Agent 的唯一事实源
│   ├── src/                    # 工具链
│   │   ├── cli.py              # 入口：12 个子命令
│   │   ├── core/               # 路径、音频预算、流水线、抓取、交付物质检
│   │   └── generator/          # 任务书、提示词模板与语义聚合
│   ├── scripts/                # 质检、清理、队列跟踪与全量自检
│   └── references/             # 安装说明、交付矩阵、命令速查、工具映射
├── agents/                     # 通用 agents 侧的技能元数据
├── .claude-plugin/             # Claude Code 插件清单
├── .codex-plugin/              # Codex 插件清单
├── .opencode/                  # OpenCode 安装说明
└── pyproject.toml              # 包元数据与 CLI 入口
```

<div align="right">

[![Back to top][badge-top]](#readme-top)

</div>

## Commands

| Command | Description | Example |
|---|---|---|
| `parse` | Parse video topology and list episodes | `bili-video2book parse "<url>" --limit 10` |
| `audio` | Download or extract the audio stream | `bili-video2book audio "<url>" --all` |
| `transcribe` | Export a per-episode article task file, with no intermediate transcript | `bili-video2book transcribe "<url>" --page 1 --article-type learning` |
| `pipeline` | Run the complete pipeline | `bili-video2book pipeline "<url>" --all --article-type learning` |
| `cluster-articles` | Consolidate per-episode articles into modular books | `bili-video2book cluster-articles "<url>"` |
| `cluster-notes` | Two-pass semantic aggregation, exports note task files | `bili-video2book cluster-notes "<url>"` |
| `dedup` | Synchronize duplicate audio assets to save tokens | `bili-video2book dedup --dry-run` |
| `cleanup` | Reclaim completed task files, keeping samples per category | `bili-video2book cleanup --dry-run` |
| `sync` | Reconcile `manifest.json` against on-disk products | `bili-video2book sync --dry-run` |
| `info` | Show environment and toolchain readiness | `bili-video2book info` |
| `login` | Persist a Bilibili SESSDATA cookie | `bili-video2book login --sessdata "<SESSDATA>"` |
| `logout` | Remove the persisted SESSDATA cookie | `bili-video2book logout` |

### Global flags

| Flag | Description | Default |
|---|---|---|
| `--base-dir` | Products root path | `BVB_OUTPUT_DIR` or `<container root>/output` |
| `--task` | Name of the course workspace directory | the most recently active one |
| `--sessdata` | Credential for this run, taking precedence over the saved copy | the saved copy |
| `--json` | Emit JSON, `parse` and `audio` only | off |

### Exit codes

| Code | Meaning |
|---|---|
| `0` | Finished normally |
| `4` | Article prompt style not confirmed, that is `--article-type` is missing or invalid |

<div align="right">

[![Back to top][badge-top]](#readme-top)

</div>

## Tech Stack

### Runtime

| Technology | Purpose |
|---|---|
| Python 3.8+ | The only runtime; standard library only |
| setuptools | Build backend, see `pyproject.toml` |

### External dependencies

| Technology | Purpose |
|---|---|
| FFmpeg | Audio extraction and slicing, 16kHz mono |

### Optional channels

| Technology | Purpose |
|---|---|
| MCP | Protocol of the host-native listening channel |

<div align="right">

[![Back to top][badge-top]](#readme-top)

</div>

## Security

- Credential storage: `login` writes the Bilibili `SESSDATA` cookie as plain text under the products root. Ignore rules exclude the file, so it never enters version control.
- Invalidation: if you suspect a leak, sign out of Bilibili to invalidate the credential, then run `logout` to clear the local copy.
- Access scope: the tool reads public Bilibili video metadata and audio streams, plus the local media files you point it at.
- Reporting: this repository has no `SECURITY.md` yet. Open an issue for security concerns.

<div align="right">

[![Back to top][badge-top]](#readme-top)

</div>

## License

[MIT](LICENSE)

<div align="right">

[![Back to top][badge-top]](#readme-top)

</div>

<!-- LINKS & IMAGES -->

[badge-top]: https://img.shields.io/badge/-BACK_TO_TOP-151515?style=flat-square
[badge-python]: https://img.shields.io/badge/Python_3.8%2B-3776AB?style=flat&logo=python&logoColor=white
[badge-mcp]: https://img.shields.io/badge/MCP-3178C6?style=flat
[badge-claude]: https://img.shields.io/badge/Claude_Code-D97757?style=flat&logo=claude&logoColor=white
[badge-codex]: https://img.shields.io/badge/Codex-000000?style=flat&logo=openai&logoColor=white
[badge-opencode]: https://img.shields.io/badge/OpenCode-3178C6?style=flat
[link-python]: https://www.python.org/
[link-mcp]: https://modelcontextprotocol.io/
[link-claude]: https://docs.anthropic.com/en/docs/claude-code
[link-codex]: https://openai.com/codex/
[link-opencode]: https://opencode.ai/
[link-license]: LICENSE
[link-omni-media]: https://github.com/LINJIANG12/omni-media
