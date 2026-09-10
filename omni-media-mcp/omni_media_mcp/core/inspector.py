"""Media Inspection and Token Estimation Engine."""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from .limits import AUDIO_EXTS, PROBE_TIMEOUT_SEC, VIDEO_EXTS

logger = logging.getLogger(__name__)


@dataclass
class StreamInfo:
    codec_type: str  # "audio" | "video"
    codec_name: str
    sample_rate: Optional[int] = None
    channels: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    bitrate: Optional[int] = None


@dataclass
class TokenEstimates:
    gemini_audio_tokens: int
    gemini_video_tokens: int
    openai_audio_tokens: int
    qwen_vision_tokens: int
    deepseek_vision_tokens: int


@dataclass
class MediaMetadata:
    file_path: str
    file_name: str
    file_size_bytes: int
    file_size_mb: float
    duration_seconds: float
    duration_human: str
    has_audio: bool
    has_video: bool
    format_name: str
    streams: List[Dict[str, Any]]
    estimates: Dict[str, int]
    recommended_mode: str
    recommended_provider: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_markdown(self) -> str:
        streams_desc = []
        for s in self.streams:
            if s.get("codec_type") == "video":
                fps = s.get("fps")  # may be None for variable/unreported framerate
                fps_str = f"{fps:.1f}" if fps else "可变/未知"
                streams_desc.append(
                    f"- 📹 视频轨: `{s.get('codec_name')}` {s.get('width')}x{s.get('height')} @ {fps_str}fps"
                )
            elif s.get("codec_type") == "audio":
                streams_desc.append(
                    f"- 🔊 音频轨: `{s.get('codec_name')}` {s.get('sample_rate')}Hz {s.get('channels')}声道"
                )

        streams_str = "\n".join(streams_desc) if streams_desc else "- (无音视频轨道)"

        return f"""### 📊 媒体文件探测报告: `{self.file_name}`

- **文件大小**: {self.file_size_mb:.2f} MB ({self.file_size_bytes:,} 字节)
- **媒体时长**: {self.duration_human} ({self.duration_seconds:.1f} 秒)
- **封装格式**: `{self.format_name}`
- **轨道信息**:
{streams_str}

#### 🎯 多模态 Token 预算预估:
- **Google Gemini 原生音频**: ~`{self.estimates.get('gemini_audio_tokens', 0):,}` Tokens (约 $0.00002)
- **Google Gemini 原生视音频**: ~`{self.estimates.get('gemini_video_tokens', 0):,}` Tokens
- **OpenAI input_audio**: ~`{self.estimates.get('openai_audio_tokens', 0):,}` Tokens
- **Qwen / DeepSeek (1FPS 抽帧)**: ~`{self.estimates.get('deepseek_vision_tokens', 0):,}` 视觉 Tokens

> 💡 **系统推荐策略**: `{self.recommended_mode}`
> 推荐模型通道: **{self.recommended_provider}**
"""


class MediaInspector:
    """Probes media metadata using ffprobe with zero external heavy dependencies."""

    @staticmethod
    def _find_ffprobe() -> Optional[str]:
        bin_path = shutil.which("ffprobe")
        if bin_path:
            return bin_path
        # Windows Winget standard paths
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        if local_app_data:
            winget_path = Path(local_app_data) / "Microsoft" / "WinGet" / "Packages"
            if winget_path.exists():
                for p in winget_path.glob("**/ffprobe.exe"):
                    return str(p)
        return None

    @classmethod
    def probe(cls, file_path: str | Path) -> MediaMetadata:
        path = Path(file_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"媒体文件不存在: {file_path}")

        file_size = path.stat().st_size
        file_size_mb = file_size / (1024 * 1024)

        duration = 0.0
        format_name = path.suffix.lstrip(".").lower()
        streams: List[StreamInfo] = []

        ffprobe_bin = cls._find_ffprobe()
        if ffprobe_bin:
            cmd = [
                ffprobe_bin,
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                str(path),
            ]
            try:
                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=PROBE_TIMEOUT_SEC)
                if res.returncode == 0 and res.stdout:
                    data = json.loads(res.stdout)
                    fmt = data.get("format", {})
                    format_name = fmt.get("format_name", format_name)
                    duration = float(fmt.get("duration", 0.0))

                    for s in data.get("streams", []):
                        ctype = s.get("codec_type")
                        cname = s.get("codec_name", "")
                        if ctype == "video":
                            # calculate fps
                            fps_val = None
                            r_frame_rate = s.get("r_frame_rate", "")
                            if "/" in r_frame_rate:
                                num, den = r_frame_rate.split("/")
                                if float(den) > 0:
                                    fps_val = float(num) / float(den)
                            streams.append(
                                StreamInfo(
                                    codec_type="video",
                                    codec_name=cname,
                                    width=s.get("width"),
                                    height=s.get("height"),
                                    fps=fps_val,
                                    bitrate=int(s.get("bit_rate")) if s.get("bit_rate") else None,
                                )
                            )
                        elif ctype == "audio":
                            streams.append(
                                StreamInfo(
                                    codec_type="audio",
                                    codec_name=cname,
                                    sample_rate=int(s.get("sample_rate")) if s.get("sample_rate") else None,
                                    channels=int(s.get("channels")) if s.get("channels") else None,
                                    bitrate=int(s.get("bit_rate")) if s.get("bit_rate") else None,
                                )
                            )
            except Exception as exc:  # ffprobe ran but failed to parse
                logger.warning("ffprobe 媒体探测失败，将回退按扩展名/ffmpeg 判定: %s", exc)

        # Fallback if ffprobe couldn't get duration
        if duration <= 0:
            ffmpeg_bin = shutil.which("ffmpeg")
            if ffmpeg_bin:
                try:
                    res = subprocess.run(
                        [ffmpeg_bin, "-i", str(path)],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=PROBE_TIMEOUT_SEC,
                    )
                    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.?\d*)", res.stderr)
                    if m:
                        hours, minutes, seconds = float(m.group(1)), float(m.group(2)), float(m.group(3))
                        duration = hours * 3600 + minutes * 60 + seconds
                except Exception as exc:
                    logger.warning("ffmpeg 时长回退解析失败: %s", exc)

        has_video = any(s.codec_type == "video" for s in streams)
        has_audio = any(s.codec_type == "audio" for s in streams)
        # If no streams detected, guess by extension
        if not streams:
            if path.suffix.lower() in VIDEO_EXTS:
                has_video = True
                has_audio = True
            elif path.suffix.lower() in AUDIO_EXTS:
                has_audio = True

        # Human-readable duration
        hrs = int(duration // 3600)
        mins = int((duration % 3600) // 60)
        secs = int(duration % 60)
        dur_human = f"{hrs:02d}:{mins:02d}:{secs:02d}" if hrs > 0 else f"{mins:02d}:{secs:02d}"

        # Token Estimations
        # Gemini Audio: ~32 tokens per second (16kHz)
        gemini_audio = int(duration * 32)
        # Gemini Video: ~260 visual tokens per second (1 fps) + 32 audio tokens per second
        gemini_video = int(duration * 292) if has_video else gemini_audio
        # OpenAI audio: ~100 tokens per second average
        openai_audio = int(duration * 100)
        # Qwen/DeepSeek vision frames: 1 frame per second, approx 768 tokens per image
        deepseek_vision = int(duration * 768) if has_video else 0

        estimates = {
            "gemini_audio_tokens": gemini_audio,
            "gemini_video_tokens": gemini_video,
            "openai_audio_tokens": openai_audio,
            "qwen_vision_tokens": deepseek_vision,
            "deepseek_vision_tokens": deepseek_vision,
        }

        # Recommendations
        if has_video and not has_audio:
            rec_mode = "仅画面无声：推荐使用视频抽帧/Vision VLM 分析画面"
            rec_prov = "Gemini / Qwen-VL / DeepSeek-V4-Vision"
        elif has_video:
            rec_mode = "标准讲座/网课视频：默认极速抽取 16kHz 人声直读；若提问板书/PPT 切换画面分析"
            rec_prov = "Gemini 2.5/3.0 Flash (全模态超大上下文最佳)"
        else:
            rec_mode = "纯音频文件：原生单声道直读，零重编码"
            rec_prov = "Gemini / Xiaomi MiMo / OpenAI input_audio"

        return MediaMetadata(
            file_path=str(path),
            file_name=path.name,
            file_size_bytes=file_size,
            file_size_mb=file_size_mb,
            duration_seconds=duration,
            duration_human=dur_human,
            has_audio=has_audio,
            has_video=has_video,
            format_name=format_name,
            streams=[asdict(s) for s in streams],
            estimates=estimates,
            recommended_mode=rec_mode,
            recommended_provider=rec_prov,
        )
