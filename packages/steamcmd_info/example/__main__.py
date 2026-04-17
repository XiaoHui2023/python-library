"""Run: from package root, ``python example`` or ``python -m example``."""

from __future__ import annotations

import argparse

from steamcmd_info import SteamCmdInfo

APPID_CS2 = 730


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch SteamCMD API info for Counter-Strike 2 (appid 730)."
    )
    parser.add_argument(
        "--proxy",
        default=None,
        metavar="URL",
        help="Optional HTTP(S) proxy if direct request fails (e.g. http://127.0.0.1:7890)",
    )
    args = parser.parse_args()

    info = SteamCmdInfo(APPID_CS2, proxy=args.proxy)

    print(f"appid:           {info.appid}")
    print(f"request_url:     {info.request_url}")
    print(f"remote version:  {info.version}")
    print(f"needs_update({info.version - 1}): {info.needs_update(info.version - 1)}")
    print(f"needs_update({info.version}):     {info.needs_update(info.version)}")


if __name__ == "__main__":
    main()
