from pathlib import Path

from hotmeme import HotMeme

CONFIG = Path(__file__).with_name("config.example.yaml")


def main() -> None:
    client = HotMeme(config_path=CONFIG)
    packet = client.crawl_once()
    if not packet.new_items and not packet.new_topics:
        raise SystemExit("未从任何已启用源获取到内容")
    if packet.new_items:
        first = packet.new_items[0]
        print(first.title)
        print(first.image_url)
    if packet.new_topics:
        print(packet.new_topics[0].title)
    print(
        "new:",
        len(packet.new_items),
        "images,",
        len(packet.new_topics),
        "topics",
    )
    print("providers_ok:", ",".join(packet.providers_ok))


if __name__ == "__main__":
    main()
