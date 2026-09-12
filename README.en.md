# Bili-Video2Book

Automated pipeline converting Bilibili video courses and local media into structured textbook articles, modular chapter books, and mindmap study notes.

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](LICENSE)
[![Python Version: 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue.svg?style=flat-square)](#)
[![Environment: Antigravity | ChatGPT | Codex | Terminal](https://img.shields.io/badge/Environment-CLI%20%7C%20Agents-111827?style=flat-square)](SKILL.md)

**[中文文档](README.md)** &nbsp;·&nbsp; [Features](#features) &nbsp;·&nbsp; [Output Assets](#output-assets) &nbsp;·&nbsp; [Two-Stage Decoupled Pipeline](#two-stage-decoupled-pipeline) &nbsp;·&nbsp; [Installation](#installation) &nbsp;·&nbsp; [CLI Usage](#cli-usage) &nbsp;·&nbsp; [License](#license)

---

## Features

- **Multi-Modal Input**: Supports Bilibili single-episode and multi-episode (multi-P) courses, plus local media files (`.mp4`, `.mkv`, `.mov`, `.flv`, `.m4a`) and directory-based local courses. **Cross-BV UGC season traversal is not implemented**: a season link can be inspected with `parse`, but the processed range is the current submission's episodes 1..N — when every season episode is a separate BV, process them one BV at a time.
- **Two-Stage Decoupled Pipeline**: Decouples single-episode article production from cross-episode semantic synthesis. Stage 1's **dispatch discipline** is upheld by the main agent (see the diagram below); the toolchain only supplies payloads, a dispatch log and gates. Stage 2 converges in **two passes** (plan modules, then merge them into notes).
- **Triple-Delivery Structured Assets**: Produces standalone single-episode textbook articles (`articles/`), compiled chapter textbooks (`textbooks/`), and syllabus-aligned mindmap notes (`notes/`).
- **Dual audio channels**: hosts with a native audio modality listen directly (`omni-media`, zero credentials); text-only hosts let an external model read the audio (`omni-media-ext`, Gemini / OpenAI protocols). Both channels share the same pagination contract, so switching is just a tool-name change.
- **Never stuck without a plan**: both semantic plans (`topic_plan.json` / `note_plan.json`) are authored by the agent. Out-of-range, missing or duplicated plans are salvaged in place and the command always exits cleanly; the plan files on disk are never rewritten by the toolchain.
- **Lightweight & Multimodal Native**: Extracts 16 kHz mono speech audio via FFmpeg and delegates listening directly to multimodal dialogue models. No local Whisper weights required, saving local GPU memory and disk space.
- **Isolated Sandbox Workspaces**: Manages each task in an independent directory with incremental resume support, disk probing, and real-time dynamic queue tracking.

---

## Output Assets

The pipeline delivers three distinct deliverables tailored to different study workflows:

| Deliverable | Storage Path | Use Case | Key Characteristics |
| :--- | :--- | :--- | :--- |
| **Single-Episode Articles** | `output/<task>/articles/` | In-depth self-study replacing long video watching | Step-by-step mathematical and logical derivations and fully annotated code examples, written in the chosen article style (`learning` = keeps the lecturer's voice, `legacy` = academic textbook tone with self-tests); **the exercise section is restored only when the lecturer actually mentioned exercises**. **Strictly preserved during modular synthesis.** |
| **Modular Chapter Books** | `output/<task>/textbooks/` | Systematic reading across complete chapters | Merges multi-episode articles into cohesive textbooks with transitional bridge paragraphs and topic summaries. |
| **Mindmap Review Notes** | `output/<task>/notes/` | Quick review, exams, and mindmap rendering | **Re-authored by sub-agents from the source articles** (not stitched from knowledge kernels). Split by the **second-pass merged notes** (one note may span several knowledge modules — **fewer and thicker beats many and scattered**). **A single note style** (the legacy 8-style matrix has been removed, so `--style` is gone): topology tree + topic sections + concept blocks + source marks, **conclusions only (no derivations)**. Natively supports VS Code Markmap and XMind. |

---

## Two-Stage Decoupled Pipeline

The execution architecture separates single-episode generation from cross-episode semantic synthesis:

> The **Stage-1 block below describes the discipline the main agent must uphold — it is not a machine
> architecture**. The queue, worker slots and sliding dispatch are maintained by the main agent; the toolchain
> only prepares payloads, records a dispatch log and evaluates gates, and it **cannot verify** who wrote what
> or whether the audio was really listened to (see [SKILL.md](SKILL.md) § 4.5).

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
【Stage 1: Dispatch Loop + Global Dynamic Sliding Pipeline】(main-agent discipline; the toolchain only observes)
  The main agent keeps its own pending-task queue and saturates the worker pool:
  ├── Dispatch rule: **total course length ≤ 60 minutes → the main agent may do it serially;
  │                  longer than 60 minutes → dispatch is mandatory**
  │                  (one sub-agent per episode by default; batch 3~5 episodes when ≥15 episodes and ≤40k tokens each)
  ├── Payload: `queue_tracker.py --next 5 --json --log-dispatch` (task file / slices / target article / per-episode budget)
  ├── Concurrency: the main agent keeps 5~6 sub-agent slots running (`SUGGEST_WORKERS` in `--summary` is advice)
  ├── Sliding Dispatch: the main agent respawns immediately upon completion (probe hit ➔ retire ➔ spawn next)
  ├── Single step: obtain the audio facts by whichever channel the host supports, then author the article directly
  │                · has read_audio (native audio): read_audio slices ➔ view_file native listening
  │                · only read_media (no native audio): read_media external transcription
  │                each sub-agent reports one line `P07 | path | bytes | executor` and never returns the article body
  └── Phase Gate: Stage 1 concludes only when 100% of episodes are completed (`STAGE1_DONE=1`)
                 │
                 ▼
【Stage 2: Two-Pass Semantic Aggregation (modules ➔ notes) + textbook integration】
  Once all articles/ are ready on disk, plan modules first and then merge them into notes:
  ├── ① Modules: cluster-notes exports topic_plan_TASK.md ➔ agent writes topic_plan.json (consumed by textbooks)
  ├── ② Merging: it also exports note_plan_TASK.md ➔ agent writes note_plan.json (one note may span modules)
  │        · a missing plan never stalls the run: out-of-range blocks are clipped, unclaimed episodes become
  │          placeholders, and a missing plan falls back to a coarse split
  ├── ③ Dispatch: exports notes/笔记XX_*_TASK.md per note (dedicated prompt + the article paths it covers)
  │        ➔ the main agent dispatches one sub-agent per note; each reads every covered article and writes the note
  ├── ④ Textbooks: cluster-articles consolidates articles/ into textbooks/ per module
  ├── Quality gates: note_quality_check.py (note standards) + render_compat_check.py (Typora rendering)
  └── Housekeeping: cleanup reclaims task-files (one prompt sample kept) + sync reconciles manifest.json
```

> **Queue Tracker Tool**: Run `python scripts/queue_tracker.py` (supports `--next N`, `--json`, `--summary`) to inspect sliding pool throughput and phase gating in real time.
>
> **Pre-delivery gates**: `python scripts/note_quality_check.py --strict` turns "boilerplate filler / hollow container headings / per-episode headings / broken inline quotes / episode voice" (all gating) plus "truncation / missing structure" (advisory) into recomputable metrics; `python scripts/render_compat_check.py --strict` gates GitHub alert blocks, bare ASCII art outside fences and fence pairing, while **missing fence language tags stay advisory unless you add `--require-lang`**.
>
> Step-by-step operating rules (including the Stage-2 gate flow, sub-agent dispatch rules and task-file matrix) live in [SKILL.md](SKILL.md); run `python scripts/selfcheck.py` for a self-check.

---

## Repository Layout (four isolated domains)

The project is split by **responsibility** into four domains that never interfere with each other — code, two MCP
servers and products each live in their own place, so upgrading or relocating one never touches the others:

```text
<container root>/
├── skill/     ← this repository: the skill & toolchain (SKILL.md, src/, scripts/, references/, .agents/)
├── mcp/       ← separate repository: the omni-media MCP (host-native listening via read_audio, fully local, zero credentials)
├── mcp-ext/   ← separate directory: the omni-media-ext MCP (external-model transcription via read_media, Gemini / OpenAI protocols, reads config.json)
└── output/    ← products root: one workspace per course + .sessdata.json / .wbi_keys.json / .cli_status.json
```

- **Independent repositories/directories** (`skill/` and `mcp/` each keep their own `.git`) that can be cloned,
  upgraded and released separately; the MCP never imports skill code and the skill never imports MCP code
  (enforced by `selfcheck`, which only probes with `find_spec`);
- **Products always live outside the code**: they can never show up in `git status`, and removing/relocating a repo
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

### 2. Install an audio MCP server (required for Stage 1 audio intake — pick one)

Stage 1 offers **two channels**, chosen by whether the host model has a native audio modality
(the pagination contract is identical, so switching means changing only the tool name):

| Channel | Host | Tool | Install |
| :--- | :--- | :--- | :--- |
| **A. Host-native listening** | Model has an audio modality (Gemini / GPT-4o Audio / Codex …) | `read_audio` | `mcp/` (own repository, **no API key at all**) |
| **B. External-model delegation** | Text-only hosts | `read_media` | `mcp-ext/` (endpoint + api_key from `config.json`) |

```bash
# Channel A: the host can listen for itself (prefer this — zero credentials)
cd ../mcp && pip install -e .                        # if not cloned: git clone <omni-media-mcp repo> mcp
python -m omni_media_mcp.cli apply --target zcode    # also: opencode/dsh/codex/antigravity/all
python selfcheck.py                                  # optional: MCP-side self-check

# Channel B: the host cannot listen to audio (an external model reads it instead)
cd ../mcp-ext && pip install -e .                    # if not installed yet
python -m omni_media_ext.cli config --init           # create config.json, fill in endpoint + api_key
python -m omni_media_ext.cli status --probe          # env + config + endpoint reachability + which one to mount
python -m omni_media_ext.cli apply --target zcode
python selfcheck.py                                  # optional: this version's self-check (incl. compatibility contract)
```

> **Channel A needs no API key**: audio is listened to natively by the host multimodal model; registration only writes the
> server command and `PYTHONPATH`. The only external dependency is system `ffmpeg`. **Channel B** keeps its credentials in
> `mcp-ext/config.json` (git-ignored) and never writes them into host configuration.
>
> Both services can be mounted **at the same time** (registration keys `omni-media` / `omni-media-ext` never overwrite each
> other). When both are present the agent prefers `read_audio`, falling back to `read_media` for `summarize` / `qa`-style
> processing. See `SKILL.md` §4.2 and the container-root README for the full rule.

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
bili-video2book pipeline "https://www.bilibili.com/video/BV14VqVBrEhc" --all --article-type learning

# Process local directory course
bili-video2book pipeline "D:\courses\software_engineering\" --all --article-type learning
```

### Scenario 2: Specific Episodes or Range
```bash
# Process episode 1
bili-video2book pipeline "https://www.bilibili.com/video/BV14VqVBrEhc" --page 1 --article-type learning

# Process episodes 2 to 5
bili-video2book pipeline "https://www.bilibili.com/video/BV14VqVBrEhc" --range 2-5 --article-type learning
```

### Scenario 3: Generate Modular Chapter Books
After Stage 1 articles are generated:
```bash
bili-video2book cluster-articles "https://www.bilibili.com/video/BV14VqVBrEhc"
```

### Scenario 4: Generate Mindmap Review Notes
```bash
# Review notes: a single note style, so --style is gone.
# Both plans (modules ➔ merged notes) are authored by the agent; a missing plan never stalls the run.
bili-video2book cluster-notes "https://www.bilibili.com/video/BV14VqVBrEhc"

# --force: re-export every note task-file
#          (notes that already exist are reused by default)
bili-video2book cluster-notes "https://www.bilibili.com/video/BV14VqVBrEhc" --force

# --force-plan: re-export both plan task-files (ignore the plans on disk and plan again)
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
> `topic_plan_TASK.md` and `note_plan_TASK.md` are course-level plan task-files and are never reclaimed.

---

## Bilibili SESSDATA Configuration

For large multi-P courses, providing a login cookie prevents HTTP 412 rate-limiting:

1. Log in to bilibili.com in your browser;
2. Press `F12` -> Application -> Cookies -> `https://www.bilibili.com`;
3. Copy the value of the `SESSDATA` entry;
4. Pick either usage:

```bash
# Option 1: one-off (applies to this run only)
bili-video2book pipeline "<url>" --all --article-type learning --sessdata "<SESSDATA>"

# Option 2: persist it once (recommended; later commands need no --sessdata)
python src/cli.py login --sessdata "<SESSDATA>"
bili-video2book pipeline "<url>" --all --article-type learning
python src/cli.py info     # show credential source and masked fingerprint
python src/cli.py logout   # remove the stored credential
```

> **Security note**: the persisted credential is stored in plaintext at `output/.sessdata.json`, which is excluded by `.gitignore` and never enters version control; an explicit `--sessdata` argument always takes precedence over the stored value. SESSDATA is equivalent to your Bilibili login session — never copy, upload, or share that file.

---

## License

This project is licensed under the [MIT License](LICENSE).
