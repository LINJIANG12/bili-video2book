"""Multimodal Provider Router and Automatic Dispatcher."""

from __future__ import annotations

import os
from typing import Dict, List, Optional

from .base import BaseMultimodalProvider
from .deepseek_provider import DeepSeekProvider
from .gemini_provider import GeminiProvider
from .mimo_provider import MiMoProvider
from .minimax_provider import MiniMaxProvider
from .openai_provider import OpenAIProvider
from .qwen_provider import QwenProvider


class MultimodalRouter:
    """Intelligently routes requests to the optimal available multimodal provider."""

    def __init__(self):
        self.providers: Dict[str, BaseMultimodalProvider] = {
            "gemini": GeminiProvider(),
            "mimo": MiMoProvider(),
            "openai": OpenAIProvider(),
            "qwen": QwenProvider(),
            "deepseek": DeepSeekProvider(),
            "minimax": MiniMaxProvider(),
        }

    def list_available_providers(self) -> List[str]:
        return [name for name, p in self.providers.items() if p.is_available()]

    def get_provider(self, name: str = "auto") -> BaseMultimodalProvider:
        key = name.lower().strip()
        if key != "auto":
            # Map aliases
            alias_map = {
                "google": "gemini",
                "xiaomi": "mimo",
                "gpt": "openai",
                "dashscope": "qwen",
                "aliyun": "qwen",
            }
            resolved_name = alias_map.get(key, key)
            provider = self.providers.get(resolved_name)
            if not provider:
                raise ValueError(
                    f"不支持的 Provider: '{name}'。支持的列表: {list(self.providers.keys())}"
                )
            if not provider.is_available():
                env_keys = {
                    "gemini": "GEMINI_API_KEY",
                    "mimo": "MIMO_API_KEY",
                    "openai": "OPENAI_API_KEY",
                    "qwen": "DASHSCOPE_API_KEY",
                    "deepseek": "DEEPSEEK_API_KEY",
                    "minimax": "MINIMAX_API_KEY",
                }
                needed = env_keys.get(resolved_name, "API_KEY")
                raise ValueError(f"指定的 Provider '{resolved_name}' 未就绪，缺少环境变量 `{needed}`。")
            return provider

        # Auto-routing priority:
        # 1. Gemini (Longest context, native waveform, lowest cost)
        # 2. Xiaomi MiMo (1M context omnimodal)
        # 3. Qwen (Strong Chinese & visual math)
        # 4. OpenAI (Standard input_audio)
        # 5. DeepSeek (Vision OCR)
        # 6. MiniMax
        priority = ["gemini", "mimo", "qwen", "openai", "deepseek", "minimax"]
        for p_name in priority:
            p = self.providers[p_name]
            if p.is_available():
                return p

        raise ValueError(
            "未检测到任何可用的多模态模型 API Key！\n"
            "请至少配置以下之一的环境变量：\n"
            "- GEMINI_API_KEY (推荐，Google Gemini 原生直吞)\n"
            "- MIMO_API_KEY (小米 MiMo 全模态)\n"
            "- DASHSCOPE_API_KEY (阿里通义千问)\n"
            "- OPENAI_API_KEY (OpenAI GPT-4o Audio)\n"
            "- DEEPSEEK_API_KEY (DeepSeek 视觉)\n"
            "- MINIMAX_API_KEY (MiniMax 视音频)\n"
        )
