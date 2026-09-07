<div align="center">

# 📚 Bili-Video2Book

### 把 B 站长视频和系列网课，一键变成能直接当教材读的深度长文与备考笔记

<p align="center">
  <b>完整保留老师讲课的每一步推导、板书演算与核心思路；看文字比刷视频快 5 倍，支持关键词秒搜，文末附带练习题助你真正学懂。</b>
</p>

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](LICENSE)
[![Hosts: OpenCode | Claude Code | Cursor](https://img.shields.io/badge/Hosts-OpenCode%20%7C%20Claude%20Code%20%7C%20Cursor-111827?style=flat-square)](SKILL.md)
[![AI Engine: Multimodal Native](https://img.shields.io/badge/Engine-Gemini%203.8%20Multimodal%20Native-8A2BE2?style=flat-square)](#)
[![Fallback: faster-whisper int8](https://img.shields.io/badge/Fallback-faster--whisper%20int8-orange?style=flat-square)](https://github.com/SYSTRAN/faster-whisper)
[![Tests: 34 passing](https://img.shields.io/badge/Tests-34%20passing-brightgreen?style=flat-square)](#)

**[English](README.md)** &nbsp;·&nbsp; [它解决什么问题](#看视频学知识最大的代价是时间与不可检索) &nbsp;·&nbsp; [它能做什么](#它能做什么) &nbsp;·&nbsp; [两套双轨形态](#两套双轨形态怎么分工) &nbsp;·&nbsp; [安装](#安装) &nbsp;·&nbsp; [怎么用](#怎么用) &nbsp;·&nbsp; [设计原则](#设计原则)

</div>

---

## 看视频学知识，最大的代价是时间与不可检索

我们之所以选择花费几十个小时去刷大学公开课或工程教学视频，是因为纸质教材往往写得过于晦涩，而视频里有主讲人极其生动的**推导演进、真实踩坑经验、黑板离散计算与认知隐喻**。

但“看视频”本身作为一种输入媒介，存在四个天然的致命硬伤：

1. **极低的信息通量与不可控的时间损耗**：人类听觉语速通常只有 150~200 字/分钟，即便开启 1.5 倍速，一门 40 小时的网课也需要枯坐 26 小时；而人类眼睛的阅读速度是 800~1200 字/分钟，信息摄取效率相差 4~6 倍；
2. **不可检索与碎片回溯成本极高**：视频是线性且不可全文搜索的流媒体。考前复习若想查一个公式细节或配置项，必须在数小时的进度条上痛苦地反复拖拽、暂停、截屏；
3. **被迫忍受视听噪音与跨集割裂**：调试麦克风、口头禅、闲聊琐碎，以及因分集下课被强行切断的工程案例；
4. **缺乏即时反馈的“虚假熟练度”**：单向视听输入极易让大脑产生“听懂了”的快感错觉，但真正合上视频动笔做题或实际写代码时，依然大脑一片空白。

**Bili-Video2Book 致力于将视频中具有知识价值的推导演进、真实示例与核心思维模型，无损重构为高效、结构化、可全文检索且具备自学自测闭环的出版级文字资产。**

---

## 它能做什么

**几十小时网课进，两套自洽专著出。**

输入 B 站任意长视频或多 P 连载网课链接，系统自动完成轻量人声音频抓取、无损切片提取、多模态直读与全局知识块规划，交付两套各司其职的双轨产物：

```text
传统看视频学习方式：
[40小时漫长视听] ──► 语速受限 ➔ 进度条反复拖拽 ➔ 无法搜索 ➔ 跨集割裂 ➔ 无检验闭环

Bili-Video2Book 重构方式：
[一键批量重构] ──┬──► 📘 9 篇单集精读教材长文（约 15 万字，articles/）
                 │     └── 全量推导 · 真实黑板运算 · 案例闭环 · 随堂自测(带正文溯源解析)
                 │
                 └──► 📑 6 大模块复习速查笔记（高密度 Cheatsheet，notes/）
                       └── ASCII 拓扑框架 · 概念本体融合(打标 > 来源: Pxx) · 自适应对比矩阵 · 避坑清单
```

### 严格闭卷事实边界（Strict Grounding）
本项目全流程贯彻“闭卷保真”防幻觉机制：
- 严禁脑补转录未出现的现代大厂流行词或虚构外部系统；
- 语料中未说明的地方明确写明“课程未说明”，保留讲述者原汁原味的比喻与表达方式。

---

## 两套双轨形态怎么分工

针对读者在自学阶段与复习阶段截然不同的认知诉求，两套交付物严格遵循不同的**内容纪律**与**排版规范**：

| 文体形态 | 读者此刻在 | 必须包含（Must have） | 坚决不能有（Must NOT have） |
| :--- | :--- | :--- | :--- |
| 📘 **精读教材长文**<br>`articles/` | **系统深入自学**<br>（彻底替代原长视频） | 详尽推导步骤、黑板离散计算与证明、案例前因后果、**文末 2~3 道紧扣核心考点的深度自测题（附带可在正文溯源的详细解析）** | 概括性跳步、口水碎语、“视频中我们看到”等视听口吻、外部事实虚构脑补 |
| 📑 **模块速查笔记**<br>`notes/` | **考前突击 / 检索查阅**<br>（高密度 Cheatsheet） | **开篇 ASCII 知识拓扑框架树**、跨集概念本体深度融合（打标 `> 来源: Pxx` 方便回溯）、**自适应横向对比矩阵**、常见反模式避坑清单 | **长篇大论的案例叙述**、**自测试卷练习题**、无对比要素时的强行空白表格 |

---

## 双层协同架构

```text
[ 输入 B 站任意长视频 / 连载网课链接 ]
                 │
                 ▼
┌── 🛠️ 工具层 (CLI 管道 · 纯本地极速) ──────────────────────────────┐
│  1. 拓扑解析  : 单P/多P/合集识别与 ?p=X 分P参数自动嗅探 (parser.py)    │
│  2. 轻量抓取  : 64kbps DASH 纯净人声音频流直取 (fetcher.py + wbi.py) │
│  3. 均衡切片  : 10 分钟无损流拷贝瞬间切片 (audio_chunker.py)          │
│  4. 声学转录  : 优先对话模型多模态直读 ➔ 经授权回退本地 Whisper      │
│  5. 语义规划  : 提取高纯度知识元并生成全局 topic_plan.json (planner.py) │
└───────────────────────────────────────────────────────────────────────┘
                 │ 导出规范化语料、知识元原子与 Agent 任务书
                 ▼
┌── 🧠 智能合成层 (宿主对话大模型 · Gemini 3.8 Flash High) ───────────┐
│  1. 语义校对  : 依据领域线索纯字面纠偏（只改字，不改话）              │
│  2. 精读长文  : 撰写单集教材级深度自学长文 (articles/Pxx_长文.md)     │
│  3. 模块大笔记: 跨集本体融合、ASCII 拓扑、自适应矩阵 (notes/模块XX.md)  │
└───────────────────────────────────────────────────────────────────────┘
```

---

## 安装

支持作为成熟 AI Agent 的原生 Skill 挂载，亦可作为本地独立 CLI 工具运行。

### 1. 🗣️ 交给 Agent 一句话（推荐）
在 OpenCode、Claude Code、Cursor 等助手中直接发送：
```text
把 https://github.com/LINJIANG12/bili-video2book 安装为我的全局 Skill。
```

### 2. 🧬 Git Clone 本地安装
```bash
git clone https://github.com/LINJIANG12/bili-video2book.git
cd bili-video2book

# 系统依赖（用于音视频无损极速切片）：
# 请确保系统已安装 ffmpeg 并加入环境变量 PATH

# 可选依赖（用于无网络时离线声学模型兜底）：
pip install faster-whisper
```

---

## 怎么用

### 场景一：一键处理整门多 P 课程（全自动流水线）
```bash
python src/cli.py pipeline "https://www.bilibili.com/video/BV14VqVBrEhc" --all
```

### 场景二：处理特定单集或分集区间
```bash
# 处理单集（例如第 1 讲）
python src/cli.py pipeline "https://www.bilibili.com/video/BV14VqVBrEhc" --page 1

# 处理指定分集区间（例如第 2 讲至第 5 讲）
python src/cli.py pipeline "https://www.bilibili.com/video/BV14VqVBrEhc" --range 2-5
```

### 场景三：仅重新聚合知识块复习大笔记
```bash
python src/cli.py cluster-notes "https://www.bilibili.com/video/BV14VqVBrEhc" --replace
```

### 场景四：直接转录本地音频
```bash
python src/cli.py transcribe "lecture.m4a" --engine auto
```

---

## 真实交付物形态

所有任务严格采用**独立沙盒工作区（Task Workspace）**归档：

```text
output/【数据库速成课】期末突击_BV14VqVBrEhc/
├── articles/                     # 📘 9 集单集精读教材长文（每篇约 1.5 万字，含自测题）
│   ├── P01_1绪论_精读文章.md
│   ├── P02_2关系数据库_精读文章.md
│   └── ...
├── notes/                        # 📑 6 大知识块融合复习速查笔记（高密度 Cheatsheet）
│   ├── 模块01_数据库系统概论与关系模型基础_P01-P02_笔记.md
│   ├── 模块02_结构化查询语言SQL核心语法与应用_P03_笔记.md
│   └── ...
├── subtitles/                    # 📝 原始与清洗后转录文本 + 知识元原子 JSON
│   ├── P01_1绪论_clean.txt
│   └── kernels/
├── audio/                        # 🎵 64kbps 纯净人声音频留档
├── topic_plan.json               # 🗺️ 跨集知识块聚类拓扑规划
└── manifest.json                 # 📋 任务元数据与流水线执行记录
```

---

## 核心设计原则

- **文字必须能够彻底替代长视频。** 拒绝浮躁的 500 字提纲，宁可写满万字，绝不遗漏推导环节与关键板书。
- **事实边界坚如磐石。** 语料即法典，禁止引入外部未经主讲人提及的技术概念与虚构大厂案例。
- **结构因内容自适应。** 坚决摒弃生硬死板的工科模板，对比矩阵按需自然生成，全学科通用。
- **消灭跨集割裂感。** 针对连载网课实行全局语义规划，同一概念分散讲，笔记集中深度融。
- **学测闭环促掌握。** 精读长文文末配备针对核心考点的自测题，答案解析 100% 在正文中溯源。

---

## 许可证

本项目基于 [MIT License](LICENSE) 开源。欢迎提交 Issue 与 Pull Request，共同推动高效、严肃、有深度的知识沉淀工程！
