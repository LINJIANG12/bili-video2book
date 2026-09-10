---
name: omni-media
description: Universal Multimodal Audio/Video Native Reading and Analysis Skill for AI Agents. Connects directly to multi-gigabyte media for transcription, structured note reconstruction, and grounded Q&A without local speech-to-text weight bloat.
triggers:
  - 音频直读
  - 读音频
  - 听音频
  - 音视频转录
  - 读视频
  - 网课笔记重构
  - 媒体探测
  - read_audio
  - read_media
  - inspect_media
  - ask_media
---

# OmniMedia Skill: 多模态音视频原生直读与理解指南

本技能为具备多模态能力的智能体（如 Codex、Antigravity、Gemini、GPT-4o Audio）提供对本地音视频文件的原生直接直读与理解能力。无需调用第三方付费 ASR，直接利用模型本体的音频模态感知长篇网课、学术讲座、会议录音及屏幕演示。

## 1. 核心工具集说明

### `read_audio` (⭐ 原生多模态首选直读工具)
直接读取本地音视频文件的音频流，返回原生音频数据块或高保真切片文件，供宿主对话模型直接感知。
- **参数列表**:
  - `file_path` (string, 必需): 本地音视频绝对路径。
  - `start_time` (string, 可选): 分页切片起始时间戳，格式如 `"00:00:00"`、`"00:15:00"` 或秒数。
  - `duration_minutes` (float, 可选): 单次读取切片时长预算（分钟）。**<= 75 分钟网课默认一次性完整就绪 (One-Shot)**；仅 > 75 分钟超长文件自动启动 30 分钟安全分卷调度。
  - `output_mode` (string, 可选): 回传通道。
    - `'file'`：**（Codex / Antigravity Agent 默认与强力推荐）** 生成 16kHz 32k AAC 优化切片并返回本地绝对路径（若输入已是 16kHz 单声道则 0 秒极速直通原路径）。携带机器可读元数据 `<!-- OMNI_STATUS: ... -->`。宿主 Agent 可直接用 `view_file` 原生挂载并聆听。
    - `'inline'`：返回 FastMCP 原生 `Audio` 数据块（受 8MB 安全阈值保护，超过自动回退至 file 通道）。
    - `'auto'`：（默认）根据文件大小、编码与时长智能路由。

### `inspect_media`
毫秒级探测音视频元数据、音轨编码及多模态模型（Gemini / GPT-4o 等）的 Token 预算消耗。
- **参数列表**:
  - `file_path` (string, 必需): 本地音视频文件路径。

### `read_media` (云端委托代读备选)
委托云端模型 API（Gemini / OpenAI / Qwen 等）对媒体进行转录或总结。**注：仅当宿主模型为纯文本模型且无法直接感知音频时作为降级备选使用。**

### `ask_media`
针对音视频事实细节进行定向抗幻觉问答（云端代读通道）。

### `probe_models`
获取主流多模态模型音视频能力基准矩阵及本地环境变量配置状态。

---

## 2. 经典工作流程

### 工作流 A：Codex / 终端 Agent 原生直读音频 (推荐)
适用于 Codex CLI、Antigravity 等具备音频理解能力但 MCP 仅支持文件/文本交互的 Agent：
1. **切片获取**：
   调用 `read_audio(file_path="D:/lecture.mp4", output_mode="file", duration_minutes=10.0)`。
2. **原生挂载与听音**：
   工具将返回生成的本地切片路径（如 `~/.omni-media/slices/lecture_slice_0_600.m4a`）以及时间范围 `[00:00:00 - 00:10:00]`。
   Agent 紧接着调用自身的原生文件读取工具（例如 `view_file(AbsolutePath="...")`）直接查看/聆听该切片。
3. **分页续读**：
   根据返回信息中的续读参数（`start_time="00:10:00"`），继续调用 `read_audio` 进行下一分卷迭代，直到通读全篇。

### 工作流 B：原生 MCP AudioContent 直读 (现代 MCP 宿主)
适用于完全支持 MCP `AudioContent` 反序列化的客户端：
- 调用 `read_audio(file_path="D:/meeting.mp3", output_mode="inline")`。
- 模型在单轮工具调用中直接接收到 `Audio` 块并立即输出分析结果。

### 工作流 C：纯文本宿主降级云端代读
若宿主完全无多模态能力（如旧版纯文本 LLM）：
- 先调用 `inspect_media(file_path)` 检查时长；
- 调用 `read_media(file_path=..., mode="summarize", duration_minutes=15)`，由外部 API 返回文本摘要。
