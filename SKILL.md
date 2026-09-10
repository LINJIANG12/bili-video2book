---
name: bili-video2book
description: 将 B 站长视频/系列网课或本地音视频重构为精读教材长文、模块合辑全书与思维导图笔记。提供音频提取、两阶段门禁调度、多模态原生听音撰写与知识整编的完整工具链。
license: MIT
compatibility: Python 3.8+, ffmpeg in PATH, Multimodal LLM Agent (Antigravity, ChatGPT/Codex)
metadata:
  author: LINJIANG12
  version: 1.6.0
  category: learning-and-education
---

# Bili-Video2Book: 视频网课重构教材与复习笔记 Skill

本 Skill 面向 AI Agent（Antigravity、OpenAI Codex / ChatGPT 等）与系统终端，用于将 B 站长视频/系列网课或本地音视频转换为结构化技术教材、模块合辑全书与思维导图复习笔记。

---

## 1. 核心原则：黑盒编排与工具调用者公约 (Black-Box Operator Contract)

执行本 Skill 的 AI 模型必须时刻牢记自身定位为**高层流水线编排者（Orchestrator）与内容创作者**，严禁以“程序员重构源码”的心态处理任务：

> [!IMPORTANT]
> **【三大不可逾越的执行红线】**：
> 1. **黑盒调用原则（严禁窥探与私造脚本）**：
>    - 严禁阅读或修改底层实现源码（如 `src/` 内部代码）来寻找“捷径”；
>    - **严禁编写任何 `gen_*.py` 等离线批量造文脚本**来伪造、填充产物。所有任务必须通过官方 CLI 命令与原生多模态工具链推进；
> 2. **音频事实保真原则（Strict Audio Grounding）**：
>    - 所有 `articles/PXX_*.md` 的撰写，必须建立在调用 `read_audio(output_mode="file")` 提取切片并通过 `view_file` 真正聆听音频的基础之上；
>    - 正文必须包含原视频讲师亲口讲述的真实案例、例题或板书比喻（Grounding Evidence），严禁脱离音频凭空脑补；
> 3. **拒绝模板八股与脱缰黑话（Anti-Template & Context Preservation）**：
>    - **严禁所有分集机械克隆相同的标题套路**（例如 100% 分集强套 `## 1. 为什么需要它：现实痛点与历史由来` 属于严重违规）；
>    - 开篇必须根据本讲特性自然切入（概念定义、语法实操、算法演算或系统机理）；
>    - 高校经典基础课（如数据结构、操作系统、数据库）严禁脱离课程实际，生搬硬套互联网大厂“微服务”、“分布式架构师”、“NVMe SSD”等浮夸黑话。

---

## 2. 凭证配置：B 站任务 SESSDATA 说明

当处理 B 站（bilibili.com 或 BV 号）合集任务时，建议提供 `SESSDATA` 登录凭证，以保障高并发抓取稳定性并避免触发 412 频控限制。本地音视频或非 B 站任务自动跳过此项。

### 获取与使用方式
1. 浏览器访问 bilibili.com 登录；
2. 按 `F12` 打开开发者工具 -> Application（应用） -> Cookies -> `https://www.bilibili.com`；
3. 复制 `SESSDATA` 对应的值；
4. 执行命令时追加 `--sessdata "<SESSDATA>"` 参数（仅保留于当前进程环境）。

---

## 3. 标准作业流程 (Standard Operating Procedures - SOP)

整个重构流水线分为一个准备阶段与两个核心阶段，Agent 只需按顺序执行指定命令与工具：

```text
[输入 URL 或本地课程目录]
          │
          ▼
【准备阶段：结构解析与音频双轨直出】
  python src/cli.py pipeline "<链接或路径>" [--all | --range X-Y] [--sessdata "..."]
  ├── 解析分 P 结构 (parts.json)
  ├── 流式下载 16kHz 单声道音频至 audio/
  └── 自动去重校验：python src/cli.py dedup "<链接或路径>"
          │
          ▼
【阶段一：单集教材长文直出 (极速多模态听音，零中间逐字稿)】
  运行 python scripts/queue_tracker.py --next 5 获取待办分集：
  ├── 1. 提取切片：read_audio(file_path="...", output_mode="file", duration_minutes=15)
  ├── 2. 多模态听音：view_file(slice_path) 原生感知讲师原声与板书案例
  ├── 3. 编写教材：依音频实际讲解内容撰写深入技术长文 (载入 ARTICLE_LEARNING_PROMPT)
  ├── 4. 写入长文：write_to_file 写入 articles/PXX_*.md (严格保留，严禁八股模板)
  └── 5. 验收门禁：python scripts/queue_tracker.py 确认 100% 达标后方可放行
          │
          ▼
【阶段二：按模块统一收敛整编（三步门禁，需 Agent 往返）】
  单集文章全部就绪后，通过官方 CLI 聚合（严禁手工写脚本拼接）：
  ├── ① 规划：python src/cli.py cluster-notes "<链接>" --style minimal
  │      首跑导出 topic_plan_TASK.md ➔ Agent 写入 topic_plan.json ➔ 重跑
  ├── ② 知识元：重跑后工具链导出 subtitles/kernels/PXX_*_KERNEL_TASK.md
  │      ➔ Agent 逐集写入 PXX_*_kernel.json（须含 "status": "extracted"）➔ 重跑
  ├── ③ 融合：知识元齐备后自动导出 notes/模块XX_*_TASK.md ➔ Agent 撰写模块笔记
  ├── 模块合辑教材：python src/cli.py cluster-articles "<链接或路径>"  --> 生成 textbooks/
  └── 交付纪律：articles/ 下单集教材长文必须 100% 完整保留，供逐讲查阅
```

---

## 4. 阶段一：单集教材长文直出执行规范

### 4.1 任务来源

先由工具链导出任务书（`pipeline` 或 `transcribe` 命令），产物位于 `articles/PXX_*_TASK.md`，内含该集音频切片清单与 `ARTICLE_LEARNING_PROMPT`。

### 4.2 工具链调用链路

1. **取切片**：对任务书清单中的切片调用 MCP 工具 `omni-media:read_audio`：
   ```json
   {
     "file_path": "<task_dir>/audio/P01_xxx.m4a",
     "output_mode": "file",
     "duration_minutes": 15
   }
   ```
   返回文本包含切片本地绝对路径与续读参数（`start_time` / `duration_minutes`）；
2. **多模态感知**：调用宿主原生 `view_file` 工具读取切片绝对路径，直接聆听讲师原声、例题推导与板书讲解；超长音频按返回的续读参数逐片听完；
3. **教材编写**：
   - 载入任务书内的 `ARTICLE_LEARNING_PROMPT`；
   - 结合**真正听到**的案例、例题、板书比喻因材施教撰写长文，严禁脱离音频凭空脑补；
4. **落盘保存**：调用 `write_to_file` 写入 `output/<task>/articles/PXX_*_精读文章.md`（≥ 1000 字节方视为完成）。

### 4.3 阶段验收

```bash
python scripts/queue_tracker.py --next 5     # 列出待办分集及其音频/长文目标路径
python scripts/queue_tracker.py --summary    # 单行状态：TOTAL/DONE/PENDING/STAGE1_DONE
```

仅当 `STAGE1_DONE=1`（全部分集长文均 ≥ 1000 字节）时，方可进入阶段二。

---

## 5. 阶段二：模块整编执行规范（三步门禁）

阶段二由工具链与 Agent 交替推进：`cluster-notes` 需按门禁**分次重跑**，每次重跑都会自动复用已产出的文件，不会重复劳动。

### 5.1 第一步：模块边界规划（TOPIC_PLAN_TASK）

```bash
python src/cli.py cluster-notes "<链接或路径>" --style minimal
```

首次运行（尚无 `topic_plan.json`）会导出规划任务书后退出：

- **任务书**：`output/<task>/topic_plan_TASK.md`
- **目标文件**：`output/<task>/topic_plan.json`

Agent 需读取任务书中的规划提示词，产出 JSON Array 并写入目标文件。硬性约束：

1. 分集 `1..N` 必须被**唯一**覆盖，不得遗漏、重复或越界（`validate_plan` 会校验）；
2. 每个知识块通常包含 1~3 集；`block_title` 必须由真实语料提炼，不得照抄分集标题。

若规划缺失或非法，工具链会重新导出任务书并以 `exit 2` 退出，**不会**采用任何本地关键词聚类结果。

### 5.2 第二步：知识元抽取（KERNEL_TASK）

规划就绪后重跑同一命令，工具链会为每个模块的每一集导出知识元任务书：

- **任务书**：`output/<task>/subtitles/kernels/PXX_*_KERNEL_TASK.md`
- **目标文件**：`output/<task>/subtitles/kernels/PXX_*_kernel.json`

Agent 需以该集 `articles/PXX_*_精读文章.md` 为语料，按任务书提示词抽取知识元并写入 JSON，且**必须包含** `"status": "extracted"`（缺少该字段或字段值不符将不被识别）。

> [!IMPORTANT]
> **知识元门禁**：任一集知识元缺失时，该模块的笔记合成会被跳过并打印待办；工具链不会用机械截断或启发式内容冒充知识元。

### 5.3 第三步：模块笔记融合（SYNTHESIS_PROMPT）

相关分集的知识元齐备后重跑同一命令，自动导出融合任务书：

- **任务书**：`output/<task>/notes/模块XX_<主题>_TASK.md`

Agent 依据任务书内的 `SYNTHESIS_PROMPT` 与 `--style` 指定风格撰写模块笔记，落盘至 `output/<task>/notes/`。

### 5.4 模块合辑教材（无需语义往返）

```bash
python src/cli.py cluster-articles "<链接或路径>"
```

直接以 `articles/` 为输入整编为 `textbooks/模块XX_<主题>_精读全书.md`，自动将单章标题降级并补充承前启后段落。`articles/` 完整保留，不做任何删除。

### 5.5 任务书与目标文件对照表

| 环节 | 任务书（Agent 读取） | 目标文件（Agent 写入） | 复用/放行条件 |
| :--- | :--- | :--- | :--- |
| 阶段一 单集长文 | `articles/PXX_*_TASK.md` | `articles/PXX_*_精读文章.md` | 文件 ≥ 1000 字节 |
| 阶段二① 模块规划 | `topic_plan_TASK.md` | `topic_plan.json` | 1..N 覆盖唯一且合法 |
| 阶段二② 知识元 | `subtitles/kernels/PXX_*_KERNEL_TASK.md` | `subtitles/kernels/PXX_*_kernel.json` | `status == "extracted"` |
| 阶段二③ 模块笔记 | `notes/模块XX_*_TASK.md` | `notes/模块XX_*_笔记.md` | 知识元齐备即导出 |

> [!TIP]
> 所有任务书均为「读完即写盘」模式：工具链只负责准备语料、渲染提示词与校验产物，**真正的语义工作全部由宿主 Agent 完成**。

---

## 6. CLI 常用命令速查表

所有任务必须通过以下标准入口调用（功能一致，三选一均可）：
- 仓库推荐：`python src/cli.py <子命令>`
- 免安装脚本：`python scripts/run.py <子命令>`
- 系统命令：`bili-video2book <子命令>`

```bash
# 1. 解析合集结构与时长
python src/cli.py parse "<链接或本地目录>" [--json]

# 2. 执行音频下载流水线（阶段一：收音频 + 派发单集文章任务书）
python src/cli.py pipeline "<链接或本地路径>" --all
python src/cli.py pipeline "<链接或本地路径>" --range 1-10

# 3. 单集文章任务书（零中间逐字稿；已存在长文则跳过）
python src/cli.py transcribe "<链接或本地路径>" [--page N]

# 4. 音频指纹去重（自动复用相同分集的语料与长文，0 Token 消耗）
python src/cli.py dedup "<链接或本地路径>"

# 5. 动态任务队列追踪器（查看待办分集与阶段门禁状态）
python scripts/queue_tracker.py --next 5
python scripts/queue_tracker.py --summary

# 6. 阶段二：整编模块教材全书（输出至 textbooks/，原有 articles/ 完整保留）
python src/cli.py cluster-articles "<链接或本地路径>"

# 7. 阶段二：模块复习笔记（CS-Xmind-Note 精简树状风格）
#    注意：需按 § 5 的三步门禁分次重跑（规划 ➔ 知识元 ➔ 融合）
python src/cli.py cluster-notes "<链接或本地路径>" --style minimal
python src/cli.py cluster-notes "<链接或本地路径>" --style minimal --replace  # 替换旧单集笔记

# 8. 环境与工具链自检
python scripts/selfcheck.py
python src/cli.py info
```

> 阶段一的音频切片依赖 MCP 工具 `omni-media:read_audio`，接入方式见 README 的安装章节。

---

## 7. 交付产物与格式标准

完成处理后，系统输出三类结构化资产：

| 产物 | 路径 | 说明 |
| :--- | :--- | :--- |
| **单集教材长文** | `output/<task>/articles/PXX_*_精读文章.md` | 每集独立长文，含完整推导演算与真实教学案例。模块整编后**严格保留，不予删除** |
| **模块复习笔记** | `output/<task>/notes/模块XX_*_笔记.md` | 跨集知识点归纳。系统**不设默认风格**，必须显式指定 `--style`（推荐 `minimal`，对齐 408 考研树状导图，支持 Markmap / XMind 导入） |
| **模块合辑教材** | `output/<task>/textbooks/模块XX_*_精读全书.md` | 按知识模块编排的完整合辑教材，含全景导读与章节逻辑过渡 |

### 7.1 工作区目录结构

```text
output/<task>/
├── audio/                     # 提取的音频与自动切片
├── parts.json                 # 分集拓扑缓存（接口受阻时离线自愈依赖）
├── manifest.json              # 任务清单与断点续跑状态
├── topic_plan.json            # ① 模块规划（Agent 产出）
├── topic_plan_TASK.md         # ① 规划任务书
├── articles/                  # 单集长文 + 各环节任务书
│   ├── PXX_*_TASK.md          #   单集长文任务书
│   └── PXX_*_精读文章.md       #   单集长文（最终产物）
├── subtitles/kernels/         # ② 知识元与任务书
├── notes/                     # ③ 模块笔记与任务书
└── textbooks/                 # 模块合辑教材
```

### 7.2 断点续跑

工具链以磁盘产物为唯一进度依据，重跑同一条命令即可续作：

- 单集长文、模块规划、知识元、模块笔记均按 § 5.5 表格的条件自动复用；
- 删除 `output/` 下某个产物文件，即视为重新派发该环节；
- 用 `python scripts/queue_tracker.py --next 5` 查看阶段一待办队列，`--summary` 获取单行状态。

详细结构模板、各类型课程开篇示范与排版规范请查阅：[references/delivery_matrix.md](references/delivery_matrix.md)。
