# Bili-Video2Book

将 B 站长视频/系列网课与本地音视频重构为结构化教材长文、模块合辑全书与思维导图笔记的自动化工具。

[![开源协议: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](LICENSE)
[![Python 版本: 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue.svg?style=flat-square)](#)
[![环境适配: Antigravity | ChatGPT | Codex | 命令行](https://img.shields.io/badge/Environment-CLI%20%7C%20Agents-111827?style=flat-square)](SKILL.md)

**[English Documentation](README.en.md)** &nbsp;·&nbsp; [功能特性](#功能特性) &nbsp;·&nbsp; [交付产物体系](#交付产物体系) &nbsp;·&nbsp; [两阶段解耦流水线](#两阶段解耦流水线) &nbsp;·&nbsp; [安装与快速开始](#安装与快速开始) &nbsp;·&nbsp; [CLI 使用指南](#cli-使用指南) &nbsp;·&nbsp; [许可证](#许可证)

---

## 功能特性

- **多态输入支持**：支持 B 站单 P、多 P 连载网课与本地常见音视频格式（`.mp4`, `.mkv`, `.mov`, `.flv`, `.m4a`）及本地多讲网课文件夹。**UGC 合集的跨稿件遍历尚未实现**：合集链接可用 `parse` 查看全季清单，实际处理范围是**当前稿件的 1..N 个分 P**；若课程是一个合集里每集独立 BV，请逐集指定 BV 号处理。
- **两阶段解耦调度**：将单集高并发转录与跨集模块系统整编彻底解耦。阶段一通过全局扁平队列与滑动窗口维持高并发流水线；阶段二按模块知识边界统一整编。
- **三轨结构化交付**：同时输出单集教材长文（`articles/`）、模块合辑教材（`textbooks/`）与考纲思维导图笔记（`notes/`），满足深入自学、系统通读与考前速记需求。
- **轻量与多模态原生**：通过 FFmpeg 极速提取轻量人声音频，依托多模态模型原生读取，不依赖本地下载与运行大型离线模型权重（如 Whisper），避免占用本地显存。
- **沙盒工作区管理**：按课程建立独立输出目录，内置增量断点续传、文件状态校验与实时队列追踪器。

---

## 交付产物体系

系统针对不同学习场景输出三类定位明确的结构化资产：

| 交付形态 | 存储路径 | 适用场景 | 核心特征 |
| :--- | :--- | :--- | :--- |
| **单集教材长文** | `output/<task>/articles/` | 单集深入自学、替代长视频 | 完整还原核心原理推导、代码实现与演算过程，按所选长文风格成稿（`learning` 学习＝保住讲师讲课口吻，`legacy` 旧版＝教材腔＋随堂自测）；**文末题目只在讲师课上确实提到时才还原**。**模块整编时严格保留，不予删除**。 |
| **模块合辑教材** | `output/<task>/textbooks/` | 系统章节精读、全卷通读 | 跨分集知识整合，消除单集孤立感；增加章节承上启下的过渡桥梁段落，形成体系化教材。 |
| **模块复习笔记** | `output/<task>/notes/` | 考前复习、日常速查、脑图构建 | **由子智能体基于模块单集长文重写生成**（非知识元拼接）；**笔记只有这一种风格**（旧版八种风格矩阵已删除，无需 `--style`）；须满足「笔记规范」：知识拓扑树 + 主题分节 + 概念块 + 溯源标注，**只写结论不写推导**，原生支持 VS Code Markmap 与 XMind 导入。 |

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
【阶段一：派发回路 + 全局动态滑动流水线】
  维护全局单一待处理任务队列 (FIFO Queue)，打满并发池推进：
  ├── 派发纪律：**课程总时长 ≤ 60 分钟 → 主 Agent 可串行亲做；超过 60 分钟 → 必须派发**
  │              （默认一集一子智能体；集数 ≥15 且单集 ≤40k token 时按建议 3~5 集打包）
  ├── 取载荷：`queue_tracker.py --next 5 --json --log-dispatch`（含任务书/切片/目标长文/本集预算）
  ├── 并发维持：恒定保持 5~6 个子智能体槽位并行处理（`--summary` 里的 SUGGEST_WORKERS）
  ├── 滑动调度：“完成一个，立即派生一个” (磁盘探针命中 ➔ 回收 ➔ 派发新集)
  ├── 单集一步：read_audio 取切片 ➔ view_file 原生听音 ➔ 直接撰写教材长文（零中间逐字稿）
  │             子智能体只回报一行 `P07 | 路径 | 字节数 | 执行者`，不回传正文
  └── 阶段门禁：所有分集全部竣工且无未完成任务时，阶段一结束（STAGE1_DONE=1）
          │
          ▼
【阶段二：按模块统一收敛整编（两趟门禁）】
  确认单集文章 (articles/) 全部就绪后，按模块拓扑聚合：
  ├── ① 规划：cluster-notes 首跑导出 topic_plan_TASK.md ➔ Agent 写 topic_plan.json ➔ 重跑
  ├── ② 笔记：逐模块导出 notes/模块XX_*_TASK.md（专属提示词 + 本模块文章路径清单）
  │        ➔ 主 Agent 派子智能体（一个模块一个），逐篇读完该模块长文后撰写模块笔记
  ├── ③ 教材：cluster-articles 以 articles/ 整编为模块合辑教材 (textbooks/)
  ├── 质检：note_quality_check.py（笔记成色）+ render_compat_check.py（渲染合规）
  └── 收尾：cleanup 回收任务书（每类留 1 份范本）+ sync 按磁盘对账回填清单
```

> **动态队列追踪工具**：配套提供 `python scripts/queue_tracker.py`（支持 `--next N`、`--json`、`--summary`），用于实时监测全局队列出队状态与阶段门禁流转。
>
> **交付前机器质检**：`python scripts/note_quality_check.py --strict` 把「套话填充 / 空壳标题 / 分集平铺标题 / 行内残缺引用 / 分集口吻」五类必查项与「断句 / 结构缺件」两类提示项变成可复算指标；`python scripts/render_compat_check.py --strict` 检查 GitHub 告警块、围栏外裸字符画与围栏配对（**「围栏缺语言标识」默认只提示，加 `--require-lang` 才纳入门禁**）。
>
> 逐步操作规范（含阶段二门禁与子智能体派发规范、任务书对照表）见 [SKILL.md](SKILL.md)；自检命令为 `python scripts/selfcheck.py`。

---

## 目录结构（三域隔离）

本项目按**职责**分成三个互不打扰的域：代码、MCP 服务、产物各占一处，任何一个的升级/搬迁都不会影响另外两个。

```text
<容器根>/
├── skill/     ← 本仓库：技能与工具链（SKILL.md、src/、scripts/、references/、.agents/）
├── mcp/       ← 独立仓库：omni-media MCP 服务（纯本地，与技能无运行时依赖）
└── output/    ← 产物根：每门课一个工作区 + .sessdata.json / .wbi_keys.json / .cli_status.json
```

- **两个仓库各自独立**（各自的 `.git`），可分别克隆、升级、发布；MCP 从不 import 技能代码，技能也从不 import MCP 代码（`selfcheck` 强制校验）；
- **产物永远在两仓库之外**：不会出现在任何 `git status` 里，删除/迁移仓库都不会动到成品；
- **命令与工作目录解耦**：`--base-dir` 缺省即产物根（绝对路径），因此在任意目录执行 CLI/脚本都能找到同一批工作区；
  需要换位置时用 `--base-dir <路径>`，或设置环境变量 `BVB_HOME`（容器根）/ `BVB_OUTPUT_DIR`（产物根）；
- `python src/cli.py info` 会打印当前解析出的「代码根 / 容器根 / 产物根」三行，便于确认。

---

## 安装与快速开始

### 1. 系统依赖

音频提取依赖系统 `ffmpeg`，请确保已安装并加入系统 `PATH` 环境变量：

- **Windows**：`winget install Gyan.FFmpeg`
- **macOS**：`brew install ffmpeg`
- **Linux (Debian/Ubuntu)**：`sudo apt update && sudo apt install -y ffmpeg`

### 2. 安装 omni-media MCP 服务（阶段一听音必需，独立仓库）

阶段一通过 MCP 工具 `omni-media:read_audio` 提取音频切片，再由宿主多模态模型原生聆听。
MCP 是**独立仓库**（与本仓库平级的 `mcp/`），只需装一次、可独立升级：

```bash
cd ../mcp && pip install -e .          # 若未克隆：git clone <omni-media-mcp 仓库地址> mcp
python -m omni_media_mcp.cli apply --target zcode   # --target 也可用 opencode/dsh/codex/antigravity/all
python selfcheck.py                    # 可选：跑 MCP 侧自检
```

> **无需任何 API Key**：音频由宿主多模态模型原生聆听，接入只写入服务启动命令与 `PYTHONPATH`，不涉及任何凭证。唯一的外部依赖是系统 `ffmpeg`。

### 3. 作为 AI Agent Skill 挂载（推荐）

在 Antigravity、ChatGPT、OpenAI Codex 等环境中直接说明：
```text
把本仓库安装为我的全局 Skill。
```
本仓库内置 `.agents/skills/bili-video2book`，符合 Open Agent Skills 标准规范，可直接通过 Agent 自然语言触发。

> **注意（工作目录契约）**：Skill 本体只有 `SKILL.md` 与 `references/`，**命令与脚本都在仓库里**。
> 挂载时请保持**整个仓库可达**（整仓复制或软链），并让 Agent **以本仓库根（`skill/`）为工作目录**执行
> `python src/cli.py …` / `python scripts/…`，否则 SKILL.md 里的命令会找不到文件。

### 4. 本地安装与命令行使用

```bash
git clone https://github.com/LINJIANG12/bili-video2book.git
cd bili-video2book

# 可选：安装为全局命令行工具
pip install -e .
```

---

## CLI 使用指南

若已执行 `pip install -e .`，可直接使用 `bili-video2book`；亦可在本仓库根目录（`skill/`）直接运行 `python src/cli.py`。
产物一律落在产物根（默认 `<容器根>/output/`），与代码目录分离；下文示例中的 `output/<task>/…` 均**相对产物根**。

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
# 模块复习笔记：笔记只有一种风格，无需 --style
bili-video2book cluster-notes "https://www.bilibili.com/video/BV14VqVBrEhc"

# --force：强制重导全部模块任务书（已产出笔记成品的模块默认会自动复用）
bili-video2book cluster-notes "https://www.bilibili.com/video/BV14VqVBrEhc" --force

# --force-plan：强制重出 topic_plan_TASK.md（丢弃旧规划，重新做模块边界规划）
bili-video2book cluster-notes "https://www.bilibili.com/video/BV14VqVBrEhc" --force-plan
```

### 场景五：查看与监控任务队列状态
```bash
# 查看当前任务工作区的完成进度与阶段判定
python scripts/queue_tracker.py

# 获取待处理队列中接下来的 5 个分集及路径
python scripts/queue_tracker.py --next 5

# 多课程并存时指定工作区（否则取最近活动的那个）
python scripts/queue_tracker.py --pattern "微机原理" --next 5
```

### 场景六：交付前质检与收尾
```bash
# 笔记成色体检（致命项：套话填充 / 空壳标题 / 分集平铺标题 / 行内残缺引用 / 分集口吻；
#              提示项：断句 / 结构缺件——加 --require-structure 才纳入门禁）
python scripts/note_quality_check.py --strict

# 渲染合规体检（致命项：GitHub 告警块 / 围栏外裸字符画 / 围栏配对；
#              提示项：围栏语言标识——加 --require-lang 才纳入门禁）
python scripts/render_compat_check.py --strict

# 任务书回收：成品产出后才回收，每类保留 1 份范本（先 --dry-run 预演）
python src/cli.py cleanup --dry-run
python src/cli.py cleanup

# 账本对账：以磁盘产物为唯一真相回填 manifest.json
python src/cli.py sync

# 可选：模块教材默认复用已有 textbooks/，需要按最新章节重编时加 --force
python src/cli.py cluster-articles "https://www.bilibili.com/video/BV14VqVBrEhc" --force
```

> **任务书是临时派发物**：`*_TASK.md` 在成品产出后由 `cleanup`（或 pipeline 收尾）自动回收，
> 每个类别保留编号最小的 1 份作为提示词范本；`topic_plan_TASK.md` 永不回收。

---

## 凭证说明：B 站 SESSDATA 配置

在批量抓取多 P 长篇网课时，建议提供登录凭证，避免频繁请求触发 B 站 412 频控限制：

1. 在浏览器登录 bilibili.com；
2. 按 `F12` 打开开发者工具 -> Application -> Cookies -> `https://www.bilibili.com`；
3. 复制 `SESSDATA` 项对应的值；
4. 二选一使用：

```bash
# 方式一：一次性传入（仅作用于本次执行）
bili-video2book pipeline "<链接>" --all --sessdata "<SESSDATA>"

# 方式二：持久化保存（推荐，保存一次后续命令免传）
python src/cli.py login --sessdata "<SESSDATA>"
bili-video2book pipeline "<链接>" --all
python src/cli.py info     # 查看凭证来源与脱敏指纹
python src/cli.py logout   # 撤销保存
```

> **安全提示**：持久化的凭证以明文存于 `output/.sessdata.json`，该路径已被 `.gitignore` 排除，不会进入版本库；命令行 `--sessdata` 参数优先级始终高于本地存档。SESSDATA 等同你的 B 站登录态，请勿复制、上传或分享该文件。

---

## 许可证

本项目基于 [MIT License](LICENSE) 开源。
