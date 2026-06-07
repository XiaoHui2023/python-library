from ff14_news.channels.cn_weibo.profile import weibo_timeline_container_id


def test_weibo_timeline_container_id_default_uid() -> None:
    assert weibo_timeline_container_id("1784473157") == "1076031784473157"
