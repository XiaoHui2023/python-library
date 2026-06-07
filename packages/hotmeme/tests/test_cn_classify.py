from hotmeme.cn_models import TopicCategory
from hotmeme.sources.cn.classify import classify_topic


def test_classify_game_topic() -> None:
    assert classify_topic("原神新版本上线", platform="bilibili") == TopicCategory.GAME


def test_classify_sports_topic() -> None:
    assert classify_topic("NBA总决赛", platform="hupu") == TopicCategory.SPORTS
