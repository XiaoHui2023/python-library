from __future__ import annotations

import unittest

from pydantic import ValidationError

from patch_bay.patchbay import PatchBay
from patch_bay.routing import RoutingTable, patch_bay_config_from_dict


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

    def test_same_from_multiple_wires_order(self) -> None:
        """同一 from 多条线按 YAML 顺序进入 RoutingTable。"""
        cfg = patch_bay_config_from_dict(
            {
                "jacks": [
                    {"name": "in", "address": "h:1"},
                    {"name": "out", "address": "h:2"},
                    {"name": "spare", "address": "h:3"},
                ],
                "wires": [
                    {"from": "in", "to": "out"},
                    {"from": "in", "to": "spare"},
                ],
                "rules": {},
            }
        )
        rt = RoutingTable.from_config(cfg)
        w = list(rt.iter_from_jack("in"))
        self.assertEqual([x.to_jack for x in w], ["out", "spare"])

    def test_jack_and_wire_names_are_stripped(self) -> None:
        cfg = patch_bay_config_from_dict(
            {
                "jacks": [
                    {"name": " a ", "address": "h:1"},
                    {"name": " b ", "address": "h:2"},
                ],
                "wires": [{"from": " a ", "to": " b "}],
                "rules": {},
            }
        )
        self.assertEqual(cfg.jacks[0].name, "a")
        self.assertEqual(cfg.wires[0].from_jack, "a")
        self.assertEqual(cfg.wires[0].to_jack, "b")

    def test_patchs_on_wire_resolved(self) -> None:
        cfg = patch_bay_config_from_dict(
            {
                "jacks": [
                    {"name": "a", "address": "h:1"},
                    {"name": "b", "address": "h:2"},
                ],
                "patchs": [
                    {"name": "p1", "patch": {"k": 1}},
                    {"name": "p2", "patch": {"m": 2}},
                ],
                "wires": [
                    {
                        "from": "a",
                        "to": "b",
                        "patchs": ["p1", "p2"],
                    },
                ],
                "rules": {},
            }
        )
        rt = RoutingTable.from_config(cfg)
        w = list(rt.iter_from_jack("a"))[0]
        self.assertEqual(
            w.patch_steps,
            (("p1", {"k": 1}), ("p2", {"m": 2})),
        )

    def test_unknown_patch_on_wire_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            patch_bay_config_from_dict(
                {
                    "jacks": [
                        {"name": "a", "address": "h:1"},
                        {"name": "b", "address": "h:2"},
                    ],
                    "patchs": [{"name": "p1", "patch": {"x": 1}}],
                    "wires": [{"from": "a", "to": "b", "patchs": ["nosuch"]}],
                    "rules": {},
                }
            )

    def test_duplicate_patch_name_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            patch_bay_config_from_dict(
                {
                    "jacks": [
                        {"name": "a", "address": "h:1"},
                        {"name": "b", "address": "h:2"},
                    ],
                    "patchs": [
                        {"name": "same", "patch": {"x": 1}},
                        {"name": "same", "patch": {"y": 2}},
                    ],
                    "wires": [{"from": "a", "to": "b"}],
                    "rules": {},
                }
            )


if __name__ == "__main__":
    unittest.main()
