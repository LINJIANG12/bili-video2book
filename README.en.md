<div align="center">

# 📚 Bili-Video2Book

### Turn Bilibili lectures into readable deep-dive textbooks and study notes in one click.

<p align="center">
  <b>Skip watching hours of video: read 5x faster, search anything instantly, and master every concept with full derivations and built-in practice questions.</b>
</p>

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](LICENSE)
[![Hosts: OpenCode | Claude Code | Cursor](https://img.shields.io/badge/Hosts-OpenCode%20%7C%20Claude%20Code%20%7C%20Cursor-111827?style=flat-square)](SKILL.md)
[![AI Engine: Multimodal Native](https://img.shields.io/badge/Engine-Multimodal%20Native%20LLM-8A2BE2?style=flat-square)](#)
[![Fallback: faster-whisper int8](https://img.shields.io/badge/Fallback-faster--whisper%20int8-orange?style=flat-square)](https://github.com/SYSTRAN/faster-whisper)
[![Tests: 34 passing](https://img.shields.io/badge/Tests-34%20passing-brightgreen?style=flat-square)](#)

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

Give it any Bilibili single long video or multi-part lecture series URL. The toolchain handles lightweight audio extraction, lossless chunking, multimodal direct ingestion, and global semantic topic planning, yielding two orthogonal deliverables:

```text
Traditional Video Watching:
[40 hours of streaming] ──► Low throughput ➔ Scrubbing bar ➔ Unsearchable ➔ Fragmented ➔ No test closure

Bili-Video2Book Reconstructed:
[One-click Batch Flow] ──┬──► 📘 Standalone In-Depth Tutorial Articles (articles/)
                         │     └── Full derivations · Blackboard math · End-to-end cases · Self-test questions
                         │
                         └──► 📑 Module Review Cheatsheets (notes/)
                               └── ASCII topologies · Ontology merge (> Source: Pxx) · Adaptive matrices · Anti-patterns
```

### Strict Closed-Book Grounding (Anti-Hallucination)
- Strictly forbids hallucinating modern tech buzzwords, external tech stacks, or corporate systems not mentioned in the transcript;
- Explicitly writes *"Not specified in lecture"* whenever details are absent, preserving the speaker's original metaphors without external embellishments.

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
[ Input Bilibili Video / Course Series URL ]
                     │
                     ▼
┌── 🛠️ Tooling Tier (CLI Pipeline · Pure Local Performance) ────────┐
│  1. Topology Parser : Single/Multi-P/Series & ?p=X parameter detection │
│  2. Lightweight Stream : 64kbps DASH voice-optimized audio download │
│  3. Lossless Chunker : 10-minute stream-copy instant segmentation  │
│  4. Acoustic ASR     : Multimodal dialogue model priority ➔ Local Whisper │
│  5. Topic Planner    : Kernel extraction & topic_plan.json generation │
└────────────────────────────────────────────────────────────────────┘
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

Use directly as a native Agent Skill, or run as a standalone local CLI.

### 1. 🗣️ Ask your Agent (Recommended)
Paste this into OpenCode, Claude Code, or Cursor:
```text
Install https://github.com/LINJIANG12/bili-video2book as my global skill.
```

### 2. 🧬 Git Clone
```bash
git clone https://github.com/LINJIANG12/bili-video2book.git
cd bili-video2book

# System dependency (for lossless fast audio remux):
# Ensure ffmpeg is available in your system PATH

# Optional dependency (for offline local model fallback):
pip install faster-whisper
```

---

## How to use

### Scenario 1: One-click Full Course Pipeline
```bash
python src/cli.py pipeline "https://www.bilibili.com/video/BV14VqVBrEhc" --all
```

### Scenario 2: Process a Single Episode or Range
```bash
# Process episode 1
python src/cli.py pipeline "https://www.bilibili.com/video/BV14VqVBrEhc" --page 1

# Process episode range 2 through 5
python src/cli.py pipeline "https://www.bilibili.com/video/BV14VqVBrEhc" --range 2-5
```

### Scenario 3: Cluster and Re-synthesize Knowledge Blocks Only
```bash
python src/cli.py cluster-notes "https://www.bilibili.com/video/BV14VqVBrEhc" --replace
```

### Scenario 4: Transcribe Local Audio Directly
```bash
python src/cli.py transcribe "lecture.m4a" --engine auto
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
├── topic_plan.json               # 🗺️ Cross-episode semantic clustering map
└── manifest.json                 # 📋 Task metadata and pipeline execution log
```

---

## Design principles

- **Text must completely replace long video.** Refuse shallow 500-word summaries; preserve the instructor's derivations, calculations, and metaphors.
- **Strict Grounding as bedrock.** Strictly forbid hallucinating unmentioned technical concepts or fabricated enterprise systems.
- **Structure follows content.** Reject rigid templates; adaptive comparison matrices generate naturally where comparable entities exist.
- **Eliminate cross-episode fragmentation.** Multi-part lectures are planned globally—concepts scattered across episodes are unified into singular entries.
- **Learning-testing closure.** Tutorial articles conclude with rigorous self-test questions whose reasoning traces 100% back to the text.

---

## License

This project is licensed under the [MIT License](LICENSE).
