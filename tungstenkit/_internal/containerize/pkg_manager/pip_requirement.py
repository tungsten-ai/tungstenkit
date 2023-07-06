import typing as t

import attrs
from packaging.specifiers import SpecifierSet
from packaging.version import Version


@attrs.frozen
class PipRequirement:
    name: str
    spec: t.Optional[Version | SpecifierSet] = attrs.field(default=None)
    index_url: t.Optional[str] = attrs.field(default=None)
    extra_index_url: t.Optional[str] = attrs.field(default=None)

    def to_str(self, index: bool = True):
        requirement = f"{self.name}"
        if isinstance(self.spec, Version):
            requirement += f"=={self.spec}"
        if isinstance(self.spec, SpecifierSet):
            requirement += str(self.spec)
        if index and self.index_url:
            requirement += f" --index-url {self.index_url}"
        if index and self.extra_index_url:
            requirement += f" --extra-index-url {self.extra_index_url}"
        return requirement
