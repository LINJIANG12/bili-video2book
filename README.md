# Bili-Video2Book

将 B 站长视频/系列网课与本地音视频重构为结构化教材长文、模块合辑全书与思维导图笔记的自动化工具。

[![开源协议: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](LICENSE)
[![Python 版本: 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue.svg?style=flat-square)](#)
[![环境适配: Claude Code | Codex | OpenCode | 命令行](https://img.shields.io/badge/Environment-CLI%20%7C%20Agents-111827?style=flat-square)](skills/bili-video2book/SKILL.md)

**[English Documentation](README.en.md)** &nbsp;·&nbsp; [功能特性](#功能特性) &nbsp;·&nbsp; [交付产物体系](#交付产物体系) &nbsp;·&nbsp; [两阶段解耦流水线](#两阶段解耦流水线) &nbsp;·&nbsp; [安装与快速开始](#安装与快速开始) &nbsp;·&nbsp; [CLI 使用指南](#cli-使用指南) &nbsp;·&nbsp; [许可证](#许可证)

---

## 功能特性

- **多态输入支持**：支持 B 站单 P、多 P 连载网课与本地常见音视频格式（`.mp4`, `.mkv`, `.mov`, `.flv`, `.m4a`）及本地多讲网课文件夹。**UGC 合集的跨稿件遍历尚未实现**：合集链接可用 `parse` 查看全季清单，实际处理范围是**当前稿件的 1..N 个分 P**；若课程是一个合集里每集独立 BV，请逐集指定 BV 号处理。
- **两阶段解耦调度**：将单集长文生产与跨集语义聚合彻底解耦。阶段一的**派发纪律**由主 Agent 维持（见下文流程图），工具层只提供载荷、台账与门禁；阶段二按知识边界**两趟**收敛（先划模块，再归并成笔记）。
- **三轨结构化交付**：同时输出单集教材长文（`articles/`）、模块合辑教材（`textbooks/`）与思维导图复习笔记（`notes/`），满足深入自学、系统通读与考前速记需求。
- **双通道听音**：有原生音频模态的宿主直接听音（`omni-media`，零凭证）；只有文本能力的宿主由外部模型代读（`omni-media-ext`，Gemini / OpenAI 协议）。两条通道分页契约同构，切换只需换工具名。
- **缺规划不停机**：两趟语义规划（`topic_plan.json` / `note_plan.json`）由 Agent 产出；规划越界、缺失或重复时工具当场抢救后继续，命令始终正常退出，盘上的规划文件永不被工具改写。
- **轻量与多模态原生**：通过 FFmpeg 极速提取轻量人声音频，依托多模态模型原生读取，不依赖本地下载与运行大型离线模型权重（如 Whisper），避免占用本地显存。
- **沙盒工作区管理**：按课程建立独立输出目录，内置增量断点续传、文件状态校验与实时队列追踪器。

---

## 交付产物体系

系统针对不同学习场景输出三类定位明确的结构化资产：

| 交付形态 | 存储路径 | 适用场景 | 核心特征 |
| :--- | :--- | :--- | :--- |
| **单集教材长文** | `output/<task>/articles/` | 单集深入自学、替代长视频 | 完整还原核心原理推导、代码实现与演算过程，按所选长文风格成稿（`learning` 学习＝保住讲师讲课口吻，`legacy` 旧版＝教材腔＋随堂自测）；**文末题目只在讲师课上确实提到时才还原**。**模块整编时严格保留，不予删除**。 |
| **模块合辑教材** | `output/<task>/textbooks/` | 系统章节精读、全卷通读 | 跨分集知识整合，消除单集孤立感；增加章节承上启下的过渡桥梁段落，形成体系化教材。 |
| **模块复习笔记** | `output/<task>/notes/` | 考前复习、日常速查、脑图构建 | **由子智能体基于长文重写生成**（非知识元拼接）；按**第二趟归并后的笔记**分篇（一篇可跨多个知识模块，**宁可少而厚、不要多而碎**）；**笔记只有这一种风格**（旧版八种风格矩阵已删除，无需 `--style`）；须满足「笔记规范」：知识拓扑树 + 主题分节 + 概念块 + 溯源标注，**只写结论不写推导**，原生支持 VS Code Markmap 与 XMind 导入。 |

---

## 两阶段解耦流水线

针对系列网课处理中的并发调度，系统采用单集生产与跨集语义聚合完全解耦的架构：

> 下图中**阶段一那一块是「主 Agent 需要维持的纪律」，不是工具层的机器架构**：
> 队列、槽位与滑动调度都由主 Agent 自己维持，工具层只负责出载荷、记台账、判门禁，
> **无法校验**谁写的、是否真听了音频（边界见 [SKILL.md](skills/bili-video2book/SKILL.md) § 4.5）。

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
【阶段一：派发回路 + 全局动态滑动流水线】（主 Agent 的纪律，工具层只观测）
  主 Agent 自建单一待处理任务队列并打满并发池推进：
  ├── 派发纪律：**课程总时长 ≤ 60 分钟 → 主 Agent 可串行亲做；超过 60 分钟 → 必须派发**
  │              （默认一集一子智能体；集数 ≥15 且单集 ≤40k token 时按建议 3~5 集打包）
  ├── 取载荷：`queue_tracker.py --next 5 --json --log-dispatch`（含任务书/切片/目标长文/本集预算）
  ├── 并发维持：主 Agent 自行保持 5~6 个子智能体槽位并行（`--summary` 里的 SUGGEST_WORKERS 是建议值）
  ├── 滑动调度：主 Agent 自行执行“完成一个，立即派生一个”(磁盘探针命中 ➔ 回收 ➔ 派发新集)
  ├── 单集一步：按宿主能力二选一取音频事实，然后直接撰写教材长文（不落盘成交付物）
  │             · 有 read_audio（原生音频）：read_audio 取切片 ➔ 用宿主的文件查看能力原生听音
  │             · 只有 read_media（无原生音频）：read_media 外部模型代读，取回逐字稿
  │             子智能体只回报一行 `P07 | 路径 | 字节数 | 执行者`，不回传正文
  └── 阶段门禁：所有分集全部竣工且无未完成任务时，阶段一结束（STAGE1_DONE=1）
          │
          ▼
【阶段二：两趟语义聚合（模块 ➔ 笔记）+ 教材整编】
  确认单集文章 (articles/) 全部就绪后，先划模块再归并笔记：
  ├── ① 模块规划：cluster-notes 导出 topic_plan_TASK.md ➔ Agent 写 topic_plan.json（消费方＝教材）
  ├── ② 笔记归并：同上导出 note_plan_TASK.md ➔ Agent 写 note_plan.json（一篇可跨多个模块）
  │        · 两趟缺规划都不停机：越界块裁掉、无人认领的集号补占位、缺规划用兜底粒度继续
  ├── ③ 笔记派发：逐篇导出 notes/笔记XX_*_TASK.md（专属提示词 + 本篇涵盖各集的长文路径清单）
  │        ➔ 主 Agent 派子智能体（一篇笔记一个），逐篇读完该篇长文后撰写笔记
  ├── ④ 教材：cluster-articles 以 articles/ 按模块整编为合辑教材 (textbooks/)
  ├── 质检：note_quality_check.py（笔记成色）+ render_compat_check.py（渲染合规）
  └── 收尾：cleanup 回收任务书（每类留 1 份范本）+ sync 按磁盘对账回填清单
```

> **动态队列追踪工具**：配套提供 `python scripts/queue_tracker.py`（支持 `--next N`、`--json`、`--summary`），用于实时监测全局队列出队状态与阶段门禁流转。
>
> **交付前机器质检**：`python scripts/note_quality_check.py --strict` 把「套话填充 / 空壳标题 / 分集平铺标题 / 行内残缺引用 / 分集口吻」五类必查项与「断句 / 结构缺件」两类提示项变成可复算指标；`python scripts/render_compat_check.py --strict` 检查 GitHub 告警块、围栏外裸字符画与围栏配对（**「围栏缺语言标识」默认只提示，加 `--require-lang` 才纳入门禁**）。
>
> 逐步操作规范（含阶段二门禁与子智能体派发规范、任务书对照表）见 [SKILL.md](skills/bili-video2book/SKILL.md)；自检命令为 `python scripts/selfcheck.py`。

---

## 目录结构（技能自包含 + 三域隔离）

本仓库是**插件 / 分发单元**；技能本体与它依赖的工具链**自包含**在同一个目录里，
因此安装只需带走那一个目录。两个音视频 MCP 服务同属**另一个仓库**，与产物各自独立成域：

```text
<容器根>/
├── skill/                          ← 本仓库（插件单元）
│   ├── skills/bili-video2book/     ← ★ 技能（安装单元）：SKILL.md + references/ + src/ + scripts/
│   ├── .codex-plugin/  .claude-plugin/  .agents/plugins/  .opencode/  ← 各平台识别用声明
│   └── AGENTS.md / CLAUDE.md                              ← 各 agent 自动加载的入口
├── omni-media/                     ← 另一个仓库：两个音视频 MCP 服务
│   ├── mcp/                        ←   宿主原生听音版（read_audio，纯本地，零凭证）
│   └── mcp-ext/                    ←   外部模型代读版（read_media，读 config.json）
└── output/                         ← 产物根：每门课一个工作区 + .sessdata.json / .wbi_keys.json / .cli_status.json
```

- **安装单元只有一个目录**：`skills/bili-video2book/`。复制或软链它即可，其余文件（README / LICENSE / 平台声明）都不需要安装；
- **各仓库/目录互相独立**（`skill/`、`omni-media/` 各有自己的 `.git`），可分别克隆、升级、发布；MCP 从不 import 技能代码，技能也从不 import MCP 代码（`selfcheck` 强制校验，只做目录存在性判断与 AST/正则静态扫描，从不真实 import）；
- **配套 MCP 仓库**：[LINJIANG12/omni-media](https://github.com/LINJIANG12/omni-media) —— 本技能的**阶段一听音通道**由它的两个服务提供（`read_audio` / `read_media`），仅通过 MCP 协议协作；位置由 `src/core/paths.py` 统一解析（新布局 `<容器根>/omni-media/{mcp,mcp-ext}`，并兼容旧的平级布局与 `OMNI_MEDIA_MCP_DIR` 覆盖）；
- **产物永远在代码之外**：不会出现在任何 `git status` 里，删除/迁移仓库都不会动到成品；
- **命令与工作目录解耦**：`--base-dir` 缺省即产物根（绝对路径），因此在任意目录执行 CLI/脚本都能找到同一批工作区；
  需要换位置时用 `--base-dir <路径>`，或设置环境变量 `BVB_HOME`（容器根）/ `BVB_OUTPUT_DIR`（产物根）；
- `python src/cli.py info` 会打印当前解析出的「代码根 / 容器根 / 产物根 / MCP 仓库」四行，便于确认。

**各平台装到哪、怎么装**：见 [`skills/bili-video2book/references/install.md`](skills/bili-video2book/references/install.md)
（平台对照表 + 手动安装三法 + 工具名映射）。

---

## 安装与快速开始

### 1. 系统依赖

音频提取依赖系统 `ffmpeg`，请确保已安装并加入系统 `PATH` 环境变量：

- **Windows**：`winget install Gyan.FFmpeg`
- **macOS**：`brew install ffmpeg`
- **Linux (Debian/Ubuntu)**：`sudo apt update && sudo apt install -y ffmpeg`

### 2. 安装音频 MCP 服务（阶段一取音频必需，二选一）

阶段一的音频处理有**两条通道**，按宿主是否具备原生音频模态选择（分页契约同构，切换只需换工具名）：

| 通道 | 适用宿主 | 工具 | 安装 |
| :--- | :--- | :--- | :--- |
| **A. 宿主原生听音** | 模型自身有音频模态（Gemini / GPT-4o Audio / Codex 等） | `read_audio` | [`omni-media/mcp/`](https://github.com/LINJIANG12/omni-media)（**无需任何 API Key**） |
| **B. 外部模型代读** | 只有文本能力的宿主 | `read_media` | [`omni-media/mcp-ext/`](https://github.com/LINJIANG12/omni-media)（读取 `config.json` 里的端点与 api_key） |

```bash
# 两个 MCP 同属一个仓库（本技能的阶段一听音通道提供方）
cd .. && git clone https://github.com/LINJIANG12/omni-media.git   # 容器布局里已存在则跳过

# 通道 A：宿主能自己听音频（优先选它，零凭证）
cd omni-media/mcp && pip install -e .
python -m omni_media_mcp.cli apply --target codex    # --target 还可用 opencode/all（完整取值以该仓库为准）
python selfcheck.py                                  # 可选：MCP 侧自检

# 通道 B：宿主听不了音频（由外部模型代读）
cd ../mcp-ext && pip install -e .                    # 若未安装
python -m omni_media_ext.cli config --init           # 生成 config.json，填入端点与 api_key
python -m omni_media_ext.cli status --probe          # 环境 + 配置 + 端点可达性 + 该挂哪一个
python -m omni_media_ext.cli apply --target codex
python selfcheck.py                                  # 可选：本版本自检（含与原版的兼容契约）
```

> **通道 A 无需任何 API Key**：音频由宿主多模态模型原生聆听，接入只写入服务启动命令与 `PYTHONPATH`，不涉及任何凭证。
> 唯一的外部依赖是系统 `ffmpeg`。**通道 B** 的凭证只放在 `omni-media/mcp-ext/config.json`（已被该仓库的 `.gitignore` 排除），不写入宿主配置。
>
> 两个服务可以**同时挂载**（注册键 `omni-media` / `omni-media-ext` 互不覆盖），此时 Agent 优先走 `read_audio`，
> 需要 `summarize` / `qa` 这类加工时再用 `read_media`。选择规则与契约对照见 `SKILL.md` §4.2 与容器根 README。

### 3. 作为 AI Agent Skill 安装（推荐）

本仓库遵循 **Agent Skills 开放规范**：`skills/bili-video2book/` 就是一个自包含的技能目录
（`SKILL.md` + `references/` + `src/` + `scripts/`），**装它一个目录即可**。

**让平台自己装**（推荐）：把仓库链接交给平台的原生插件 / 技能安装通道，或直接让该平台的 agent 阅读
[`skills/bili-video2book/references/install.md`](skills/bili-video2book/references/install.md) 自行判断。
仓库已备好各平台声明：`.codex-plugin/plugin.json`（Codex）、`.claude-plugin/plugin.json`（Claude Code）、
`.agents/plugins/marketplace.json`（通用 agents）、`.opencode/INSTALL.md`（OpenCode）。

**手动安装**（任何平台都可用）：把 `skills/bili-video2book/` 复制或软链到该平台的技能目录。

| 平台 | 用户级 | 项目级 |
| :--- | :--- | :--- |
| Claude Code | `~/.claude/skills/bili-video2book/` | `<项目>/.claude/skills/bili-video2book/` |
| Codex | `~/.codex/skills/bili-video2book/` | `<项目>/.codex/skills/bili-video2book/` |
| OpenCode | 见 `.opencode/INSTALL.md`（无打包插件，按目录安装） | `<项目>/.opencode/skills/bili-video2book/` |
| 通用 agents | `~/.agents/skills/bili-video2book/` | `<项目>/.agents/skills/bili-video2book/` |
| 其它平台 | 该平台自己的技能目录 | `<项目>/.<平台>/skills/bili-video2book/` |

> **工作目录契约**：技能的命令写成 `python src/cli.py …` / `python scripts/…` 的相对形式，
> **请以技能目录（`SKILL.md` 所在目录）为当前工作目录执行**——工具链就在同一个目录里。
>
> **诚实边界**：除末行兜底外，表内每行的安装位都有公开依据；其它平台请以**该平台实际**的工具与目录
> 为准，不要照搬别处看到的路径（`references/install.md` 有手动安装三法，`references/host-tools/` 有工具名映射与判断方法）。

### 4. 本地安装与命令行使用

```bash
git clone https://github.com/LINJIANG12/bili-video2book.git
cd bili-video2book

# 可选：安装为全局命令行工具
pip install -e .
```

### 5. 环境要求与缺失处理

| 依赖 | 必需性 | 缺失时 |
| :--- | :--- | :--- |
| Python 3.8+ | 必需 | 工具链无法启动（无非 Python 实现，请先安装解释器） |
| ffmpeg（在 `PATH`） | 必需 | 本地媒体在取音频阶段失败并打印三平台安装命令；B 站下载会退化为不转码保存，请以 `info` 为准 |
| ffprobe | 可选 | 自动降级为 `ffmpeg -i` 解析时长，流程照常 |
| `read_audio` 或 `read_media` | 必需 | 阶段一停下并要求先挂载其一，不会跳过音频保真 |

```bash
# 以下命令在技能目录（skills/bili-video2book/）下执行
python src/cli.py info        # 一次看全：Python 版本 / ffmpeg / ffprobe / 听音通道 / 三域路径
python scripts/selfcheck.py   # 全量契约自检（技能自包含 + 多宿主声明 + Python 3.8 兼容）
```

`info` 会把每个缺失项连同**可照做的下一步**一起打印：ffmpeg 缺失时给出
`winget install Gyan.FFmpeg` / `brew install ffmpeg` / `apt install ffmpeg`；Python 低于 3.8 时明确提示升级；
两条听音通道都不可用时提示先挂载。五类缺失情形与降级口径详见 [SKILL.md §8](skills/bili-video2book/SKILL.md)。

---

## CLI 使用指南

若已执行 `pip install -e .`，可直接使用 `bili-video2book`；亦可在**技能目录**（`skills/bili-video2book/`）下
直接运行 `python src/cli.py`。下文所有 `python src/cli.py …` / `python scripts/…` 示例均**以技能目录为当前工作目录**。
产物一律落在产物根（默认 `<容器根>/output/`），与代码目录分离；下文示例中的 `output/<task>/…` 均**相对产物根**。

### 场景一：处理整门课程流水线
```bash
# 处理整门 B 站网课合集（--article-type 必填，不传即 exit 4）
bili-video2book pipeline "https://www.bilibili.com/video/BV14VqVBrEhc" --all --article-type learning

# 处理本地整套视频课程目录
bili-video2book pipeline "D:\courses\software_engineering\" --all --article-type learning
```

### 场景二：处理指定分集或区间
```bash
# 处理第 1 讲
bili-video2book pipeline "https://www.bilibili.com/video/BV14VqVBrEhc" --page 1 --article-type learning

# 处理第 2 讲至第 5 讲
bili-video2book pipeline "https://www.bilibili.com/video/BV14VqVBrEhc" --range 2-5 --article-type learning
```

### 场景三：生成模块合辑教材
在阶段一单集长文生成完毕后，整编生成模块教材：
```bash
bili-video2book cluster-articles "https://www.bilibili.com/video/BV14VqVBrEhc"
```

### 场景四：生成思维导图复习笔记
```bash
# 复习笔记：笔记只有一种风格，无需 --style
# 两趟规划（模块 ➔ 归并成笔记）都由 Agent 产出；缺规划不会卡住，命令始终正常退出
bili-video2book cluster-notes "https://www.bilibili.com/video/BV14VqVBrEhc"

# --force：强制重导全部笔记任务书
#          （已产出笔记成品的篇默认自动复用）
bili-video2book cluster-notes "https://www.bilibili.com/video/BV14VqVBrEhc" --force

# --force-plan：强制重出两趟规划任务书（忽略盘上旧规划，重新做模块划分与笔记归并）
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
> 每个类别保留编号最小的 1 份作为提示词范本；`topic_plan_TASK.md` / `note_plan_TASK.md` 属课程级规划任务书，永不回收。

---

## 凭证说明：B 站 SESSDATA 配置

在批量抓取多 P 长篇网课时，建议提供登录凭证，避免频繁请求触发 B 站 412 频控限制：

1. 在浏览器登录 bilibili.com；
2. 按 `F12` 打开开发者工具 -> Application -> Cookies -> `https://www.bilibili.com`；
3. 复制 `SESSDATA` 项对应的值；
4. 二选一使用：

```bash
# 方式一：一次性传入（仅作用于本次执行）
bili-video2book pipeline "<链接>" --all --article-type learning --sessdata "<SESSDATA>"

# 方式二：持久化保存（推荐，保存一次后续命令免传）
python src/cli.py login --sessdata "<SESSDATA>"
bili-video2book pipeline "<链接>" --all --article-type learning
python src/cli.py info     # 查看凭证来源与脱敏指纹
python src/cli.py logout   # 撤销保存
```

> **安全提示**：持久化的凭证以明文存于 `output/.sessdata.json`，该路径已被 `.gitignore` 排除，不会进入版本库；命令行 `--sessdata` 参数优先级始终高于本地存档。SESSDATA 等同你的 B 站登录态，请勿复制、上传或分享该文件。

---

## 许可证

本项目基于 [MIT License](LICENSE) 开源。
