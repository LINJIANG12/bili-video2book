<div align="center">

# 📚 Bili-Video2Book

### Turn Bilibili lectures into readable deep-dive textbooks, chapter-level books, and mindmap study notes in one click.

<p align="center">
  <b>Skip watching hours of video: read 5x faster, search anything instantly, and master every concept with full derivations and built-in practice questions.</b>
</p>

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](LICENSE)
[![Hosts: Antigravity | ChatGPT | OpenAI Codex | Terminal (pip)](https://img.shields.io/badge/Hosts-Antigravity%20%7C%20ChatGPT%20%7C%20Codex%20%7C%20Terminal-111827?style=flat-square)](SKILL.md)
[![Standard: Open Agent Skills](https://img.shields.io/badge/Standard-Open%20Agent%20Skills-blue?style=flat-square)](SKILL.md)
[![AI Engine: Agent-Native Multimodal Dispatch](https://img.shields.io/badge/Engine-Agent--Native%20Multimodal%20Dispatch-8A2BE2?style=flat-square)](#)
[![Deliverables: Triple-Delivery Assets](https://img.shields.io/badge/Deliverables-Triple--Delivery%20Assets-orange?style=flat-square)](#)
[![Tests: 49 passing](https://img.shields.io/badge/Tests-49%20passing-brightgreen?style=flat-square)](#)

**[中文说明](README.md)** &nbsp;·&nbsp; [Why Replace Video](#the-hidden-cost-of-watching-video-is-time-and-unsearchability) &nbsp;·&nbsp; [What It Does](#what-it-does) &nbsp;·&nbsp; [Triple-Delivery Assets](#triple-delivery-matrix-three-distinct-missions) &nbsp;·&nbsp; [8 Note Styles](#8-diverse-note-styles-matrix) &nbsp;·&nbsp; [Two-Tier Architecture](#two-tier-architecture) &nbsp;·&nbsp; [Install](#install) &nbsp;·&nbsp; [How to Use](#how-to-use) &nbsp;·&nbsp; [Design Principles](#design-principles)

</div>

---

## The hidden cost of watching video is time and unsearchability

We watch dozens of hours of university lecture videos and engineering talks because textbooks are often dry and condensed, while lectures contain the instructor's **vivid derivations, real-world pitfall recaps, blackboard calculations, and cognitive metaphors**.

However, watching video as an input medium carries four major inherent bottlenecks:

1. **Extremely Low Information Throughput**: Normal speaking rate is only 150–200 words/minute. Even at 1.5x speed, a 40-hour lecture series drains 26 hours of sitting in front of a screen. In contrast, human reading speed is 800–1200 words/minute—a 4x to 6x efficiency multiplier;
2. **Zero Full-Text Searchability & Painful Revision**: Video is a linear, unsearchable stream. Reviewing a specific formula, configuration parameter, or proof requires minutes of scrub-bar hunting and pause-frame guesswork;
3. **Audio Noise & Cross-Episode Fragmentation**: Microphone adjustments, verbal tics, and narrative cases abruptly severed by class bell intervals;
4. **The "Illusion of Competence" Without Feedback**: Passive audiovisual consumption easily tricks the brain into feeling "I get it," yet once the video closes and an actual exam problem or coding assignment begins, the mind goes blank.

**Bili-Video2Book exists to losslessly reconstruct the derivation, blackboard math, and mental models of long videos into structured, searchable, and self-tested deep-dive articles, modular textbooks, and review mindmaps.**

---

## What it does

**Tens of hours of lectures in, three structured books out.**

Input any Bilibili long video/series URL, local media file (`.mp4`/`.mkv`/`.mov`/`.flv`), or entire local lecture folder. The system extracts lightweight 64kbps voice, applies balanced lossless slicing, enables agent-native multimodal reading, and executes global knowledge block planning to deliver three distinct asset classes:

```text
Traditional video study:
[40h Watching & Listening] ──► Low throughput ➔ Timeline scrub hunting ➔ Unsearchable ➔ Fragmented ➔ No feedback

Bili-Video2Book Triple-Track Reconstruction:
[One-Click Batch Pipeline] ──┬──► 📘 Product A: Deep-Dive Single-Episode Textbooks (articles/, full derivations, strictly preserved)
                             │     └── Complete derivations · Blackboard math · Case closures · Self-test exercises
                             │
                             ├──► 📚 Product C: Modular Chapter Textbooks (textbooks/, newly clustered publishing books)
                             │     └── Seamless chapter transitions · Elimination of repetitive boilerplate · Module summaries
                             │
                             └──► 📑 Product B: Clustered Mindmap Study Notes (notes/, CS-Xmind-Note 408 Exam Tree)
                                   └── Multi-level * list tree · * > Definition single-line quotes · ASCII topologies · Pitfall lists
```

### 🌐 Polymorphic Input Support (Online & Local)
- **Bilibili Online URLs**: Automatic resolution for single videos, multi-part course series, and UGC seasons (with `?p=X` auto-detection);
- **Local Media Files**: Universal 64kbps voice extraction for all major video formats (`.mp4`, `.mkv`, `.mov`, `.avi`, `.flv`, `.webm`, `.ts`, etc.);
- **Local Course Directories**: Pass an entire directory of lecture videos—the engine automatically applies natural sorting (e.g. `01, 02`, `Part1, Part2`) to order P01..Pn, then runs the full batch extraction, in-depth article generation, chapter textbook integration, and module mindmap synthesis!

### Strict Closed-Book Grounding (Anti-Hallucination)
- **Video content as sole source of truth**: Strictly forbids hallucinating unmentioned examples, figures, statistics, jargon, or conclusions;
- **Explicit gaps, faithful preservation**: Explicitly writes *"Not mentioned in video"* whenever details are absent, preserving the speaker's authentic metaphors and reasoning path without ungrounded embellishments.

### Agent-Native Transcription Policy (Zero Local Model Weights)
- **No local Whisper model downloads**: Completely eliminates downloading gigabytes of local Whisper model checkpoints, preventing GPU VRAM exhaustion and complex environment failures;
- **Lightweight audio extraction**: Fast 64kbps audio extraction and 10-minute lossless stream-copy chunking via system FFmpeg, dispatched directly to host dialogue models (Antigravity, ChatGPT, Codex, etc.).

---

## Triple-Delivery Matrix: Three Distinct Missions

| Asset | Reader is | Core Characteristics (Must have) | Redlines (Must NOT have) |
| :--- | :--- | :--- | :--- |
| 📘 **Single-Episode Deep-Dive**<br>`articles/` | **In-depth learning**<br>(Completely replaces watching the video) | Exhaustive derivation steps, blackboard discrete math & proofs, case lifecycle, **2–3 end-of-article self-test questions with grounded explanations** | Summarized skips, filler words, audiovisual phrasing ("as we see on screen"), ungrounded external hallucinations.<br>⚠️ **Strictly preserved during module integration, never deleted!** |
| 📚 **Modular Chapter Textbook**<br>`textbooks/` | **Comprehensive chapter study**<br>(Publishing-grade volume) | Clustered multi-episode knowledge blocks, formal chapter hierarchy, **smooth transition bridges connecting subtopics**, module synthesis and takeaways | Simple mechanical concatenation of single articles, stripping away derivation depth or architecture diagrams |
| 📑 **Clustered Mindmap Note**<br>`notes/` | **Revision / Rapid Lookup**<br>(High-density Cheatsheet) | **Aligned with SSHeRun/CS-Xmind-Note 408 Exam Tree**: ASCII topology tree, pure multi-level `*` list indentation, `* > Definition: ...` single-line quotes, **adaptive comparison matrices**, anti-pattern checklists. **1-click import into XMind & VS Code Markmap** | Long narrative prose paragraphs, flat unindented text walls, long exam papers (self-test items placed in dedicated review cards) |

---

## 8 Diverse Note Styles Matrix

Aligned with open-source note design benchmarks, supporting 8 high-density styles (**Xiaohongshu style completely removed; no hardcoded defaults, users are prompted to choose**):

| Key | Style Name | Core Focus & Structural Features | Best For |
| :--- | :--- | :--- | :--- |
| `minimal` | **Minimal** | **SSHeRun/CS-Xmind-Note 408 Exam Tree**: pure multi-level list indentation (`*`), single-line quote definition (`* > Definition: ...`), zero oral noise, native XMind / Markmap rendering | CS exams, rapid review, cheatsheets, interactive mindmaps |
| `detailed` | **Detailed** | Encyclopedic long-form notes: maximum detail preservation, background reasoning, derivations, and step-by-step production code analysis | Self-study, reference manuals, in-depth engineering |
| `academic` | **Academic** | Formal mathematical/logical definitions, system computing models, asymptotic complexity bounds ($O$ / $\Omega$), proof invariants, and literature evolution | CS theory, paper seminars, algorithm analysis |
| `tutorial` | **Tutorial** | Hands-on workshop: prerequisites, step-by-step terminal commands, expected console outputs, and troubleshooting FAQs | Practical projects, environment setups, coding workshops |
| `task_oriented` | **Task-Oriented** | Engineering sprint cards: SMART goal definitions, prerequisite checklists (`- [ ]`), phase action items (Input ➔ Action ➔ Acceptance Criteria), and risk mitigations | Project delivery, team coordination, agile acceptance |
| `business` | **Business** | CTO / Executive briefing: Executive Summary (TL;DR), business pain points, quantitative ROI calculations, SWOT strategic matrices, and compliance roadmaps | Architecture review, technical evaluation, executive reporting |
| `meeting_minutes` | **Meeting Minutes** | Formal minutes: attendee & metadata card, core discussion topics (viewpoints & rationale), formal decisions (`[DEC-xx]`), and Action Items table (Owner & DDL) | Retrospectives, design reviews, requirement alignments |
| `life_journal` | **Life Journal** | Personal essay & philosophy: slice-of-life intro, awakening moments, real-world metaphors for technical concepts, and warm takeaways | Technical essays, blogging, cognitive metaphors |

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
│  5. Module Integrator: cluster-articles textbook compilation (integrator.py) │
│  6. Topic Planner    : Kernel extraction & duration-aware clustering         │
└────────────────────────────────────────────────────────────────────────────┘
                     │ Emits clean text, kernels JSON, and AGENT_TASK.md
                     ▼
┌── 🧠 Synthesis Tier (Host Dialogue Agent · Multimodal Native) ───────┐
│  1. Semantic Rectifier : Literal proofreading with domain hints    │
│  2. In-Depth Articles  : Standalone video-replacement chapters     │
│  3. Chapter Textbooks  : Publishing-grade modular full books       │
│  4. Mindmap Notes      : CS-Xmind-Note tree-structured notes       │
└────────────────────────────────────────────────────────────────────┘
```

---

## Install

Runs as a native Skill in AI Agents or as an independent local CLI tool.

### 1. 🗣️ Ask Your AI Agent (Recommended)
In Antigravity, ChatGPT, or OpenAI Codex:
```text
Install https://github.com/LINJIANG12/bili-video2book as my global skill.
```

> **Codex / Antigravity Hint**:
> - **In-Repo Execution**: Built-in `.agents/skills/bili-video2book`. Run `$bili-video2book` or prompt directly.
> - **Global Setup**: Copy or symlink to `~/.agents/skills/bili-video2book`.

### 2. 🧬 Local Terminal Installation (Terminal / pip)
```bash
git clone https://github.com/LINJIANG12/bili-video2book.git
cd bili-video2book

# Install as global CLI tool (editable mode)
pip install -e .

# System dependency for fast lossless audio slicing:
# Ensure ffmpeg is installed and available in system PATH
```

---

## How to use

Run `bili-video2book` anywhere or `python src/cli.py` in-repo:

### Scenario 1: Full-Course Automated Pipeline
```bash
# Online Bilibili course
bili-video2book pipeline "https://www.bilibili.com/video/BV14VqVBrEhc" --all

# Local multi-episode directory
bili-video2book pipeline "D:\videos\Software_Engineering_Course\" --all
```

### Scenario 2: Process Specific Part or Range
```bash
# Process episode 1
bili-video2book pipeline "https://www.bilibili.com/video/BV14VqVBrEhc" --page 1

# Process episodes 2 to 5
bili-video2book pipeline "https://www.bilibili.com/video/BV14VqVBrEhc" --range 2-5
```

### Scenario 3: Consolidate Chapter Textbooks (New `textbooks/` Asset)
```bash
# Compiles single articles in articles/ into publishing-grade chapter textbooks
# Discipline: Original articles in articles/ are strictly preserved without deletion!
bili-video2book cluster-articles "https://www.bilibili.com/video/BV14VqVBrEhc"
```

### Scenario 4: Generate Clustered Mindmap Notes (Pick Style)
```bash
# Minimal style (SSHeRun/CS-Xmind-Note 408 Exam Tree)
bili-video2book cluster-notes "https://www.bilibili.com/video/BV14VqVBrEhc" --style minimal

# Detailed encyclopedic style
bili-video2book cluster-notes "https://www.bilibili.com/video/BV14VqVBrEhc" --style detailed

# Omit --style to view interactive selection prompt
bili-video2book cluster-notes "https://www.bilibili.com/video/BV14VqVBrEhc"
```

### Scenario 5: Transcribe Local Media File
```bash
bili-video2book transcribe "lecture.mp4"
```

---

## Real Workspace Layout

```text
output/【公开课】浙江大学：软件工程 陈越（全33讲）_BV16g411M7r2/
├── articles/                     # 📘 [Product A] 34 In-Depth Textbooks (Full derivations, strictly preserved)
│   ├── P01_第1讲 软件工程概述-1_精读文章.md
│   ├── P02_第2讲 软件工程概述-2_精读文章.md
│   └── ... (All 34 episodes with self-test questions & grounded solutions)
├── textbooks/                    # 📚 [Product C] 14 Modular Chapter Textbooks (Publishing-grade books)
│   ├── 模块01_软件工程导论与学科范式_精读全书.md       (P01~P02 consolidated with transition bridges)
│   ├── 模块02_软件过程模型体系与演进_精读全书.md       (P03~P05 consolidated)
│   └── ... (14 cohesive chapter volumes)
├── notes/                        # 📑 [Product B] 14 Clustered Mindmap Notes (CS-Xmind-Note 408 Tree)
│   ├── 模块01_软件工程导论与学科范式_P01-P02_笔记.md  (Multi-level * tree, single-line quotes, matrices)
│   ├── 模块02_软件过程模型体系与演进_P03-P05_笔记.md
│   └── ... (1-click rendering in XMind / VS Code Markmap)
├── subtitles/                    # 📝 Clean transcripts & kernel atoms JSON
│   ├── P01_第1讲 软件工程概述-1_clean.txt
│   └── kernels/
├── audio/                        # 🎵 64kbps pure voice audio archives
├── topic_plan.json               # 🗺️ Duration-aware knowledge block cluster plan
└── manifest.json                 # 📋 Task lifecycle manifest (relative paths, portable)
```

---

## Design principles

- **Derivations matter, fully replace the video**: Refuse superficial 500-word summaries; write thorough long-form chapters preserving blackboard steps;
- **Grounding as the single source of truth**: Forbid external hallucinations; write *"Not mentioned in video"* when absent;
- **Zero local model downloads**: Strictly adhere to the agent-native dispatch architecture, delegating heavy transcription to multimodal host models;
- **Triple-delivery assets for distinct study phases**: `articles/` for deep study, `textbooks/` for chapter mastery, `notes/` for exam review;
- **Textbook integration never deletes single articles**: Single-episode articles in `articles/` remain 100% intact;
- **8 customizable note styles**: Minimal style matches the CS-Xmind-Note 408 tree, eliminating oral fluff;
- **Closed-loop exercises with grounded solutions**: Practice questions with verifiable reasoning chains.

---

## License

Open-sourced under the [MIT License](LICENSE). Contributions, issues, and PRs are warmly welcomed!
