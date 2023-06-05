import json
import typing as t
from datetime import datetime
from pathlib import Path, PurePath, PurePosixPath

import attrs
import cattrs
import yaml
from packaging.version import Version

T = t.TypeVar("T")

converter = cattrs.Converter()

_unstructure_hooks: t.List[t.Tuple[type, t.Callable]] = list()


def register_unstructure_hook(type_: t.Type[T], hook: t.Callable[[T], str]):
    _unstructure_hooks.append((type_, hook))


def register_structure_hook(type_, hook):
    converter.register_structure_hook(type_, lambda s, _: hook(s))


def save_attrs_as_yaml(obj, path: Path):
    if not path.parent.exists():
        path.parent.mkdir(parents=True)

    d = attrs.asdict(obj, recurse=True, value_serializer=_serialize)
    with open(path, "w") as f:
        dumped = yaml.dump(d, default_flow_style=False)
        f.write(dumped)


def load_attrs_from_yaml(cls: t.Type[T], path: Path) -> T:
    with open(path, "r") as f:
        dict = yaml.load(f, Loader=yaml.Loader)

    return converter.structure(dict, cls)


def save_attrs_as_json(obj, path: Path):
    if not path.parent.exists():
        path.parent.mkdir(parents=True)

    d = attrs.asdict(obj, recurse=True, value_serializer=_serialize)
    with open(path, "w") as f:
        json.dump(d, f, indent=2)


def load_attrs_from_json(cls: t.Type[T], path: Path) -> T:
    with open(path, "r") as f:
        dict = json.load(f)

    return converter.structure(dict, cls)


def convert_attrs_to_json(obj: object) -> str:
    d = attrs.asdict(obj, recurse=True, value_serializer=_serialize)
    return json.dumps(d, indent=2)


def convert_json_to_attrs(json_: t.Union[str, bytes], cls: t.Type[T]) -> T:
    return converter.structure(json.loads(json_), cls)


def _serialize(inst, field, value):
    for cls, hook in _unstructure_hooks:
        if isinstance(value, cls):
            return hook(value)
    return value


register_unstructure_hook(datetime, lambda dt: dt.isoformat())
register_unstructure_hook(PurePath, lambda p: str(p))
register_unstructure_hook(Version, lambda v: str(v))

register_structure_hook(Path, lambda s: Path(s))
register_structure_hook(PurePosixPath, lambda s: PurePosixPath(s))
register_structure_hook(Version, lambda s: Version(s))
register_structure_hook(datetime, lambda s: datetime.fromisoformat(s))
