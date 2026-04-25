from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterator, Mapping

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .peer import canonical_peer


def _strip_nonempty_str(v: Any, *, field: str) -> str:
    if not isinstance(v, str):
        raise TypeError(f"{field} must be str")
    s = v.strip()
    if not s:
        raise ValueError(f"{field} must be non-empty")
    return s


class JackEntry(BaseModel):
    """配置中的一个接入点，供连线引用与投递定位。"""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="接入点名称，供连线引用；列表内唯一")
    address: str = Field(
        description="接入点地址，写成 host:port；列表内唯一",
    )

    @field_validator("name", mode="before")
    @classmethod
    def _strip_name(cls, v: Any) -> str:
        return _strip_nonempty_str(v, field="name")

    @field_validator("address", mode="before")
    @classmethod
    def _strip_address(cls, v: Any) -> str:
        if not isinstance(v, str):
            raise TypeError("address must be str")
        return canonical_peer(v)


class Wire(BaseModel):
    """配置中的一条有向连线。

    同一来源可以配置多条出线；每条线独立判断条件并按顺序套用补丁。
    """

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    from_jack: str = Field(alias="from", description="源接入点名称")
    to_jack: str = Field(alias="to", description="目标接入点名称")
    rule: str | None = Field(
        default=None,
        description="规则 id，对应 rules；省略则恒为真",
    )
    patchs: list[str] = Field(
        default_factory=list,
        description="要应用的补丁名列表，按顺序套用；空表示不改写数据",
    )

    @field_validator("from_jack", "to_jack", mode="before")
    @classmethod
    def _strip_jack_refs(cls, v: Any) -> str:
        return _strip_nonempty_str(v, field="jack ref")

    @field_validator("patchs", mode="before")
    @classmethod
    def _coerce_patchs(cls, v: Any) -> list[str]:
        if v is None:
            return []
        if not isinstance(v, list):
            raise TypeError("patchs must be a list of patch names")
        out: list[str] = []
        for i, item in enumerate(v):
            if not isinstance(item, str):
                raise TypeError(f"patchs[{i}] must be str")
            out.append(_strip_nonempty_str(item, field="patch name"))
        return out


class PatchEntry(BaseModel):
    """配置中的一条具名数据补丁。"""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="补丁名称，供 wires.patchs 引用")
    patch: dict[str, Any] = Field(
        description="字段改写表；字段必须已存在，且目标值类型必须与原值一致",
    )

    @field_validator("name", mode="before")
    @classmethod
    def _strip_name(cls, v: Any) -> str:
        return _strip_nonempty_str(v, field="patch name")

    @field_validator("patch", mode="before")
    @classmethod
    def _coerce_patch_map(cls, v: Any) -> dict[str, Any]:
        if not isinstance(v, dict):
            raise TypeError("patch must be a dict")
        out: dict[str, Any] = {}
        for k, val in v.items():
            if not isinstance(k, str):
                raise TypeError("patch keys must be str")
            ks = k.strip()
            if not ks:
                raise ValueError("patch keys must be non-empty")
            out[ks] = val
        return out


class PatchBayConfig(BaseModel):
    """PatchBay 的完整配置模型。"""

    model_config = ConfigDict(extra="forbid")

    jacks: list[JackEntry] = Field(description="接入点清单")
    wires: list[Wire] = Field(description="连线；rule 可省略表示恒为真")
    patchs: list[PatchEntry] = Field(
        default_factory=list,
        description="具名补丁表，供 wires.patchs 引用",
    )
    rules: dict[str, str] = Field(
        default_factory=dict,
        description="规则 id 到条件表达式的映射",
    )
    listen: int = Field(
        default=8765,
        ge=0,
        le=65535,
        description="保留端口配置，常规配置可省略",
    )

    @field_validator("listen", mode="before")
    @classmethod
    def _coerce_listen_port(cls, v: Any) -> int:
        if v is None:
            return 8765
        if isinstance(v, bool):
            raise TypeError("listen must be a port number")
        if isinstance(v, int):
            return v
        if isinstance(v, str):
            s = v.strip()
            if not s:
                return 8765
            if ":" in s:
                return int(s.rpartition(":")[-1])
            return int(s)
        raise TypeError(f"listen must be int or str port, got {type(v).__name__}")

    @model_validator(mode="after")
    def _wires_and_rules_consistent(self) -> PatchBayConfig:
        names = [j.name for j in self.jacks]
        if len(set(names)) != len(names):
            raise ValueError("jacks 中 name 必须唯一")
        addrs = [j.address for j in self.jacks]
        if len(set(addrs)) != len(addrs):
            raise ValueError("jacks 中 address 必须唯一")
        patch_by_name: dict[str, PatchEntry] = {}
        for p in self.patchs:
            if p.name in patch_by_name:
                raise ValueError(f"patchs 中 name 必须唯一: {p.name!r}")
            patch_by_name[p.name] = p
        name_set = set(names)
        for w in self.wires:
            if w.from_jack not in name_set:
                raise ValueError(f"连线引用未知 Jack（from）: {w.from_jack!r}")
            if w.to_jack not in name_set:
                raise ValueError(f"连线引用未知 Jack（to）: {w.to_jack!r}")
            if w.rule is None:
                pass
            elif w.rule not in self.rules:
                raise ValueError(f"连线引用未知规则 id: {w.rule!r}")
            else:
                expr = self.rules[w.rule].strip()
                if not expr:
                    raise ValueError(f"规则 {w.rule!r} 的表达式为空")
            for pn in w.patchs:
                if pn not in patch_by_name:
                    raise ValueError(f"连线引用未知补丁名: {pn!r}")
        return self


class ResolvedWire:
    """运行期可直接使用的连线。"""

    __slots__ = ("from_jack", "to_jack", "expression", "patch_steps")

    def __init__(
        self,
        *,
        from_jack: str,
        to_jack: str,
        expression: str,
        patch_steps: tuple[tuple[str, dict[str, Any]], ...],
    ) -> None:
        self.from_jack = from_jack
        self.to_jack = to_jack
        self.expression = expression
        self.patch_steps = patch_steps


class RoutingTable:
    """按来源索引候选连线，供转发时快速查找。"""

    __slots__ = ("_by_from_jack",)

    def __init__(self, wires: list[ResolvedWire]) -> None:
        by_from: dict[str, list[ResolvedWire]] = defaultdict(list)
        for w in wires:
            by_from[w.from_jack].append(w)
        self._by_from_jack = dict(by_from)

    @classmethod
    def from_config(cls, config: PatchBayConfig) -> RoutingTable:
        patch_by_name = {p.name: p for p in config.patchs}
        resolved: list[ResolvedWire] = []
        for w in config.wires:
            if w.rule is None:
                expr = "True"
            else:
                expr = config.rules[w.rule].strip()
            steps: list[tuple[str, dict[str, Any]]] = []
            for pn in w.patchs:
                pe = patch_by_name[pn]
                steps.append((pe.name, dict(pe.patch)))
            resolved.append(
                ResolvedWire(
                    from_jack=w.from_jack,
                    to_jack=w.to_jack,
                    expression=expr,
                    patch_steps=tuple(steps),
                )
            )
        return cls(resolved)

    def iter_from_jack(self, from_jack: str) -> Iterator[ResolvedWire]:
        yield from self._by_from_jack.get(from_jack, ())

    def to_mapping(self) -> list[dict[str, Any]]:
        """生成当前拓扑快照。

        Returns:
            list[dict[str, Any]]: 每条连线一行的可序列化结构。
        """
        rows: list[dict[str, Any]] = []
        for fj, rules in sorted(self._by_from_jack.items()):
            for w in rules:
                rows.append(
                    {
                        "from_jack": fj,
                        "to_jack": w.to_jack,
                        "expression": w.expression,
                        "patch_steps": [
                            {"name": n, "patch": p} for n, p in w.patch_steps
                        ],
                    }
                )
        return rows


def patch_bay_config_from_dict(data: Mapping[str, Any]) -> PatchBayConfig:
    """从内存映射构造配置模型。

    Args:
        data: 用户或调用方提供的配置映射。

    Returns:
        PatchBayConfig: 校验后的配置模型。

    Raises:
        TypeError: 配置根结构不是字典时抛出。
    """
    if not isinstance(data, dict):
        raise TypeError("config must be a dict")
    return PatchBayConfig.model_validate(data)
