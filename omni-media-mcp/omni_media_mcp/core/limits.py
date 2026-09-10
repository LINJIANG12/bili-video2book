"""Centralized safety limits, whitelists, and shared constants for OmniMedia.

This module is the single source of truth for file-size caps, subprocess
timeouts, media-extension whitelists, and enum-like whitelists so callers
(server.py, providers, core helpers, benchmarks) do not duplicate magic
numbers or hardcoded extension sets.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Resource-safety limits
# ---------------------------------------------------------------------------

# Maximum wall-clock seconds allowed for any single ffmpeg/ffprobe subprocess.
# Prevents a runaway encode from blocking the MCP event loop indefinitely.
SUBPROCESS_TIMEOUT_SEC: int = 300

# Maximum wall-clock seconds for a metadata probe (ffprobe / ffmpeg -i). Probes
# must fail fast: they run on the request path before any real work begins.
PROBE_TIMEOUT_SEC: int = 15

# Maximum payload size we are willing to base64-encode fully into memory when
# sending media inline to a provider. Above this, callers should either slice
# the media or switch to a provider upload path (e.g. Gemini Files API).
MAX_INLINE_BYTES: int = 20 * 1024 * 1024  # 20 MiB

# Maximum seconds to keep polling a remote upload (e.g. Gemini Files API
# state transition) before giving up with a clear error.
UPLOAD_POLL_TIMEOUT_SEC: int = 120

# Maximum safe payload size for inline base64 audio over MCP stdio transport.
# Kept strictly under 8 MiB to prevent JSON-RPC stdio buffer overflow in clients.
MAX_SAFE_INLINE_BYTES: int = 8 * 1024 * 1024  # 8 MiB

# Default slice duration budget (minutes) when none is specified on large media.
DEFAULT_SAFE_SLICE_MINUTES: float = 10.0

# Maximum duration in minutes for single-shot audio generation without chunking
MAX_ONESHOT_MINUTES: float = 75.0

# Maximum concurrent FFmpeg processes to prevent CPU/IO thrashing under multi-agent workloads
MAX_CONCURRENT_FFMPEG: int = 3

# High-compression voice bitrate for speech LLM perception
AUDIO_BITRATE_VOICE: str = "32k"

# ---------------------------------------------------------------------------
# Media extension whitelists
# ---------------------------------------------------------------------------

VIDEO_EXTS: frozenset[str] = frozenset(
    {".mp4", ".mkv", ".mov", ".flv", ".webm", ".avi", ".wmv", ".ts"}
)

AUDIO_EXTS: frozenset[str] = frozenset(
    {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".opus"}
)

MEDIA_EXTS: frozenset[str] = frozenset(VIDEO_EXTS | AUDIO_EXTS)

# ---------------------------------------------------------------------------
# Whitelists for free-form string parameters exposed as MCP tool arguments
# ---------------------------------------------------------------------------

MODE_WHITELIST: frozenset[str] = frozenset({"transcribe", "summarize", "qa", "custom"})

PROBE_CATEGORY_WHITELIST: frozenset[str] = frozenset({"all", "audio", "video"})

OUTPUT_MODE_WHITELIST: frozenset[str] = frozenset({"auto", "file", "inline"})

# ---------------------------------------------------------------------------
# Storage paths
# ---------------------------------------------------------------------------

from pathlib import Path


def get_slices_cache_dir() -> Path:
    """Returns persistent cache directory for extracted audio slices."""
    cache_dir = Path.home() / ".omni-media" / "slices"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir

