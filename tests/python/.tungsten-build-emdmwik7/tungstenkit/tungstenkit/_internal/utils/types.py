import typing

from packaging.version import Version

from tungstenkit._versions import py_version


def get_type_args(t):
    if py_version >= Version("3.8"):
        return typing.get_args(t)
    try:
        return t.__args__
    except AttributeError:
        return tuple()


def get_type_origin(t):
    if py_version >= Version("3.8"):
        origin = typing.get_origin(t)
        if origin is None:
            return t
    try:
        if py_version >= Version("3.7"):
            return t.__origin__
        return t.__extra__
    except AttributeError:
        return t


def get_qualname(t):
    module = t.__module__
    if module == "__builtin__":
        return t.__name__
    return module + "." + t.__name__


def get_superclass_type_args(cls, supercls: type) -> tuple:
    for base in cls.__orig_bases__:  # type: ignore
        if get_type_origin(base) is supercls:
            args = get_type_args(base)
            return args
    return tuple()
