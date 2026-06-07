from __future__ import annotations

from hotmeme.cn_models import TopicCategory, TopicItem

_ENTERTAINMENT = frozenset({"明星", "综艺", "娱乐", "八卦", "演唱会", "影视"})
_SOCIETY = frozenset({"社会", "新闻", "事故", "政策", "法院", "警方"})
_GAME = frozenset({"游戏", "电竞", "原神", "英雄联盟", "Steam", "NGA", "攻略"})
_TECH = frozenset({"科技", "AI", "程序员", "手机", "数码", "掘金", "开源"})
_SPORTS = frozenset({"体育", "足球", "篮球", "NBA", "虎扑", "奥运", "联赛"})
_FILM = frozenset({"电影", "豆瓣", "票房", "剧集", "动漫", "B站", "番剧"})


def classify_topic(title: str, *, platform: str = "") -> TopicCategory:
    """按标题关键词与平台做粗分类。"""
    text = f"{title} {platform}"
    if any(word in text for word in _GAME):
        return TopicCategory.GAME
    if any(word in text for word in _SPORTS):
        return TopicCategory.SPORTS
    if any(word in text for word in _FILM):
        return TopicCategory.FILM
    if any(word in text for word in _TECH):
        return TopicCategory.TECH
    if any(word in text for word in _SOCIETY):
        return TopicCategory.SOCIETY
    if any(word in text for word in _ENTERTAINMENT):
        return TopicCategory.ENTERTAINMENT
    return TopicCategory.OTHER


def annotate_topics(topics: list[TopicItem]) -> list[TopicItem]:
    """为热点项填入粗分类。"""
    annotated: list[TopicItem] = []
    for topic in topics:
        if topic.category is not None:
            annotated.append(topic)
            continue
        category = classify_topic(topic.title, platform=topic.platform)
        annotated.append(topic.model_copy(update={"category": category}))
    return annotated
