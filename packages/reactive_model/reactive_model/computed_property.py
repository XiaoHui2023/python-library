from typing import Callable, Generic, TypeVar

from reactive_model.computed_model import ComputedModel

T = TypeVar("T")

class computed_property(Generic[T]):
    def __init__(self, func: Callable[..., T]) -> None:
        self.func = func
        self.storage_name = ""

    def __set_name__(self, owner, name):
        self.storage_name = f"__computed_{name}"

    def __get__(self, obj, owner=None) -> T:
        if obj is None:
            return self

        model = obj.__dict__.get(self.storage_name)
        if model is None:
            model = ComputedModel(lambda: self.func(obj))
            obj.__dict__[self.storage_name] = model

        return model.value