import typing as t
from abc import ABC, abstractmethod

import attrs

from tungstenkit._internal.utils.string import removesuffix

T = t.TypeVar("T", bound="BaseImage")


@attrs.frozen
class BaseImage(ABC):
    @abstractmethod
    def get_repository(self) -> str:
        pass

    @abstractmethod
    def get_tag(self) -> str:
        pass

    @property
    def name(self) -> str:
        return self.get_repository() + ":" + self.get_tag()

    @classmethod
    def typename(cls) -> str:
        return removesuffix(cls.__name__, "Image").lower()


@attrs.frozen
class BaseImageCollection(t.Generic[T], ABC):
    images: t.List[T]

    @classmethod
    @abstractmethod
    def from_remote(cls) -> "BaseImageCollection":
        pass

    @classmethod
    @abstractmethod
    def from_file(cls) -> "BaseImageCollection":
        pass

    @classmethod
    def typename(cls) -> str:
        return removesuffix(cls.__name__, "ImageCollection").lower()
