from __future__ import annotations

import asyncio
import inspect
import logging
from typing import Any, Self

from pydantic import Field, PrivateAttr, model_validator
from reactive_model import ListRefModel, computed_property
from .base import BaseAutomation
from .info import AttributeInfo, MethodInfo, introspect_attributes, introspect_methods
from .registry_catalog import ENTITY_NAMESPACE, entity_registry

logger = logging.getLogger(__name__)
_SENTINEL = object()

_VARIABLE_TYPE_CASTERS = {"int": int, "float": float, "str": str, "bool": bool}


class Entity(BaseAutomation):
    """Automation 实体类型。

    声明式扩展元数据在 properties；配置驱动的动态字段在 variables，字符串初值在构建阶段参与表达式求值。
    """

    properties: list[AttributeInfo] = Field(
        default_factory=list,
        description="扩展属性元数据列表（声明式）。",
    )
    variables: dict[str, dict[str, Any]] = Field(
        default_factory=dict,
        description="动态变量定义：名称到 {type, value, default, description}；初值为字符串时在加载构建阶段求值。",
    )

    _builtin_attribute_infos: ListRefModel[AttributeInfo] = PrivateAttr(
        default_factory=ListRefModel
    )
    _builtin_method_infos: ListRefModel[MethodInfo] = PrivateAttr(
        default_factory=ListRefModel
    )
    _variable_values: dict[str, Any] = PrivateAttr(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _lift_legacy_variable_properties(cls, data: Any) -> Any:
        """历史上 variable 类型把映射写在 properties 字典里；迁入 variables。"""

        if not isinstance(data, dict):
            return data
        props = data.get("properties")
        if not isinstance(props, dict):
            return data
        if data.get("variables"):
            raise ValueError(
                "不可同时使用 properties 字典与 variables，请只保留其一",
            )
        out = {k: v for k, v in data.items() if k != "properties"}
        out["variables"] = dict(props)
        out["properties"] = []
        return out

    @model_validator(mode="after")
    def _init_introspection_after_model(self) -> Self:
        """在实例与私有运行字段就绪后填充内省缓存。"""

        self._init_entity_introspection()
        return self

    def __getattr__(self, name: str) -> Any:
        try:
            return super().__getattribute__(name)
        except AttributeError:
            pass
        try:
            priv = object.__getattribute__(self, "__pydantic_private__")
            if name in priv:
                return priv[name]
        except AttributeError:
            pass
        try:
            vd = object.__getattribute__(self, "_variable_values")
        except AttributeError:
            raise AttributeError(name) from None
        if name in vd:
            return vd[name]
        raise AttributeError(
            f"{type(self).__name__!r} object has no attribute {name!r}",
        )

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_"):
            super().__setattr__(name, value)
            return
        try:
            vd = object.__getattribute__(self, "_variable_values")
        except AttributeError:
            vd = None
        if vd is not None and name in vd:
            old = vd[name]
            spec = self.variables[name]
            type_name = spec.get("type", "str")
            if type_name == "list":
                new = list(value) if not isinstance(value, list) else value
            else:
                new = self._cast_dynamic(type_name, value)
            vd[name] = new
            try:
                changed = old != new
            except Exception:
                changed = True
            if changed:
                self._dispatch_public_attribute_change(name, old, new)
            return
        old = getattr(self, name, _SENTINEL)
        super().__setattr__(name, value)
        if old is not _SENTINEL:
            new = getattr(self, name)
            try:
                changed = old != new
            except Exception:
                changed = True
            if changed:
                self._dispatch_public_attribute_change(name, old, new)

    def _dispatch_public_attribute_change(
        self, name: str, old: Any, new: Any
    ) -> None:
        """普通字段写入后：调度子类钩子与上下文中的属性监听回调。"""

        coro = self.on_attribute_change(name, old, new)
        if inspect.iscoroutine(coro):
            self._schedule_coroutine(coro)
        for h in list(self._ctx._on_state_changed):
            out = h(self, name, old, new)
            if inspect.iscoroutine(out):
                self._schedule_coroutine(out)

    def _schedule_coroutine(self, coro: object) -> None:
        """在已绑定的主循环上启动协程。"""

        loop = self._ctx.main_loop
        if loop is not None and loop.is_running():
            loop.create_task(coro)
            return
        try:
            asyncio.get_running_loop().create_task(coro)
        except RuntimeError:
            logger.warning("无法调度协程：当前无运行中的事件循环")

    async def on_attribute_change(self, name: str, old: Any, new: Any) -> None:
        """属性变化钩子，由普通属性赋值路径在事件循环中异步调度。

        Args:
            name: 变更的属性名。
            old: 旧值。
            new: 新值。
        """

    async def on_build(self) -> None:
        """渲染动态变量初值并写入运行期表。

        派生类若重写本方法且配置里仍使用 variables，请先执行父类逻辑（含本方法中的渲染与填充）。
        """

        if not self.variables:
            return
        ctx = self._ctx
        for name, spec in self.variables.items():
            type_name = spec.get("type", "str")
            value = spec.get("value")
            if type_name == "list":
                seq = value or []
                self._variable_values[name] = [
                    ctx.create_renderer()(x) if isinstance(x, str) else x
                    for x in seq
                ]
            else:
                v = (
                    ctx.create_renderer()(value)
                    if isinstance(value, str)
                    else value
                )
                self._variable_values[name] = self._cast_dynamic(type_name, v)

    async def _update_attributes(self, new_spec: dict[str, Any]) -> None:
        """按规格批量更新模型字段或动态变量，未知键记错误日志。

        Args:
            new_spec: 字段名到新值的映射。
        """
        for key, value in new_spec.items():
            if key in self.__class__.model_fields:
                setattr(self, key, value)
            elif key in self.variables:
                setattr(self, key, value)
            else:
                logger.error(
                    "%s.%s: update unknown attribute %r",
                    self.instance_name,
                    key,
                    key,
                )

    def _init_entity_introspection(self) -> None:
        """填充内置属性与方法的内省缓存。"""

        priv = object.__getattribute__(self, "__pydantic_private__")
        infos = priv["_builtin_attribute_infos"]
        methods = priv["_builtin_method_infos"]
        infos.value = list(introspect_attributes(type(self)))
        methods.value = list(introspect_methods(type(self)))

    @staticmethod
    def _cast_dynamic(type_name: str, value: Any) -> Any:
        if value is None:
            return None
        caster = _VARIABLE_TYPE_CASTERS.get(type_name)
        if caster is not None:
            return caster(value)
        return value

    def get_variable_values(self) -> dict[str, Any]:
        """返回动态变量当前值的浅拷贝。"""

        return dict(self._variable_values)

    @computed_property
    def _attribute_infos(self) -> list[AttributeInfo]:
        """合并内省、声明式 properties 与 variables 元数据。

        Returns:
            列表: 合并后的属性元数据条目。
        """
        from_vars = [
            AttributeInfo(
                name=name,
                type=spec.get("type", "str"),
                description=spec.get("description", ""),
                readonly=False,
                default=spec.get("default"),
            )
            for name, spec in self.variables.items()
        ]
        return (
            list(self._builtin_attribute_infos.value)
            + list(self.properties)
            + from_vars
        )

    @computed_property
    def _to_attribute_info(self) -> dict[str, AttributeInfo]:
        """按名称索引属性元数据。

        Returns:
            映射: 名称到单条元数据条目。
        """
        return {x.name: x for x in self._attribute_infos}

    @computed_property
    def _method_infos(self) -> list[MethodInfo]:
        """内省得到的实例方法元数据列表。

        Returns:
            列表: 方法元数据条目。
        """
        return list(self._builtin_method_infos.value)


Entity.registered_kind = ENTITY_NAMESPACE
entity_registry.register(ENTITY_NAMESPACE, Entity)
entity_registry.register("variable", Entity)
