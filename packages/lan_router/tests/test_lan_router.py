import unittest

from lan_router import Device, create_router


class LanRouterTests(unittest.TestCase):
    def test_create_router_rejects_unknown_vendor(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            create_router("unknown")  # type: ignore[arg-type]
        self.assertIn("不支持", str(ctx.exception))

    def test_device_model(self) -> None:
        d = Device(name="n", ip="192.168.0.1", mac="00:00:00:00:00:01", type="wifi")
        self.assertEqual(d.name, "n")
        self.assertEqual(d.ip, "192.168.0.1")


if __name__ == "__main__":
    unittest.main()
