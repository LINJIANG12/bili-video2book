---
name: bilibili-audio-knowledge-extractor
version: 1.3.0
description: |
  Bilibili 视频音频提取、本地语音转录与结构化知识沉淀 Skill（宿主 Agent 原生合成架构）。
  支持任意 B 站视频/多P分集/系列合集链接：拓扑解析、64kbps 轻量音频抓取、10 分钟均衡切片、
  本地 faster-whisper 语音转录、安全文本规范化、知识块语义规划与提示词导出。
  本 Skill 只负责【工具层】（下载/转录/清洗/规划/导出）；所有语义校对、体系笔记与
  【可替代视频级】精读长文均由宿主对话模型（Agent 自身）按导出的提示词原生完成。
triggers:
  - bilibili 视频笔记
  - B站视频转文章
  - 提取B站音频
  - 解析B站合集
  - 制作学习笔记
  - 整理视频
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

1. **转录与提取策略**：
   - 官方/AI 字幕探测（命中即免转录）；
   - **优先对话大模型（多模态）**：直接利用具备多模态能力的宿主对话大模型读取切片音频流进行高保真逐字转录；
   - **安全阻断与询问兜底**：仅在确认对话大模型不具备音频模态或不可用时，系统自动停止并汇报问题，交互询问用户是否采用本地 `faster-whisper` 模型进行离线转录兜底；
   - 64kbps 轻量人声音频下载 + FFmpeg 10 分钟均衡无损切片；
   - 非破坏性文本规范化（折叠标点/空白，绝不误伤成语叠词）；
   - 知识块语义规划提示词与分块合成任务书导出（`topic_plan.json`、`模块XX_AGENT_TASK.md`）。
2. **合成层（宿主对话模型）**：
   - 语义校对：纠正同音错别字、繁转简、理顺断句；
   - 笔记：按【知识块】聚合（多P课程严禁按单集出笔记），执行概念本体融合，剔除冗长案例叙述与测验题；
   - 精读文章：单集一篇【可完全替代观看原视频】的教材级长文（含推导、案例复盘与可选自测题）。

## 范围决策树（何时单集？何时全量？）

- **单 P 独立视频**：零打扰直接 `pipeline` 单集全流程。
- **多 P 课程 + 显式全量意图**（"全部/整门课/全套"）：`audio --all` + `pipeline --all` + 知识块聚合笔记。
- **多 P 课程 + 显式单集意图**（"第X讲" 或 URL 带 `?p=X`）：只处理该集。
- **多 P 课程 + 意图模糊**：回显拓扑并给出三选一确认（仅首集 / 全量聚合 / 指定区间）。

## 交付物规范

- `articles/`：**每集一篇**精读长文。目标=替代视频：现实痛点背景➔原理推演（禁止跳步）➔真实案例/演示全景复盘➔方案权衡与反模式➔总结延展➔可选随堂自测（仅在课程/教程且有必要时附带 2~3 题，非教学类坚决不加，避免突兀出戏）。严格闭卷事实边界（Strict Grounding）。
- `notes/`：**按知识块聚合**（通常 1~3 集一块）。纯粹的高密度复习速查定位（不收录长篇案例叙述，不含练习测验题）：含 ASCII 知识拓扑、概念本体深度融合（标明 `> 来源: Pxx` 方便回溯）、自适应横向对比矩阵（有可比实体才画表，无可比要素坚决不强出表）、常见反模式避坑清单。朴素 GitHub 风格。
- `subtitles/`：原始转录 + 规范化语料 + `kernels/` 知识元 JSON。

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
python src/cli.py parse "<链接>" [--json]
python src/cli.py audio "<链接>" --all --quality low
python src/cli.py transcribe "<链接或本地音频>" [--engine auto|agent|local] [--model base]
python src/cli.py subtitle "<链接>"
python src/cli.py clean <file>
python src/cli.py prompt "<链接>" --type note|article|rectify|both
python src/cli.py note "<链接>" --transcript-file <file>
python src/cli.py pipeline "<链接>" [--page N|--range A-B|--all] [--engine auto|agent|local] [--model base] [--force]
python src/cli.py cluster-notes "<链接>" [--block-id N] [--start-block N --end-block M] [--replace] [--force]
```

任务产物统一归档于：`output/<任务名>_<BVID>/{audio,subtitles,notes,articles,topic_plan.json,manifest.json}`
