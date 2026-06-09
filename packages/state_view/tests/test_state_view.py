import unittest
from dataclasses import dataclass, field
from enum import Enum

from state_view import StateView, StateViewError


class CaseName(str, Enum):
    smoke = "smoke"
    regression = "regression"


@dataclass
class CaseConfig:
    name: CaseName
    enabled: bool = True
    count: int = 1


@dataclass
class RunState:
    name: str
    project: str
    seed: int = 1
    cases: list[CaseConfig] = field(default_factory=list)

    @property
    def total_runs(self) -> int:
        return sum(case.count for case in self.cases if case.enabled)


def make_state() -> RunState:
    return RunState(
        name="demo",
        project="alpha",
        seed=1,
        cases=[CaseConfig(name=CaseName.smoke)],
    )


class StateViewTests(unittest.TestCase):
    def test_get_exports_fields_and_computed_property(self) -> None:
        view = StateView(make_state())
        self.assertEqual(
            view.get(),
            {
                "name": "demo",
                "project": "alpha",
                "seed": 1,
                "cases": [{"name": "smoke", "enabled": True, "count": 1}],
                "total_runs": 1,
            },
        )

    def test_set_updates_seed_and_recomputes_total_runs(self) -> None:
        state = make_state()
        view = StateView(
            state,
            editable=["seed", "cases"],
            readonly=["name", "project", "total_runs"],
        )
        data = view.set({"seed": 123})
        self.assertEqual(state.seed, 123)
        self.assertEqual(data["seed"], 123)
        self.assertEqual(data["total_runs"], 1)

    def test_set_replaces_cases_list(self) -> None:
        state = make_state()
        view = StateView(
            state,
            editable=["seed", "cases"],
            readonly=["name", "project", "total_runs"],
        )
        data = view.set(
            {
                "cases": [
                    {"name": "smoke", "enabled": True, "count": 5},
                ]
            }
        )
        self.assertEqual(len(state.cases), 1)
        self.assertEqual(state.cases[0].count, 5)
        self.assertEqual(data["total_runs"], 5)

    def test_set_partial_patch_allowed(self) -> None:
        state = make_state()
        view = StateView(state, editable=["seed"])
        view.set({"seed": 42})
        self.assertEqual(state.seed, 42)

    def test_schema_marks_property_readonly(self) -> None:
        view = StateView(
            make_state(),
            editable=["seed", "cases"],
            readonly=["name", "project", "total_runs"],
        )
        schema = view.schema()
        self.assertTrue(schema["seed"]["editable"])
        self.assertFalse(schema["name"]["editable"])
        self.assertTrue(schema["name"]["readonly"])
        self.assertTrue(schema["total_runs"]["computed"])
        self.assertEqual(schema["cases"]["type"], "array")
        self.assertEqual(
            schema["cases"]["items"]["properties"]["name"]["enum"],
            ["smoke", "regression"],
        )

    def test_set_rejects_readonly_field(self) -> None:
        view = StateView(make_state(), readonly=["name"])
        with self.assertRaises(StateViewError) as ctx:
            view.set({"name": "other"})
        self.assertEqual(ctx.exception.path, "name")

    def test_set_rejects_computed_property(self) -> None:
        view = StateView(make_state())
        with self.assertRaises(StateViewError) as ctx:
            view.set({"total_runs": 99})
        self.assertEqual(ctx.exception.path, "total_runs")

    def test_set_rejects_unknown_field(self) -> None:
        view = StateView(make_state())
        with self.assertRaises(StateViewError) as ctx:
            view.set({"missing": 1})
        self.assertEqual(ctx.exception.path, "missing")

    def test_set_rejects_invalid_enum(self) -> None:
        view = StateView(make_state(), editable=["cases"])
        with self.assertRaises(StateViewError) as ctx:
            view.set({"cases": [{"name": "bad", "enabled": True, "count": 1}]})
        self.assertIn("cases.0.name", ctx.exception.path)

    def test_editable_whitelist_blocks_other_fields(self) -> None:
        view = StateView(make_state(), editable=["seed"])
        with self.assertRaises(StateViewError) as ctx:
            view.set({"project": "beta"})
        self.assertEqual(ctx.exception.path, "project")

    def test_default_all_dataclass_fields_editable_except_property(self) -> None:
        view = StateView(make_state())
        schema = view.schema()
        self.assertTrue(schema["seed"]["editable"])
        self.assertFalse(schema["total_runs"]["editable"])
