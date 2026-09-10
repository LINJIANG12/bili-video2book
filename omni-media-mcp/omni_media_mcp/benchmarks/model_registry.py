"""Unified Model Capability Registry and Metadata."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, List, Optional


@dataclass
class ModelSpec:
    model_id: str
    vendor: str  # "Google", "Xiaomi", "OpenAI", "Alibaba", "DeepSeek", "MiniMax"
    family: str
    display_name: str
    context_window: int
    audio_capability: str  # "native_waveform" | "input_audio" | "vision_only" | "speech_bridge"
    video_capability: str  # "native_container" | "sampled_frames" | "none"
    max_file_size_mb: int
    env_key: str
    audio_cost_per_hour_usd: float
    video_mme_score: float  # Video-MME benchmark accuracy (%)
    artificial_analysis_elo: int
    recommended_use_case: str


MODEL_REGISTRY: Dict[str, ModelSpec] = {
    # 1. Google Gemini
    "gemini-2.5-flash": ModelSpec(
        model_id="gemini-2.5-flash",
        vendor="Google",
        family="Gemini",
        display_name="Gemini 2.5 Flash",
        context_window=1048576,
        audio_capability="native_waveform",
        video_capability="native_container",
        max_file_size_mb=2048,
        env_key="GEMINI_API_KEY",
        audio_cost_per_hour_usd=0.015,
        video_mme_score=79.2,
        artificial_analysis_elo=1340,
        recommended_use_case="长篇网课/连载公开课教材重构，高性价比首选",
    ),
    "gemini-3.0-flash": ModelSpec(
        model_id="gemini-3.0-flash",
        vendor="Google",
        family="Gemini",
        display_name="Gemini 3.0 Flash",
        context_window=2097152,
        audio_capability="native_waveform",
        video_capability="native_container",
        max_file_size_mb=2048,
        env_key="GEMINI_API_KEY",
        audio_cost_per_hour_usd=0.018,
        video_mme_score=82.5,
        artificial_analysis_elo=1375,
        recommended_use_case="超大规模音视频合集端到端理解与极速响应",
    ),

    # 2. 小米 Xiaomi (MiMo 系列)
    "mimo-v2.5": ModelSpec(
        model_id="mimo-v2.5",
        vendor="Xiaomi (小米)",
        family="MiMo",
        display_name="Xiaomi MiMo-V2.5",
        context_window=1048576,
        audio_capability="native_waveform",
        video_capability="native_container",
        max_file_size_mb=1024,
        env_key="MIMO_API_KEY",
        audio_cost_per_hour_usd=0.016,
        video_mme_score=78.8,
        artificial_analysis_elo=1330,
        recommended_use_case="小米开源原生全模态架构，端到端声画感知与长时序跟踪",
    ),

    # 3. OpenAI
    "gpt-4o-audio-preview": ModelSpec(
        model_id="gpt-4o-audio-preview",
        vendor="OpenAI",
        family="GPT-4o",
        display_name="GPT-4o Audio Preview",
        context_window=128000,
        audio_capability="input_audio",
        video_capability="sampled_frames",
        max_file_size_mb=20,
        env_key="OPENAI_API_KEY",
        audio_cost_per_hour_usd=0.06,
        video_mme_score=77.5,
        artificial_analysis_elo=1325,
        recommended_use_case="高保真口语转录与多语言自然表达",
    ),

    # 4. 阿里 Alibaba Qwen
    "qwen2.5-vl-72b-instruct": ModelSpec(
        model_id="qwen2.5-vl-72b-instruct",
        vendor="Alibaba (阿里通义千问)",
        family="Qwen-VL",
        display_name="Qwen2.5-VL 72B Instruct",
        context_window=131072,
        audio_capability="speech_bridge",
        video_capability="native_container",
        max_file_size_mb=500,
        env_key="DASHSCOPE_API_KEY",
        audio_cost_per_hour_usd=0.025,
        video_mme_score=81.1,
        artificial_analysis_elo=1355,
        recommended_use_case="中文板书数学公式识别、视频复杂图表解析",
    ),
    "qwen3-omni-flash": ModelSpec(
        model_id="qwen3-omni-flash",
        vendor="Alibaba (阿里通义千问)",
        family="Qwen-Omni",
        display_name="Qwen3-Omni-Flash",
        context_window=262144,
        audio_capability="native_waveform",
        video_capability="native_container",
        max_file_size_mb=1024,
        env_key="DASHSCOPE_API_KEY",
        audio_cost_per_hour_usd=0.02,
        video_mme_score=80.4,
        artificial_analysis_elo=1348,
        recommended_use_case="中文全模态视音频交互与低延迟理解",
    ),

    # 5. DeepSeek
    "deepseek-v4-flash-vision-exp": ModelSpec(
        model_id="deepseek-v4-flash-vision-exp",
        vendor="DeepSeek",
        family="DeepSeek-Vision",
        display_name="DeepSeek-V4-Flash-Vision-Exp",
        context_window=131072,
        audio_capability="speech_bridge",
        video_capability="sampled_frames",
        max_file_size_mb=100,
        env_key="DEEPSEEK_API_KEY",
        audio_cost_per_hour_usd=0.01,
        video_mme_score=78.2,
        artificial_analysis_elo=1335,
        recommended_use_case="代码屏幕录屏 OCR 抓取、架构图推理、超低推理单价",
    ),

    # 6. MiniMax (稀宇科技)
    "minimax-h3": ModelSpec(
        model_id="minimax-h3",
        vendor="MiniMax (稀宇科技)",
        family="MiniMax",
        display_name="MiniMax H3 Omni",
        context_window=262144,
        audio_capability="native_waveform",
        video_capability="native_container",
        max_file_size_mb=1024,
        env_key="MINIMAX_API_KEY",
        audio_cost_per_hour_usd=0.03,
        video_mme_score=79.6,
        artificial_analysis_elo=1338,
        recommended_use_case="原生多模态视频理解与跨模态生成",
    ),
}


def get_model_spec(model_id_or_alias: str) -> Optional[ModelSpec]:
    """Retrieves model specification by ID or common alias."""
    alias_map = {
        "gemini": "gemini-2.5-flash",
        "gemini-flash": "gemini-2.5-flash",
        "gemini-pro": "gemini-2.5-flash",
        "mimo": "mimo-v2.5",
        "xiaomi": "mimo-v2.5",
        "openai": "gpt-4o-audio-preview",
        "gpt4o": "gpt-4o-audio-preview",
        "qwen": "qwen2.5-vl-72b-instruct",
        "qwen-omni": "qwen3-omni-flash",
        "deepseek": "deepseek-v4-flash-vision-exp",
        "minimax": "minimax-h3",
    }
    key = alias_map.get(model_id_or_alias.lower(), model_id_or_alias)
    return MODEL_REGISTRY.get(key)
