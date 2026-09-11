# Bili-Video2Book

Automated pipeline converting Bilibili video courses and local media into structured textbook articles, modular chapter books, and mindmap study notes.

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](LICENSE)
[![Python Version: 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue.svg?style=flat-square)](#)
[![Environment: Antigravity | ChatGPT | Codex | Terminal](https://img.shields.io/badge/Environment-CLI%20%7C%20Agents-111827?style=flat-square)](SKILL.md)

**[中文文档](README.md)** &nbsp;·&nbsp; [Features](#features) &nbsp;·&nbsp; [Output Assets](#output-assets) &nbsp;·&nbsp; [Two-Stage Decoupled Pipeline](#two-stage-decoupled-pipeline) &nbsp;·&nbsp; [Installation](#installation) &nbsp;·&nbsp; [CLI Usage](#cli-usage) &nbsp;·&nbsp; [License](#license)

---

## Features

- **Multi-Modal Input**: Supports Bilibili single-episode and multi-episode (multi-P) courses, plus local media files (`.mp4`, `.mkv`, `.mov`, `.flv`, `.m4a`) and directory-based local courses. **Cross-BV UGC season traversal is not implemented**: a season link can be inspected with `parse`, but the processed range is the current submission's episodes 1..N — when every season episode is a separate BV, process them one BV at a time.
- **Two-Stage Decoupled Pipeline**: Decouples single-episode high-throughput processing from cross-episode modular synthesis. Stage 1 maintains a flat queue with a continuous sliding window pool (5~6 concurrent workers); Stage 2 consolidates modular assets once all episodes finish.
- **Triple-Delivery Structured Assets**: Produces standalone single-episode textbook articles (`articles/`), compiled chapter textbooks (`textbooks/`), and syllabus-aligned mindmap notes (`notes/`).
- **Lightweight & Multimodal Native**: Extracts 16 kHz mono speech audio via FFmpeg and delegates listening directly to multimodal dialogue models. No local Whisper weights required, saving local GPU memory and disk space.
- **Isolated Sandbox Workspaces**: Manages each task in an independent directory with incremental resume support, disk probing, and real-time dynamic queue tracking.

---

## Output Assets

The pipeline delivers three distinct deliverables tailored to different study workflows:

| Deliverable | Storage Path | Use Case | Key Characteristics |
| :--- | :--- | :--- | :--- |
| **Single-Episode Articles** | `output/<task>/articles/` | In-depth self-study replacing long video watching | Step-by-step mathematical and logical derivations and fully annotated code examples, written in the chosen article style (`learning` = keeps the lecturer's voice, `legacy` = academic textbook tone with self-tests); **the exercise section is restored only when the lecturer actually mentioned exercises**. **Strictly preserved during modular synthesis.** |
| **Modular Chapter Books** | `output/<task>/textbooks/` | Systematic reading across complete chapters | Merges multi-episode articles into cohesive textbooks with transitional bridge paragraphs and topic summaries. |
| **Mindmap Review Notes** | `output/<task>/notes/` | Quick review, exams, and mindmap rendering | **Re-authored by sub-agents from the module's own single-episode articles** (not stitched from knowledge kernels). **A single note style** (the legacy 8-style matrix has been removed, so `--style` is gone): topology tree + topic sections + concept blocks + source marks, **conclusions only (no derivations)**. Natively supports VS Code Markmap and XMind. |

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
【Stage 2: Modular Synthesis & Notes Generation (two passes)】
  Once all articles/ are ready on disk, consolidates by module boundaries:
  ├── ① Planning: first cluster-notes run exports topic_plan_TASK.md ➔ Agent writes topic_plan.json ➔ re-run
  ├── ② Notes: exports notes/模块XX_*_TASK.md per module (dedicated prompt + the module's article paths)
  │        ➔ the main Agent dispatches one sub-agent per module; each reads every module article and writes the note
  ├── ③ Textbooks: cluster-articles consolidates articles/ into textbooks/
  ├── Quality gates: note_quality_check.py (note standards) + render_compat_check.py (Typora rendering)
  └── Housekeeping: cleanup reclaims task-files (one prompt sample kept) + sync reconciles manifest.json
```

> **Queue Tracker Tool**: Run `python scripts/queue_tracker.py` (supports `--next N`, `--json`, `--summary`) to inspect sliding pool throughput and phase gating in real time.
>
> **Pre-delivery gates**: `python scripts/note_quality_check.py --strict` turns "boilerplate filler / hollow container headings / per-episode headings / broken inline quotes / episode voice" (all gating) plus "truncation / missing structure" (advisory) into recomputable metrics; `python scripts/render_compat_check.py --strict` gates GitHub alert blocks, bare ASCII art outside fences and fence pairing, while **missing fence language tags stay advisory unless you add `--require-lang`**.
>
> Step-by-step operating rules (including the Stage-2 gate flow, sub-agent dispatch rules and task-file matrix) live in [SKILL.md](SKILL.md); run `python scripts/selfcheck.py` for a self-check.

---

## Repository Layout (three isolated domains)

The project is split by **responsibility** into three domains that never interfere with each other — code, MCP server and
products each live in their own place, so upgrading or relocating one never touches the others:

```text
<container root>/
├── skill/     ← this repository: the skill & toolchain (SKILL.md, src/, scripts/, references/, .agents/)
├── mcp/       ← separate repository: the omni-media MCP server (fully local, no runtime dependency on the skill)
└── output/    ← products root: one workspace per course + .sessdata.json / .wbi_keys.json / .cli_status.json
```

- **Two independent repositories** (each with its own `.git`) that can be cloned, upgraded and released separately;
  the MCP never imports skill code and the skill never imports MCP code (enforced by `selfcheck`);
- **Products always live outside both repos**: they can never show up in `git status`, and removing/relocating a repo
  never touches your deliverables;
- **Commands are decoupled from the working directory**: `--base-dir` defaults to the products root (an absolute path),
  so running the CLI from any directory finds the same workspaces. Override it with `--base-dir <path>`, or set
  `BVB_HOME` (container root) / `BVB_OUTPUT_DIR` (products root);
- `python src/cli.py info` prints the resolved code root / container root / products root for confirmation.

---

## Installation

### 1. System Dependencies

Audio processing relies on system `ffmpeg`. Ensure it is installed and available in `PATH`:

- **Windows**: `winget install Gyan.FFmpeg`
- **macOS**: `brew install ffmpeg`
- **Linux (Debian/Ubuntu)**: `sudo apt update && sudo apt install -y ffmpeg`

### 2. Install the omni-media MCP Server (separate repository, required for Stage 1 listening)

Stage 1 uses the MCP tool `omni-media:read_audio` to extract audio slices that the host multimodal model listens to natively.
The MCP ships as its **own repository** (sibling `mcp/`), installed once and upgradable independently:

```bash
cd ../mcp && pip install -e .     # if not cloned yet: git clone <omni-media-mcp repo> mcp
python -m omni_media_mcp.cli apply --target zcode   # also: opencode/dsh/codex/antigravity/all
python selfcheck.py               # optional: MCP-side self-check
```

> **No API key required**: audio is listened to natively by the host multimodal model. Registration only writes the server command and `PYTHONPATH` — no credentials are involved. The only external dependency is system `ffmpeg`.

### 3. Install as an AI Agent Skill (Recommended)

In Antigravity, ChatGPT, or OpenAI Codex:
```text
Install this repository as my global skill.
```
The repository includes `.agents/skills/bili-video2book` compliant with Open Agent Skills specifications.

> **Working-directory contract**: the skill bundle itself only ships `SKILL.md` and `references/`; every command and
> script lives in the repository. When installing globally, keep the **whole repository reachable** (copy or symlink it)
> and run `python src/cli.py …` / `python scripts/…` **from this repository root (`skill/`)**, otherwise the documented
> commands will not resolve.

### 4. Local CLI Installation

```bash
git clone https://github.com/LINJIANG12/bili-video2book.git
cd bili-video2book

# Optional: install as global command
pip install -e .
```

---

## CLI Usage

If installed via `pip install -e .`, use `bili-video2book` directly; or run `python src/cli.py` in this repository root
(`skill/`). All products land in the products root (default `<container root>/output/`), never inside the code
repository; the `output/<task>/…` paths below are relative to that products root.

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
# Module review notes: a single note style, so --style is gone
bili-video2book cluster-notes "https://www.bilibili.com/video/BV14VqVBrEhc"

# --force: re-export every module task-file (modules whose notes already exist are reused by default)
bili-video2book cluster-notes "https://www.bilibili.com/video/BV14VqVBrEhc" --force

# --force-plan: re-export topic_plan_TASK.md (discard the previous module plan and plan again)
bili-video2book cluster-notes "https://www.bilibili.com/video/BV14VqVBrEhc" --force-plan
```

### Scenario 5: Inspect Dynamic Queue Status
```bash
# Check current progress and phase gate status
python scripts/queue_tracker.py

# Retrieve next 5 pending episodes and file targets
python scripts/queue_tracker.py --next 5

# Pick a specific workspace when several courses live side by side
python scripts/queue_tracker.py --pattern "微机原理" --next 5
```

### Scenario 6: Pre-delivery Quality Gates & Housekeeping
```bash
# Note quality gate (fatal: boilerplate / hollow headings / per-episode headings / inline quotes / episode voice;
#                    advisory: truncation, missing structure — add --require-structure to gate them)
python scripts/note_quality_check.py --strict

# Render compatibility gate (fatal: GitHub alert blocks / bare ASCII art / unbalanced fences;
#                            advisory: missing fence language tags — add --require-lang to gate them)
python scripts/render_compat_check.py --strict

# Reclaim dispatch task-files once their products exist (keeps one prompt sample per category)
python src/cli.py cleanup --dry-run
python src/cli.py cleanup

# Reconcile manifest.json with what is actually on disk
python src/cli.py sync

# Optional: cluster-articles reuses existing textbooks/; pass --force to re-integrate from latest articles
python src/cli.py cluster-articles "https://www.bilibili.com/video/BV14VqVBrEhc" --force
```

> **Task-files are transient dispatch artifacts**: `*_TASK.md` is reclaimed by `cleanup` (or at the end of
> `pipeline`) once its product lands, keeping the lowest-numbered sample per category for prompt reference.
> `topic_plan_TASK.md` is never reclaimed.

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
