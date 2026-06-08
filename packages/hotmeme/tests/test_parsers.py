from hotmeme.sources.parsers.xiaohongshu import (
    _xhs_card_has_media,
    parse_xhs_note_card,
    parse_xhs_search_notes,
    parse_xhs_search_notes_traced,
)





def test_parse_xhs_search_notes() -> None:

    data = {

        "items": [

            {

                "note_card": {

                    "note_id": "note1",

                    "display_title": "小红书笔记",

                    "type": "normal",

                    "cover": {"url_default": "https://example.com/n.jpg"},

                    "user": {"nickname": "博主"},

                    "interact_info": {"liked_count": "20"},

                },

            },

        ],

    }

    items = parse_xhs_search_notes(data)

    assert len(items) == 1

    assert items[0].title == "小红书笔记"

    assert items[0].image_url == "https://example.com/n.jpg"





def test_parse_xhs_app_v2_interact_info_on_item_wrapper() -> None:
    data = {
        "data": {
            "items": [
                {
                    "note": {
                        "id": "note_wrapper",
                        "title": "外层互动",
                        "type": "normal",
                        "images_list": [{"url": "https://example.com/wrap.jpg"}],
                        "user": {"nickname": "博主"},
                    },
                    "interact_info": {
                        "liked_count": "7429",
                        "comment_count": "10",
                    },
                },
            ],
        },
    }
    items = parse_xhs_search_notes(data)
    assert len(items) == 1
    assert items[0].score == 7439.0


def test_parse_xhs_app_v2_multi_image_and_body() -> None:
    data = {
        "data": {
            "items": [
                {
                    "note": {
                        "id": "multi1",
                        "display_title": "封面标题",
                        "desc": "正文第二段",
                        "type": "normal",
                        "images_list": [
                            {"url": "https://example.com/a.jpg"},
                            {"url_size_large": "https://example.com/b.jpg"},
                        ],
                    },
                },
            ],
        },
    }
    items = parse_xhs_search_notes(data)
    assert len(items) == 1
    assert items[0].title == "封面标题"
    assert items[0].body == "正文第二段"
    assert items[0].image_urls == [
        "https://example.com/a.jpg",
        "https://example.com/b.jpg",
    ]


def test_parse_xhs_app_v2_search_notes() -> None:

    data = {

        "data": {

            "items": [

                {

                    "note": {

                        "id": "note2",

                        "title": "App 笔记",

                        "type": "normal",

                        "images_list": [{"url": "https://example.com/app.jpg"}],

                        "user": {"nickname": "博主"},

                        "liked_count": 12,

                    },

                },

            ],

        },

    }

    items = parse_xhs_search_notes(data)

    assert len(items) == 1

    assert items[0].title == "App 笔记"

    assert items[0].image_url == "https://example.com/app.jpg"
    assert items[0].score == 12.0


def test_parse_xhs_app_v2_video_note() -> None:
    data = {
        "data": {
            "items": [
                {
                    "note": {
                        "id": "video1",
                        "title": "搞笑视频",
                        "type": "video",
                        "images_list": [
                            {
                                "url": "https://example.com/thumb.jpg",
                                "url_size_large": "https://example.com/large.jpg",
                            },
                        ],
                        "video_info_v2": {
                            "image": {"thumbnail": "https://example.com/frame.webp"},
                            "media": {
                                "stream": {
                                    "h265": [
                                        {
                                            "master_url": "https://example.com/video.mp4",
                                        },
                                    ],
                                },
                            },
                        },
                        "liked_count": "1.2万",
                        "comments_count": "10",
                    },
                },
            ],
        },
    }
    items = parse_xhs_search_notes(data)
    assert len(items) == 1
    assert items[0].video_url is None
    assert items[0].image_url == "https://example.com/large.jpg"
    assert items[0].media_type.value == "image"
    assert items[0].score == 12_010.0


def test_parse_xhs_image_list_info_list() -> None:
    data = {
        "data": {
            "items": [
                {
                    "note_card": {
                        "note_id": "web1",
                        "display_title": "Web 图集",
                        "type": "normal",
                        "image_list": [
                            {
                                "info_list": [
                                    {
                                        "image_scene": "WB_DFT",
                                        "url": "https://example.com/info_list.jpg",
                                    },
                                ],
                            },
                        ],
                    },
                },
            ],
        },
    }
    items = parse_xhs_search_notes(data)
    assert len(items) == 1
    assert items[0].image_url == "https://example.com/info_list.jpg"


def test_parse_xhs_video_stream_backup_urls() -> None:
    note = {
        "id": "video2",
        "title": "仅 backup",
        "type": "video",
        "video_info_v2": {
            "image": {"thumbnail": "https://example.com/thumb.webp"},
            "media": {
                "stream": {
                    "h265": [
                        {
                            "backup_urls": [
                                "https://example.com/backup.mp4",
                            ],
                        },
                    ],
                },
            },
        },
    }
    item = parse_xhs_note_card(note)
    assert item is not None
    assert item.video_url is None
    assert item.image_url == "https://example.com/thumb.webp"


def test_parse_xhs_video_cover_only_falls_back_to_image() -> None:
    note = {
        "id": "video3",
        "title": "无流仅有封面",
        "type": "video",
        "images_list": [{"url": "https://example.com/cover-only.jpg"}],
    }
    item = parse_xhs_note_card(note)
    assert item is not None
    assert item.media_type.value == "image"
    assert item.image_url == "https://example.com/cover-only.jpg"
    assert item.video_url is None


def test_parse_xhs_never_drops_when_cover_present() -> None:
    fixtures = [
        {
            "id": "n1",
            "cover": {"url_default": "https://example.com/a.jpg"},
        },
        {
            "id": "n2",
            "images_list": [{"url": "https://example.com/b.jpg"}],
        },
        {
            "id": "n3",
            "type": "video",
            "images_list": [{"url": "https://example.com/video-cover.jpg"}],
            "video_info_v2": {
                "media": {
                    "stream": {
                        "h264": [{"master_url": "https://example.com/v.mp4"}],
                    },
                },
            },
        },
    ]
    for note in fixtures:
        assert _xhs_card_has_media(note), note["id"]
        parsed = parse_xhs_note_card(note)
        assert parsed is not None, note["id"]
        assert parsed.image_url
        assert parsed.video_url is None
        assert parsed.media_type.value == "image"


def test_parse_xhs_cover_info_and_parse_stats() -> None:
    data = {
        "data": {
            "items": [
                {
                    "note": {
                        "id": "note3",
                        "title": "封面在 cover_info",
                        "cover_info": {"url": "https://example.com/cover_info.jpg"},
                    },
                },
                {
                    "note": {
                        "id": "note4",
                        "title": "无图笔记",
                    },
                },
            ],
        },
    }
    items, stats = parse_xhs_search_notes_traced(data)
    assert len(items) == 1
    assert items[0].image_url == "https://example.com/cover_info.jpg"
    assert stats.api_list_items == 2
    assert stats.note_candidates == 2
    assert stats.parsed_with_media == 1
    assert stats.no_media == 1

