"""Content Type Classifier for Adaptive Note Generation.

Categorizes video content into:
1. study: Educational courses, tutorials, lectures, exam reviews, coding practices.
2. news: Tech announcements, version releases, event recaps, industry news, reviews.
3. general: Speeches, interviews, essays, experience sharing, general knowledge talks.
"""

import re
from typing import Any, Dict, List, Optional, Tuple


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

        # Score matching
        study_score = sum(1 for kw in cls.STUDY_KEYWORDS if kw.lower() in combined_text)
        news_score = sum(1 for kw in cls.NEWS_KEYWORDS if kw.lower() in combined_text)
        general_score = sum(1 for kw in cls.GENERAL_KEYWORDS if kw.lower() in combined_text)

        # Regular expression boosts
        if re.search(r"第\s*\d+\s*(讲|课|集|P|章)", combined_text, re.IGNORECASE):
            study_score += 2
        if re.search(r"\b(v\d+\.\d+|\d+\.\d+\s*(dev|beta|rc))\b", combined_text, re.IGNORECASE):
            news_score += 2
        if re.search(r"(公开课|课程|教程|原理|考研|期末)", combined_text):
            study_score += 2
        if re.search(r"(重磅|发布|更新|最新功能|新特性|大事件)", combined_text):
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
