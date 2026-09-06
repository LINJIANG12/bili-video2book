"""Agent Model Client: Native Multimodal Audio & Reasoning Integration.

Directly connects to the Agent's configured dialogue model (e.g. gemini-3.8-flash-high)
via the local gateway configured in ~/.config/opencode/opencode.jsonc.

Features:
- Auto-discovery of active dialogue model and gateway options.
- Dynamic modality probe (can_transcribe_audio) to ensure model supports audio input.
- High-efficiency multimodal audio ingestion (base64 inlineData) for direct acoustic transcription.
- Multi-protocol support (Google Gemini REST and OpenAI-compatible).
"""

import base64
import json
import os
import re
import shutil
import subprocess
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from .audio_chunker import AudioChunker
from ..generator.prompt_templates import AUDIO_TRANSCRIPTION_PROMPT


class AgentModelClient:
    _cached_config: Optional[Dict[str, Any]] = None

    @classmethod
    def discover_config(cls, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """
        Discover active dialogue model configuration.
        Priority:
        1. Environment variables (AGENT_BASE_URL, AGENT_API_KEY, AGENT_MODEL)
        2. ~/.config/opencode/opencode.jsonc or opencode.json
        """
        if cls._cached_config and not force_refresh:
            return cls._cached_config

        # 1. Environment variables
        env_url = os.environ.get("AGENT_BASE_URL")
        env_key = os.environ.get("AGENT_API_KEY")
        env_model = os.environ.get("AGENT_MODEL")
        if env_url and env_model:
            config = {
                "base_url": env_url.rstrip("/"),
                "api_key": env_key or "",
                "model": env_model,
                "protocol": "gemini" if "/v1beta" in env_url or "gemini" in env_model.lower() else "openai",
                "modalities": ["text", "image", "audio", "video"] if "gemini" in env_model.lower() else ["text"],
            }
            cls._cached_config = config
            return config

        # 2. Inspect opencode config paths
        user_home = Path.home()
        possible_paths = [
            user_home / ".config" / "opencode" / "opencode.jsonc",
            user_home / ".config" / "opencode" / "opencode.json",
        ]

        for p in possible_paths:
            if p.exists():
                try:
                    raw = p.read_text(encoding="utf-8")
                    # Remove comments for jsonc
                    clean_json = re.sub(r"//.*?\n|/\*.*?\*/", "", raw, flags=re.DOTALL)
                    data = json.loads(clean_json)

                    active_model_full = data.get("model", "")
                    provider_name = active_model_full.split("/")[0] if "/" in active_model_full else "gemini"
                    model_id = active_model_full.split("/")[-1] if "/" in active_model_full else active_model_full

                    provider_cfg = data.get("provider", {}).get(provider_name, {})
                    options = provider_cfg.get("options", {})
                    base_url = options.get("baseURL", "http://127.0.0.1:8045/v1beta").rstrip("/")
                    api_key = options.get("apiKey", "")

                    model_meta = provider_cfg.get("models", {}).get(model_id, {})
                    modalities = model_meta.get("modalities", {}).get("input", ["text"])

                    # If modalities not explicitly listed, check model family
                    if not modalities or modalities == ["text"]:
                        if any(k in model_id.lower() for k in ("gemini-2", "gemini-3", "flash", "omni")):
                            modalities = ["text", "image", "audio", "video"]

                    protocol = "gemini" if "/v1beta" in base_url or "gemini" in provider_name.lower() else "openai"

                    config = {
                        "base_url": base_url,
                        "api_key": api_key,
                        "model": model_id,
                        "provider": provider_name,
                        "protocol": protocol,
                        "modalities": modalities,
                    }
                    cls._cached_config = config
                    return config
                except Exception:
                    pass

        # Fallback to local gateway defaults
        cls._cached_config = {
            "base_url": "http://127.0.0.1:8045/v1beta",
            "api_key": "",
            "model": "gemini-3.8-flash-high",
            "provider": "gemini",
            "protocol": "gemini",
            "modalities": ["text", "image", "audio", "video"],
        }
        return cls._cached_config

    @classmethod
    def can_transcribe_audio(cls) -> bool:
        """Check if the active dialogue model supports native audio input modality."""
        cfg = cls.discover_config()
        if not cfg:
            return False
        modalities = cfg.get("modalities", [])
        return "audio" in modalities

    @classmethod
    def is_available(cls) -> bool:
        """Probe connectivity to the dialogue model gateway."""
        cfg = cls.discover_config()
        if not cfg:
            return False
        base_url = cfg["base_url"]
        probe_url = f"{base_url}/models" if cfg["protocol"] == "gemini" else f"{base_url}/models"
        try:
            req = urllib.request.Request(probe_url, headers={"User-Agent": "opencode-agent-client"}, method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                return resp.status == 200
        except Exception:
            return False

    @classmethod
    def generate_content(
        cls,
        prompt: str,
        audio_path: Optional[Union[str, Path]] = None,
        timeout: int = 180,
    ) -> str:
        """
        Send prompt and optional audio to dialogue model (supports Gemini & OpenAI protocols).
        """
        cfg = cls.discover_config()
        if not cfg:
            raise RuntimeError("Dialogue model configuration could not be discovered.")

        base_url = cfg["base_url"]
        api_key = cfg.get("api_key", "")
        model = cfg["model"]
        protocol = cfg.get("protocol", "gemini")

        # Encode audio if provided
        audio_b64 = None
        mime_type = "audio/mp3"
        tmp_mp3_to_clean = None

        if audio_path:
            if not cls.can_transcribe_audio():
                raise RuntimeError("Current dialogue model does not support audio input modality.")

            path_obj = Path(audio_path).resolve()
            if not path_obj.exists():
                raise FileNotFoundError(f"Audio file not found: {audio_path}")

            # Transcode to 64k mp3 if needed
            if path_obj.suffix.lower() != ".mp3":
                tmp_mp3 = path_obj.parent / f"_tmp_{path_obj.stem}_{os.getpid()}.mp3"
                cmd = ["ffmpeg", "-y", "-i", str(path_obj), "-acodec", "libmp3lame", "-b:a", "64k", str(tmp_mp3)]
                try:
                    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                    audio_bytes = tmp_mp3.read_bytes()
                    tmp_mp3_to_clean = tmp_mp3
                except Exception:
                    audio_bytes = path_obj.read_bytes()
            else:
                audio_bytes = path_obj.read_bytes()

            audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

        try:
            if protocol == "gemini":
                url = f"{base_url}/models/{model}:generateContent"
                headers = {"Content-Type": "application/json"}
                if api_key:
                    headers["x-goog-api-key"] = api_key

                parts: List[Dict[str, Any]] = []
                if audio_b64:
                    parts.append({
                        "inlineData": {
                            "mimeType": mime_type,
                            "data": audio_b64,
                        }
                    })
                parts.append({"text": prompt})

                payload = {"contents": [{"role": "user", "parts": parts}]}
                data_bytes = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")

                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))
                    candidates = resp_data.get("candidates", [])
                    if candidates:
                        content_parts = candidates[0].get("content", {}).get("parts", [])
                        return "".join(p.get("text", "") for p in content_parts).strip()
                    return ""
            else:
                # OpenAI compatible endpoint
                url = f"{base_url}/chat/completions"
                headers = {"Content-Type": "application/json"}
                if api_key:
                    headers["Authorization"] = f"Bearer {api_key}"

                messages: List[Dict[str, Any]] = []
                if audio_b64:
                    messages.append({
                        "role": "user",
                        "content": [
                            {"type": "input_audio", "input_audio": {"data": audio_b64, "format": "mp3"}},
                            {"type": "text", "text": prompt},
                        ],
                    })
                else:
                    messages.append({"role": "user", "content": prompt})

                payload = {"model": model, "messages": messages}
                data_bytes = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")

                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))
                    choices = resp_data.get("choices", [])
                    if choices:
                        return choices[0].get("message", {}).get("content", "").strip()
                    return ""
        except urllib.error.HTTPError as err:
            err_body = err.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Dialogue model request failed ({err.code}): {err_body}") from err
        finally:
            if tmp_mp3_to_clean and tmp_mp3_to_clean.exists():
                try:
                    tmp_mp3_to_clean.unlink(missing_ok=True)
                except OSError:
                    pass

    @classmethod
    def transcribe_audio(
        cls,
        audio_path: Union[str, Path],
        chunk_minutes: int = 10,
        initial_prompt: Optional[str] = None,
        max_concurrency: int = 4,
    ) -> Dict[str, Any]:
        """
        Multimodal audio-to-text transcription using the active dialogue model.
        Chunks audio into balanced 10-minute slices and transcribes them in parallel.
        """
        path_obj = Path(audio_path).resolve()
        if not path_obj.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        duration_sec = AudioChunker.get_audio_duration(str(path_obj))
        slices = AudioChunker.chunk_audio(str(path_obj), chunk_minutes=chunk_minutes, balanced=True)

        prompt = initial_prompt or AUDIO_TRANSCRIPTION_PROMPT

        def _worker(ch: Dict[str, Any]) -> Dict[str, Any]:
            ch_path = Path(ch["filepath"])
            ch_prompt = f"{prompt}\n当前片段相对时间：{ch['start_time_str']} -> {ch['end_time_str']}"
            ch_text = cls.generate_content(ch_prompt, audio_path=ch_path, timeout=120)

            # Clean temporary chunk file if it's not the original
            if ch_path != path_obj:
                try:
                    ch_path.unlink(missing_ok=True)
                except OSError:
                    pass

            return {
                "chunk_index": ch["chunk_index"],
                "text": ch_text,
                "start_sec": ch["start_sec"],
                "end_sec": ch["end_sec"],
                "start_time_str": ch["start_time_str"],
                "end_time_str": ch["end_time_str"],
            }

        concurrency = min(len(slices), max_concurrency)
        with ThreadPoolExecutor(max_workers=max(1, concurrency)) as executor:
            chunk_results = list(executor.map(_worker, slices))

        chunk_results.sort(key=lambda x: x["chunk_index"])

        all_texts = [cr["text"] for cr in chunk_results]
        segments = [
            {
                "start": cr["start_sec"],
                "end": cr["end_sec"],
                "start_fmt": cr["start_time_str"],
                "end_fmt": cr["end_time_str"],
                "text": cr["text"],
            }
            for cr in chunk_results
        ]
        timestamped_lines = [
            f"[{cr['start_time_str']} -> {cr['end_time_str']}] {cr['text']}"
            for cr in chunk_results
        ]

        full_text = "\n\n".join(all_texts)
        cfg = cls.discover_config()
        model_name = cfg.get("model", "dialogue-model") if cfg else "dialogue-model"

        return {
            "full_text": full_text,
            "timestamped_text": "\n".join(timestamped_lines),
            "segments": segments,
            "total_segments": len(segments),
            "engine": f"agent ({model_name})",
            "duration": duration_sec,
        }
