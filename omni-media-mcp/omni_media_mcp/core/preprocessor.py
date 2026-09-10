"""High-speed Media Preprocessing Engine using FFmpeg."""

from __future__ import annotations

import os
import shutil
import subprocess
import threading
import time
import uuid
from pathlib import Path
from typing import List, Optional

from .limits import AUDIO_BITRATE_VOICE, MAX_CONCURRENT_FFMPEG, SUBPROCESS_TIMEOUT_SEC
from .temp_manager import ManagedTempDir

_FFMPEG_LOCK = threading.BoundedSemaphore(MAX_CONCURRENT_FFMPEG)


def _atomic_replace_file(src: Path, dst: Path, retries: int = 4, delay: float = 0.25) -> None:
    """Safely replace dst with src on Windows and POSIX, handling transient file locks."""
    for attempt in range(retries):
        try:
            os.replace(src, dst)
            return
        except OSError:
            if attempt == retries - 1:
                raise
            time.sleep(delay * (attempt + 1))


class MediaPreprocessor:
    """Performs lightning-fast, lossless or lightweight stream extractions.

    Every subprocess launch is bounded by ``SUBPROCESS_TIMEOUT_SEC`` so a
    stalled or oversized encode cannot block the caller indefinitely. Callers
    running on an asyncio event loop MUST dispatch these blocking methods via
    ``asyncio.to_thread`` (or an executor) instead of invoking them inline.
    """

    @staticmethod
    def _find_ffmpeg() -> str:
        bin_path = shutil.which("ffmpeg")
        if bin_path:
            return bin_path
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        if local_app_data:
            winget_path = Path(local_app_data) / "Microsoft" / "WinGet" / "Packages"
            if winget_path.exists():
                for p in winget_path.glob("**/ffmpeg.exe"):
                    return str(p)
        raise RuntimeError("系统未找到 ffmpeg，请确保 ffmpeg 已安装并加入系统 PATH。")

    @staticmethod
    def parse_time_str(t: str | int | float | None) -> Optional[float]:
        """Converts 'HH:MM:SS', 'MM:SS', or seconds string/number into total float seconds.

        Raises:
            ValueError: if the value cannot be parsed or is negative (negative
                timestamps would otherwise produce meaningless ffmpeg slices).
        """
        if t is None:
            return None
        if isinstance(t, (int, float)):
            if t < 0:
                raise ValueError(f"时间戳不能为负数: {t}")
            return float(t)
        s = str(t).strip()
        if not s:
            return None
        parts = s.split(":")
        try:
            if len(parts) == 3:
                seconds = float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
            elif len(parts) == 2:
                seconds = float(parts[0]) * 60 + float(parts[1])
            else:
                seconds = float(parts[0])
        except ValueError:
            raise ValueError(f"无法解析时间戳格式: '{t}'，请使用 'HH:MM:SS' 或秒数")
        if seconds < 0:
            raise ValueError(f"时间戳不能为负数: {t}")
        return seconds

    @staticmethod
    def format_time_str(seconds: float) -> str:
        """Formats seconds into 'HH:MM:SS'."""
        sec = max(0.0, seconds)
        hrs = int(sec // 3600)
        mins = int((sec % 3600) // 60)
        rem_sec = int(sec % 60)
        return f"{hrs:02d}:{mins:02d}:{rem_sec:02d}"

    @classmethod
    def extract_optimized_audio(
        cls,
        input_file: str | Path,
        output_file: Optional[str | Path] = None,
        start_time: Optional[str | int | float] = None,
        duration_seconds: Optional[float] = None,
        bitrate: str = AUDIO_BITRATE_VOICE,
        codec: str = "aac",
    ) -> Path:
        """Extracts 16kHz mono audio (1:1 optimal for Gemini and speech LLMs).

        Supports optional start_time and duration_seconds slicing.
        Safeguarded by concurrency semaphore and atomic file staging.

        Args:
            codec: Output audio codec. Defaults to ``aac`` (for .m4a). Pass
                ``libmp3lame`` together with an ``.mp3`` output path when a
                provider only accepts mp3/wav (e.g. OpenAI input_audio).
        """
        src = Path(input_file).resolve()
        if not src.exists():
            raise FileNotFoundError(f"输入文件不存在: {input_file}")

        if output_file:
            dst = Path(output_file).resolve()
            dst.parent.mkdir(parents=True, exist_ok=True)
        else:
            dst = src.parent / f"{src.stem}_16k_mono.m4a"

        tmp_id = f"tmp_{os.getpid()}_{uuid.uuid4().hex[:8]}"
        tmp_dst = dst.parent / f"{dst.stem}.{tmp_id}{dst.suffix}"

        ffmpeg = cls._find_ffmpeg()
        cmd = [ffmpeg, "-y"]

        if start_time is not None:
            cmd.extend(["-ss", str(start_time)])

        cmd.extend(["-i", str(src)])

        if duration_seconds is not None:
            cmd.extend(["-t", str(duration_seconds)])

        cmd.extend([
            "-vn",          # strip video
            "-acodec", codec,
            "-ar", "16000",  # 16kHz
            "-ac", "1",      # mono channel
            "-b:a", str(bitrate),   # voice bitrate
            str(tmp_dst),
        ])

        try:
            with _FFMPEG_LOCK:
                res = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=SUBPROCESS_TIMEOUT_SEC,
                )
            if res.returncode != 0 or not tmp_dst.exists() or tmp_dst.stat().st_size == 0:
                raise RuntimeError(f"FFmpeg 音频抽取失败: {res.stderr}")

            _atomic_replace_file(tmp_dst, dst)
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(
                f"FFmpeg 音频抽取超时 (>{SUBPROCESS_TIMEOUT_SEC}s): 文件可能过大，建议先切片。"
            ) from e
        finally:
            if tmp_dst.exists():
                try:
                    tmp_dst.unlink(missing_ok=True)
                except OSError:
                    pass

        return dst

    @classmethod
    def slice_video(
        cls,
        input_file: str | Path,
        output_file: Optional[str | Path] = None,
        start_time: Optional[str | int | float] = None,
        duration_seconds: Optional[float] = None,
    ) -> Path:
        """Slices video segment for vision multimodal processing."""
        src = Path(input_file).resolve()
        if not src.exists():
            raise FileNotFoundError(f"输入文件不存在: {input_file}")

        dst = Path(output_file).resolve() if output_file else src.parent / f"{src.stem}_slice.mp4"
        dst.parent.mkdir(parents=True, exist_ok=True)

        ffmpeg = cls._find_ffmpeg()
        cmd = [ffmpeg, "-y"]

        if start_time is not None:
            cmd.extend(["-ss", str(start_time)])

        cmd.extend(["-i", str(src)])

        if duration_seconds is not None:
            cmd.extend(["-t", str(duration_seconds)])

        cmd.extend([
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "28",
            "-c:a", "aac",
            "-ar", "16000",
            "-ac", "1",
            "-b:a", "64k",
            str(dst),
        ])

        try:
            with _FFMPEG_LOCK:
                res = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=SUBPROCESS_TIMEOUT_SEC,
                )
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(
                f"FFmpeg 视频切片超时 (>{SUBPROCESS_TIMEOUT_SEC}s): 文件可能过大，建议先切片。"
            ) from e
        if res.returncode != 0 or not dst.exists() or dst.stat().st_size == 0:
            raise RuntimeError(f"FFmpeg 视频切片失败: {res.stderr}")

        return dst

    @classmethod
    def extract_video_keyframes(
        cls,
        input_file: str | Path,
        output_dir: str | Path,
        fps: float = 1.0,
        max_frames: int = 120,
    ) -> List[Path]:
        """Extracts sampled JPG frames for Vision models (DeepSeek, Claude, GPT-4o Vision)."""
        src = Path(input_file).resolve()
        out_dir = Path(output_dir).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)

        ffmpeg = cls._find_ffmpeg()
        # Scale to max 720p width to save tokens and bandwidth
        frame_pattern = str(out_dir / "frame_%04d.jpg")
        cmd = [
            ffmpeg,
            "-y",
            "-i", str(src),
            "-vf", f"fps={fps},scale='min(1280,iw)':-2",
            "-q:v", "3",
            "-frames:v", str(max_frames),
            frame_pattern,
        ]

        try:
            with _FFMPEG_LOCK:
                res = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=SUBPROCESS_TIMEOUT_SEC,
                )
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(
                f"FFmpeg 抽帧超时 (>{SUBPROCESS_TIMEOUT_SEC}s): 视频可能过大或不可解码。"
            ) from e
        if res.returncode != 0:
            raise RuntimeError(f"FFmpeg 抽帧失败: {res.stderr}")

        frames = sorted(out_dir.glob("frame_*.jpg"))
        return frames

    @classmethod
    def compress_video_for_multimodal(
        cls,
        input_file: str | Path,
        output_file: Optional[str | Path] = None,
        target_height: int = 480,
    ) -> Path:
        """Compresses a video to 480p 15fps lightweight MP4.

        Note:
            The historical docstring implied this only ran for files larger
            than 100MB, but the implementation is *unconditional*. Currently
            no caller invokes this method. Intended to be used before uploading
            oversized videos to multimodal backends.
        """
        src = Path(input_file).resolve()
        dst = Path(output_file).resolve() if output_file else src.parent / f"{src.stem}_480p.mp4"
        dst.parent.mkdir(parents=True, exist_ok=True)

        ffmpeg = cls._find_ffmpeg()
        cmd = [
            ffmpeg,
            "-y",
            "-i", str(src),
            "-vf", f"scale=-2:{target_height}",
            "-r", "15",
            "-c:v", "libx264",
            "-crf", "30",
            "-preset", "veryfast",
            "-c:a", "aac",
            "-ar", "16000",
            "-ac", "1",
            "-b:a", "64k",
            str(dst),
        ]

        try:
            with _FFMPEG_LOCK:
                res = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=SUBPROCESS_TIMEOUT_SEC,
                )
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(
                f"FFmpeg 视频压缩超时 (>{SUBPROCESS_TIMEOUT_SEC}s): 文件可能过大。"
            ) from e
        if res.returncode != 0 or not dst.exists() or dst.stat().st_size == 0:
            raise RuntimeError(f"FFmpeg 视频压缩失败: {res.stderr}")

        return dst
