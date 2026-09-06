"""Kernel Extractor: Builds prompts for Agent to extract atomic factual knowledge kernels, plus local fallback structuring.

Architecture: CLI provides tooling (transcripts, prompts, local fallback JSON). The mature Agent itself performs semantic extraction and synthesis.
"""

import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional


class KernelExtractor:
    KERNEL_PROMPT = """你是一位顶尖计算机科学与工程知识萃取专家。
请仔细阅读以下单集课程转录文本，执行【高纯度事实知识元（Factual Knowledge Kernel）】抽取。

【分集信息】：P{page:02d} - {title}
【原始转录文本】：
{transcript_text}

【萃取原则与要求】：
1. **头尾过渡噪声剥离**：
   - 坚决过滤开篇 3~5 分钟内的考勤、调试设备、开场白闲聊、上节课简单复习客套；
   - 坚决过滤结尾 2~3 分钟内的下课通知、作业提醒、下节预告；
   - 仅保留从引入实质概念、技术模型展开到核心推导结束的实质性正文。
2. **拒绝预设模板**：
   - 严禁生搬硬套固定的段落模板，严禁输出无意义的概括性空话；
   - 忠实还原老师传达的核心概念定义、模型运转机理、优缺点权衡、对比要素、生动具体的工程案例与避坑反模式。
3. **输出格式规范**：
   - 必须严格输出为合法 JSON 字典，严禁在 JSON 外包裹任何 Markdown 标记或多余文字：

```json
{{
  "page": {page},
  "title": "{title}",
  "definitions": [
    {{"term": "专业术语名称", "essence": "核心本质与精准定义"}}
  ],
  "mechanisms_and_models": [
    {{"name": "模型/机理名称", "details": "底层运行机制、核心步骤或关键参数"}}
  ],
  "comparisons": [
    {{"entities": "概念A vs 概念B", "distinction": "两者的本质差异、适用场景对比"}}
  ],
  "case_studies": [
    {{"case_name": "案例名称（如在线支付系统）", "context": "遇到的具体问题与工程演进", "lesson": "核心启发与解决方案"}}
  ],
  "anti_patterns": [
    "工程实践或考点中需规避的反模式/错误认识"
  ]
}}
```
"""

    @staticmethod
    def strip_transient_chatter(text: str) -> str:
        """Heuristic helper to trim obvious introductory or closure sentences."""
        cleaned = re.sub(r"^(大家好|同学们好|我们现在开始上课|上节课我们讲了).*?[。！？\n]", "", text)
        cleaned = re.sub(r"(今天就讲到这里|下课了|下节课再见|把作业交一下).*?$", "", cleaned)
        return cleaned.strip()

    @classmethod
    def degraded_extract(cls, page: int, title: str, text: str) -> Dict[str, Any]:
        """Circuit-breaker degradation fallback when model extraction fails."""
        cleaned = cls.strip_transient_chatter(text)
        sentences = [s.strip() for s in re.split(r"[。！？\n]+", cleaned) if len(s.strip()) > 15]

        return {
            "page": page,
            "title": title,
            "status": "degraded",
            "definitions": [{"term": title, "essence": sentences[0] if sentences else title}],
            "mechanisms_and_models": [],
            "comparisons": [],
            "case_studies": [],
            "anti_patterns": [],
            "raw_summary": " ".join(sentences[:5]),
        }

    @classmethod
    def build_kernel_prompt(cls, page: int, title: str, transcript_text: str) -> str:
        """Build the kernel-extraction prompt for the Agent to execute natively."""
        safe_title = title.replace("{", "(").replace("}", ")")
        safe_text = transcript_text[:25000]
        return cls.KERNEL_PROMPT.replace("{page:02d}", f"{page:02d}").replace("{page}", str(page)).replace("{title}", safe_title).replace("{transcript_text}", safe_text)

    @classmethod
    def extract_single_kernel(
        cls,
        page: int,
        title: str,
        transcript_text: str,
        kernel_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """
        Local fallback structuring (no network).
        The mature Agent should execute build_kernel_prompt() natively for high-quality kernels.
        This method only provides checkpoint reuse + local degraded structuring for offline tooling.
        """
        if kernel_path and kernel_path.exists() and kernel_path.stat().st_size > 50:
            try:
                cached = json.loads(kernel_path.read_text(encoding="utf-8"))
                if cached.get("status") == "extracted" and (cached.get("definitions") or cached.get("mechanisms_and_models")):
                    return cached
            except Exception:
                pass

        if not transcript_text or len(transcript_text.strip()) < 50:
            return cls.degraded_extract(page, title, transcript_text or "")

        fallback = cls.degraded_extract(page, title, transcript_text)
        if kernel_path:
            kernel_path.parent.mkdir(parents=True, exist_ok=True)
            kernel_path.write_text(json.dumps(fallback, ensure_ascii=False, indent=2), encoding="utf-8")
        return fallback

    @classmethod
    def extract_batch_kernels(
        cls,
        episodes: List[Dict[str, Any]],
        ws: Any,
        max_workers: int = 5,
    ) -> List[Dict[str, Any]]:
        """Run sub-agents in parallel to extract knowledge kernels for multiple episodes."""
        kernels_dir = ws.subtitles_dir / "kernels"
        kernels_dir.mkdir(parents=True, exist_ok=True)

        def _subagent_worker(ep: Dict[str, Any]) -> Dict[str, Any]:
            p_num = ep["page"]
            clean_title = "".join(c for c in ep["title"] if c.isalnum() or c in (" ", "-", "_")).strip()
            k_path = kernels_dir / f"P{p_num:02d}_{clean_title}_kernel.json"

            # Read clean transcript file
            clean_txt_file = ws.subtitles_dir / f"P{p_num:02d}_{clean_title}_clean.txt"
            if clean_txt_file.exists():
                text = clean_txt_file.read_text(encoding="utf-8")
            else:
                text = ep.get("transcript", "")

            return cls.extract_single_kernel(
                page=p_num,
                title=ep["title"],
                transcript_text=text,
                kernel_path=k_path,
            )

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(executor.map(_subagent_worker, episodes))

        results.sort(key=lambda x: x["page"])
        return results
