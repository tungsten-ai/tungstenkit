from abc import ABC

import attrs

from tungstenkit._internal.utils.string import removesuffix


@attrs.frozen
class BaseImage(ABC):
    @property
    def name(self) -> str:
        return self.get_repository() + ":" + self.get_tag()

    def get_repository(self) -> str:
        raise NotImplementedError

    def get_tag(self) -> str:
        raise NotImplementedError

    @classmethod
    def type(cls) -> str:
        return removesuffix(cls.__name__, "Image").lower()
