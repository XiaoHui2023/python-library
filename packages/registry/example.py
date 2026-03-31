from registry import Registry

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


assert registry.get("event.startup") is StartupEvent
assert registry.get("condition.is_admin") is IsAdmin
assert registry.get("send_mail") is SendMail

print("测试通过")