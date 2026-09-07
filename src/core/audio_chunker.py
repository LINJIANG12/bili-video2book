"""Lossless Audio Chunker using FFmpeg Stream Copy.

Optimized for multimodal AI models (Audio Agents / Multimodal LLMs):
- Splits long lectures (e.g. 45min - 2hours) into 10-20 min semantic chunks
- Zero re-encoding: uses `-acodec copy` for instantaneous (<0.1s) segmentation
- Generates structured manifest with timestamps for downstream AI aggregation
"""

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional


class AudioChunker:
    @staticmethod
    def get_audio_duration(audio_filepath: str) -> float:
        """Get audio file duration in seconds using ffprobe or ffmpeg."""
        ffprobe_bin = shutil.which("ffprobe")
        if ffprobe_bin:
            cmd = [
                ffprobe_bin,
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(audio_filepath),
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if res.returncode == 0 and res.stdout.strip():
                try:
                    return float(res.stdout.strip())
                except ValueError:
                    pass

        # Fallback to ffmpeg -i parsing
        ffmpeg_bin = shutil.which("ffmpeg")
        if ffmpeg_bin:
            cmd = [ffmpeg_bin, "-i", str(audio_filepath)]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            output = res.stderr
            # Parse Duration: 00:40:09.12
            import re
            m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.?\d*)", output)
            if m:
                hours = float(m.group(1))
                minutes = float(m.group(2))
                seconds = float(m.group(3))
                return hours * 3600 + minutes * 60 + seconds

        return 0.0

    @classmethod
    def chunk_audio(
        cls,
        audio_filepath: str,
        chunk_minutes: int = 10,
        balanced: bool = True,
        output_dir: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Split audio into segments using stream copy.
        If duration <= chunk_minutes (default 10 min), returns single file.
        If duration > chunk_minutes and balanced=True, divides duration evenly into N=ceil(duration/chunk) slices.
        """
        import math

        src = Path(audio_filepath).resolve()
        if not src.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_filepath}")

        total_duration = cls.get_audio_duration(str(src))
        chunk_seconds = chunk_minutes * 60

        # If audio is shorter than or equal to target chunk size (<= 10 min), return single file
        if total_duration <= chunk_seconds or chunk_seconds <= 0:
            return [{
                "chunk_index": 1,
                "start_sec": 0.0,
                "end_sec": total_duration,
                "duration_sec": total_duration,
                "start_time_str": "00:00:00",
                "end_time_str": cls.format_seconds(total_duration),
                "filepath": str(src),
            }]

        target_dir = Path(output_dir).resolve() if output_dir else src.parent / f"{src.stem}_chunks"
        target_dir.mkdir(parents=True, exist_ok=True)

        ffmpeg_bin = shutil.which("ffmpeg")
        if not ffmpeg_bin:
            raise RuntimeError("FFmpeg is required for audio chunking")

        # Balanced-average chunking: N = ceil(duration / chunk_seconds)
        if balanced:
            num_chunks = max(1, math.ceil(total_duration / float(chunk_seconds)))
            slice_dur = total_duration / float(num_chunks)
        else:
            slice_dur = float(chunk_seconds)
            num_chunks = max(1, math.ceil(total_duration / float(chunk_seconds)))

        chunks = []
        for index in range(1, num_chunks + 1):
            start_sec = (index - 1) * slice_dur
            end_sec = min(total_duration, index * slice_dur) if index < num_chunks else total_duration
            duration_current = end_sec - start_sec

            chunk_filename = f"{src.stem}_part_{index:03d}{src.suffix}"
            chunk_path = target_dir / chunk_filename

            cmd = [
                ffmpeg_bin,
                "-y",
                "-ss", str(round(start_sec, 2)),
                "-i", str(src),
                "-t", str(round(duration_current, 2)),
                "-acodec", "copy",
                str(chunk_path),
            ]
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

            chunks.append({
                "chunk_index": index,
                "start_sec": round(start_sec, 2),
                "end_sec": round(end_sec, 2),
                "duration_sec": round(duration_current, 2),
                "start_time_str": cls.format_seconds(start_sec),
                "end_time_str": cls.format_seconds(end_sec),
                "filepath": str(chunk_path),
            })

        return chunks

    @staticmethod
    def format_seconds(seconds: float) -> str:
        """Format seconds into HH:MM:SS string."""
        s = int(round(seconds))
        hours = s // 3600
        minutes = (s % 3600) // 60
        secs = s % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    # Alias for method compatibility
    format_time = format_seconds
