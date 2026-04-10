import unittest

from automation.hub import Hub, State


class HubTests(unittest.TestCase):
    def test_section_unknown_raises(self) -> None:
        hub = Hub()
        with self.assertRaises(KeyError) as ctx:
            hub.section("unknown")
        self.assertIn("Unknown automation section", str(ctx.exception))

    def test_initial_state(self) -> None:
        hub = Hub()
        self.assertEqual(hub.state, State.IDLE)
        self.assertEqual(hub.config, {})


if __name__ == "__main__":
    unittest.main()
