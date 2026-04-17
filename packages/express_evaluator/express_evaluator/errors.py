from __future__ import annotations


class EvaluatorError(Exception):
    """Base exception for express_evaluator."""


class UndefinedVariableError(EvaluatorError):
    """Raised when a variable or path cannot be resolved."""


class ExpressionSyntaxError(EvaluatorError):
    """Raised when an expression cannot be parsed."""


class UnsafeExpressionError(EvaluatorError):
    """Raised when an expression uses disabled or unsafe syntax."""


class SyntaxRegistrationError(EvaluatorError):
    """Raised when syntax registration fails."""


class UnknownConfigurationError(EvaluatorError):
    """Raised when a syntax or preset name is unknown."""