import urllib.error
import urllib.request

_USER_AGENT = "Mozilla/5.0 (compatible; python-library-ff14-news/0.1)"


def fetch_html(url: str, *, timeout_seconds: float) -> str:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": _USER_AGENT, "Accept": "text/html"},
    )
    try:
        raw = urllib.request.urlopen(req, timeout=timeout_seconds).read()
    except urllib.error.HTTPError as exc:
        raise ValueError(f"HTTP {exc.code} for {url}") from exc
    return raw.decode("utf-8", "replace")
