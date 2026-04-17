from __future__ import annotations

from typing import Any, Optional

import requests


def _build_requests_proxies(proxy: Optional[str]) -> Optional[dict[str, str]]:
    if not proxy:
        return None
    return {"http": proxy, "https": proxy}


def _get_json(
    url: str,
    *,
    proxy: Optional[str],
    timeout: float,
    session: requests.Session,
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {"timeout": timeout}
    proxies = _build_requests_proxies(proxy)
    if proxies:
        kwargs["proxies"] = proxies
    response = session.get(url, **kwargs)
    response.raise_for_status()
    return response.json()


def fetch_json_with_proxy_fallback(
    url: str,
    *,
    proxy: Optional[str] = None,
    timeout: float = 60,
    session: Optional[requests.Session] = None,
) -> dict[str, Any]:
    """
    GET JSON from ``url``: first without a proxy; on any failure, retry once
    with ``proxy`` if it is set. If ``proxy`` is omitted, the first error is raised.
    """
    sess = session or requests.Session()
    try:
        return _get_json(url, proxy=None, timeout=timeout, session=sess)
    except Exception:
        if not proxy:
            raise
        return _get_json(url, proxy=proxy, timeout=timeout, session=sess)
