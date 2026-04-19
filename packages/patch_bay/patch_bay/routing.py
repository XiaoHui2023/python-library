from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterator, Mapping

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class JackEntry(BaseModel):
    """配置里声明的一个 Jack：``name`` 供连线复用；``address`` 须与该机 Jack 握手时上报的一致。"""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="全局唯一名称，供 wires 引用")
    address: str = Field(description="该机 hello 中的地址，形如 host:port；在 jacks 中唯一")


class Wire(BaseModel):
    """有向连线：源 name → 目标 name，命中规则表达式时才转发。"""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    from_jack: str = Field(alias="from", description="源 Jack 的 name")
    to_jack: str = Field(alias="to", description="目标 Jack 的 name")
    rule: str | None = Field(
        default=None,
        description="规则 id，对应 PatchBayConfig.rules；省略则恒为真、直接通行",
    )


class PatchBayConfig(BaseModel):
    """PatchBay 根配置：Jack 列表、连线、规则表；可选监听地址。"""

    model_config = ConfigDict(extra="forbid")

    jacks: list[JackEntry] = Field(description="Jack 清单（name + address）")
    wires: list[Wire] = Field(description="连线；rule 可省略表示恒为真")
    rules: dict[str, str] = Field(
        default_factory=dict,
        description="rule_id → 条件表达式（express_evaluator）",
    )
    listen: int = Field(
        default=8765,
        ge=0,
        le=65535,
        description="PatchBay 监听端口；绑定地址固定为 0.0.0.0",
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
        name_set = set(names)
        for w in self.wires:
            if w.from_jack not in name_set:
                raise ValueError(f"连线引用未知 Jack（from）: {w.from_jack!r}")
            if w.to_jack not in name_set:
                raise ValueError(f"连线引用未知 Jack（to）: {w.to_jack!r}")
            if w.rule is None:
                continue
            if w.rule not in self.rules:
                raise ValueError(f"连线引用未知规则 id: {w.rule!r}")
            expr = self.rules[w.rule].strip()
            if not expr:
                raise ValueError(f"规则 {w.rule!r} 的表达式为空")
        return self


class ResolvedWire:
    """运行期解析后的一条线（含表达式正文）。"""

    __slots__ = ("from_jack", "to_jack", "expression")

    def __init__(
        self,
        *,
        from_jack: str,
        to_jack: str,
        expression: str,
    ) -> None:
        self.from_jack = from_jack
        self.to_jack = to_jack
        self.expression = expression


class RoutingTable:
    """按源 Jack 名称索引连线，转发前对每条候选线按数据包求值。"""

    __slots__ = ("_by_from_jack",)

    def __init__(self, wires: list[ResolvedWire]) -> None:
        by_from: dict[str, list[ResolvedWire]] = defaultdict(list)
        for w in wires:
            by_from[w.from_jack].append(w)
        self._by_from_jack = dict(by_from)

    @classmethod
    def from_config(cls, config: PatchBayConfig) -> RoutingTable:
        resolved: list[ResolvedWire] = []
        for w in config.wires:
            if w.rule is None:
                expr = "True"
            else:
                expr = config.rules[w.rule].strip()
            resolved.append(
                ResolvedWire(
                    from_jack=w.from_jack,
                    to_jack=w.to_jack,
                    expression=expr,
                )
            )
        return cls(resolved)

    def iter_from_jack(self, from_jack: str) -> Iterator[ResolvedWire]:
        yield from self._by_from_jack.get(from_jack, ())

    def to_mapping(self) -> list[dict[str, Any]]:
        """拓扑快照：每条连线一行。"""
        rows: list[dict[str, Any]] = []
        for fj, rules in sorted(self._by_from_jack.items()):
            for w in rules:
                rows.append(
                    {
                        "from_jack": fj,
                        "to_jack": w.to_jack,
                        "expression": w.expression,
                    }
                )
        return rows


def patch_bay_config_from_dict(data: Mapping[str, Any]) -> PatchBayConfig:
    """从内存 dict 构造配置。"""
    if not isinstance(data, dict):
        raise TypeError("config must be a dict")
    return PatchBayConfig.model_validate(data)
