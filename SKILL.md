---
name: bilibili-audio-knowledge-extractor
version: 1.4.0
description: |
  Bilibili 视频与本地音视频提取、语音转录与结构化知识沉淀 Skill（宿主 Agent 原生合成架构）。
  支持任意 B 站视频/多P合集/本地视频文件/本地课程目录：多态识别、全格式通用 64k 纯音频剥离、
  10 分钟均衡切片、多模态直读与本地 whisper 语音转录、安全文本规范化、知识块规划与提示词导出。
  本 Skill 只负责【工具层】（提取/转录/清洗/规划/导出）；所有语义校对、体系笔记与
  【可替代视频级】精读长文均由宿主对话模型（Agent 自身）按导出的提示词原生完成。
triggers:
  - bilibili 视频笔记
  - B站视频转文章
  - 提取B站音频
  - 解析B站合集
  - 制作学习笔记
  - 整理视频
  - 本地视频转文章
  - 本地网课笔记
  - 本地视频提取音频
  - 课程总结
  - 视频精读
  - 公开课笔记
  - 全套课总结
  - bilibili.com/video/
  - b23.tv
  - BV号
---

# Bilibili 音频与结构化知识提取 Skill

## 核心定位与职责边界

本 Skill 采用【工具层 + 宿主 Agent 合成层】双层架构：

1. **转录与提取策略（优先对话模型，whisper 仅兜底）**：
    - 字幕直取已移除，统一走转录（转录来源只剩 Agent 原生/whisper 兜底）；
    - **Agent 原生转录优先**：由宿主对话模型按 TRANSCRIBE_TASK 直接听译（见末尾“通用能力探测与派发协议”）；
   - **本地 whisper 仅兜底**：原生不可用/拒转时，才用本地 `faster-whisper`（CPU int8 / GPU float16）转录；
   - 64kbps 轻量人声音频并发预取下载（6线程并行）；
   - 非破坏性文本规范化（折叠连续标点/空白，绝不误伤成语叠词）；
   - 任务提示词规范导出：单集精读长文任务书（`articles/PXX_*_TASK.md`）与知识块聚合复习大笔记任务书（`topic_plan.json`、`notes/模块XX_*_TASK.md`）。
2. **合成层（宿主 Agent 主程序 5 并发派发）**：
   - 宿主 Agent 主程序直接作为调度器，以 5 个并发通道（Task 子代理或并行会话）领跑任务书：
   - 语义校对：纠正同音错别字、繁转简、理顺断句；
   - 精读长文：按 `ARTICLE_LEARNING_PROMPT` 亲自撰写【可完全替代观看原视频】的教材级长文（含推导、真实案例复盘与可选自测题）；
   - 体系大笔记：按 `topic_plan.json` 知识块聚合，执行概念本体深度融合（标明 `> 来源: Pxx`），自适应横向对比矩阵与避坑反模式。

## 范围决策树（何时单集？何时全量？）

- **单 P / 本地单视频**：零打扰直接 `pipeline` 单集全流程。
- **多 P 课程 / 本地网课目录 + 显式全量意图**（"全部/整门课/全套"）：`pipeline --all` + 知识块聚合笔记。
- **多 P 课程 + 显式单集意图**（"第X讲" 或 URL 带 `?p=X`）：只处理该集。
- **多 P 课程 + 意图模糊**：回显拓扑并给出三选一确认（仅首集 / 全量聚合 / 指定区间）。

## 交付物规范

- `articles/`：**每集一篇**精读长文。目标=替代视频：现实痛点背景➔原理推演（禁止跳步）➔真实案例/演示全景复盘➔方案权衡与反模式➔总结延展➔可选随堂自测（仅在课程/教程且有必要时附带 2~3 题，非教学类坚决不加，避免突兀出戏）。严格闭卷事实边界（Strict Grounding）。
- `notes/`：**按知识块聚合**（通常 1~3 集一块）。纯粹的高密度复习速查定位（不收录长篇案例叙述，不含练习测验题）：含 ASCII 知识拓扑、概念本体深度融合（标明 `> 来源: Pxx` 方便回溯）、自适应横向对比矩阵（有可比实体才画表，无可比要素坚决不强出表）、常见反模式避坑清单。朴素 GitHub 风格。
- `subtitles/`：仅作转录语料存储（原始转录 + 规范化语料 + `kernels/` 知识元 JSON，字幕直取已移除）。

## 标准工作流（宿主 Agent 执行协议）

1. 解析：`python src/cli.py parse "<链接>"`
2. 工具层跑批（转录/清洗/规划/导出任务书）：
   ```bash
   python src/cli.py pipeline "<链接>" --page 1        # 单集
   python src/cli.py pipeline "<链接>" --all            # 全量（含知识块聚合规划）
   python src/cli.py cluster-notes "<链接>"             # 仅聚合笔记
   ```
3. **Agent 合成（关键步骤，由对话模型自己完成）**：
   - 读取 `subtitles/PXX_*_clean.txt`，按 `ASR_RECTIFY_PROMPT`（`python src/cli.py prompt "<链接>" --transcript-file <clean_txt> --type rectify`）做纯字面级语义校对纠偏，覆写为校对版；
   - 对每集：按 `ARTICLE_LEARNING_PROMPT`（`python src/cli.py prompt "<链接>" --transcript-file <校对语料> --type article`）亲自撰写可替代视频级的精读长文并落盘；
   - 对多P：读取 `topic_plan.json` 与 `notes/模块XX_AGENT_TASK.md`，汇总该块全部知识元，按 `SYNTHESIS_PROMPT` 亲自融合撰写模块复习大笔记，覆写 baseline 笔记，删除对应单集碎片笔记。
4. 汇报交付物路径清单。

## 常用 CLI 速查

```bash
python src/cli.py parse "<链接或本地文件/目录>" [--json]
python src/cli.py audio "<链接或本地文件/目录>" [--all] [--quality low]
python src/cli.py transcribe "<链接或本地视频/音频>" [--engine auto|agent|local] [--model base]
python src/cli.py clean <file>
python src/cli.py prompt "<链接或本地路径>" --type note|article|rectify|both
python src/cli.py note "<链接或本地路径>" --transcript-file <file>
python src/cli.py pipeline "<链接或本地文件/目录>" [--page N|--range A-B|--all] [--engine auto|agent|local] [--model base] [--force]
python src/cli.py cluster-notes "<链接或本地目录>" [--block-id N] [--start-block N --end-block M] [--replace] [--force]
```

任务产物统一归档于：`output/<任务名>_<BVID>/{audio,subtitles,notes,articles,topic_plan.json,manifest.json}`

## 通用能力探测与派发协议

### §0 能力探测（约5分钟切片，Agent 原生试转录）
- 取 1 个约 5 分钟音频切片（`audio/` 内任选一集的中段），由 Agent 按 TRANSCRIBE_TASK 原生转录。
- 判定阈值（分语言）+ 无拒转语义三者缺一不可：
  - 中文：有效产出 ≥ 0.8 字/秒（5分钟 ≈ ≥240 字）；
  - 英文：有效产出 ≥ 0.4 词/秒（5分钟 ≈ ≥120 词）；
  - 无拒转语义：不得出现“无法/不能处理音频”等拒绝话术，且产出与音频可听内容对应。
- 低密度（音乐/静音/片头）允许换一切片复测一次；两次皆低则判 `audio_native=false`。
- 结论写入 `output/<任务>/agent_capabilities.json`（如 `{"audio_native": true, "lang": "zh", "rate": 1.2}`），随任务归档；同任务复用免重测。

### §1 转录分支
- `audio_native=true` → 子智能体按 TRANSCRIBE_TASK 原生转录（以任务书为准）。
- `audio_native=false` → 本地 whisper 兜底（`transcribe --engine local`）。
- 全程零环境变量、零端口；所有路径相对仓库根（`output/<任务>/...`）。

### §2 派发模板（6集连续区间 × 5并发）
- 切分：按 P 号每 6 集一个连续区间（如 P01–P06），区间内 5 并发派发子智能体。
- 派生 prompt 五件套（逐字写入每发任务）：
  1. 精确路径：音频/输出/语料的仓库相对路径（如 `output/<任务>/audio/P01_xxx.m4a`）；
  2. 必读提示词路径：`TRANSCRIBE_TASK` 任务书与 `ASR_RECTIFY_PROMPT` 路径；
  3. 工具原则：只读 + 精确路径 + 不计数解析（禁 `wc` 式行数推断，只读指定文件）；
  4. 缓存优先：命中 `subtitles/` 已转录语料直接复用，不重转（字幕直取已移除）；
  5. 回执：完成后回传语料相对路径 + 字数 + 状态（done/needs-whisper）。
- `manifest.json` 断点续派：每集 `done/needs-whisper/pending` 入账，未 done 者下一轮只派未完成集。

### §3 失败分级（全程不阻塞）
- L1 原生超时/连续拒转 → 切 whisper `tiny` 快速试探（确认音频有效性）。
- L2 tiny 仍失败 → 接受人工外挂文本（置于 `subtitles/PXX_*_manual.txt`，标记 `engine=manual`）。
- 任何一级失败只标记该集状态，不阻塞其他并发通道与后续合成。
