# 🎙️ OmniMedia MCP: 宿主原生音视频直读服务

> **零本地模型负担、零外部 API 凭证**：直接借用宿主多模态对话模型的音频感知能力，聆听长篇网课、学术讲座与会议录音。

[![MCP 标准: 2024-11-05](https://img.shields.io/badge/MCP%20标准-FastMCP%202.2.0-blue.svg?style=flat-square)](#)
[![适配宿主: OpenCode | ZCode | DSH | Codex | Antigravity](https://img.shields.io/badge/适配宿主-OpenCode%20%7C%20ZCode%20%7C%20DSH%20%7C%20Codex%20%7C%20Antigravity-111827?style=flat-square)](#)
[![凭证需求: 零 API Key](https://img.shields.io/badge/凭证需求-零%20API%20Key-2ea44f?style=flat-square)](#)

---

## 🧭 设计定位：宿主原生听音，不需要任何 API Key

本服务**不调用任何第三方 ASR 或多模态 API**，也**不需要配置任何密钥**。它只做三件事：

1. **探测**：毫秒级读出媒体的时长、轨道、编码与规格（`inspect_media`）；
2. **切片**：用 FFmpeg 抽取 16kHz 单声道轻量人声，按预算切成安全大小的切片（`read_audio`）；
3. **交付**：把切片路径或原生的音频数据块交给宿主模型，由**宿主自己的多模态内核**直接聆听。

> **历史沿革**：早期版本提供「云端委托代读」通道（`read_media` / `ask_media` / `probe_models` 与 Gemini / OpenAI / Qwen / DeepSeek / MiMo / MiniMax 六家 provider）。
> 该通道已**彻底移除**——宿主模型原生听音延迟更低、质量更好，且不需要任何外部凭证与付费额度。
> 因此本项目**不再需要、也不再读取** `GEMINI_API_KEY` / `OPENAI_API_KEY` / `DASHSCOPE_API_KEY` / `DEEPSEEK_API_KEY` / `MIMO_API_KEY` / `MINIMAX_API_KEY`。
> 唯一的外部依赖是系统 `ffmpeg`。

---

## 🛠️ CLI 治理与操作指南 (对齐 FastCtx 范式)

```bash
# 1. 诊断环境依赖与各宿主挂载状态
omni-media status

# 2. 显式接入指定宿主 (显示 Diff 预览，用户确认后安全写入)
omni-media apply --target zcode
omni-media apply --target all --yes    # 非交互脚本模式

# 3. 显式撤销指定宿主接入 (干净移除配置，零残留，不破坏宿主其他设置)
omni-media unapply --target zcode

# 4. 启动 MCP 协议 stdio 传输服务 (供任意支持 MCP 的宿主加载)
omni-media serve

# 5. 终端直读媒体规格 (无需启动外部客户端)
omni-media inspect /path/to/media.mp4
```

---

## 📋 宿主配置接入规范

各宿主通过独立的 Host Adapter 适配，支持指定 `--target`。接入只写入服务启动命令与 `PYTHONPATH`，**不写入任何凭证**：

### 1. ZCode (Z.ai) (`--target zcode`)
- **配置路径**：`~/.zcode/mcp_config.json` 或项目 `./zcode.json`
- **配置结构**：
  ```json
  {
    "mcpServers": {
      "omni-media": {
        "command": "python",
        "args": ["-m", "omni_media_mcp.server"],
        "env": {
          "PYTHONPATH": "/path/to/omni-media-mcp"
        }
      }
    }
  }
  ```

### 2. OpenCode (`--target opencode`)
- **配置路径**：`~/.config/opencode/opencode.jsonc` 或项目 `./opencode.jsonc`
- **配置结构**：同上的 `mcp` 段，`type: "local"` 且 `enabled: true`。

### 3. DeepSeek Harness (`--target dsh`)
- **配置路径**：`~/.dsh/config.json` 或项目 `./dsh.config.json`

### 4. OpenAI Codex & Open Agent Skills (`--target codex`)
- **MCP 接入**：`~/.codex/config.json`
- **技能规范**：同步安装 `skills/omni-media/SKILL.md`（或 `~/.agents/skills/omni-media/SKILL.md`），供 Codex CLI 依据自然语言自动触发。

### 5. Google Antigravity (`--target antigravity`)
- **配置路径**：`~/.gemini/config/mcp_config.json`

---

## ⚡ 上下文预算控制与分卷续读

针对数小时的长视频或长篇学术讲座，`read_audio` 提供时间段与预算控制，避免单次返回过多内容冲垮 Agent 上下文窗口：

```python
read_audio(
    file_path="D:/lecture.mp4",
    output_mode="file",
    duration_minutes=15.0,
)
```

切片文件返回时携带机器可读状态与续读提示：

```text
<!-- OMNI_STATUS: {"status": "IN_PROGRESS", "is_finished": false, "next_start_time": "00:15:00", ...} -->
> ⏱️ 续读下一分卷参数: start_time="00:15:00", duration_minutes=15.0
```

Agent 仅需在下一轮调用中传入 `start_time="00:15:00"` 即可无缝衔接。

---

## 📦 暴露给 Agent 的工具

### `read_audio` (⭐ 核心，阶段一听音唯一入口)
读取本地音视频的音频流，返回**本机切片绝对路径**（`output_mode="file"`）或 MCP 原生 `Audio` 数据块（`inline`），供宿主模型直接聆听。
- `file_path`（必需）：本地音视频绝对路径；
- `start_time`：切片起始时间戳（`"00:15:00"` 或秒数）；
- `duration_minutes`：本次时长预算；未指定且媒体超过 75 分钟时自动按 30 分钟安全分卷；
- `output_mode`：`file`（推荐，返回本地切片路径）/ `inline`（返回原生 Audio 块）/ `auto`。

### `inspect_media`
毫秒级探测媒体时长、轨道编码、体积与规格。不含任何凭证或联网行为。

---

## 🔑 凭证与依赖

- **凭证**：无需任何 API Key，服务不读取、不存储、不传输任何密钥。
- **系统依赖**：`ffmpeg`（含 `ffprobe`）需在 `PATH` 中；缺失时切片与探测功能不可用。
- **Python 依赖**：仅 `mcp>=1.0.0`。
