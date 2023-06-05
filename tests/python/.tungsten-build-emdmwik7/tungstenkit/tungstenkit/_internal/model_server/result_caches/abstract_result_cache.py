import abc
import time
import typing as t
from pathlib import Path
from threading import Thread

from .shared import Result

CLEANUP_PERIOD_SEC = 10


class AbstractResultCache(Thread):
    def __init__(self, expiration: float):
        self._expiration = expiration
        super().__init__(daemon=True)

    @abc.abstractmethod
    def register(self, num_inputs: int) -> str:
        pass

    @abc.abstractmethod
    def get_num_inputs(self, prediction_id: str) -> int:
        pass

    @abc.abstractmethod
    def set_log_path(self, input_ids: t.List[str], log_path: Path) -> None:
        pass

    @abc.abstractmethod
    def set_running(self, input_ids: t.List[str]) -> None:
        pass

    @abc.abstractmethod
    def set_success(
        self,
        input_ids: t.List[str],
        outputs: t.List[t.Dict],
        demo_outputs: t.List[t.Optional[t.Dict]],
    ) -> None:
        pass

    @abc.abstractmethod
    def set_failure(self, prediction_id: str, error_message: str) -> None:
        pass

    @abc.abstractmethod
    def get_result(self, prediction_id: str) -> Result:
        pass

    @abc.abstractmethod
    def wait_until_done(self, prediction_id: str, timeout: float) -> None:
        pass

    @abc.abstractmethod
    def remove(self, prediction_id: str) -> None:
        pass

    @abc.abstractmethod
    def cleanup(self) -> None:
        pass

    def run(self):
        while True:
            time.sleep(CLEANUP_PERIOD_SEC)
            self.cleanup()
