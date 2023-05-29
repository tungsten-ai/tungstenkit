import abc
import typing as t

from tungstenkit._internal.io import BaseIO

from .shared import Batch


class AbstractInputQueue(abc.ABC):
    @abc.abstractmethod
    def push(
        self,
        prediction_id: str,
        inputs: t.List[BaseIO],
        is_demo: bool,
    ) -> t.List[str]:
        pass

    @abc.abstractmethod
    def pop(self, max_batch_size: int, timeout: t.Optional[float] = None) -> Batch:
        pass

    @abc.abstractmethod
    def remove(self, prediction_id: str) -> t.List[str]:
        pass
