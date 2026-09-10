# Bili-Video2Book

Automated pipeline converting Bilibili video courses and local media into structured textbook articles, modular chapter books, and mindmap study notes.

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](LICENSE)
[![Python Version: 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue.svg?style=flat-square)](#)
[![Environment: Antigravity | ChatGPT | Codex | Terminal](https://img.shields.io/badge/Environment-CLI%20%7C%20Agents-111827?style=flat-square)](SKILL.md)

**[中文文档](README.md)** &nbsp;·&nbsp; [Features](#features) &nbsp;·&nbsp; [Output Assets](#output-assets) &nbsp;·&nbsp; [Two-Stage Decoupled Pipeline](#two-stage-decoupled-pipeline) &nbsp;·&nbsp; [Installation](#installation) &nbsp;·&nbsp; [CLI Usage](#cli-usage) &nbsp;·&nbsp; [License](#license)

---

## Features

- **Multi-Modal Input**: Supports Bilibili single-episode, multi-episode series, and UGC collections, as well as local media files (`.mp4`, `.mkv`, `.mov`, `.flv`, `.m4a`) and directory-based local courses.
- **Two-Stage Decoupled Pipeline**: Decouples single-episode high-throughput processing from cross-episode modular synthesis. Stage 1 maintains a flat queue with a continuous sliding window pool (5~6 concurrent workers); Stage 2 consolidates modular assets once all episodes finish.
- **Triple-Delivery Structured Assets**: Produces standalone single-episode textbook articles (`articles/`), compiled chapter textbooks (`textbooks/`), and syllabus-aligned mindmap notes (`notes/`).
- **Lightweight & Multimodal Native**: Extracts 64kbps speech audio via FFmpeg and delegates listening directly to multimodal dialogue models. No local Whisper weights required, saving local GPU memory and disk space.
- **Isolated Sandbox Workspaces**: Manages each task in an independent directory with incremental resume support, disk probing, and real-time dynamic queue tracking.

---

## Output Assets

The pipeline delivers three distinct deliverables tailored to different study workflows:

| Deliverable | Storage Path | Use Case | Key Characteristics |
| :--- | :--- | :--- | :--- |
| **Single-Episode Articles** | `output/<task>/articles/` | In-depth self-study replacing long video watching | Step-by-step mathematical and logical derivations, fully annotated code examples, and 2~3 self-test exercises with sourced answers. **Strictly preserved during modular synthesis.** |
| **Modular Chapter Books** | `output/<task>/textbooks/` | Systematic reading across complete chapters | Merges multi-episode articles into cohesive textbooks with transitional bridge paragraphs and topic summaries. |
| **Mindmap Review Notes** | `output/<task>/notes/` | Quick review, exams, and mindmap rendering | Requires an explicit `--style` (no default is set); `minimal` follows the CS-Xmind-Note tree structure (multi-level `*` indentation and single-line `* > Definition:` quotes). Natively supports VS Code Markmap and XMind. |

---

## Two-Stage Decoupled Pipeline

The execution architecture separates single-episode generation from modular consolidation:

```text
[Bilibili URL or Local Course Directory]
                 │
                 ▼
【Preparation: Topology Parsing & Audio Extraction】
  bili-video2book pipeline "<URL or path>" [--all | --range X-Y]
  ├── Parses multi-P topology into parts.json and manifest.json
  └── Downloads and extracts speech audio into audio/ (60min threshold)
                 │
                 ▼
【Stage 1: Global Dynamic Sliding Pipeline】
  Maintains a flat global FIFO queue and saturates the worker pool:
  ├── Concurrency: 5~6 lightweight micro-agents running concurrently
  ├── Sliding Dispatch: Immediate respawn upon completion (probe hit ➔ retire ➔ spawn next)
  ├── Single step: read_audio slice ➔ view_file native listening ➔ author the textbook article (zero intermediate transcript)
  └── Phase Gate: Stage 1 concludes only when 100% of episodes are completed
                 │
                 ▼
【Stage 2: Modular Synthesis & Notes Generation】
  Once all articles/ are ready on disk, consolidates by module boundaries:
  ├── Chapter Textbooks: Calls cluster-articles to produce textbooks/
  ├── Mindmap Notes: Calls cluster-notes --style minimal to produce notes/
  └── Final Delivery: Verifies triple-asset integrity and full index
```

> **Queue Tracker Tool**: Run `python scripts/queue_tracker.py` (supports `--next N`, `--json`, `--summary`) to inspect sliding pool throughput and phase gating in real time.
>
> Step-by-step operating rules (including the Stage-2 three-gate flow and task-file matrix) live in [SKILL.md](SKILL.md); run `python scripts/selfcheck.py` for a self-check.

---

## Installation

### 1. System Dependencies

Audio processing relies on system `ffmpeg`. Ensure it is installed and available in `PATH`:

- **Windows**: `winget install Gyan.FFmpeg`
- **macOS**: `brew install ffmpeg`
- **Linux (Debian/Ubuntu)**: `sudo apt update && sudo apt install -y ffmpeg`

### 2. Install the omni-media MCP Server (required for Stage 1 listening)

Stage 1 uses the MCP tool `omni-media:read_audio` to extract audio slices that the host multimodal model listens to natively.

```bash
cd omni-media-mcp && pip install -e .
python -m omni_media_mcp.cli apply --target zcode
```

> **No API key required**: audio is listened to natively by the host multimodal model. Registration only writes the server command and `PYTHONPATH` — no credentials are involved. The only external dependency is system `ffmpeg`.

### 3. Install as an AI Agent Skill (Recommended)

In Antigravity, ChatGPT, or OpenAI Codex:
```text
Install this repository as my global skill.
```
The repository includes `.agents/skills/bili-video2book` compliant with Open Agent Skills specifications.

### 4. Local CLI Installation

```bash
git clone https://github.com/LINJIANG12/bili-video2book.git
cd bili-video2book

# Optional: install as global command
pip install -e .
```

---

## CLI Usage

If installed via `pip install -e .`, use `bili-video2book` directly; or run `python src/cli.py` in the repository root:

### Scenario 1: Full Course Pipeline
```bash
# Process complete Bilibili course
bili-video2book pipeline "https://www.bilibili.com/video/BV14VqVBrEhc" --all

# Process local directory course
bili-video2book pipeline "D:\courses\software_engineering\" --all
```

### Scenario 2: Specific Episodes or Range
```bash
# Process episode 1
bili-video2book pipeline "https://www.bilibili.com/video/BV14VqVBrEhc" --page 1

# Process episodes 2 to 5
bili-video2book pipeline "https://www.bilibili.com/video/BV14VqVBrEhc" --range 2-5
```

### Scenario 3: Generate Modular Chapter Books
After Stage 1 articles are generated:
```bash
bili-video2book cluster-articles "https://www.bilibili.com/video/BV14VqVBrEhc"
```

### Scenario 4: Generate Mindmap Review Notes
```bash
# Minimal tree style (recommended for review and Markmap rendering)
bili-video2book cluster-notes "https://www.bilibili.com/video/BV14VqVBrEhc" --style minimal

# Detailed comprehensive style
bili-video2book cluster-notes "https://www.bilibili.com/video/BV14VqVBrEhc" --style detailed
```

### Scenario 5: Inspect Dynamic Queue Status
```bash
# Check current progress and phase gate status
python scripts/queue_tracker.py

# Retrieve next 5 pending episodes and file targets
python scripts/queue_tracker.py --next 5
```

---

## Bilibili SESSDATA Configuration

For large multi-P courses, providing a login cookie prevents HTTP 412 rate-limiting:

1. Log in to bilibili.com in your browser;
2. Press `F12` -> Application -> Cookies -> `https://www.bilibili.com`;
3. Copy the value of the `SESSDATA` entry;
4. Pick either usage:

```bash
# Option 1: one-off (applies to this run only)
bili-video2book pipeline "<url>" --all --sessdata "<SESSDATA>"

# Option 2: persist it once (recommended; later commands need no --sessdata)
python src/cli.py login --sessdata "<SESSDATA>"
bili-video2book pipeline "<url>" --all
python src/cli.py info     # show credential source and masked fingerprint
python src/cli.py logout   # remove the stored credential
```

> **Security note**: the persisted credential is stored in plaintext at `output/.sessdata.json`, which is excluded by `.gitignore` and never enters version control; an explicit `--sessdata` argument always takes precedence over the stored value. SESSDATA is equivalent to your Bilibili login session — never copy, upload, or share that file.

---

## License

This project is licensed under the [MIT License](LICENSE).
