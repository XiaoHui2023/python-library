from automation.loader import SECTION_TO_REGISTRIES


def export_schema() -> dict:
    result = {}
    for section_name, registry in SECTION_TO_REGISTRIES.items():
        result[section_name] = {}
        for reg_name in registry.get_registered_names():
            parts = reg_name.split(".")
            short = parts[-1] if len(parts) > 1 else reg_name
            cls = registry.get(short)
            schema = cls.model_json_schema()
            schema.get("properties", {}).pop("instance_name", None)
            result[section_name][short] = schema
    return result