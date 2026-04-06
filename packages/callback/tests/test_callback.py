import unittest

from callback import Callback


class CallbackTests(unittest.TestCase):
    def tearDown(self) -> None:
        Callback.function_registry.clear()

    def test_trigger_invokes_registered_handler(self) -> None:
        class Inc(Callback):
            callback_name: str = "Inc"
            name: str
            data: int

        class Holder:
            def __init__(self) -> None:
                @Inc
                def _(cb: Inc) -> None:
                    cb.data += 1

        Holder()
        cb = Inc.trigger(name="test", data=1)
        self.assertEqual(cb.data, 2)


if __name__ == "__main__":
    unittest.main()
