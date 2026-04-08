import re
import logging
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

SPEC_HOSTS = [
    "https://miot-spec.org",
    "https://spec.miot-spec.com",
]


class MiotSpec:
    def __init__(self, data: dict):
        self.raw = data
        self.type: str = data.get("type", "")
        self.description: str = data.get("description", "")
        self.services: dict[int, MiotService] = {}
        for s in data.get("services") or []:
            srv = MiotService(s)
            if srv.name:
                self.services[srv.iid] = srv

    @staticmethod
    async def from_model(
        session: aiohttp.ClientSession, model: str
    ) -> "MiotSpec | None":
        spec_type = await MiotSpec._get_model_type(session, model)
        if not spec_type:
            return None
        return await MiotSpec.from_type(session, spec_type)

    @staticmethod
    async def from_type(
        session: aiohttp.ClientSession, spec_type: str
    ) -> "MiotSpec | None":
        data = await _fetch_spec(
            session, f"/miot-spec-v2/instance?type={spec_type}"
        )
        if not data or not data.get("services"):
            return None
        return MiotSpec(data)

    @staticmethod
    async def _get_model_type(
        session: aiohttp.ClientSession, model: str
    ) -> str | None:
        data = await _fetch_spec(
            session, "/miot-spec-v2/instances?status=all", timeout=90
        )
        if not data:
            return None
        best: dict[str, Any] | None = None
        for v in data.get("instances") or []:
            if v.get("model") != model:
                continue
            if best is None:
                best = v
            elif (
                v.get("status") == "released"
                and best.get("status") != "released"
            ):
                best = v
            elif v.get("version", 0) > best.get("version", 0):
                if best.get("status") != "released":
                    best = v
        return best.get("type") if best else None

    def services_mapping(
        self, exclude_services: list[str] | None = None
    ) -> dict[str, dict]:
        """Generate {name: {siid, piid}} mapping for readable properties."""
        mapping: dict[str, dict] = {}
        svc_names: dict[str, int] = {}
        for srv in self.services.values():
            svc_names[srv.name] = svc_names.get(srv.name, 0) + 1

        for srv in self.services.values():
            if srv.name == "device_information":
                continue
            if exclude_services and srv.name in exclude_services:
                continue
            for prop in srv.properties.values():
                if not prop.readable:
                    continue
                if prop.name == srv.name:
                    key = prop.name
                elif svc_names.get(srv.name, 1) > 1:
                    key = f"{srv.name}_{srv.iid}.{prop.name}"
                else:
                    key = f"{srv.name}.{prop.name}"
                mapping[key] = {"siid": srv.iid, "piid": prop.iid}
        return mapping

    def get_service(self, name: str) -> "MiotService | None":
        for srv in self.services.values():
            if srv.name == name:
                return srv
        return None

    def __repr__(self):
        return f"MiotSpec({self.type}, services={len(self.services)})"


class MiotService:
    def __init__(self, data: dict):
        self.raw = data
        self.iid: int = int(data.get("iid") or 0)
        self.type: str = data.get("type", "")
        self.name: str = _name_from_type(self.type)
        self.description: str = data.get("description", "")
        self.properties: dict[int, MiotProperty] = {}
        self.actions: dict[int, MiotAction] = {}
        for p in data.get("properties") or []:
            prop = MiotProperty(p, self.iid)
            if prop.name:
                self.properties[prop.iid] = prop
        for a in data.get("actions") or []:
            act = MiotAction(a, self.iid)
            if act.name:
                self.actions[act.iid] = act

    def get_property(self, name: str) -> "MiotProperty | None":
        for p in self.properties.values():
            if p.name == name:
                return p
        return None

    def get_action(self, name: str) -> "MiotAction | None":
        for a in self.actions.values():
            if a.name == name:
                return a
        return None

    def __repr__(self):
        return f"MiotService({self.name}, iid={self.iid})"


class MiotProperty:
    def __init__(self, data: dict, siid: int):
        self.raw = data
        self.siid: int = siid
        self.iid: int = int(data.get("iid") or 0)
        self.type: str = data.get("type", "")
        self.name: str = _name_from_type(self.type)
        self.description: str = data.get("description", "")
        self.format: str = data.get("format", "")
        self.access: list[str] = data.get("access") or []
        self.unit: str = data.get("unit", "")
        self.value_list: list[dict] = data.get("value-list") or []
        self.value_range: list = data.get("value-range") or []

    @property
    def readable(self) -> bool:
        return "read" in self.access

    @property
    def writeable(self) -> bool:
        return "write" in self.access

    def __repr__(self):
        return f"MiotProperty({self.name}, siid={self.siid}, piid={self.iid})"


class MiotAction:
    def __init__(self, data: dict, siid: int):
        self.raw = data
        self.siid: int = siid
        self.iid: int = int(data.get("iid") or 0)
        self.type: str = data.get("type", "")
        self.name: str = _name_from_type(self.type)
        self.description: str = data.get("description", "")
        self.ins: list[int] = data.get("in") or []
        self.out: list[int] = data.get("out") or []

    def __repr__(self):
        return f"MiotAction({self.name}, siid={self.siid}, aiid={self.iid})"


# ── Helpers ──────────────────────────────────────────────────


def _name_from_type(typ: str) -> str:
    parts = f"{typ}:::".split(":")
    name = parts[3] if len(parts) > 3 else ""
    return re.sub(r"\W+", "_", name).lower().strip("_")


async def _fetch_spec(
    session: aiohttp.ClientSession, path: str, timeout: int = 30
) -> dict | None:
    for host in SPEC_HOSTS:
        url = f"{host}{path}"
        try:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=timeout)
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                _LOGGER.warning(
                    "Spec request %s returned status %s", url, resp.status
                )
        except Exception as exc:
            _LOGGER.debug("Spec request %s failed: %s", url, exc)
            continue
    return None