import unittest

from registry import Registry


class RegistryTests(unittest.TestCase):
    def test_decorator_registration(self) -> None:
        registry = Registry()
        event = registry.namespace("event")
        condition = registry.namespace("condition")

        @event("startup")
        class StartupEvent:
            pass

        @condition("is_admin")
        class IsAdmin:
            pass

        @registry("send_mail")
        class SendMail:
            pass

        self.assertIs(registry.get("event.startup"), StartupEvent)
        self.assertIs(registry.get("condition.is_admin"), IsAdmin)
        self.assertIs(registry.get("send_mail"), SendMail)


if __name__ == "__main__":
    unittest.main()
