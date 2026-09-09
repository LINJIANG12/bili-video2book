# 故障排除与常见问题 (Troubleshooting)

在视频抓取、音频提取与 Agent 流水线处理过程中，可能遇到各类网络风控、环境缺失及离线异常。请遵循本手册进行自愈与排障。

---

## 1. 哔哩哔哩 412 风控拦截 (HTTP 412 Precondition Failed)

### 现象
CLI 输出类似于：
```text
HTTP 412: 被B站风控拦截，请提供Cookie或稍后重试
```

### 处置策略（三要素）
1. **提供有效 SESSDATA Cookie**：
   - 在 B 站网页端登录后，打开浏览器 F12 -> Application -> Cookies -> `https://bilibili.com`。
   - 复制 `SESSDATA` 字段的值。
   - 在执行 CLI 时附加参数：
     ```bash
     python src/cli.py pipeline "https://www.bilibili.com/video/BVxxx" --all --sessdata "your_sessdata_here"
     ```
2. **退避与重试（已内建）**：
   - 网络层已统一封装退避重试（`src/core/http_client.py`）：自动识别 412/429/5xx、解析 `Retry-After` 响应头并执行带抖动的指数退避，无需手动配置。
   - 可随时运行 `python src/cli.py info` 查看上次 412/熔断状态（记录于 `output/.cli_status.json`）。
3. **切换本地模式**：
   - 若 IP 被临时拉黑，可先通过其他途径（如浏览器插件或本地播放器缓存）将视频保存至本地，然后把**本地文件或目录路径直接传给 CLI**（系统自动识别本地媒体，无需任何附加标志位）：
     ```bash
     python src/cli.py pipeline "D:\videos\lecture01.mp4"
     ```

---

## 2. 本地 ffmpeg 缺失或不可用

### 现象
CLI 警告：
```text
Warning: ffmpeg not found in PATH! Audio extraction disabled.
```

### 处置方法
- **Windows**：
  - 使用 winget 安装：`winget install Gyan.FFmpeg`
  - 或下载解压后，将 `bin/ffmpeg.exe` 所在目录添加至系统 `PATH` 环境变量。
- **macOS**：
  - `brew install ffmpeg`
- **Linux (Ubuntu/Debian)**：
  - `sudo apt update && sudo apt install -y ffmpeg`

---

## 3. 音频切片与 Agent 原生直读模式

- 本框架全面采用 **Agent 原生多模态派发架构**，明确仅使用原生模式。
- CLI 在“阶段一”完成音视频元数据提取与音频切片（默认 10 分钟切片，可用 `--chunk-minutes` 调整，规避上下文溢出）。
- 宿主模型直接挂载音频切片进行原生听音/解析、知识提炼与双轨教材构建，无需也不依赖外部转录工具。
- **转录与模型底线纪律**：**绝不使用本地模型转录，严禁下载模型**。所有转录与重构处理必须依托多模态 Agent 原生理解能力或云端接口，严禁在本地安装部署或下载离线模型权重（如 Whisper、Faster-Whisper 等），杜绝占用用户本地硬件算力与磁盘空间。

