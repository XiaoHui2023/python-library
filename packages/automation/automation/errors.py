from enum import StrEnum


class LoadPhase(StrEnum):
    """加载阶段"""
    BUILD = "build"
    VALIDATE = "validate"
    ACTIVATE = "activate"


class LoadErrorCode(StrEnum):
    """加载错误码"""
    MISSING_TYPE = "missing_type"
    UNKNOWN_TYPE = "unknown_type"
    INVALID_CONFIG = "invalid_config"
    MISSING_ACTIONS = "missing_actions"
    INVALID_ACTION_SPEC = "invalid_action_spec"
    BUILD_FAILED = "build_failed"
    VALIDATION_FAILED = "validation_failed"
    ACTIVATION_FAILED = "activation_failed"


class AutomationLoadError(ValueError):
    """自动化加载异常，携带完整上下文"""


class ConfigLoadError(AutomationLoadError):
    """兼容旧名；新代码请使用 AutomationLoadError。"""

    def __init__(
        self,
        *,
        section: str,
        instance: str,
        phase: LoadPhase,
        code: LoadErrorCode,
        cause: Exception | None = None,
    ):
        self.section = section
        self.instance = instance
        self.phase = phase
        self.code = code
        self.cause = cause
        detail = str(cause) if cause else ""
        super().__init__(
            f"[{phase}/{code}] {section}.{instance}: {detail}"
        )