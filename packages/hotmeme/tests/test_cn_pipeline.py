from hotmeme import HotMeme
from hotmeme.cn_models import CnSourcesConfig, HotpushConfig, TikHubConfig
from hotmeme.models import HotMemeModels


def test_fetch_cn_hot_without_enabled_sources() -> None:
    client = HotMeme(
        config=HotMemeModels(
            cn=CnSourcesConfig(
                hotpush=HotpushConfig(enabled=False),
                tikhub=TikHubConfig(enabled=False),
            ),
        ),
    )
    feed = client.fetch_cn_hot(limit=5)
    assert feed.items == []
    assert feed.providers_ok == []
    assert feed.providers_failed == []
