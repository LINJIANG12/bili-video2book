"""Model Benchmark Reporting Engine.

Note: despite historical wording referencing "live probing" / online sources,
:meth:`BenchmarkProber.generate_report` renders a **static** snapshot from
:data:`~omni_media_mcp.benchmarks.model_registry.MODEL_REGISTRY` combined with
the **local** activation state of each provider's API key. It performs no
network calls.
"""

from __future__ import annotations

import os
from typing import Dict

from ..core.limits import PROBE_CATEGORY_WHITELIST
from .model_registry import MODEL_REGISTRY, ModelSpec

# A model can meaningfully process video if it exposes container or sampled-frame capability.
_VIDEO_CAPABILITIES = {"native_container", "sampled_frames"}
# A model can meaningfully process audio unless it is strictly vision-only.
_AUDIO_CAPABILITIES = {"native_waveform", "input_audio", "speech_bridge"}


class BenchmarkProber:
    """Generates comparative intelligence reports from a static registry and live env status."""

    @classmethod
    def get_live_environment_status(cls) -> Dict[str, bool]:
        status = {}
        for spec in MODEL_REGISTRY.values():
            status[spec.env_key] = bool(os.environ.get(spec.env_key))
        return status

    @staticmethod
    def _category_matches(spec: ModelSpec, category: str) -> bool:
        """Return True if ``spec`` belongs to ``category`` ('all' | 'audio' | 'video')."""
        if category == "all":
            return True
        if category == "video":
            return spec.video_capability in _VIDEO_CAPABILITIES
        if category == "audio":
            return spec.audio_capability in _AUDIO_CAPABILITIES
        # Unreachable when whitelist is enforced by callers; kept defensive.
        return True

    @classmethod
    def generate_report(cls, category: str = "all") -> str:
        """Render the benchmark matrix for a category.

        Args:
            category: Which models to include — 'all' (default), 'audio', or
                'video'. Raises ValueError for unsupported values.

        Returns:
            A markdown report built from the static MODEL_REGISTRY snapshot and
            each model's local API-key activation status. No network I/O.
        """
        category = (category or "all").strip().lower()
        if category not in PROBE_CATEGORY_WHITELIST:
            raise ValueError(
                f"不支持的类别: '{category}'。支持: {sorted(PROBE_CATEGORY_WHITELIST)}"
            )

        env_status = cls.get_live_environment_status()

        rows = []
        for spec in MODEL_REGISTRY.values():
            if not cls._category_matches(spec, category):
                continue
            is_active = "✅ 已就绪" if env_status.get(spec.env_key) else f"⚠️ 缺少 `{spec.env_key}`"

            # Context human
            ctx_k = f"{spec.context_window // 1000}k"

            rows.append(
                f"| **{spec.display_name}** | {spec.vendor} | {ctx_k} | {spec.audio_capability} | {spec.video_mme_score:.1f}% | {spec.artificial_analysis_elo} | ${spec.audio_cost_per_hour_usd:.3f}/h | {is_active} |"
            )

        table_str = "\n".join(rows)

        return f"""# 🌐 全球前沿多模态大模型音视频能力基准矩阵 (2026 最新)

> 数据来源：内置静态基准快照（源自 Video-MME / Artificial Analysis / 厂商官方规格，非实时联网）；本地激活状态实时读取。

| 模型型号 | 研发厂商 | 上下文窗口 | 音频支持形态 | Video-MME 得分 | AA Elo 评分 | 音频单价预估 | 本地激活状态 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
{table_str}

---

### 💡 智能选型指南与决策建议:

1. **公开课/系列网课/精读长文重构（首选）**：
   - **Google Gemini 2.5 / 3.0 Flash**：100万~200万 Token 超大上下文，原生音频波形直吞，每小时处理成本仅约 $0.015，抗噪与术语推导综合第一。
2. **端到端国产全模态开源生态**：
   - **小米 Xiaomi MiMo-V2.5**：100万 Token 原生全模态，MoE 高吞吐，适合私有部署与全模态端侧协同。
3. **高密度板书/PPT/复杂图表提取**：
   - **阿里 Qwen2.5-VL / Qwen3-Omni** & **DeepSeek-V4-Flash-Vision**：对黑板数学公式、代码终端 OCR 与中文专业术语识别极强。
4. **口语质感与细粒度对话转录**：
   - **OpenAI GPT-4o Audio**：标准 `input_audio`，自然对话理解与语调识别极优。
"""
