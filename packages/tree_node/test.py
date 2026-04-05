from callback import Callback

class A(Callback):
    callback_name: str = "A"
    """回调名称"""
    name: str
    """名称"""
    data: int
    """数据"""

class Other:
    def __init__(self):
        @A
        def _(cb:A):
            print(f"on_{cb.callback_name}: {cb.name}")
            cb.data += 1


if __name__ == "__main__":
    Other()
    a = A.trigger(name="test", data=1)
    print(a.data)