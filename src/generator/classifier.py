"""Content Type Classifier for Adaptive Note Generation.

Categorizes video content into:
1. study: Educational courses, tutorials, lectures, exam reviews, coding practices.
2. news: Tech announcements, version releases, event recaps, industry news, reviews.
3. general: Speeches, interviews, essays, experience sharing, general knowledge talks.
"""

import re
from typing import Any, Dict, List, Optional, Tuple


def _compile_keyword_regex(keywords: List[str]) -> "re.Pattern":
    """将关键词列表预编译为零宽前瞻合并正则。

    - 长词优先排序，保证复合词（如"深度评测"）优先命中；
    - 零宽前瞻 (?=(...)) 使引擎在每个位置重试，重叠短词（如"测评"）也能独立计数，
      与逐关键词 `kw in text` 的子串判定语义完全等价，但只需单次扫描。
    """
    ordered = sorted(set(keywords), key=len, reverse=True)
    alternation = "|".join(re.escape(k) for k in ordered)
    return re.compile(f"(?=({alternation}))", re.IGNORECASE)


def _count_keyword_hits(pattern: "re.Pattern", text: str) -> int:
    """统计文本中命中的唯一关键词数量（每个关键词最多计 1 分）。"""
    return len({m.group(1) for m in pattern.finditer(text)})


class NoteClassifier:
    STUDY = "study"
    NEWS = "news"
    GENERAL = "general"

    CATEGORIES = {STUDY, NEWS, GENERAL}

    # Keyword indicators for educational / tutorial content
    STUDY_KEYWORDS = [
        "教程", "公开课", "讲座", "大学", "考研", "期末", "复习",
        "考点", "知识点", "高频", "题解", "算法", "原理", "从零开始",
        "手把手", "深入理解", "实战教学", "第.+讲", "第.+课", "全套课程",
        "计算机", "操作系统", "网络", "微机", "编程语言", "基础入门",
        "学习指南", "精讲", "通俗易懂", "零基础", "底层剖析", "自学",
    ]

    # Keyword indicators for news / release / changelog / tech intelligence
    NEWS_KEYWORDS = [
        "重磅", "发布", "更新", "最新功能", "dev", "preview", "预览版",
        "beta", "rc", "新特性", "盘点", "速递", "汇总", "动态", "前沿",
        "测评", "实测", "深度评测", "体验", "大会", "发布会", "年度发布",
        "新闻", "趋势", "快讯", "行情", "重大突破", "正式推出", "震撼来袭",
        "版本更新", "更新日志", "changelog", "大事件",
    ]

    # Keyword indicators for talks / experience sharing / essays
    GENERAL_KEYWORDS = [
        "演讲", "分享", "访谈", "对话", "感悟", "思考", "心得",
        "职场", "人生", "创业", "经验", "观点", "随笔", "杂谈",
        "纪录片", "故事", "自述", "复盘", "成长", "复盘分析",
    ]

    # 模块加载时一次性预编译合并正则（长词优先，零宽前瞻支持重叠命中），
    # 运行时以单次扫描替代逐关键词的 O(N*M) 线性遍历。
    _STUDY_KW_RE = _compile_keyword_regex(STUDY_KEYWORDS)
    _NEWS_KW_RE = _compile_keyword_regex(NEWS_KEYWORDS)
    _GENERAL_KW_RE = _compile_keyword_regex(GENERAL_KEYWORDS)

    # 分类加成规则同样预编译，避免每次调用重复解析
    _EPISODE_RE = re.compile(r"第\s*\d+\s*(讲|课|集|P|章)", re.IGNORECASE)
    _VERSION_RE = re.compile(r"\b(v\d+\.\d+|\d+\.\d+\s*(dev|beta|rc))\b", re.IGNORECASE)
    _STUDY_BOOST_RE = re.compile(r"(公开课|课程|教程|原理|考研|期末)")
    _NEWS_BOOST_RE = re.compile(r"(重磅|发布|更新|最新功能|新特性|大事件)")

    @classmethod
    def classify(
        cls,
        title: str,
        desc: str = "",
        tags: Optional[List[str]] = None,
        override: Optional[str] = None,
    ) -> Tuple[str, str]:
        """
        Classify content into 'study', 'news', or 'general'.
        Returns (category_code, explanation_reason).
        """
        if override and override.strip().lower() in cls.CATEGORIES:
            cat = override.strip().lower()
            return cat, f"用户显式指定模式: {cat}"

        combined_text = f"{title} {desc} {' '.join(tags or [])}".lower()

        # Score matching（预编译合并正则单次扫描，语义与逐关键词子串判定等价）
        study_score = _count_keyword_hits(cls._STUDY_KW_RE, combined_text)
        news_score = _count_keyword_hits(cls._NEWS_KW_RE, combined_text)
        general_score = _count_keyword_hits(cls._GENERAL_KW_RE, combined_text)

        # Regular expression boosts（预编译规则复用）
        if cls._EPISODE_RE.search(combined_text):
            study_score += 2
        if cls._VERSION_RE.search(combined_text):
            news_score += 2
        if cls._STUDY_BOOST_RE.search(combined_text):
            study_score += 2
        if cls._NEWS_BOOST_RE.search(combined_text):
            news_score += 2

        if news_score > study_score and news_score > general_score:
            return cls.NEWS, f"命中了前沿资讯/动态特性关键词 (得分: {news_score})"
        elif study_score >= news_score and study_score > general_score and study_score > 0:
            return cls.STUDY, f"命中了教学/课程/知识体系关键词 (得分: {study_score})"
        elif general_score > 0:
            return cls.GENERAL, f"命中了演讲/思考/经验分享关键词 (得分: {general_score})"

        # Default fallback
        if study_score > 0:
            return cls.STUDY, f"匹配教学特征 (得分: {study_score})"
        return cls.GENERAL, "未触发特定垂类规则，采用通用知识结构"
