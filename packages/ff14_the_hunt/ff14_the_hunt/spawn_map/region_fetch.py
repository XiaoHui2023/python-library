from __future__ import annotations

import urllib.error
import urllib.parse
import urllib.request


def site_root_from_api_base(base_url: str) -> str:
    """由 Bear Tracker ``/api`` 根地址推导站点静态资源根。"""
    url = base_url.rstrip("/")
    if url.endswith("/api"):
        return url[:-4]
    return url


def region_map_image_url(site_root: str, region: str) -> str:
    """区域狩猎地图 PNG 地址（与站点 ``HuntRegions`` 目录一致）。"""
    root = site_root.rstrip("/")
    encoded_region = urllib.parse.quote(region, safe="")
    return f"{root}/static/images/HuntRegions/{encoded_region}.png"


class RegionMapFetcher:
    """按区域名拉取并缓存狩猎地图原图字节。"""

    def __init__(
        self,
        *,
        site_root: str,
        timeout_seconds: float = 120.0,
    ) -> None:
        self._site_root = site_root.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._cache: dict[str, bytes] = {}

    @property
    def site_root(self) -> str:
        return self._site_root

    def fetch_bytes(self, region: str) -> bytes:
        """拉取区域地图 PNG；同区域重复调用走内存缓存。

        Args:
            region: Bear Tracker ``Region`` 名，例如 ``Shaaloani``。

        Returns:
            PNG 文件原始字节。

        Raises:
            RuntimeError: HTTP 或网络失败。
        """
        cached = self._cache.get(region)
        if cached is not None:
            return cached
        url = region_map_image_url(self._site_root, region)
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "python-library-ff14-the-hunt",
                "Referer": f"{self._site_root}/timer",
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(
                request,
                timeout=self._timeout_seconds,
            ) as response:
                data = response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"region map {region} failed: HTTP {exc.code}: {detail}"
            ) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"region map {region} failed: {exc}") from exc
        self._cache[region] = data
        return data
