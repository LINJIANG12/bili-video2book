"""Kernel Extractor: Exports knowledge-kernel extraction task-files for Agent-native execution.

Architecture: the CLI only provides tooling (source resolution, task-file export, cache reuse).
The host dialogue model performs the real semantic extraction and writes the kernel JSON.
A missing kernel is reported as pending -- it is never faked with local heuristics.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import fsutil
from .workspace import sanitize_filename


class KernelExtractor:
    STATUS_EXTRACTED = "extracted"
    STATUS_PENDING = "need-agent-kernel"

    KERNEL_PROMPT = """你是一位顶尖计算机科学与工程知识萃取专家。
请仔细阅读以下单集课程语料，执行【高纯度事实知识元（Factual Knowledge Kernel）】抽取。

【分集信息】：P{page:02d} - {title}
【待萃取语料正文】：
{transcript_text}

【萃取原则与要求】：
1. **头尾过渡噪声剥离**：
   - 坚决过滤开篇的考勤、调试设备、开场白闲聊、上节课简单复习客套；
   - 坚决过滤结尾的下课通知、作业提醒、下节预告；
   - 仅保留从引入实质概念、技术模型展开到核心推导结束的实质性正文。
2. **拒绝预设模板**：
   - 严禁生搬硬套固定的段落模板，严禁输出无意义的概括性空话；
   - 忠实还原语料传达的核心概念定义、模型运转机理、优缺点权衡、对比要素、生动具体的工程案例与避坑反模式。
3. **输出格式规范**：
   - 必须严格输出为合法 JSON 字典，严禁在 JSON 外包裹任何 Markdown 标记或多余文字：

```json
{{
  "page": {page},
  "title": "{title}",
  "status": "extracted",
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

    # ------------------------------------------------------------------
    # Paths and source resolution
    # ------------------------------------------------------------------

    @classmethod
    def kernel_json_path(cls, ws: Any, page: int, title: str) -> Path:
        """Canonical on-disk location of an episode's Agent-produced kernel JSON."""
        return ws.subtitles_dir / "kernels" / f"P{page:02d}_{sanitize_filename(title)}_kernel.json"

    @staticmethod
    def find_article(ws: Any, page: int) -> Optional[Path]:
        """Locate the episode's single-episode article (excludes task-files).

        体积判定走 `fsutil.file_size`：工作区里若混入不可访问的装入点，
        `stat()` 会抛 OSError，而本方法几乎是所有链路的公共依赖，
        不能让它成为「一门课拖垮整轮」的单点。
        """
        candidates = [
            f for f in sorted(ws.articles_dir.glob(f"P{page:02d}_*.md"))
            if not f.name.endswith("_TASK.md")
        ]
        if candidates and fsutil.file_size(candidates[0]) > 200:
            return candidates[0]
        return None

    # ------------------------------------------------------------------
    # Prompt and task-file export
    # ------------------------------------------------------------------

    @classmethod
    def build_kernel_prompt(cls, page: int, title: str, transcript_text: str) -> str:
        """Build the kernel-extraction prompt for the Agent to execute natively."""
        safe_title = title.replace("{", "(").replace("}", ")")
        safe_text = transcript_text[:25000]
        prompt = (
            cls.KERNEL_PROMPT
            .replace("{page:02d}", f"{page:02d}")
            .replace("{page}", str(page))
            .replace("{title}", safe_title)
            .replace("{transcript_text}", safe_text)
        )
        # The schema example uses doubled braces so it survives the replacements above.
        return prompt.replace("{{", "{").replace("}}", "}")

    @classmethod
    def export_kernel_task(
        cls,
        page: int,
        title: str,
        source_text: str,
        source_path: Path,
        kernel_path: Path,
    ) -> Path:
        """Export the KERNEL_TASK file that instructs the host Agent to extract kernels."""
        kernel_path = Path(kernel_path)
        task_file = kernel_path.parent / f"P{page:02d}_{sanitize_filename(title)}_KERNEL_TASK.md"
        prompt = cls.build_kernel_prompt(page, title, source_text)
        content = (
            f"# P{page:02d} {title} 知识元抽取任务书（KERNEL_TASK）\n\n"
            f"> 状态：{cls.STATUS_PENDING} | 由宿主 Agent 阅读语料后原生抽取；CLI 不做本地启发式抽取\n\n"
            f"## 1. 语料来源\n\n"
            f"- 单集精读文章：`{Path(source_path).as_posix()}`\n\n"
            f"## 2. 落盘要求\n\n"
            f"- 目标文件：`{kernel_path.as_posix()}`\n"
            f"- 必须为合法 JSON 对象，且必须写入 `\"status\": \"{cls.STATUS_EXTRACTED}\"`\n"
            f"- 严禁在 JSON 外包裹任何 Markdown 代码块标记或多余文字\n"
            f"- 抽取完成后重跑对应 CLI 命令即可自动复用该知识元文件\n\n"
            f"---\n\n"
            f"## 3. 抽取提示词\n\n{prompt}\n"
        )
        task_file.parent.mkdir(parents=True, exist_ok=True)
        task_file.write_text(content, encoding="utf-8")
        return task_file

    # ------------------------------------------------------------------
    # Cache reuse / pending reporting
    # ------------------------------------------------------------------

    @classmethod
    def load_kernel(cls, kernel_path: Optional[Path]) -> Optional[Dict[str, Any]]:
        """Load an Agent-produced kernel, or None when it is absent/not yet extracted."""
        if not kernel_path:
            return None
        path = Path(kernel_path)
        if not path.exists() or path.stat().st_size < 50:
            return None
        try:
            cached = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
        if not isinstance(cached, dict):
            return None
        if cached.get("status") != cls.STATUS_EXTRACTED:
            return None
        if not (cached.get("definitions") or cached.get("mechanisms_and_models")):
            return None
        return cached

    @classmethod
    def collect_kernel(cls, page: int, title: str, ws: Any) -> Dict[str, Any]:
        """Reuse the Agent-produced kernel, otherwise export a task-file and report it as pending."""
        article = cls.find_article(ws, page)
        if article is None:
            return {
                "page": page,
                "title": title,
                "status": "need-agent-article",
                "definitions": [],
                "mechanisms_and_models": [],
                "comparisons": [],
                "case_studies": [],
                "anti_patterns": [],
            }

        kernel_path = cls.kernel_json_path(ws, page, title)
        cached = cls.load_kernel(kernel_path)
        if cached is not None:
            # 成品已落盘：顺手回收该集知识元任务书（保持编号最小的一份作范本）
            try:
                from .task_cleanup import reclaim_kernel_task
                reclaim_kernel_task(ws, page)
            except Exception:
                pass
            return cached

        task_file = cls.export_kernel_task(
            page=page,
            title=title,
            source_text=article.read_text(encoding="utf-8"),
            source_path=article,
            kernel_path=kernel_path,
        )
        return {
            "page": page,
            "title": title,
            "status": cls.STATUS_PENDING,
            "task_file": str(task_file),
            "definitions": [],
            "mechanisms_and_models": [],
            "comparisons": [],
            "case_studies": [],
            "anti_patterns": [],
        }

    @classmethod
    def extract_batch_kernels(cls, episodes: List[Dict[str, Any]], ws: Any) -> List[Dict[str, Any]]:
        """Collect kernels for a block: reuse extracted ones, export task-files for the rest."""
        results = [cls.collect_kernel(ep["page"], ep["title"], ws) for ep in episodes]
        results.sort(key=lambda x: x["page"])
        return results

    @staticmethod
    def pending_pages(kernels: List[Dict[str, Any]]) -> List[int]:
        """Episodes whose kernels are not yet Agent-extracted."""
        return [
            k["page"] for k in kernels
            if k.get("status") in (KernelExtractor.STATUS_PENDING, "need-agent-article")
        ]
