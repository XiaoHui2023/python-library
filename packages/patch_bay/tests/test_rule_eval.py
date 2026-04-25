from __future__ import annotations

import unittest

from express_evaluator import Evaluator

from patch_bay.rule_eval import rule_allows


class TestRuleEval(unittest.TestCase):
    def test_rule_uses_packet_data_as_root(self) -> None:
        packet = b'{"type":"message","user_id":123}'

        self.assertTrue(rule_allows('{type} == "message"', packet, Evaluator()))
        self.assertTrue(rule_allows("{user_id} == 123", packet, Evaluator()))

    def test_rule_supports_nested_data_from_root(self) -> None:
        packet = b'{"message":{"type":"text"},"members":[{"role":"admin"}]}'

        self.assertTrue(rule_allows('{message.type} == "text"', packet, Evaluator()))
        self.assertTrue(rule_allows('{members.0.role} == "admin"', packet, Evaluator()))

    def test_missing_root_field_drops_packet(self) -> None:
        packet = b'{"type":"message"}'

        self.assertFalse(rule_allows('{data.type} == "message"', packet, Evaluator()))

    def test_non_object_packet_drops_placeholder_rule(self) -> None:
        self.assertFalse(rule_allows("{type} == 1", b"[1,2]", Evaluator()))


if __name__ == "__main__":
    unittest.main()
