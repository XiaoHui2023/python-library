from pathlib import Path

from hotmeme.config_build import build_config


def test_build_config_merges_api_key_from_file(tmp_path: Path) -> None:
    config = tmp_path / "cfg.yaml"
    config.write_text(
        "tikhub:\n  enabled: true\n  api_key: null\n",
        encoding="utf-8",
    )
    models = build_config(config_path=config, api_key="from-param")
    assert models.tikhub is not None
    assert models.tikhub.api_key == "from-param"


def test_build_config_overrides_platforms_from_file(tmp_path: Path) -> None:
    config = tmp_path / "cfg.yaml"
    config.write_text(
        "pipeline:\n  platforms:\n    - douyin\n    - xiaohongshu\n",
        encoding="utf-8",
    )
    models = build_config(config_path=config, platforms=["xiaohongshu"])
    assert models.pipeline is not None
    assert models.pipeline.platforms == ["xiaohongshu"]
