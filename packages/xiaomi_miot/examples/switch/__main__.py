import os
import time
from pathlib import Path
from dotenv import load_dotenv
from xiaomi_miot import execute

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

IP = os.environ["SWITCH_IP"]
TOKEN = os.environ["SWITCH_TOKEN"]
EXPECTED = os.environ["SWITCH_VALUE"].lower() == "true"

base = {"type": "switch", "ip": IP, "token": TOKEN}
tests: list[tuple[str, dict, bool]] = []  # (name, result, passed)


def check(name: str, result: dict, expect_on: bool | None = None):
    if expect_on is not None:
        passed = result.get("ok") and result.get("value") == expect_on
    else:
        passed = result.get("ok", False)
    tests.append((name, result, passed))


# Step 1: 获取初始状态
r = execute(base)
check("获取初始状态", r)

# Step 2: 设置为期望值的【相反值】
r = execute({**base, "on": not EXPECTED})
check(f"设置为 {not EXPECTED}", r)

time.sleep(3)

# Step 3: 验证反向值生效
r = execute(base)
check(f"验证状态 == {not EXPECTED}", r, expect_on=not EXPECTED)

# Step 4: 设置为最终期望值
r = execute({**base, "on": EXPECTED})
check(f"设置为 {EXPECTED}", r)

# Step 5: 验证最终期望值生效
r = execute(base)
check(f"验证状态 == {EXPECTED}", r, expect_on=EXPECTED)

# 打印测试结果
print("\n" + "=" * 50)
print("测试结果")
print("=" * 50)
all_passed = True
for name, result, passed in tests:
    icon = "PASS" if passed else "FAIL"
    print(f"  [{icon}] {name}")
    if not passed:
        all_passed = False
        print(f"         {result}")
print("=" * 50)
print(f"{'全部通过' if all_passed else '存在失败'} ({sum(p for *_, p in tests)}/{len(tests)})")