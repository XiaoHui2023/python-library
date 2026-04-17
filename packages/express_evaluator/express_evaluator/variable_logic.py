from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from .errors import UndefinedVariableError

VARIABLE_RE = re.compile(r"\{([^{}]+)\}")
_SINGLE_VAR_RE = re.compile(r"^\{([^{}]+)\}$")
_PLACEHOLDER_PREFIX = "__value_"


def is_single_placeholder(value: str) -> str | None:
    match = _SINGLE_VAR_RE.match(value.strip())
    if not match:
        return None
    return match.group(1).strip()


def resolve_path(data: Any, path: str, *, strict: bool = True) -> Any:
    current = data

    for raw_part in path.split("."):
        part = raw_part.strip()
        if not part:
            raise UndefinedVariableError(f"Invalid empty path segment in {path!r}")

        if isinstance(current, Mapping):
            if part in current:
                current = current[part]
                continue
            if strict:
                raise UndefinedVariableError(f"Key {part!r} not found while resolving {path!r}")
            return None

        if isinstance(current, (list, tuple)):
            if not part.isdigit():
                if strict:
                    raise UndefinedVariableError(
                        f"Expected numeric index but got {part!r} while resolving {path!r}"
                    )
                return None

            index = int(part)
            if index >= len(current):
                if strict:
                    raise UndefinedVariableError(
                        f"Index {index} out of range while resolving {path!r}"
                    )
                return None

            current = current[index]
            continue

        if part.startswith("_"):
            raise UndefinedVariableError(f"Private attribute access is not allowed: {part!r}")

        if hasattr(current, part):
            current = getattr(current, part)
            continue

        if strict:
            raise UndefinedVariableError(
                f"Attribute {part!r} not found on {type(current).__name__!r} while resolving {path!r}"
            )
        return None

    return current


def replace_placeholders(
    expression: str,
    data: Mapping[str, Any],
    *,
    strict: bool = True,
) -> tuple[str, dict[str, Any]]:
    values: dict[str, Any] = {}

    def repl(match: re.Match[str]) -> str:
        token = match.group(1).strip()
        name = f"{_PLACEHOLDER_PREFIX}{len(values)}"
        values[name] = resolve_path(data, token, strict=strict)
        return name

    parsed = VARIABLE_RE.sub(repl, expression)
    return parsed, values