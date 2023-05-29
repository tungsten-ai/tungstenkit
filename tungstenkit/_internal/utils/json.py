import typing as t

from .uri import check_if_uri_in_allowed_schemes


def apply_to_jsonable(jsonable: t.Any, cond: t.Callable, fn: t.Callable) -> t.Any:
    """Apply a function to a jsonable object if a value safisfies a condition"""
    if isinstance(jsonable, dict):
        converted_dict = dict()
        for key, value in jsonable.items():
            if isinstance(value, dict) or isinstance(value, list):
                value = apply_to_jsonable(value, cond, fn)
            elif cond(value):
                value = fn(value)
            converted_dict[key] = value
        return converted_dict

    if isinstance(jsonable, list):
        converted_list = []
        for item in jsonable:
            if isinstance(item, dict) or isinstance(item, list):
                item = apply_to_jsonable(item, cond, fn)
            elif cond(item):
                item = fn(item)
            converted_list.append(item)
        return converted_list

    if cond(jsonable):
        return fn(jsonable)

    return jsonable


def get_uris_in_jsonable(jsonable: t.Any, schemes: t.List[str]) -> t.List[str]:
    uris = set()

    def fn(v: str):
        if check_if_uri_in_allowed_schemes(v, schemes):
            uris.add(v)
        return v

    apply_to_jsonable(jsonable, cond=lambda o: isinstance(o, str), fn=fn)
    return list(uris)


def change_strings_in_jsonable(jsonable: t.Any, values: t.List[str], updates: t.List):
    assert len(values) == len(updates)

    def fn(v):
        if v in values:
            idx = values.index(v)
            return updates[idx]
        return v

    if len(values) > 0:
        return apply_to_jsonable(jsonable, cond=lambda o: isinstance(o, str), fn=fn)
    return jsonable
