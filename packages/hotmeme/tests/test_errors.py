from hotmeme.common.errors import TikHubApiError, format_platform_fetch_error


def test_tikhub_api_error_detail_lines_include_response_json() -> None:
    exc = TikHubApiError(
        "TikHub 请求失败: 请求失败，请重试",
        method="GET",
        path="/api/v1/xiaohongshu/web_v2/fetch_hot_list",
        params={"count": 5},
        body={"code": 500, "message_zh": "请求失败，请重试", "request_id": "abc"},
    )
    text = "\n".join(exc.detail_lines())
    assert "接口: GET /api/v1/xiaohongshu/web_v2/fetch_hot_list" in text
    assert '"request_id": "abc"' in text
    assert format_platform_fetch_error("xiaohongshu", exc).startswith("[xiaohongshu]")
