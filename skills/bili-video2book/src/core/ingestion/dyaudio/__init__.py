"""dyaudio —— 抖音音频采集工具包。

模块划分（全部自包含于 douyin/ 目录内）：

- ``sm3``           纯 Python 国密 SM3（仅标准库，用于 a_bogus 签名）
- ``abogus``        抖音 Web 端 a_bogus 请求签名（纯 Python 移植）
- ``config``        运行配置（cookie / 代理 / 限速 / 输出目录等）
- ``utils``         通用工具（链接提取、文件名清洗、日志）
- ``client``        带签名、限速、重试的 HTTP 客户端
- ``share_parser``  单视频解析（走移动端分享页，免签名）
- ``user_crawler``  博主主页作品分页抓取 + 合集归类
- ``mix_crawler``   合集（mix）列表接口（尽力而为的补充）
- ``downloader``    音频下载 / ffmpeg 提取
"""

__version__ = "1.0.0"
