from __future__ import annotations

import unittest

from reactive_model import RefModel, computed_property


class TestComputedProperty(unittest.TestCase):
    def test_access_on_class_returns_descriptor(self) -> None:
        class Host:
            def __init__(self) -> None:
                self.x = RefModel(1)

            @computed_property
            def doubled(self) -> int:
                return self.x.value * 2

        desc = Host.doubled
        self.assertIsInstance(desc, computed_property)
        self.assertEqual(desc.storage_name, "__computed_doubled")

    def test_lazy_compute_and_cache(self) -> None:
        calls: list[int] = []

        class Host:
            def __init__(self) -> None:
                self.x = RefModel(1)

            @computed_property
            def doubled(self) -> int:
                calls.append(1)
                return self.x.value * 2

        h = Host()
        self.assertEqual(calls, [])
        self.assertEqual(h.doubled, 2)
        self.assertEqual(calls, [1])
        self.assertEqual(h.doubled, 2)
        self.assertEqual(calls, [1])

    def test_invalidates_when_dependency_changes(self) -> None:
        class Host:
            def __init__(self) -> None:
                self.x = RefModel(1)

            @computed_property
            def doubled(self) -> int:
                return self.x.value * 2

        h = Host()
        self.assertEqual(h.doubled, 2)
        h.x.value = 3
        self.assertEqual(h.doubled, 6)

    def test_model_stored_on_instance_dict(self) -> None:
        class Host:
            def __init__(self) -> None:
                self.x = RefModel(10)

            @computed_property
            def label(self) -> str:
                return f"x={self.x.value}"

        h = Host()
        self.assertNotIn("__computed_label", h.__dict__)
        _ = h.label
        self.assertIn("__computed_label", h.__dict__)
        model = h.__dict__["__computed_label"]
        self.assertEqual(model.value, "x=10")

    def test_per_instance_independence(self) -> None:
        class Host:
            def __init__(self, n: int) -> None:
                self.x = RefModel(n)

            @computed_property
            def doubled(self) -> int:
                return self.x.value * 2

        a = Host(2)
        b = Host(5)
        self.assertEqual(a.doubled, 4)
        self.assertEqual(b.doubled, 10)
        a.x.value = 3
        self.assertEqual(a.doubled, 6)
        self.assertEqual(b.doubled, 10)

    def test_two_computed_properties_same_instance(self) -> None:
        class Host:
            def __init__(self) -> None:
                self.x = RefModel(2)

            @computed_property
            def doubled(self) -> int:
                return self.x.value * 2

            @computed_property
            def tripled(self) -> int:
                return self.x.value * 3

        h = Host()
        self.assertEqual(h.doubled, 4)
        self.assertEqual(h.tripled, 6)
        h.x.value = 4
        self.assertEqual(h.doubled, 8)
        self.assertEqual(h.tripled, 12)


if __name__ == "__main__":
    unittest.main()
