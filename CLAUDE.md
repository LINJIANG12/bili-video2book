# bili-video2book

本仓库 = **一个跨 agent 的 Agent Skill**（外加供各平台识别的插件声明）。
把 B 站长视频/系列网课或本地音视频重构为**精读教材长文、模块合辑全书与思维导图笔记**，
并自带一套**纯标准库**的 Python 工具链。

## 技能在哪

| 内容 | 路径 | 说明 |
| :--- | :--- | :--- |
| 技能定义 | `skills/bili-video2book/SKILL.md` | **唯一真源** |
| 参考文档 | `skills/bili-video2book/references/` | 含各平台安装对照与工具映射 |
| 工具链（技能的依赖） | `skills/bili-video2book/src/`、`skills/bili-video2book/scripts/` | 必须与 SKILL.md 一起安装 |

## 安装：只装技能目录

**安装单元就是 `skills/bili-video2book/` 这一个目录**（核心 skill + 它依赖的工具链），
其余文件（`README*.md`、`LICENSE`、平台声明、`pyproject.toml`）都是仓库级材料，**无需安装**。

按当前平台选一条，完整对照见 `skills/bili-video2book/references/install.md`：

- **Claude Code**：把 `skills/bili-video2book/` 复制或软链到 `~/.claude/skills/bili-video2book`
  （项目级则放 `<项目>/.claude/skills/bili-video2book`）。本仓库作为插件安装时 `skills/` 会被自动发现。
- **Codex**：`.codex-plugin/plugin.json` 已声明 `"skills": "./skills/"`；也可直接复制/软链到 `~/.codex/skills/bili-video2book`。
- **OpenCode**：见 `.opencode/INSTALL.md`（本仓库**不含打包插件**，按**目录**安装：软链或复制
  `skills/bili-video2book/` 到 OpenCode 的技能目录）。
- **通用 agents**：`.agents/plugins/marketplace.json` 已声明插件源；也可复制/软链到 `~/.agents/skills/bili-video2book`。
- **其它平台**：把 `skills/bili-video2book/` 放进该平台的技能目录（用户级或项目级），
  或直接让该平台的 agent 阅读 `skills/bili-video2book/references/install.md` 自行判断。

> 安装只复制该目录即可，**不要**只复制 `SKILL.md` —— 工具链在同一个目录里。

## 运行前置

- **Python 3.8+**（工具链是纯 Python 实现，无第三方依赖）
- **系统 ffmpeg**（在 `PATH`；取音频/切片的硬前置）
- 宿主需具备听音通道之一：MCP 工具 `read_audio`（宿主有原生音频模态）或 `read_media`（外部模型代读）
- 两个听音服务由配套仓库提供：[`LINJIANG12/omni-media`](https://github.com/LINJIANG12/omni-media)
  （装在 `<容器根>/omni-media/`：`mcp/` 原生听音、`mcp-ext/` 外部模型代读）

自检环境：`python skills/bili-video2book/src/cli.py info`

## 改本仓库时

- 自检（唯一门禁）：`cd skills/bili-video2book && python scripts/selfcheck.py`
- 硬约束：纯标准库；Python 3.8 语法（不得用 `list[str]` / `X | Y` / `removeprefix` 等 3.9+ 构造）；
  子进程统一走 `src/core/proc.py::run_quiet` 且必须带 `timeout=`；脚本入口调用 `src/core/console.py::enable_utf8_console()`
- 技能正文只描述**行动语义**（"读文件""写盘""让宿主的子智能体去做"），
  **不得写死某个平台的私有工具名**；平台差异统一放在 `references/host-tools/` 下
