from __future__ import annotations

import logging
from typing import Any

from express_evaluator import Evaluator
from express_evaluator.errors import EvaluatorError

from .packet_scope import build_packet_eval_scope

logger = logging.getLogger(__name__)


def rule_allows(expression: str, packet: bytes, evaluator: Evaluator) -> bool:
    """条件为真则放行；求值异常或结果为假则吞包。"""
    data: dict[str, Any] = build_packet_eval_scope(packet)
    try:
        out = evaluator.evaluate(expression, data)
    except EvaluatorError:
        logger.debug("rule dropped packet (eval error)", exc_info=True)
        return False
    except Exception:
        logger.debug("rule dropped packet (unexpected error)", exc_info=True)
        return False
    return bool(out)
