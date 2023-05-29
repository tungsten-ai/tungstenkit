import re
from itertools import takewhile


# For compatibility with python<3.9
def removesuffix(string: str, suffix: str) -> str:
    if string.endswith(suffix):
        return string[: -len(suffix)]
    else:
        return string[:]


# For compatibility with python<3.9
def removeprefix(string: str, prefix: str) -> str:
    if string.startswith(prefix):
        return string[len(prefix) :]
    else:
        return string[:]


def camel_to_snake(name: str) -> str:
    name = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", name).lower()


def get_common_prefix(*strings: str):
    return "".join(c[0] for c in takewhile(lambda x: all(x[0] == y for y in x), zip(*strings)))
