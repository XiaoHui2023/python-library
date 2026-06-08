from hotmeme.sources.parsers.douyin import parse_douyin_video_search

from hotmeme.sources.parsers.xiaohongshu import parse_xhs_search_notes





def test_parse_douyin_video_search() -> None:

    data = {

        "data": [

            {

                "aweme_info": {

                    "aweme_id": "999",

                    "desc": "抖音视频",

                    "author": {"nickname": "达人"},

                    "video": {

                        "play_addr": {"url_list": ["https://example.com/v.mp4"]},

                        "cover": {"url_list": ["https://example.com/c.jpg"]},

                    },

                    "statistics": {"digg_count": 50},

                },

            },

        ],

    }

    items = parse_douyin_video_search(data)

    assert len(items) == 1

    assert items[0].video_url == "https://example.com/v.mp4"

    assert items[0].community == "douyin"





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

