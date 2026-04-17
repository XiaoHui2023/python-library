from express_evaluator import Evaluator

data = {
    "user": {
        "name": "Alice",
        "age": 20,
    },
    "items": [
        {"name": "A", "enabled": True},
        {"name": "B", "enabled": False},
        {"name": "C", "enabled": True},
    ],
}

evaluator = Evaluator()

print(evaluator("{user.age} >= 18", data))
print(evaluator("[x.name for x in {items} if x.enabled]", data))
print(evaluator("all(x.enabled for x in {items})", data))
print(evaluator('any({items}, "enabled")', data))