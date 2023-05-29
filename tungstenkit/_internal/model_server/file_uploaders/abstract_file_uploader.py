import abc
import typing as t

from tungstenkit._internal import io


class AbstractFileUploader(abc.ABC):
    @abc.abstractmethod
    def upload(self, files: t.List[io.File]) -> t.List[io.File]:
        pass
