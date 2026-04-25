from __future__ import annotations

import logging
from typing import Any

from express_evaluator import Evaluator
from express_evaluator.errors import EvaluatorError

from .packet_scope import build_packet_eval_scope

logger = logging.getLogger(__name__)


def rule_allows(expression: str, packet: bytes, evaluator: Evaluator) -> bool:
    """判断数据包是否满足连线上的条件表达式。

    Args:
        expression: 配置中声明的条件表达式。
        packet: 传输中收到的原始载荷。
        evaluator: 负责执行表达式的求值器。

    Returns:
        bool: 表达式结果为真时返回 True；求值失败或结果为假时返回 False。
    """
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
