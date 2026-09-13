"""ytaudio —— YouTube 音频采集工具包（基于 yt-dlp）。

模块划分（全部自包含于 yt/ 目录内）：

- ``config``    运行配置（Cookie/代理/PO Token/限速/过滤规则等）
- ``utils``     通用工具（频道 URL 归一化、文件名清洗、日志）
- ``filters``   作品类型过滤：**只保留普通视频**，剔除 Shorts 短视频与直播/回放
- ``engine``    yt-dlp 封装：选项构造、反爬与签名参数、限速重试
- ``single``    单视频解析与下载
- ``channel``   频道视频分页 + 播放列表（合集）识别与归类
- ``downloader``按目录分组下载 + 断点续跑（archive）
"""

__version__ = "1.0.0"
