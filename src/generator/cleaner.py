"""Safe, Non-Destructive Spoken Text Cleaner & Normalizer.

Philosophy:
1. Abolishes destructive character-level regexes that mutilate Chinese idioms (e.g. "代代相传", "常常", "层层递进").
2. Preserves all grammatical verbs (e.g. "是不是") and demonstrative pronouns (e.g. "这个", "那个").
3. Safely normalizes consecutive duplicate punctuation (e.g. "，，" -> "，", "、、" -> "、") and excessive whitespace.
4. Leaves complex semantic deduplication and filler optimization to the host dialogue LLM.
"""

import re
from typing import Any, Dict


class TextCleaner:
    # 预编译通用文本清洗正则以复用提升执行效率
    _CHINESE_SPACE_RE = re.compile(r"(?<=[\u4e00-\u9fa5])\s+(?=[\u4e00-\u9fa5])")
    _PUNCT_COLLAPSE_RE = re.compile(r"([，。！？、,!?])\1+")
    _MULTI_NEWLINE_RE = re.compile(r"\n{3,}")

    @classmethod
    def clean(cls, raw_transcript: str) -> Dict[str, Any]:
        """Execute non-destructive cleaning and normalization."""
        if not raw_transcript:
            return {
                "original_length": 0,
                "cleaned_length": 0,
                "compression_ratio": 0.0,
                "cleaned_text": "",
            }

        orig_len = len(raw_transcript)
        text = raw_transcript

        # 1. Normalize spaces between Chinese characters
        text = cls._CHINESE_SPACE_RE.sub("", text)

        # 2. Collapse consecutive identical punctuation marks
        text = cls._PUNCT_COLLAPSE_RE.sub(r"\1", text)

        # 3. Collapse multiple blank lines
        text = cls._MULTI_NEWLINE_RE.sub("\n\n", text)

        # 4. Strip line-level whitespace
        lines = [line.strip() for line in text.split("\n")]
        cleaned_text = "\n".join(lines).strip()

        cleaned_len = len(cleaned_text)
        compression_ratio = round((1 - cleaned_len / max(1, orig_len)) * 100, 2) if orig_len > 0 else 0.0

        return {
            "original_length": orig_len,
            "cleaned_length": cleaned_len,
            "compression_ratio": max(0.0, compression_ratio),
            "cleaned_text": cleaned_text,
        }

