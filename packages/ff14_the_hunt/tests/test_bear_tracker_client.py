import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from ff14_the_hunt.bear_tracker.client import (
    BearTrackerBlockedError,
    BearTrackerClient,
)


def test_post_raises_blocked_error_for_forbidden() -> None:
    client = BearTrackerClient(min_request_interval_seconds=0.0)
    http_error = urllib.error.HTTPError(
        url="https://tracker.beartoolkit.com/api/syncSession",
        code=403,
        msg="Forbidden",
        hdrs={"Retry-After": "60"},
        fp=None,
    )

    with patch(
        "ff14_the_hunt.bear_tracker.client.urlopen_read",
        side_effect=http_error,
    ):
        with pytest.raises(BearTrackerBlockedError) as raised:
            client.sync_session()

    assert raised.value.status_code == 403
    assert raised.value.retry_after_seconds == 60.0


def test_client_paces_consecutive_requests() -> None:
    client = BearTrackerClient(min_request_interval_seconds=1.0)
    sleep = MagicMock()

    with patch("ff14_the_hunt.bear_tracker.client.time.sleep", sleep):
        with patch(
            "ff14_the_hunt.bear_tracker.client.time.monotonic",
            side_effect=[10.0, 10.0, 10.2, 11.0],
        ):
            client._pace_request()  # type: ignore[attr-defined]
            client._pace_request()  # type: ignore[attr-defined]

    sleep.assert_called_once()
    assert sleep.call_args.args[0] == pytest.approx(0.8)
