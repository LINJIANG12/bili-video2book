---
name: bili-video2book
description: 将 B 站长视频/系列网课或本地音视频重构为精读教材长文、模块合辑全书与思维导图笔记。提供音频提取、两阶段门禁调度、多模态原生听音撰写与知识整编的完整工具链。
license: MIT
compatibility: Python 3.8+, ffmpeg in PATH, Multimodal LLM Agent (Antigravity, ChatGPT/Codex)
metadata:
  author: LINJIANG12
  version: 2.0.0
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
> 4. **提示词风格红线（Prompt-Style Gate）**：
>    - 当前提供两种长文风格：**`learning`「学习」（推荐，当前版）** 与 **`legacy`「旧版」（原稳定版，教材腔、随堂自测）**；
>    - **风格由用户确认**：`pipeline` / `transcribe` 都必须带 `--article-type`；未指定时工具层打印风格菜单并在交互终端请用户当场选择，
>      仍然确认不了就**以退出码 4 终止任务**（工具层不猜、不兜底）；
>    - 另有咨询答疑 / 访谈对谈 / 测评体验 / 直播闲聊四种形态只登记、未提供提示词：命中即终止；
>      **严禁换个名字硬套、严禁手工套用别的提示词继续写**。

---

## 2. 凭证配置：B 站任务 SESSDATA 说明

当处理 B 站（bilibili.com 或 BV 号）合集任务时，建议提供 `SESSDATA` 登录凭证，以保障高并发抓取稳定性并避免触发 412 频控限制。本地音视频或非 B 站任务自动跳过此项。

### 获取方式
1. 浏览器访问 bilibili.com 登录；
2. 按 `F12` 打开开发者工具 -> Application（应用） -> Cookies -> `https://www.bilibili.com`；
3. 复制 `SESSDATA` 对应的值。

### 使用方式（二选一）
1. **一次性**：命令追加 `--sessdata "<SESSDATA>"`，仅作用于本次执行；
2. **持久化（推荐）**：执行一次 `python src/cli.py login --sessdata "<SESSDATA>"`，之后所有命令自动使用，无需重复传参。

```bash
python src/cli.py login --sessdata "<SESSDATA>"   # 保存凭证
python src/cli.py info                            # 查看凭证来源与脱敏指纹
python src/cli.py logout                          # 撤销保存
```

> [!WARNING]
> **凭证安全须知**：持久化的 SESSDATA 以明文存于 `output/.sessdata.json`，该路径已被 `.gitignore` 排除（另有显式规则兜底），不会进入版本库；命令行参数 `--sessdata` 的优先级始终高于本地存档。SESSDATA 等同你的 B 站登录态，请勿复制、上传或分享该文件；若怀疑泄露，请到 B 站退出登录使其失效，并运行 `logout` 清除本地存档。

---

## 3. 标准作业流程 (Standard Operating Procedures - SOP)

> [!IMPORTANT]
> **运行前置（三域布局与工作目录契约）**：本仓库是**技能域**，只含代码与文档；MCP 服务与产物各自独立成域：
>
> ```text
> <容器根>/
> ├── skill/     ← 本仓库（技能/CLI/脚本；命令里的 src/ 与 scripts/ 都指这里）
> ├── mcp/       ← 独立仓库：omni-media MCP 服务（与技能无运行时依赖）
> └── output/    ← 产物根：各课程工作区 + .sessdata.json / .wbi_keys.json / .cli_status.json
> ```
>
> - 所有命令写成 `python src/cli.py …` / `python scripts/…` 的相对形式，**请以本仓库根（`skill/`）为当前工作目录执行**；
> - **产物根默认就是容器根下的 `output/`**，与代码彻底分离：命令可在任意目录执行（`--base-dir` 缺省即产物根，绝对路径）；
>   需要改位置时用 `--base-dir <路径>`，或设 `BVB_HOME`（容器根）/ `BVB_OUTPUT_DIR`（产物根）；
> - `.agents/skills/bili-video2book/` 里只有 `SKILL.md` 与 `references/`，**不含 `src/`、`scripts/`**：
>   挂载为全局 Skill 时请保持**整个仓库可达**（整仓复制或软链），不要只复制 SKILL.md。

整个重构流水线分为一个准备阶段与两个核心阶段，Agent 只需按顺序执行指定命令与工具：

```text
[输入 URL 或本地课程目录]
          │
          ▼
【第 0 步：确认长文提示词风格（工作流启动前，不可跳过）】
  从风格菜单中选一种 ➔ 显式传 --article-type <风格键>（或由工具在交互终端当场询问）
  ├── learning「学习」（推荐，当前版）／ legacy「旧版」（原稳定版）➔ 继续
  └── 未指定且确认不了 / 拼写错误 / 命中未提供提示词的形态
        ➔ 打印风格菜单 + exit 4 终止任务（不猜、不降级、不硬套）
          │
          ▼
【准备阶段：结构解析与音频双轨直出】
  python src/cli.py pipeline "<链接或路径>" [--all | --range X-Y] --article-type learning [--sessdata "..."]
  ├── 解析分 P 结构 (parts.json)
  ├── 流式下载 16kHz 单声道音频至 audio/
  └── 可选去重：python src/cli.py dedup "<链接或路径>"（pipeline 不会自动调用，需手动执行）
          │
          ▼
【阶段一：单集教材长文直出 (极速多模态听音，零中间逐字稿)】
  运行 python scripts/queue_tracker.py --next 5 获取待办分集：
  ├── 1. 提取切片：read_audio(file_path="...", output_mode="file")（切片已按 60 分钟预算切好，一次听完）
  ├── 2. 多模态听音：view_file(slice_path) 原生感知讲师原声与板书案例
  ├── 3. 编写教材：依音频实际讲解内容撰写深入技术长文 (载入 ARTICLE_LEARNING_PROMPT)
  ├── 4. 写入长文：write_to_file 写入 articles/PXX_*.md (严格保留，严禁八股模板)
  └── 5. 验收门禁：python scripts/queue_tracker.py 确认 100% 达标后方可放行
          │
          ▼
【阶段二：按模块统一收敛整编（两趟门禁，需 Agent + 子智能体往返）】
  单集文章全部就绪后，通过官方 CLI 聚合（严禁手工写脚本拼接）：
  ├── ① 规划（第一趟）：python src/cli.py cluster-notes "<链接>"
  │      首跑导出 topic_plan_TASK.md ➔ Agent 写入 topic_plan.json ➔ 重跑
  ├── ② 笔记（第二趟）：规划就绪后自动逐模块导出 notes/模块XX_*_TASK.md
  │      ➔ 主 Agent 派子智能体（一模块一个）逐篇读完该模块 articles/ 后撰写模块笔记
  ├── 模块合辑教材：python src/cli.py cluster-articles "<链接或路径>"  --> 生成 textbooks/
  ├── 质检门禁：python scripts/note_quality_check.py --strict（笔记成色）
  │            python scripts/render_compat_check.py --strict（渲染合规）
  ├── 收尾：python src/cli.py cleanup（回收任务书，每类留 1 份范本）
  │        python src/cli.py sync（按磁盘对账回填 manifest）
  └── 交付纪律：articles/ 下单集教材长文必须 100% 完整保留，供逐讲查阅
```

---

## 4. 阶段一：单集教材长文直出执行规范

### 4.0 长文提示词风格（用户确认，工作流第一步）

当前提供两种长文写出风格，**由用户确认后使用**。跑 `pipeline` / `transcribe` 时显式传 `--article-type`；不传则打印菜单并在交互终端询问，确认不了即终止任务：

| 风格键 | 名称 | 写出取向 | 状态 |
| :--- | :--- | :--- | :--- |
| `learning` | **学习** | 保住讲师讲课口吻（我/我们/你们、比喻、轶事、临场判断）+ 比读教材轻松 + 高信息密度 + 技术文档式朴素标题；正文可读、好看 | **推荐（当前版）** |
| `legacy` | **旧版** | 改写前的原稳定版：客观学术第一视角、充分展开推导、去口语化、随堂自测 | 已提供（逐字保留） |
| `consulting` / `interview` / `review` / `livestream` | 咨询答疑 / 访谈对谈 / 测评体验 / 直播闲聊 | — | 已登记，**提示词未提供**（命中即终止） |

未指定类型、拼写无法命中、或判为「提示词未提供」的类型时，命令会**打印类型菜单并以退出码 4 终止任务**，不会落盘任何任务书。此时既不要换个类型名重试，也不要手工套用别的提示词继续写。

命中的类型会写进任务书抬头（`> 长文类型：…`）并记入 `manifest.json` 的 `article_type` 字段，便于回查这一篇是按哪套提示词写的。

### 4.1 任务来源

先由工具链导出任务书（`pipeline` 或 `transcribe` 命令），产物位于 `articles/PXX_*_TASK.md`，内含该集音频切片清单与所选类型的文章撰写提示词。

### 4.2 工具链调用链路

1. **取切片**：对任务书清单中的切片调用 MCP 工具 `omni-media:read_audio`：
   ```json
   {
     "file_path": "<task_dir>/audio/P01_xxx.m4a",
     "output_mode": "file"
   }
   ```
   任务书里的切片本就是按 **60 分钟预算**切好的（每片 ≤ 60 分钟，`omni-media` 对 ≤ 75 分钟文件一次性整片就绪），
   因此**不要传 `duration_minutes`**，一次听完整片即可；只有返回文本里 `OMNI_STATUS` 显示 `is_finished=false`（超长媒体自动分卷）时，
   才用返回的 `start_time` / `duration_minutes` 续读下一卷；
2. **多模态感知**：调用宿主原生 `view_file` 工具读取切片绝对路径，直接聆听讲师原声、例题推导与板书讲解；超长音频按返回的续读参数逐片听完；
3. **教材编写**：
   - 载入任务书内所选类型的文章撰写提示词（当前提供 `learning` 学习版与 `legacy` 旧版）；
   - 结合**真正听到**的案例、例题、板书比喻因材施教撰写长文，严禁脱离音频凭空脑补；
   - 讲师只在幻灯片上展示、音频里没有逐字念出的代码或表格**不要替他补写**，更不要基于补写出来的内容做逐行解析；
4. **落盘保存**：调用 `write_to_file` 写入 `output/<task>/articles/PXX_*_精读文章.md`（≥ 1000 字节方视为完成）。

### 4.3 阶段验收

```bash
python scripts/queue_tracker.py --next 5     # 列出待办分集及其音频/长文目标路径
python scripts/queue_tracker.py --summary    # 单行状态：TOTAL/DONE/PENDING/STAGE1_DONE
python scripts/queue_tracker.py --pattern "<目录名关键字>"   # 多课程并存时指定工作区（否则取最近活动的那个）
```

仅当 `STAGE1_DONE=1`（全部分集长文均 ≥ 1000 字节）时，方可进入阶段二。

---

## 5. 阶段二：模块整编执行规范（两趟门禁 + 子智能体派发）

阶段二由工具链与 Agent 交替推进：`cluster-notes` 需按门禁**分次重跑**，每次重跑都会自动复用已产出的文件，不会重复劳动。

### 5.1 第一步：模块边界规划（TOPIC_PLAN_TASK）

```bash
python src/cli.py cluster-notes "<链接或路径>"
```

首次运行（尚无 `topic_plan.json`）会导出规划任务书后退出：

- **任务书**：`output/<task>/topic_plan_TASK.md`
- **目标文件**：`output/<task>/topic_plan.json`

Agent 需读取任务书中的规划提示词，产出 JSON Array 并写入目标文件。硬性约束：

1. 分集 `1..N` 必须被**唯一**覆盖，不得遗漏、重复或越界（`validate_plan` 会校验）；
2. 每个知识块通常包含 1~3 集；`block_title` 必须由真实语料提炼，不得照抄分集标题。

若规划缺失或非法，工具链会重新导出任务书并以 `exit 2` 退出，**不会**采用任何本地关键词聚类结果。

### 5.2 第二步：模块笔记融合（MODULE_NOTE_TASK，文章直供）

规划就绪后重跑同一命令，工具链逐模块校验**该模块各集单集精读长文是否齐备**，齐备即导出模块笔记任务书：

- **任务书**：`output/<task>/notes/模块XX_<主题>_TASK.md`
- **目标文件**：`output/<task>/notes/模块XX_<主题>_笔记.md`
- **语料**：该模块各集 `articles/PXX_*_精读文章.md`（任务书中列出**路径清单 + 字节数**）

Agent 需按任务书内的 `MODULE_NOTE_PROMPT`（专属提示词）撰写，并逐条落实其中的**结构要求**、**密度纪律（只写结论、不写推导）**、**零套话禁令**与**笔记版式规范**；笔记只有这一种风格，无需再指定 `--style`。若某模块尚有分集没有长文，该模块会被跳过并打印待办，其余模块照常推进。

> [!IMPORTANT]
> **语料纪律（v1.7 起）**：模块笔记的唯一事实来源是**单集精读长文**；知识元（kernel）已从「前置门禁」降级为「可选索引」——默认不参与，只有显式追加 `--kernel-index` 时才会把历史知识元作为定位索引注入。原因是空壳知识元会把笔记质量一并拖垮。

### 5.3 子智能体派发规范（推荐做法）

模块笔记的撰写工作量大且各模块彼此独立，**推荐由主 Agent 派子智能体并行产出**（一个模块一个子智能体）：

| 环节 | 做法 |
| :--- | :--- |
| 派发粒度 | **一个模块 = 一个子智能体**，互不交叉，避免上下文互相污染 |
| 输入 | 子智能体自行读取该模块的任务书 + 按清单**逐篇整篇读完**该模块全部 `articles/`（主 Agent 不代读） |
| 输出 | 子智能体只写 `notes/模块XX_*_笔记.md`，**不回传正文**；回报固定一行：`模块XX \| 文件路径 \| 字节数 \| 覆盖分集 \| 套话0/分集标题0/断句0` |
| 并发 | 建议 5~6 个并发；模块多时分批派发（例如 5+5+1） |
| 返修 | 质检不达标时，把质检脚本输出的「文件:行号:原文」贴给该模块子智能体重派，最多 2 轮；仍不达标则由主 Agent 亲自返修该模块 |

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
| 阶段二② 模块笔记 | `notes/模块XX_*_TASK.md` | `notes/模块XX_*_笔记.md` | 该模块各集长文齐备即导出 |
| 阶段二③ 模块教材 | ——（纯工具整编） | `textbooks/模块XX_*_精读全书.md` | `articles/` 齐备即整编 |

> [!TIP]
> 所有任务书均为「读完即写盘」模式：工具链只负责准备语料、渲染提示词与校验产物，**真正的语义工作全部由宿主 Agent（通常为子智能体）完成**。

### 5.6 交付前质检与收尾（机器门禁）

```bash
python scripts/note_quality_check.py --strict    # 笔记成色：套话 / 空壳标题 / 分集标题 / 行内残缺引用 / 分集口吻 / 断句 / 结构缺件
python scripts/render_compat_check.py --strict   # 渲染合规：GitHub 告警块 / 围栏外字符画 / 围栏配对 / 语言标识
python src/cli.py cleanup --dry-run              # 任务书回收预演（成品产出后才回收，每类留 1 份范本）
python src/cli.py sync                           # 按磁盘对账回填 manifest.json
```

- **笔记成色致命项**（`套话填充 / 空壳标题 / 分集平铺标题 / 行内残缺引用 / 分集口吻`）在两套合格语料上实测均为 0，必须清零；
- **断句与结构缺件**为启发式警告项：默认按「每份 ≤ 4 处断句」提示，**结构缺件默认只报告不拦**，
  需要纳入门禁时显式加 `--require-structure`；
- **渲染致命项**为 `GitHub 告警块 / 围栏外裸字符画 / 围栏配对`；**围栏缺语言标识默认只提示不拦**，
  需要死守时加 `--require-lang`；
- 任务书是**临时派发物**：成品产出后由 `cleanup` 回收，每个类别保留编号最小的 1 份作为提示词范本；`topic_plan_TASK.md` 永不回收。

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
#    注意：--article-type 是长文提示词风格，由用户确认；learning=学习（推荐）/ legacy=旧版
#    未指定则打印风格菜单并当场询问，确认不了即 exit 4 终止
python src/cli.py pipeline "<链接或本地路径>" --all --article-type learning
python src/cli.py pipeline "<链接或本地路径>" --range 1-10 --article-type legacy

# 3. 单集文章任务书（零中间逐字稿；已存在长文则跳过）
python src/cli.py transcribe "<链接或本地路径>" --page 1 --article-type learning

# 4. 音频指纹去重（自动复用相同分集的语料与长文，0 Token 消耗）
python src/cli.py dedup "<链接或本地路径>"

# 5. 动态任务队列追踪器（查看待办分集与阶段门禁状态）
python scripts/queue_tracker.py --next 5
python scripts/queue_tracker.py --summary

# 6. 阶段二：整编模块教材全书（输出至 textbooks/，原有 articles/ 完整保留）
python src/cli.py cluster-articles "<链接或本地路径>"                             # 已有教材默认复用
python src/cli.py cluster-articles "<链接或本地路径>" --force                     # 按最新章节强制重编

# 7. 阶段二：模块复习笔记（只有一种版式）
#    注意：需按 § 5 的两趟门禁分次重跑（规划 ➔ 笔记），笔记建议由子智能体按模块并行产出
python src/cli.py cluster-notes "<链接或本地路径>"                                # 笔记只有一种风格，无需 --style
python src/cli.py cluster-notes "<链接或本地路径>" --force                        # 强制重导全部模块任务书
python src/cli.py cluster-notes "<链接或本地路径>" --force-plan                   # 强制重出 topic_plan_TASK（丢弃旧规划）
python src/cli.py cluster-notes "<链接或本地路径>" --kernel-index                 # 可选：注入历史知识元作索引
python src/cli.py cluster-notes "<链接或本地路径>" --replace                      # 替换 1.7 之前的旧版单集笔记

# 8. 交付前质检与收尾
python scripts/note_quality_check.py --strict      # 笔记成色体检（套话/空壳标题/分集标题/断句/结构缺件）
python scripts/render_compat_check.py --strict     # 渲染合规体检（告警块/裸字符画/围栏配对）
python src/cli.py cleanup --dry-run                # 任务书回收预演（成品产出后才回收，每类留 1 份范本）
python src/cli.py sync                             # 按磁盘对账回填 manifest.json

# 9. 环境与工具链自检
python scripts/selfcheck.py
python src/cli.py info

# 10. 登录凭证：持久化保存 SESSDATA（保存一次，后续命令免传）
python src/cli.py login --sessdata "<SESSDATA>"
python src/cli.py logout
```

> 阶段一的音频切片依赖 MCP 工具 `omni-media:read_audio`。MCP 服务是**独立仓库**（容器根下的 `mcp/`，与技能无运行时依赖），
> 装一次即可长期使用，接入方式见 README 的安装章节。

### 6.1 完整参数表（速查表之外的开关都在这里）

| 入口 | 参数 | 用途 |
| :--- | :--- | :--- |
| `parse` | `--limit N` / `--json` | 列表最多显示 N 条（默认 10）/ 输出 JSON |
| `audio` | `--page N` `--all` `--range X-Y` `--quality low\|medium\|high` `--url-only` `--output DIR` `--chunk-minutes N` `--json` `--force` | 单集或批量取音频；`--url-only` 只打印直链不下载；`--chunk-minutes` 默认 10；`--output` 覆盖音频目录 |
| `transcribe` | `--page N` `--output PATH` `--article-type <风格>` | 单集文章任务书；`--output` 仅在长文已存在时用于导出副本 |
| `pipeline` | `--all` `--range X-Y` `--page N` `--quality <档>` `--prefetch-workers N` `--skip-failed` `--chunk-minutes N`（默认 60） `--force` `--article-type <风格>` `--task NAME` `--base-dir DIR` | 阶段一主入口；`--skip-failed` 把音频失败集记入跳过名单继续跑；`--force` 重派已完成分集 |
| `cluster-notes` | `--force` `--force-plan` `--kernel-index` `--replace` `--block-id N` `--start-block N` `--end-block N` | 只处理指定模块区间时用后三个；`--replace` 备份并移除 1.7 之前的旧版单集笔记 |
| `cluster-articles` | `--force` | 默认复用已有教材，`--force` 按最新章节重编 |
| `dedup` | `--dry-run` | 只报告重复分集，不复制语料与长文 |
| `cleanup` | `--keep N`（默认 1） `--dry-run` `--task 关键字` `--all` | 每类保留 N 份任务书范本；`--all` 为兼容保留（不加即全量） |
| `sync` | `--dry-run` `--task 关键字` `--all` | 按磁盘对账回填 manifest |
| `note_quality_check.py` | `--strict` `--require-structure` `--max-truncated N`（默认 4） `--dir` `--task` `--base-dir` `--json` | 结构缺件默认只提示，`--require-structure` 才纳入门禁 |
| `render_compat_check.py` | `--strict` `--require-lang` `--dir` `--task` `--base-dir` `--json` | 语言标识默认只提示，`--require-lang` 才纳入门禁 |
| `queue_tracker.py` | `--next N` `--summary` `--json` `--dir PATH` `--pattern 关键字` `--base-dir DIR` | 多课程并存时必须用 `--dir`/`--pattern` 指定工作区；`--base-dir` 缺省即产物根 |
| `cleanup_tasks.py` | `--keep N` `--dry-run` `--task` `--json` `--strict` | `cleanup` 的独立脚本入口（功能一致） |

---

## 7. 交付产物与格式标准

完成处理后，系统输出三类结构化资产：

| 产物 | 路径 | 说明 |
| :--- | :--- | :--- |
| **单集教材长文** | `output/<task>/articles/PXX_*_精读文章.md` | 每集独立长文，按该集所选**长文类型**的提示词撰写（`learning` 学习＝保住讲师讲课风格 + 高信息密度 + 成稿好读好看；`legacy` 旧版＝客观学术第一视角 + 随堂自测），含真实教学案例与讲师亲口讲的推导。模块整编后**严格保留，不予删除** |
| **模块复习笔记** | `output/<task>/notes/模块XX_*_笔记.md` | 跨集知识点归纳，按 § 7.4 的「笔记规范」产出。**笔记只有这一种风格**（旧版八种风格矩阵已删除），无需 `--style`；原生支持 Markmap / XMind 导入 |
| **模块合辑教材** | `output/<task>/textbooks/模块XX_*_精读全书.md` | 按知识模块编排的完整合辑教材，含全景导读与章节逻辑过渡 |

### 7.1 工作区目录结构

以下路径**均相对产物根**（默认 `<容器根>/output/`，与 `skill/`、`mcp/` 平级）：

```text
output/<task>/
├── audio/                     # 提取的音频与自动切片
├── parts.json                 # 分集拓扑缓存（接口受阻时离线自愈依赖；局部运行按 page 合并，不会截断）
├── manifest.json              # 任务清单与断点续跑状态（可用 `cli.py sync` 按磁盘对账回填）
├── topic_plan.json            # ① 模块规划（Agent 产出）
├── topic_plan_TASK.md         # ① 规划任务书（课程级唯一，永不回收）
├── articles/                  # 单集长文 + 派发任务书
│   ├── PXX_*_TASK.md          #   单集长文任务书（临时派发物，完成后回收，保留 P01 一份范本）
│   └── PXX_*_精读文章.md       #   单集长文（最终产物，严格保留）
├── subtitles/kernels/         # 知识元（可选索引；历史工作区遗留，默认不参与笔记生成）
├── notes/                     # ② 模块笔记 + 派发任务书（每模块保留 1 份任务书范本）
│   ├── 模块XX_*_TASK.md       #   模块笔记任务书（临时派发物，成品产出后回收）
│   └── 模块XX_*_笔记.md       #   模块笔记（跨集融合，阶段二产物）
└── textbooks/                 # ③ 模块合辑教材
```

产物根同时存放运行时状态文件：`.sessdata.json`（凭证，`cli.py login`）、`.wbi_keys.json`（WBI 签名密钥缓存）、
`.cli_status.json`（上次 412/熔断记录）。这些文件**永远不在代码仓库里**，因此不会被误提交。

> **处理范围**：流水线处理的是**当前稿件的 1..N 个分 P**（即 `parts.json` 的内容）。
> 若课程是「UGC 合集里每集独立 BV」，`parse` 会列出全季清单，但 `pipeline` / `cluster-*` **不会**跨稿件遍历，
> 需要逐集指定 BV 号分别处理。

> **产物命名兼容**：工具层的规范名是 `PXX_*_精读文章.md`，但复用判定走**宽容定位**
> （`KernelExtractor.find_article`）：历史工作区里形如 `PXX_<标题>.md` 的无后缀长文同样被认作已完成，
> 不会被要求重写。任务书（`*_TASK.md`）永远排除在产物判定之外。

> **任务书回收**：`*_TASK.md` 是工具层写给 Agent 的**临时派发物**，成品产出后由 `cli.py cleanup`
> （或 pipeline 收尾）自动回收，**每个类别保留编号最小的 1 份**作为提示词范本，便于随时翻阅写法。
> 成品尚未产出的任务书一律保留，不会误删进行中的派发。

### 7.2 断点续跑

工具链以磁盘产物为唯一进度依据，重跑同一条命令即可续作：

- 单集长文、模块规划、模块笔记、模块教材均按 § 5.5 表格的条件自动复用（模块笔记与模块教材命中成品即跳过，打印 `[cached]`）；
- 删除产物根下某个**产物**文件（如 `<产物根>/<task>/articles/PXX_*_精读文章.md`），即视为重新派发该环节；
- 任务书会被自动回收，因此**不要靠删除任务书来重派**。需要重导时的正确做法：
  - 模块笔记：`cluster-notes --force`；
  - 模块教材：`cluster-articles --force`；
  - 单集长文：`pipeline --force`（`transcribe` 没有 `--force`，重派请直接删除该集长文后再跑）；
- 用 `python scripts/queue_tracker.py --next 5` 查看阶段一待办队列，`--summary` 获取单行状态；多课程并存时加 `--pattern` / `--dir` / `--base-dir`；
- 若 `manifest.json` 与实际产物不一致（例如 Agent 直接写盘后清单未回填），执行 `python src/cli.py sync` 按磁盘对账。

### 7.3 阅读器与渲染兼容

三类交付物默认在 **Typora** 中阅读，同时兼容 VS Code Markmap 与 XMind 导入。交付产物必须遵守以下渲染硬约束：

- 字符画 / 拓扑图 / 框图**必须**放进 ` ```text ` 围栏；裸写在渲染时会被合并空格、彻底错位；围栏必须成对闭合；
- 提示类内容统一写 `> **提示**：……` / `> **易错点**：……`，**禁用** `> [!TIP]` 一类的 GitHub 专有告警块（旧版 Typora 会露出字面标记）；
- 代码块与围栏**必须标注语言标识**（字符画一律 `text`，不得留空语言）。
  > **门禁口径**：`render_compat_check.py --strict` 只把「告警块 / 围栏外裸字符画 / 围栏配对」当致命项；
  > **缺语言标识默认只统计不拦**（历史成品存在既有缺口），需要死守时加 `--require-lang`；
- 行内公式 `$…$` 需在 **Typora → 偏好设置 → Markdown → 勾选「内联公式」** 后才会正常渲染（这是阅读侧的一次性设置，请向使用者说明）。

> **范围说明**：本规范文档自身出现的告警块（`> [!IMPORTANT]` 等）仅用于提示阅读本文档的人与 Agent；**交付产物一律禁用该语法**，两者不可混淆。

### 7.4 笔记规范（交付硬约束，只有这一种风格）

模块笔记必须**按知识主题**组织，严禁按分集平铺。构件、禁令与密度纪律如下：

| 必备构件 | 要求 |
| :--- | :--- |
| H1 标题 | 用模块主题命名（不得是分集编号或分集标题） |
| 元信息抬头 | 紧随 H1 的 **2 行**引用块：`> 整理自《课程全称》Pxx~Pyy 单集精读长文` + `> 渲染支持：Typora / VS Code Markmap / XMind 一键脑图` |
| 知识拓扑树 | 一棵 ` ```text ` 围栏树，`├──`/`└──` 骨架 + `────` 引线**纵向对齐同一列**，一级节点标分集区间 |
| 主题分节 | `## 1. <主题>` … 每节首行 `> **一句话主旨**：…`（30~60 字） |
| 概念块 | `* **术语（English，缩写）**` → `* > 定义：…` → 条件/数值/规则/边界条目 → `* > 易错点：…`（确有才写） |
| 溯源标注 | 每个概念块末尾 `* > 来源: P03, P05` |
| **不收尾** | 写到最后一个知识主题就结束：**不写「速查卡」，也不写「一句话总纲」**（与树、条目重复，已废弃） |

| 禁令 | 说明 |
| :--- | :--- |
| 禁分集平铺标题 | 任何级别标题都不得是分集编号或分集标题（`### P16 …` / `### 第16讲 …` 一律不合格） |
| 禁分集口吻 | 正文不得出现「本集」「上一讲」「P16 中提到」「视频里说」（`> 来源:` 标注除外） |
| 禁套话填充 | 「概念属性与边界」「形式化表述与理论依据明确」「符合全国计算机专业考纲核心知识点」等无信息量句式 |
| 禁中途截断 | 转述与引用必须完整成句，不得砍在半句上 |
| 禁硬造子标题 | 没有并列关系的内容不凑 `###`；某标题下只讲得了一两句话就并回上一节 |

> **密度纪律（第一条）**：**只写结论，不写推导**——每条写清"是什么、条件是什么、数值是多少、规则怎么定、边界在哪里"就够了；不写"为什么"、不写推理过程、不写讲解铺垫，机理也压成一句话结论。实测这一条把笔记体量从长文的 105% 压到 62%（第 6~8 轮）。

> **两条排版硬约束**（都实测翻过车）：① 概念块里的 ` ```text ` 字符画**围栏整体缩进 4 空格**留在列表项内——写在第 0 列会终止列表、渲染时概念块断成两截；② 拓扑树末级注释**纵向对齐同一列**，宽度按「汉字 2 列、ASCII 1 列」计算。

以上禁令可由 `python scripts/note_quality_check.py --strict` 机器验收（在两套人工精修语料上实测均为 0 命中）。

详细结构模板、各类型课程开篇示范与完整渲染兼容规范请查阅：[references/delivery_matrix.md](references/delivery_matrix.md)。
