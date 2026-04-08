from __future__ import annotations

import unittest

from watch_config import ChangeEntry, ChangeLog, ChangeType


class ChangeLogTests(unittest.TestCase):
    def test_is_empty_true_when_no_entries(self) -> None:
        log = ChangeLog()
        self.assertTrue(log.is_empty)
        self.assertEqual(len(log), 0)

    def test_added_removed_updated_type_changed(self) -> None:
        log = ChangeLog()
        log.added("$.a", 1)
        log.removed("$.b", 2)
        log.updated("$.c", 0, 9)
        log.type_changed("$.d", "x", 1)

        self.assertFalse(log.is_empty)
        self.assertEqual(len(log), 4)

        types = [e.type for e in log.entries]
        self.assertEqual(
            types,
            [
                ChangeType.ADDED,
                ChangeType.REMOVED,
                ChangeType.UPDATED,
                ChangeType.TYPE_CHANGED,
            ],
        )

        self.assertEqual(log.entries[0].path, "$.a")
        self.assertIsNone(log.entries[0].old_value)
        self.assertEqual(log.entries[0].new_value, 1)

        self.assertEqual(log.entries[1].old_value, 2)
        self.assertIsNone(log.entries[1].new_value)

        self.assertEqual(log.entries[2].old_value, 0)
        self.assertEqual(log.entries[2].new_value, 9)

        self.assertEqual(log.entries[3].old_value, "x")
        self.assertEqual(log.entries[3].new_value, 1)

    def test_iter_yields_entries(self) -> None:
        log = ChangeLog()
        log.added("$.x", 1)
        iterated = list(log)
        self.assertEqual(len(iterated), 1)
        self.assertIsInstance(iterated[0], ChangeEntry)


if __name__ == "__main__":
    unittest.main()
