---
name: bili-video2book
description: 将 B 站长视频/系列网课或本地音视频重构为高保真精读教材长文与模块速查大笔记；提供音频下载、Agent 原生转录派发、知识元抽取、知识块聚合与任务书导出的完整流水线工具链。Use when converting Bilibili or local videos into structured notes, articles, textbooks, or cheatsheets.
license: MIT
compatibility: Python 3.8+, ffmpeg in PATH, Multimodal LLM Agent (Antigravity, ChatGPT/Codex)
metadata:
  author: LINJIANG12
  version: 1.4.0
  category: learning-and-education
---

# 📚 Bili-Video2Book: 视频网课重构教材与复习笔记 Skill

本 Skill 专为 AI Agent（Antigravity、OpenAI Codex / ChatGPT 等）及系统终端命令行设计，能够将 B 站长视频/系列网课或本地音视频，重构成**高保真精读教材长文**与**模块速查大笔记**。

---

## 🔑 核心前置约束：B 站任务 SESSDATA 凭证引导

> ⚠️ **强制守则**：当且仅当目标输入为 **B 站（bilibili.com 或 BV 号）任务**时，在执行批量音视频解析与下载前，必须优先检查或引导用户提供 `SESSDATA` 登录凭证，确保长期稳定调用、彻底规避 B 站 412/风控限制。如果是本地音视频或非 B 站任务，则跳过此步。

### 用户引导指南（在发起 B 站批量任务前主动呈现）
1. 告知用户："为确保批量抓取长篇合集不被 B 站 412 风控拦截，建议提供有效 SESSDATA 登录凭证。"
2. 获取步骤提示：
   - 在浏览器登录 bilibili.com；
   - 按 `F12` 打开开发者工具 -> Application（应用/存储） -> Cookies -> `https://www.bilibili.com`；
   - 找到名为 `SESSDATA` 的项，复制其值并提供；
3. 执行时挂载 `--sessdata "<SESSDATA>"` 参数，凭证仅保留于当前任务执行进程，不泄露至无关环境。

---

## 🎯 核心工作流：两阶段原生流水线与子智能体派发

```text
[用户输入 URL / 本地文件]
      │
      ▼
【阶段一：CLI 结构解析与一次性全量音频搞定】
  bili-video2book pipeline "<链接或本地路径>" [--all | --range X-Y] [--sessdata "xxx"]
  ├── 解析合集元数据与分 P 拓扑
  ├── 一次性批量完整下载任务所需的全部音频文件并自动切片落盘 (audio/)
  └── 导出转录与双轨任务书 (articles/PXX_*_TASK.md, notes/模块XX_*_TASK.md)
      │
      ▼
【阶段二：子智能体（Sub-agent）并发批处理重构】
  宿主 Agent 盘点已就绪的音频总时长，动态规划派发规则：
  ├── 派发约束：同时派生 3 个子智能体并行执行任务
  ├── 任务配额：原则上每个子智能体负责约 3 小时（非硬性约束，根据模块完整性微调）
  ├── 短任务分配：若总时长不足 3 小时，按模块/分 P 边界将任务合理均分给子智能体
  └── 子智能体职责：多模态直读音频切片与任务书，完成转录、单集教材长文与模块笔记
```

---

## 🤖 子智能体（Sub-agent）派发执行规范

> ⚠️ **转录与模型底线纪律**：**绝不使用本地模型转录，严禁下载模型**。所有转录与重构处理必须依托多模态 Agent 原生能力或云端接口，严禁在本地环境中下载安装任何离线模型权重（如 Whisper、Faster-Whisper 等离线模型），坚决杜绝占用用户本地磁盘与硬件算力。

当阶段一完成音频的一次性批量下载后，宿主 Agent **严禁单线程串行处理全部长音频**，必须遵循以下工作约束进行子智能体派发：

1. **音频就绪前置检查**：
   - 确认当前任务的音频文件已全部批量下载完毕（存储于 `output/<task_dir>/audio/`）。
   - 统计任务总时长（小时/分钟）及各分 P / 模块划分。
2. **派生 3 个子智能体并行**：
   - 宿主智能体必须规划任务切分清单，并发启动 **3 个子智能体**（例如：`agent-part1`、`agent-part2`、`agent-part3`）。
3. **时长与配额切分准则**：
   - **基准负载**：每个子智能体负责 **3 小时左右** 的音频任务（非硬性教条，优先保证知识模块的语义连贯，不强行拆散单一完整模块）。
   - **总时长 < 3 小时**：若合集总时长较短，则根据分 P 或章节边界将总任务合理切分为 2~3 个子任务包，由 3 个子智能体协作完成。
   - **总时长 >> 9 小时**：按 3 个并发批次逐步推进，每轮各负责 3 小时左右任务，直至全部消化。
4. **子智能体派生 Prompt 规范（极简自主驱动）**：
   - **信息极简**：宿主智能体在派生子智能体时，提示词（Prompt）**严禁粘贴大量冗余长文、代码块或重复背景说明**。
   - **仅需包含两项核心要素**：
     1. **具体分配的任务**：明确指出子智能体负责的分 P / 模块范围、音频切片路径与对应任务书文件；
     2. **技能路径（SKILL 路径）**：明确给出本 Skill 的路径（如当前工作区下的 `SKILL.md` 及 `references/`，或已安装的 Skill 路径），要求子智能体自行读取规范后独立完成。
5. **子智能体产出要求（方案 A：深度适配 Antigravity 与 ChatGPT）**：
   - 子智能体自行读取 Skill 规范后，自主检索分配给自己的音频切片与任务书（`articles/PXX_*_TRANSCRIBE_TASK.md`）：
     - **Antigravity 宿主**：使用 `view_file` 工具依次打开切片音频文件，由模型多模态核心原生聆听并转录，保存至 `subtitles/PXX_*_clean.txt`。
     - **ChatGPT / Codex 宿主**：通过挂载音频分片或直接多模态输入，完成转录落盘至 `subtitles/PXX_*_clean.txt`。
   - 语料就绪后，基于单集任务书（`articles/PXX_*_TASK.md`）撰写教材长文，并协同完成模块大笔记（`notes/`）。

---

## 🛠️ CLI 常用命令速查

Agent 或用户在终端执行操作时，可灵活选择以下调用方式（效果完全一致）：
- **全局终端命令（推荐）**：`bili-video2book <子命令>`（执行 `pip install -e .` 安装后全局可用）
- **免安装脚本直调**：`python "<skill_dir>/scripts/run.py" <子命令>`（任意工作目录下均可直接调用）
- **仓库内就地执行**：`python src/cli.py <子命令>`（当前终端工作目录位于本仓库内）

### 1. 解析元数据与合集结构

```bash
bili-video2book parse "<链接或本地文件/目录>" [--json]
```

### 2. 执行两阶段准备流水线

```bash
# 单集 / 本地单视频
bili-video2book pipeline "<链接或本地文件>" --page 1

# 多 P 课程全量处理（含知识块聚合规划）
bili-video2book pipeline "<链接或本地目录>" --all

# 指定分 P 范围
bili-video2book pipeline "<链接>" --range 1-5
```

### 3. 生成提示词与知识块聚合

```bash
# 提取或重跑提示词
bili-video2book prompt "<链接或本地路径>" --type article|note|rectify

# 聚合多 P 笔记 (必须显式指定 --style 风格，系统不设默认值)
bili-video2book cluster-notes "<链接或本地目录>" --style minimal --replace

# 整编模块精读全书 (生成 textbooks/ 目录全卷教材，原有 articles/ 完整保留不删)
bili-video2book cluster-articles "<链接或本地目录>"
```

---

## 📋 多轨交付纪律与排版规范

完成阶段一的音视频准备后，Agent 必须支持三类交付物的撰写与整编：

1. **产物 A：单集精读教材长文 (`articles/`)**
   - 彻底去除口语闲聊，重构为体系化的学术/技术专著文风。
   - 包含背景推演、核心原理推导、真实案例全景复盘与可选自测题。
   - 即使整编为模块全书后，单集文章**严格保留，严禁删除**。
   - 详细规格请查阅：[references/delivery_matrix.md](references/delivery_matrix.md)。
2. **产物 B：模块速查大笔记 (`notes/`)**
   - 支持 8 种风格选择（系统不设硬编码默认风格，提示用户自主指定 `--style`）。
   - **精简风格 (minimal)**：严格遵循 `SSHeRun/CS-Xmind-Note` 408 考研思维导图树状结构（Markdown 标题 + 多级 `*` 缩进、`* > 定义：...` 单行引用、步骤化归纳、零口水话、天然契合 Markmap / XMind 渲染脑图）。
   - 详细排版与风格定义请查阅：[references/delivery_matrix.md](references/delivery_matrix.md) 与 [references/ascii_topology_guide.md](references/ascii_topology_guide.md)。
3. **产物 C：模块精读全书 (`textbooks/`)**
   - 在全部单集文章（`articles/`）完成后，按模块整编为出版级全卷精读教材（`模块XX_..._精读全书.md`）。
   - 包含全景目录导航、小节递进过渡桥梁、综合实战串讲与模块技术总结。
   - 原单篇 `articles/` 完整保留供按讲定向查阅。

---

## 🛡️ 抗幻觉与事实边界守则 (Strict Grounding)

1. **绝对忠于原视频**：所有核心技术定义、推导逻辑必须以原音视频讲解为准。
2. **严禁无中生有**：原视频未涉及的库或方法，不得脑补；若遇音质模糊或表述不全，采用引用标记：
   > ⚠️ 原视频在此处讲解较为简略，建议查阅官方文档关于 xxx 的说明。
3. **风控自愈与网络排障**：若遭遇 B 站 412 拦截或本地 ffmpeg 缺失，请查阅 [references/troubleshooting.md](references/troubleshooting.md)。
4. **模型纪律**：**绝不使用本地模型转录，严禁下载模型**。
