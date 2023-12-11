import typing as t


def remove_useless_allof_in_jsonschema(jsonschema: t.Dict):
    type_ = jsonschema.get("type", None)
    if type_ and type_ == "object":
        updated_props = dict()
        for prop_name, prop in jsonschema.get("properties", {}).items():
            allof: t.List = prop.get("allOf", None) if isinstance(prop, dict) else None
            if allof:
                updated_prop = prop.copy()
                if len(allof) == 0:
                    updated_prop.pop("allOf")
                elif len(allof) == 1:
                    updated_prop.pop("allOf")
                    subschema = allof.pop()
                    updated_prop.update(subschema)

                updated_props[prop_name] = updated_prop

        for prop_name, prop in updated_props.items():
            jsonschema["properties"][prop_name] = prop

        for prop in jsonschema.get("properties", {}).values():
            remove_useless_allof_in_jsonschema(prop)
