import logging
from dataclasses import dataclass
from pathlib import Path

from watch_config import WatchConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%H:%M:%S",
)

CONFIG_FILEPATH = Path(__file__).parent / "config.yaml"


@dataclass
class AppConfig:
    host: str
    port: int
    debug: bool = False


watcher = WatchConfig(CONFIG_FILEPATH, AppConfig)


@watcher
def on_config(cfg: AppConfig):
    logging.getLogger(__name__).info(
        "Config loaded: host=%s, port=%s, debug=%s",
        cfg.host, cfg.port, cfg.debug,
    )


watcher.run()