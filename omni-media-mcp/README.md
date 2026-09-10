# 🎙️ OmniMedia MCP: 通用多模态音视频直读服务与 CLI

> **零本地模型负担，基于全球主流大模型原生全模态内核，直接“聆听”和“观看”音视频长篇教材与学术讲座。**

[![MCP 标准: 2024-11-05](https://img.shields.io/badge/MCP%20标准-FastMCP%202.2.0-blue?style=flat-square)](#)
[![适配宿主: OpenCode | ZCode | DSH | Codex | Antigravity](https://img.shields.io/badge/适配宿主-OpenCode%20%7C%20ZCode%20%7C%20DSH%20%7C%20Codex%20%7C%20Antigravity-111827?style=flat-square)](#)
[![多厂商支持: Gemini | Xiaomi MiMo | OpenAI | Qwen | DeepSeek | MiniMax](https://img.shields.io/badge/多厂商支持-Gemini%20%7C%20MiMo%20%7C%20OpenAI%20%7C%20Qwen%20%7C%20DeepSeek-8A2BE2?style=flat-square)](#)

---

## 🛠️ CLI 治理与操作指南 (对齐 FastCtx 范式)

本工具提供确定性、可审计、显式生命周期的命令行接口：

```bash
# 1. 诊断环境依赖、API 凭证与各宿主挂载状态
omni-media status

# 2. 显式接入指定宿主 (显示 Diff 预览，用户确认后安全写入)
omni-media apply --target opencode
omni-media apply --target zcode
omni-media apply --target dsh
omni-media apply --target codex
omni-media apply --target antigravity
omni-media apply --target all --yes    # 非交互脚本模式

# 3. 显式撤销指定宿主接入 (干净移除配置，零残留，不破坏宿主其他设置)
omni-media unapply --target opencode
omni-media unapply --target all --yes

# 4. 启动 MCP 协议 stdio 传输服务 (供任意支持 MCP 的宿主加载)
omni-media serve

# 5. 终端直读音视频 (无需启动外部客户端)
omni-media inspect /path/to/media.mp4
omni-media read /path/to/media.mp4 --mode summarize --provider auto
omni-media read /path/to/media.mp4 --start-time "00:00:00" --duration-minutes 15
omni-media ask /path/to/media.mp4 "第 15 分钟推导的核心结论是什么？"
omni-media probe
```

---

## 📋 宿主配置接入规范

各宿主通过独立的 Host Adapter 适配，支持指定 `--target`：

### 1. OpenCode (`--target opencode`)
- **配置路径**：`~/.config/opencode/opencode.jsonc` 或项目 `./opencode.jsonc`
- **配置结构**：
  ```jsonc
  {
    "mcp": {
      "omni-media": {
        "type": "local",
        "command": "python",
        "args": ["-m", "omni_media_mcp.server"],
        "env": {
          "GEMINI_API_KEY": "${GEMINI_API_KEY}"
        },
        "enabled": true
      }
    }
  }
  ```

### 2. ZCode (Z.ai) (`--target zcode`)
- **配置路径**：`~/.zcode/mcp_config.json` 或项目 `./zcode.json`
- **配置结构**：
  ```json
  {
    "mcpServers": {
      "omni-media": {
        "command": "python",
        "args": ["-m", "omni_media_mcp.server"],
        "env": {
          "GEMINI_API_KEY": "${GEMINI_API_KEY}"
        }
      }
    }
  }
  ```

### 3. DeepSeek Harness (`--target dsh`)
- **配置路径**：`~/.dsh/config.json` 或项目 `./dsh.config.json`
- **配置结构**：
  ```json
  {
    "mcpServers": {
      "omni-media": {
        "command": "python",
        "args": ["-m", "omni_media_mcp.server"],
        "env": {
          "DEEPSEEK_API_KEY": "${DEEPSEEK_API_KEY}",
          "GEMINI_API_KEY": "${GEMINI_API_KEY}"
        }
      }
    }
  }
  ```

### 4. OpenAI Codex & Open Agent Skills (`--target codex`)
- **MCP 接入**：`~/.codex/config.json`
- **技能规范**：同步安装 `.agents/skills/omni-media/SKILL.md`（或 `~/.agents/skills/omni-media/SKILL.md`），供 Codex CLI 依据自然语言自动触发。

### 5. Google Antigravity (`--target antigravity`)
- **配置路径**：`~/.gemini/config/mcp_config.json`
- **配置结构**：标准注入 `mcpServers["omni-media"]`。

---

## ⚡ 上下文预算控制与分卷续读

针对数小时的长视频或长篇学术讲座，工具提供时间段与预算控制参数，避免单次返回过多内容冲垮 Agent 上下文窗口：

```python
read_media(
    file_path="D:/lecture.mp4",
    mode="summarize",
    start_time="00:00:00",
    duration_minutes=15.0
)
```

输出文末会自动携带分页标记与下一分卷续读参数：
```text
---
> ⏱️ 分页状态: 已读取分卷 [00:00:00 - 00:15:00] / 总时长 01:20:00
> 💡 续读下一分卷参数: start_time="00:15:00"
```
Agent 仅需在下一轮调用中传入 `start_time="00:15:00"` 即可无缝衔接。

---

## 📦 暴露给 Agent 的核心工具与资源

### 工具 (Tools)
- **`read_media`**：全能音视频直读工具。支持 `transcribe`（高保真逐字稿）、`summarize`（精读教材长文）、`qa`（问答）、`custom`（自定义指示）；
- **`inspect_media`**：毫秒级媒体探针，输出时长、轨道编码及各大模型的 Token 预估；
- **`ask_media`**：针对音视频特定时间戳与内容的抗幻觉精准问答（Strict Grounding）；
- **`probe_models`**：联网评测与模型咨询探针（集成 Artificial Analysis、Video-MME、LMSYS Arena 数据）。

### 资源 (Resources)
- `media://supported-models`：实时查询所有支持的模型参数与特性清单；
- `media://system-status`：系统环境健康度与 API Key 激活状态报告。

---

## 🔑 多厂商 API 环境变量

- `GEMINI_API_KEY`：Google Gemini（100万~200万超大上下文，首选推荐）；
- `MIMO_API_KEY`：小米 Xiaomi MiMo-V2.5 1M 全模态；
- `OPENAI_API_KEY`：OpenAI GPT-4o Audio / GPT-5 input_audio；
- `DASHSCOPE_API_KEY`：阿里通义千问 Qwen2.5-VL / Qwen-Omni；
- `DEEPSEEK_API_KEY`：DeepSeek V4 视觉模型；
- `MINIMAX_API_KEY`：MiniMax 稀宇科技音视频模型。
