import typing as t

import attrs
from packaging.version import Version


@attrs.frozen
class PipRequirement:
    name: str
    version: t.Optional[Version] = attrs.field(default=None)
    pip_index_url: t.Optional[str] = attrs.field(default=None)
    pip_extra_index_url: t.Optional[str] = attrs.field(default=None)

    def to_str(self, index: bool = True):
        requirement = f"{self.name}"
        if self.version:
            requirement += f"=={self.version}"
        if index and self.pip_index_url:
            requirement += f" --index-url {self.pip_index_url}"
        if index and self.pip_extra_index_url:
            requirement += f" --extra-index-url {self.pip_extra_index_url}"
        return requirement
