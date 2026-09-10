# Bili-Video2Book

将 B 站长视频/系列网课与本地音视频重构为结构化教材长文、模块合辑全书与思维导图笔记的自动化工具。

[![开源协议: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](LICENSE)
[![Python 版本: 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue.svg?style=flat-square)](#)
[![环境适配: Antigravity | ChatGPT | Codex | 命令行](https://img.shields.io/badge/Environment-CLI%20%7C%20Agents-111827?style=flat-square)](SKILL.md)

**[English Documentation](README.en.md)** &nbsp;·&nbsp; [功能特性](#功能特性) &nbsp;·&nbsp; [交付产物体系](#交付产物体系) &nbsp;·&nbsp; [两阶段解耦流水线](#两阶段解耦流水线) &nbsp;·&nbsp; [安装与快速开始](#安装与快速开始) &nbsp;·&nbsp; [CLI 使用指南](#cli-使用指南) &nbsp;·&nbsp; [许可证](#许可证)

---

## 功能特性

- **多态输入支持**：支持 B 站单 P、多 P 连载网课、UGC 合集链接，以及本地常见音视频格式（`.mp4`, `.mkv`, `.mov`, `.flv`, `.m4a`）和本地多讲网课文件夹。
- **两阶段解耦调度**：将单集高并发转录与跨集模块系统整编彻底解耦。阶段一通过全局扁平队列与滑动窗口维持高并发流水线；阶段二按模块知识边界统一整编。
- **三轨结构化交付**：同时输出单集教材长文（`articles/`）、模块合辑教材（`textbooks/`）与考纲思维导图笔记（`notes/`），满足深入自学、系统通读与考前速记需求。
- **轻量与多模态原生**：通过 FFmpeg 极速提取轻量人声音频，依托多模态模型原生读取，不依赖本地下载与运行大型离线模型权重（如 Whisper），避免占用本地显存。
- **沙盒工作区管理**：按课程建立独立输出目录，内置增量断点续传、文件状态校验与实时队列追踪器。

---

## 交付产物体系

系统针对不同学习场景输出三类定位明确的结构化资产：

| 交付形态 | 存储路径 | 适用场景 | 核心特征 |
| :--- | :--- | :--- | :--- |
| **单集教材长文** | `output/<task>/articles/` | 单集深入自学、替代长视频 | 完整还原核心原理推导、代码实现与演算过程；文末配备 2~3 道自测题与溯源解析。**模块整编时严格保留，不予删除**。 |
| **模块合辑教材** | `output/<task>/textbooks/` | 系统章节精读、全卷通读 | 跨分集知识整合，消除单集孤立感；增加章节承上启下的过渡桥梁段落，形成体系化教材。 |
| **模块复习笔记** | `output/<task>/notes/` | 考前复习、日常速查、脑图构建 | 需显式指定 `--style`（系统不设默认）；推荐 `minimal` 对齐 CS-Xmind-Note 考研思维导图规范，多级列表展开结合单行核心定义，原生支持 VS Code Markmap 与 XMind 导入。 |

---

## 两阶段解耦流水线

针对系列网课处理中的并发调度，系统采用单集生产与模块整编完全解耦的架构：

```text
[输入 URL 或本地课程目录]
          │
          ▼
【准备阶段：结构解析与音频就绪】
  bili-video2book pipeline "<链接或本地路径>" [--all | --range X-Y]
  ├── 智能解析分 P 拓扑与元数据，生成任务清单 (parts.json)
  └── 批量提取轻量人声音频至 audio/ (单集阈值 60min，整轨直接处理)
          │
          ▼
【阶段一：全局动态滑动流水线】
  维护全局单一待处理任务队列 (FIFO Queue)，打满并发池推进：
  ├── 并发维持：恒定保持 5~6 个微智能体槽位并行处理
  ├── 滑动调度：“完成一个，立即派生一个” (磁盘探针命中 ➔ 回收 ➔ 派发新集)
  ├── 单集一步：read_audio 取切片 ➔ view_file 原生听音 ➔ 直接撰写教材长文（零中间逐字稿）
  └── 阶段门禁：所有分集全部竣工且无未完成任务时，阶段一结束
          │
          ▼
【阶段二：按模块统一收敛整编】
  确认单集文章 (articles/) 全部就绪后，按模块拓扑聚合：
  ├── 模块合辑教材：调用 cluster-articles 生成各模块教材全书 (textbooks/)
  ├── 思维导图笔记：调用 cluster-notes --style minimal 生成考纲导图笔记 (notes/)
  └── 交付校验：核对各轨资产完整性与目录索引
```

> **动态队列追踪工具**：配套提供 `python scripts/queue_tracker.py`（支持 `--next N`、`--json`、`--summary`），用于实时监测全局队列出队状态与阶段门禁流转。
>
> 逐步操作规范（含阶段二三步门禁与任务书对照表）见 [SKILL.md](SKILL.md)；自检命令为 `python scripts/selfcheck.py`。

---

## 安装与快速开始

### 1. 系统依赖

音频提取依赖系统 `ffmpeg`，请确保已安装并加入系统 `PATH` 环境变量：

- **Windows**：`winget install Gyan.FFmpeg`
- **macOS**：`brew install ffmpeg`
- **Linux (Debian/Ubuntu)**：`sudo apt update && sudo apt install -y ffmpeg`

### 2. 安装 omni-media MCP 服务（阶段一听音必需）

阶段一通过 MCP 工具 `omni-media:read_audio` 提取音频切片，再由宿主多模态模型原生聆听。

```bash
cd omni-media-mcp && pip install -e .
python -m omni_media_mcp.cli apply --target zcode
```

> 接入会把已配置的 provider API Key 写入宿主配置文件，请勿将其纳入版本控制。

### 3. 作为 AI Agent Skill 挂载（推荐）

在 Antigravity、ChatGPT、OpenAI Codex 等环境中直接说明：
```text
把本仓库安装为我的全局 Skill。
```
本仓库内置 `.agents/skills/bili-video2book`，符合 Open Agent Skills 标准规范，可直接通过 Agent 自然语言触发。

### 4. 本地安装与命令行使用

```bash
git clone https://github.com/LINJIANG12/bili-video2book.git
cd bili-video2book

# 可选：安装为全局命令行工具
pip install -e .
```

---

## CLI 使用指南

若已执行 `pip install -e .`，可直接使用 `bili-video2book`；亦可在仓库根目录直接运行 `python src/cli.py`：

### 场景一：处理整门课程流水线
```bash
# 处理整门 B 站网课合集
bili-video2book pipeline "https://www.bilibili.com/video/BV14VqVBrEhc" --all

# 处理本地整套视频课程目录
bili-video2book pipeline "D:\courses\software_engineering\" --all
```

### 场景二：处理指定分集或区间
```bash
# 处理第 1 讲
bili-video2book pipeline "https://www.bilibili.com/video/BV14VqVBrEhc" --page 1

# 处理第 2 讲至第 5 讲
bili-video2book pipeline "https://www.bilibili.com/video/BV14VqVBrEhc" --range 2-5
```

### 场景三：生成模块合辑教材
在阶段一单集长文生成完毕后，整编生成模块教材：
```bash
bili-video2book cluster-articles "https://www.bilibili.com/video/BV14VqVBrEhc"
```

### 场景四：生成模块思维导图复习笔记
```bash
# 使用 minimal 精简树状风格 (推荐考研与日常速记)
bili-video2book cluster-notes "https://www.bilibili.com/video/BV14VqVBrEhc" --style minimal

# 使用 detailed 详细全景风格
bili-video2book cluster-notes "https://www.bilibili.com/video/BV14VqVBrEhc" --style detailed
```

### 场景五：查看与监控任务队列状态
```bash
# 查看当前任务工作区的完成进度与阶段判定
python scripts/queue_tracker.py

# 获取待处理队列中接下来的 5 个分集及路径
python scripts/queue_tracker.py --next 5
```

---

## 凭证说明：B 站 SESSDATA 配置

在批量抓取多 P 长篇网课时，建议提供登录凭证，避免频繁请求触发 B 站 412 频控限制：
1. 在浏览器登录 bilibili.com；
2. 按 `F12` 打开开发者工具 -> Application -> Cookies -> `https://www.bilibili.com`；
3. 复制 `SESSDATA` 项对应的值；
4. 在命令中追加 `--sessdata "<SESSDATA>"` 参数即可。

---

## 许可证

本项目基于 [MIT License](LICENSE) 开源。
