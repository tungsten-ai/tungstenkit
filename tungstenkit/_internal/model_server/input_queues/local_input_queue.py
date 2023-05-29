import time
import typing as t
from threading import Lock

import attrs
from fastapi.encoders import jsonable_encoder
from loguru import logger

from tungstenkit._internal.io import BaseIO

from ..ids import check_input_in_prediction, get_input_ids_from_prediction_id
from .abstract_input_queue import AbstractInputQueue
from .shared import Batch


@attrs.frozen(eq=True)
class Input:
    input_id: str = attrs.field(eq=True)
    data: dict = attrs.field(eq=False)
    hash_for_batching: str = attrs.field(eq=False)
    demo: bool = attrs.field(eq=False)


class LocalInputQueue(AbstractInputQueue):
    def __init__(self) -> None:
        super().__init__()
        self._list: t.List[Input] = list()
        self._lock: Lock = Lock()

    def push(
        self,
        prediction_id: str,
        inputs: t.List[BaseIO],
        is_demo: bool,
    ) -> t.List[str]:
        input_ids = get_input_ids_from_prediction_id(prediction_id, len(inputs))
        self._list.extend(
            Input(
                input_id=input_id,
                data=jsonable_encoder(inp),
                hash_for_batching=inp._hash_for_batching(),
                demo=is_demo,
            )
            for input_id, inp in zip(input_ids, inputs)
        )

        logger.debug(f"Pushed {len(inputs)} inputs of prediction {prediction_id} to input queue")
        return input_ids

    def pop(self, max_batch_size: int, timeout: t.Optional[float] = None) -> Batch:
        assert max_batch_size > 0
        inputs: t.List[Input] = []
        if timeout:
            start_time = time.monotonic()

        while True:
            if timeout and time.monotonic() - start_time > timeout:
                raise TimeoutError
            try:
                inputs.append(self._list.pop(0))
                is_demo = inputs[0].demo
                hash_for_batching = inputs[0].hash_for_batching
                break
            except IndexError:
                time.sleep(0.005)

        with self._lock:
            i = 0
            while len(inputs) < max_batch_size and i < len(self._list):
                if (
                    self._list[i].hash_for_batching == hash_for_batching
                    and self._list[i].demo == is_demo
                ):
                    inputs.append(self._list.pop(i))
                else:
                    i += 1

        return Batch(
            input_ids=[inp.input_id for inp in inputs],
            data=[inp.data for inp in inputs],
            is_demo=is_demo,
        )

    def remove(self, prediction_id: str) -> t.List[str]:
        with self._lock:
            to_be_removed: t.List[Input] = []
            for inp in self._list:
                if check_input_in_prediction(input_id=inp.input_id, prediction_id=prediction_id):
                    to_be_removed.append(inp)

            removed: t.List[Input] = []
        
            for inp in to_be_removed:
                try:
                    self._list.remove(inp)
                    removed.append(inp)
                    logger.debug(f"Input {inp.input_id} was removed from input queue")
                except ValueError:
                    continue

        return [r.input_id for r in removed]
