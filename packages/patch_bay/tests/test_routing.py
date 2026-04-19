from __future__ import annotations

import unittest

from patch_bay.patchbay import PatchBay
from patch_bay.routing import (
    JackEntry,
    PatchBayConfig,
    RoutingTable,
    Wire,
    patch_bay_config_from_dict,
)


def _minimal_cfg(**overrides: object) -> dict:
    base = {
        "jacks": [
            {"name": "a", "address": "127.0.0.1:1"},
            {"name": "b", "address": "127.0.0.1:2"},
        ],
        "wires": [
            {"from": "a", "to": "b", "rule": "r1"},
        ],
        "rules": {"r1": "True"},
    }
    base.update(overrides)
    return base


class TestRouting(unittest.TestCase):
    def test_targets_broadcast(self) -> None:
        cfg = patch_bay_config_from_dict(
            {
                "jacks": [
                    {"name": "a", "address": "h:1"},
                    {"name": "b", "address": "h:2"},
                    {"name": "c", "address": "h:3"},
                ],
                "wires": [
                    {"from": "a", "to": "b", "rule": "r1"},
                    {"from": "a", "to": "c", "rule": "r1"},
                ],
                "rules": {"r1": "True"},
            }
        )
        rt = RoutingTable.from_config(cfg)
        w1 = list(rt.iter_from_jack("a"))
        self.assertEqual(len(w1), 2)

    def test_patch_bay_init_config(self) -> None:
        pb = PatchBay(_minimal_cfg())
        self.assertEqual(pb.config.listen, 8765)

    def test_wire_omit_rule_passes_through(self) -> None:
        cfg = patch_bay_config_from_dict(
            {
                "jacks": [
                    {"name": "a", "address": "h:1"},
                    {"name": "b", "address": "h:2"},
                ],
                "wires": [{"from": "a", "to": "b"}],
                "rules": {},
            }
        )
        rt = RoutingTable.from_config(cfg)
        w = list(rt.iter_from_jack("a"))
        self.assertEqual(len(w), 1)
        self.assertEqual(w[0].expression, "True")


if __name__ == "__main__":
    unittest.main()
