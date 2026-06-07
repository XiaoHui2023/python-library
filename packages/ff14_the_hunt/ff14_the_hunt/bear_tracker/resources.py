from __future__ import annotations

from typing import Any


class BearResources:
    """``syncSession`` 返回的 resources 只读视图。"""

    def __init__(self, resources: dict[str, Any]) -> None:
        self._resources = resources

    @property
    def database_hunt(self) -> dict[str, Any]:
        return self._resources.get("DatabaseHunt", {})

    @property
    def spawn_point(self) -> dict[str, Any]:
        return self._resources.get("SpawnPoint", {})

    @property
    def data_centers(self) -> dict[str, Any]:
        return self._resources.get("DataCenters", {})

    def worlds_for_data_centers(self, data_center_names: list[str]) -> list[str]:
        worlds: list[str] = []
        for name in data_center_names:
            info = self.data_centers.get(name)
            if not info:
                continue
            for world in info.get("Names", []):
                if world not in worlds:
                    worlds.append(world)
        return worlds

    def hunt_meta(self, hunt_key: str) -> dict[str, Any]:
        meta = self.database_hunt.get(hunt_key)
        if meta:
            return meta
        trimmed = hunt_key[:-2] if len(hunt_key) > 2 else hunt_key
        return self.database_hunt.get(trimmed, {})

    def spawn_map_key(self, hunt_key: str, meta: dict[str, Any]) -> str | None:
        patch = meta.get("Patch", "")
        region = meta.get("Region", "")
        if patch == "DT" and hunt_key.startswith("Arch Aethereater "):
            return f"Arch Aethereater {region}"
        if patch == "EW" and hunt_key.startswith("Ker "):
            return hunt_key
        if patch == "ShB" and hunt_key.startswith("Forgiven Rebellion "):
            return hunt_key
        if hunt_key in self.spawn_point:
            return hunt_key
        return None
