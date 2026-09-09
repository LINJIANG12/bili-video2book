<div align="center">

# 📚 Bili-Video2Book

### Turn Bilibili lectures into readable deep-dive textbooks and study notes in one click.

<p align="center">
  <b>Skip watching hours of video: read 5x faster, search anything instantly, and master every concept with full derivations and built-in practice questions.</b>
</p>

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](LICENSE)
[![Hosts: Antigravity | ChatGPT | OpenAI Codex | Terminal (pip)](https://img.shields.io/badge/Hosts-Antigravity%20%7C%20ChatGPT%20%7C%20Codex%20%7C%20Terminal-111827?style=flat-square)](SKILL.md)
[![Standard: Open Agent Skills](https://img.shields.io/badge/Standard-Open%20Agent%20Skills-blue?style=flat-square)](SKILL.md)
[![AI Engine: Plan A Native Audio (Antigravity/ChatGPT)](https://img.shields.io/badge/Engine-Plan%20A%20Native%20Audio(Antigravity%2FChatGPT)-8A2BE2?style=flat-square)](#)
[![Tests: 49 passing](https://img.shields.io/badge/Tests-49%20passing-brightgreen?style=flat-square)](#)

**[中文说明](README.md)** &nbsp;·&nbsp; [Why Replace Video](#the-hidden-cost-of-watching-video-is-time-and-unsearchability) &nbsp;·&nbsp; [What It Does](#what-it-does) &nbsp;·&nbsp; [Two Deliverable Forms](#two-distinct-forms-two-different-missions) &nbsp;·&nbsp; [Install](#install) &nbsp;·&nbsp; [How to Use](#how-to-use) &nbsp;·&nbsp; [Design Principles](#design-principles)

</div>

---

## The hidden cost of watching video is time and unsearchability

We watch dozens of hours of university lecture videos and engineering talks because textbooks are often dry and condensed, while lectures contain the instructor's **vivid derivations, real-world pitfall recaps, blackboard calculations, and cognitive metaphors**.

However, watching video as an input medium carries four major inherent bottlenecks:

1. **Extremely Low Information Throughput**: Normal speaking rate is only 150–200 words/minute. Even at 1.5x speed, a 40-hour lecture series drains 26 hours of sitting in front of a screen. In contrast, human reading speed is 800–1200 words/minute—a 4x to 6x efficiency multiplier;
2. **Zero Full-Text Searchability & Painful Revision**: Video is a linear, unsearchable stream. Reviewing a specific formula, configuration parameter, or proof requires minutes of scrub-bar hunting and pause-frame guesswork;
3. **Audio Noise & Cross-Episode Fragmentation**: Microphone adjustments, verbal tics, and narrative cases abruptly severed by class bell intervals;
4. **The "Illusion of Competence" Without Feedback**: Passive audiovisual consumption easily tricks the brain into feeling "I get it," yet once the video closes and an actual exam problem or coding assignment begins, the mind goes blank.

**Bili-Video2Book exists to losslessly reconstruct the derivation, examples, and mental models of long videos into structured, searchable, and self-tested study articles and review notes.**

---

## What it does

**Tens of hours of lectures in, two structured books out.**

Input any Bilibili long video/series URL, local media file (`.mp4`/`.mkv`/`.mov`/`.flv`), or entire local lecture folder. The system extracts lightweight 64kbps human voice, applies balanced lossless slicing, enables multimodal transcription, and performs global knowledge block planning to deliver two distinct deliverables:

```text
Traditional video study:
[40h Watching & Listening] ──► Low throughput ➔ Timeline scrub hunting ➔ Unsearchable ➔ Fragmented ➔ No feedback

Bili-Video2Book pipeline:
[One-Click Reconstruction] ──┬──► 📘 9 In-Depth Single-Episode Textbooks (~150k words, articles/)
                             │     └── Full derivations · Blackboard steps · Case closures · Self-test exercises
                             │
                             └──► 📑 6 Clustered Knowledge Block Notes (High-density Cheatsheets, notes/)
                                   └── ASCII topologies · Merged ontologies (> Source: Pxx) · Comparative matrices · Pitfalls
```

### 🌐 Polymorphic Input Support (Online & Local)
- **Bilibili Online URLs**: Automatic resolution for single videos, multi-part course series, and UGC seasons (with `?p=X` auto-detection);
- **Local Media Files**: Universal 64kbps voice extraction for all major video formats (`.mp4`, `.mkv`, `.mov`, `.avi`, `.flv`, `.webm`, `.ts`, etc.);
- **Local Course Directories**: Pass an entire directory of lecture videos—the engine automatically applies natural sorting (e.g. `01, 02`, `Part1, Part2`) to order P01..Pn, then runs the full batch extraction, in-depth article generation, and module review synthesis!

### Strict Closed-Book Grounding (Anti-Hallucination)
- **Video content as sole source of truth**: Strictly forbids hallucinating unmentioned examples, figures, statistics, jargon, or conclusions;
- **Explicit gaps, faithful preservation**: Explicitly writes *"Not mentioned in video"* whenever details are absent, preserving the speaker's authentic metaphors and reasoning path without ungrounded embellishments.

---

## Two distinct forms, two different missions

Tailored for the contrasting cognitive requirements between first-time in-depth learning and rapid exam revision:

| Form | Reader is | Must have | Must **NOT** have |
| :--- | :--- | :--- | :--- |
| 📘 **Deep-Dive Article**<br>`articles/` | **In-depth learning**<br>(Completely replaces watching the video) | Exhaustive derivation steps, blackboard discrete math & proofs, case lifecycle, **2–3 end-of-article self-test questions with grounded explanations** | Summarized skips, filler words, audiovisual phrasing ("as we see on screen"), ungrounded external hallucinations |
| 📑 **Review Cheatsheet**<br>`notes/` | **Revision / Rapid Lookup**<br>(High-density Cheatsheet) | **Opening ASCII knowledge topology tree**, cross-episode ontology merge (annotated `> Source: Pxx`), **adaptive comparison matrices**, anti-pattern checklists | **Narrative case storytelling**, **exam test papers**, forced empty tables without comparable entities |

---

## Two-tier architecture

```text
[ Input Bilibili Video / Course Series URL / Local Video / Course Directory ]
                     │
                     ▼
┌── 🛠️ Tooling Tier (CLI Entry · PipelineCoordinator Domain Service · Local) ─┐
│  1. Topology Parser  : Single/Multi-P & local directory auto-detection       │
│  2. Unified Network  : WBI signing · 412 risk-control retry (http_client)    │
│  3. Audio Stripper   : 64kbps DASH download / Universal FFmpeg extract       │
│  4. Lossless Chunker : 10-minute stream-copy instant segmentation            │
│  5. Pipeline Orchestrator: two-stage flow + resume (pipeline.py)             │
│  6. Topic Planner    : Kernel extraction & duration-aware clustering         │
└────────────────────────────────────────────────────────────────────────────┘
                     │ Emits clean text, kernels JSON, and AGENT_TASK.md
                     ▼
┌── 🧠 Synthesis Tier (Host Dialogue Agent · Multimodal Native) ───────┐
│  1. Semantic Rectifier : Literal proofreading with domain hints    │
│  2. In-Depth Articles  : Standalone video-replacement chapters     │
│  3. Review Cheatsheets : Cross-episode ontology merge & topologies │
└────────────────────────────────────────────────────────────────────┘
```

---

## Install

Use directly as a native Agent Skill, or run as a standalone local CLI tool.

### 1. 🗣️ Ask your Agent (Recommended)
Paste this into Antigravity, ChatGPT, or OpenAI Codex:
```text
Install https://github.com/LINJIANG12/bili-video2book as my global skill.
```

> **Note (Codex Standard)**:
> - **In-Repo Execution**: This repository provides `.agents/skills/bili-video2book`. In Codex CLI or Open Agent Skills supported tools, trigger directly via `$bili-video2book` or plain prompt.
> - **Global Usage**: Symlink or copy this repository to `~/.agents/skills/bili-video2book`.

### 2. 🧬 Local Install & Terminal CLI (pip)
```bash
git clone https://github.com/LINJIANG12/bili-video2book.git
cd bili-video2book

# Optional: Install globally as terminal CLI command (usable anywhere)
pip install -e .

# System dependency (for lossless fast audio extraction and remux):
# Ensure ffmpeg is available in your system PATH

# Zero third-party Python dependency: Pure Python Standard Library implementation!
```

---

## How to use

If installed via `pip install -e .`, use `bili-video2book` directly from any working directory. Or run `python src/cli.py` in repo root:

### Scenario 1: One-click Full Course Pipeline (Bilibili or Local Folder)
```bash
# Bilibili course
bili-video2book pipeline "https://www.bilibili.com/video/BV14VqVBrEhc" --all

# Local video course folder (auto natural sort P01..Pn, batch transcription & module notes)
bili-video2book pipeline "D:\videos\Database_Course\" --all
```

### Scenario 2: Process a Single Episode or Range
```bash
# Process episode 1
python src/cli.py pipeline "https://www.bilibili.com/video/BV14VqVBrEhc" --page 1

# Process single local video file
python src/cli.py pipeline "D:\videos\lecture01.mp4"

# Process episode range 2 through 5
python src/cli.py pipeline "https://www.bilibili.com/video/BV14VqVBrEhc" --range 2-5
```

### Scenario 3: Cluster and Re-synthesize Knowledge Blocks Only
```bash
python src/cli.py cluster-notes "https://www.bilibili.com/video/BV14VqVBrEhc" --replace
```

### Scenario 4: Transcribe Local Video or Audio Directly
```bash
# Automatically strips 64k audio from any video container (.mp4, .mkv, .mov, etc.).
# Cached clean transcript => reused; otherwise a TRANSCRIBE_TASK is exported for the dialogue model (sole path).
python src/cli.py transcribe "lecture.mp4"
python src/cli.py transcribe "lecture.m4a"
```

---

## Real-world task workspace

Every task is strictly encapsulated in an isolated sandbox directory:

```text
output/【Database Course】Final_Sprint_BV14VqVBrEhc/
├── articles/                     # 📘 9 standalone deep-dive articles (~15k chars each, with self-tests)
│   ├── P01_Introduction_article.md
│   ├── P02_Relational_Algebra_article.md
│   └── ...
├── notes/                        # 📑 6 synthesized review notes (High-density Cheatsheets)
│   ├── Module01_Database_Intro_P01-P02_notes.md
│   ├── Module02_SQL_Core_Syntax_P03_notes.md
│   └── ...
├── subtitles/                    # 📝 Raw & normalized transcripts + knowledge kernel JSONs
│   ├── P01_Introduction_clean.txt
│   └── kernels/
├── audio/                        # 🎵 64kbps voice audio archives
├── topic_plan.json               # 🗺️ Cross-episode semantic clustering map (duration-aware)
└── manifest.json                 # 📋 Task metadata & pipeline log (relative paths, portable)
```

---

## Design principles

- **Text must completely replace long video.** Refuse shallow 500-word summaries; preserve the instructor's derivations, calculations, and metaphors.
- **Strict Grounding as bedrock.** Strictly forbid hallucinating unmentioned examples, figures, concepts, or fabricated cases; preserve original nuance faithfully.
- **Structure follows content.** Reject rigid templates; adaptive comparison matrices generate naturally where comparable entities exist.
- **Eliminate cross-episode fragmentation.** Multi-part lectures are planned globally—concepts scattered across episodes are unified into singular entries.
- **Learning-testing closure.** Tutorial articles conclude with rigorous self-test questions whose reasoning traces 100% back to the text.

---

## License

This project is licensed under the [MIT License](LICENSE).
