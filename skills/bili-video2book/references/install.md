# 安装对照：把本技能装到各平台

> **本文件是给"读到这个仓库的 AI Agent"看的**：按你所在平台查表，或按"手动安装三法"自行判断。

## 一、安装单元只有一个目录

```
skills/bili-video2book/        ← 装这一个目录即可（核心 skill + 它依赖的工具链）
├── SKILL.md
├── references/                （含本文件、host-tools/ 与 cli-cookbook.md 场景手册）
├── scripts/                   （入口脚本）
└── src/                       （工具链实现）
```

其余文件是**仓库级材料，不需要安装**：`README.md` / `README.en.md` / `LICENSE` /
`pyproject.toml` / `AGENTS.md` / `CLAUDE.md` / `agents/` / `.codex-plugin/` /
`.claude-plugin/` / `.agents/plugins/` / `.opencode/`。

> ⚠️ **不要只复制 `SKILL.md`**：工具链在同一个目录里，缺了它技能无法运行。

## 二、前置依赖（装之前先确认）

| 依赖 | 必需性 | 说明 |
| :--- | :--- | :--- |
| Python 3.8+ | 必需 | 工具链是纯标准库实现，无第三方包 |
| 系统 `ffmpeg`（在 `PATH`） | 必需 | 取音频/切片的硬前置 |
| 听音通道之一 | 必需 | MCP 工具 `read_audio`（宿主有原生音频模态）或 `read_media`（外部模型代读）；两者由配套仓库 [LINJIANG12/omni-media](https://github.com/LINJIANG12/omni-media) 提供，装在 `<容器根>/omni-media/` 下 |

确认：在技能目录下执行 `python src/cli.py info`（会打印解析到的 MCP 仓库位置与两条听音通道的就位状态）。

## 三、平台对照表

**除末行兜底外，表内每一行的安装位都有实据**（本机实测存在该目录，或有官方文档 / 官方插件声明支撑）。
**没有实据的平台不逐个列表**——它们合并为末行「其它平台」，走第四节的「手动安装三法」自行判断，
不要照搬别处看到的路径。

| 平台 | 用户级安装位 | 项目级安装位 | 依据 |
| :--- | :--- | :--- | :--- |
| **Claude Code** | `~/.claude/skills/bili-video2book/` | `<项目>/.claude/skills/bili-video2book/` | 已证实（本机存在 `~/.claude/skills/`） |
| **Codex** | `~/.codex/skills/bili-video2book/`；或作为插件（本仓库 `.codex-plugin/plugin.json` 已声明 `"skills": "./skills/"`） | `<项目>/.codex/skills/bili-video2book/` | 已证实（本机存在 `~/.codex/skills/`；插件清单按 Agent Skills 规范声明） |
| **OpenCode** | 把 `skills/bili-video2book/` 放进 OpenCode 的技能目录；**候选**：`~/.config/opencode/skills/bili-video2book/` | `<项目>/.opencode/skills/bili-video2book/` | 工具名映射已核实（见 `host-tools/opencode.md`）；安装位以本平台实际目录为准（本机存在 `~/.config/opencode/`） |
| **通用 agents** | `~/.agents/skills/bili-video2book/` | `<项目>/.agents/skills/bili-video2book/` | 已证实（本机存在 `~/.agents/skills/`；本仓库 `.agents/plugins/marketplace.json` 已声明插件源） |
| **其它平台** | 该平台自己的技能目录 | `<项目>/.<平台>/skills/bili-video2book/` | 无公开依据，走第四节「手动安装三法」 |

> 表里没有的平台，**不要**照着别处的路径去创建目录；先按第四节确认本平台实际的技能目录。

## 四、手动安装三法（平台不在表里时）

按可靠性排序：

1. **平台原生插件注册**（最省事）：若本平台支持从 Git 仓库安装插件/扩展，直接把本仓库地址交给它；
   本仓库已备好 `.codex-plugin/plugin.json`、`.claude-plugin/plugin.json`、`.agents/plugins/marketplace.json`。
2. **软链**（只维护一份）：把 `skills/bili-video2book/` 链到本平台的技能目录。
   - Linux/macOS：`ln -s <仓库>/skills/bili-video2book <平台技能目录>/bili-video2book`
   - Windows：优先 `mklink /J`（junction，无需开发者模式），其次 `mklink /D`（需开发者模式）
3. **复制**（最笨但最稳）：整目录复制到本平台的技能目录。注意：源更新后需重新复制。

**判断本平台的技能目录**：先用自然语言问本平台的 agent「你的 skill 目录在哪 / 支持 Agent Skills 规范吗」，
或直接查看该平台的配置根下是否有 `skills/`。

## 五、装完怎么验证

1. 技能目录能被本平台列出（各平台有列出 skill 的命令或提问方式）；
2. 在技能目录下执行 `python src/cli.py info`，应打印 Python / ffmpeg / ffprobe / 听音通道 / 三域路径；
3. 执行 `python scripts/selfcheck.py`，应全部通过。

## 六、工具名差异怎么办

本技能正文只描述**行动语义**（"读文件""写盘""派子智能体""原生听音"），
平台私有工具名统一放在 [`host-tools/`](host-tools/) 下按平台分文件。
先读 [`host-tools/README.md`](host-tools/README.md) 了解基线，再读你所在平台那一份。
