import os
import time
import typing as t
from pathlib import Path
from threading import Event
from uuid import uuid4

import attrs
from fasteners import ReaderWriterLock
from loguru import logger

from .. import server_exceptions
from ..ids import get_input_ids_from_prediction_id, get_prediction_id_from_input_id
from .abstract_result_cache import AbstractResultCache
from .shared import PredictionStatus, Result


def _get_curr_time() -> float:
    return time.monotonic()


@attrs.define(kw_only=True)
class UnitResult:
    status: PredictionStatus = attrs.field(default="pending")
    log_id: t.Optional[str] = attrs.field(default=None)
    output: t.Optional[t.Dict] = attrs.field(default=None)
    demo_output: t.Optional[t.Dict] = attrs.field(default=None)
    error_message: t.Optional[str] = attrs.field(default=None)
    done_event: Event = attrs.field(factory=Event)
    done_at: t.Optional[float] = attrs.field(default=None)

    def _set_running(self):
        if self.status == "success" or self.status == "failure":
            return

        self.status = "running"

    def _set_output(
        self,
        output: t.Dict,
        demo_output: t.Optional[t.Dict] = None,
    ):
        if self.status == "success" or self.status == "failure":
            return

        self.output = output
        self.demo_output = demo_output
        self.status = "success"
        self.done_at = _get_curr_time()
        self.done_event.set()

    def _set_error_message(self, error_message: str):
        if self.status == "success" or self.status == "failure":
            return

        self.status = "failure"
        self.error_message = error_message
        self.done_at = _get_curr_time()
        self.done_event.set()


def _get_status_from_unit_results(
    unit_results: t.List[UnitResult],
) -> PredictionStatus:
    running_or_success_any = False
    success_all = True
    for r in unit_results:
        if r.status == "failure":
            return "failure"

        success = r.status == "success"
        running = r.status == "running"
        success_all &= success
        running_or_success_any |= success or running
    if success_all:
        return "success"
    if running_or_success_any:
        return "running"
    return "pending"


def _get_error_message_from_unit_results(
    unit_results: t.List[UnitResult],
):
    for r in unit_results:
        if r.error_message is not None:
            return r.error_message


class LocalResultCache(AbstractResultCache):
    def __init__(self, expiration: float):
        self._map_pred_id_to_inp_ids: t.Dict[str, t.List[str]] = dict()
        self._results: t.Dict[str, UnitResult] = dict()
        self._logs: t.Dict[str, Path] = dict()
        self._last_log_num = 0
        self._locks: t.Dict[str, ReaderWriterLock] = dict()
        AbstractResultCache.__init__(self, expiration=expiration)

    def register(self, num_inputs: int) -> str:
        prediction_id = uuid4().hex
        input_ids = get_input_ids_from_prediction_id(prediction_id, num_inputs)
        self._map_pred_id_to_inp_ids[prediction_id] = input_ids

        for input_id in input_ids:
            if input_id in self._results:
                raise server_exceptions.InputIDAlreadyExists(prediction_id)

            self._results[input_id] = UnitResult()
            self._locks[prediction_id] = ReaderWriterLock()

        return prediction_id

    def set_log_path(self, input_ids: t.List[str], log_path: Path) -> None:
        self._last_log_num += 1
        log_id = str(self._last_log_num)
        for input_id in input_ids:
            if input_id not in self._results.keys():
                raise server_exceptions.InputIDNotFound(input_id)

            self._results[input_id].log_id = log_id

        self._logs[log_id] = log_path

        return None

    def get_num_inputs(self, prediction_id: str) -> int:
        if prediction_id not in self._map_pred_id_to_inp_ids.keys():
            raise server_exceptions.PredictionIDNotFound(prediction_id)

        return len(self._map_pred_id_to_inp_ids[prediction_id])

    def set_running(self, input_ids: t.List[str]) -> None:
        for input_id in input_ids:
            if input_id not in self._results.keys():
                raise server_exceptions.InputIDNotFound(input_id)

            pred_id = get_prediction_id_from_input_id(input_id)
            with self._locks[pred_id].write_lock():
                if self._results[input_id].status == "pending":
                    self._results[input_id]._set_running()

        return None

    def set_success(
        self,
        input_ids: t.List[str],
        outputs: t.List[t.Dict],
        demo_outputs: t.List[t.Optional[t.Dict]],
    ) -> None:
        for input_id, output, demo_output in zip(input_ids, outputs, demo_outputs):
            if input_id not in self._results.keys():
                raise server_exceptions.InputIDNotFound(input_id)

            pred_id = get_prediction_id_from_input_id(input_id)
            with self._locks[pred_id].write_lock():
                if (
                    self._results[input_id].status == "pending"
                    or self._results[input_id].status == "running"
                ):
                    self._results[input_id]._set_output(output, demo_output)

        return None

    def set_failure(self, prediction_id: str, error_message: str) -> None:
        with self._locks[prediction_id].write_lock():
            for input_id in get_input_ids_from_prediction_id(
                prediction_id, self.get_num_inputs(prediction_id)
            ):
                if (
                    self._results[input_id].status == "pending"
                    or self._results[input_id].status == "running"
                ):
                    self._results[input_id]._set_error_message(error_message)

        return None

    def get_result(self, prediction_id: str) -> Result:
        if prediction_id not in self._locks.keys():
            raise server_exceptions.PredictionIDNotFound(prediction_id)

        with self._locks[prediction_id].read_lock():
            if prediction_id not in self._map_pred_id_to_inp_ids.keys():
                raise server_exceptions.PredictionIDNotFound(prediction_id)

            unit_results: t.List[UnitResult] = []
            for input_id in self._map_pred_id_to_inp_ids[prediction_id]:
                if input_id not in self._results.keys():
                    raise server_exceptions.InputIDNotFound(input_id)

                unit_results.append(self._results[input_id])

            status = _get_status_from_unit_results(unit_results)
            log = None
            if any(r.log_id for r in unit_results):
                log = self._get_log_str_from_unit_results(unit_results)

        if status == "failure":
            error_message = _get_error_message_from_unit_results(unit_results)
            return Result(status=status, error_message=error_message, logs=log)

        if status == "success":
            outputs = [r.output for r in unit_results]
            _demo_outputs = [r.demo_output for r in unit_results]
            demo_outputs = _demo_outputs if all(o is not None for o in _demo_outputs) else None

            return Result(
                status=status, outputs=outputs, logs=log, demo_outputs=demo_outputs  # type: ignore
            )

        return Result(status=status, logs=log)

    def wait_until_done(self, prediction_id: str, timeout: float) -> None:
        if prediction_id not in self._locks.keys():
            raise server_exceptions.PredictionIDNotFound(prediction_id)

        with self._locks[prediction_id].read_lock():
            input_ids = self._map_pred_id_to_inp_ids[prediction_id]
            unit_results = [self._results[input_id] for input_id in input_ids]
            done_events = [r.done_event for r in unit_results]

        success = True
        for event in done_events:
            success &= event.wait(timeout=timeout)
        if not success:
            raise server_exceptions.PredictionTimeout
        return None

    def cleanup(self) -> None:
        curr_t = _get_curr_time()
        predictions_to_be_deleted = []
        for prediction_id, input_ids in self._map_pred_id_to_inp_ids.items():
            if any(
                isinstance(self._results[input_id].done_at, float)
                and curr_t - self._results[input_id].done_at > self._expiration  # type: ignore
                for input_id in input_ids
            ):
                predictions_to_be_deleted.append(prediction_id)

        logger.debug(f"Cleanup predictions: {predictions_to_be_deleted}")
        for prediction_id in predictions_to_be_deleted:
            self.remove(prediction_id)

        logger.debug(f"Remaining results: {', '.join([str(key) for key in self._results.keys()])}")

        logs_to_be_deleted = []
        for log_id in self._logs.keys():
            if not any(result.log_id == log_id for result in self._results.values()):
                logs_to_be_deleted.append(log_id)
        logger.debug(f"Cleanup logs: {logs_to_be_deleted}")
        for log_id in logs_to_be_deleted:
            if self._logs[log_id].exists():
                os.remove(self._logs[log_id])
            del self._logs[log_id]
        logger.debug(f"Remaining logs: {', '.join([str(key) for key in self._logs.keys()])}")

    def remove(self, prediction_id: str) -> None:
        if prediction_id not in self._locks.keys():
            raise server_exceptions.PredictionIDNotFound(prediction_id)

        with self._locks[prediction_id].write_lock():
            input_ids = self._map_pred_id_to_inp_ids[prediction_id]
            del self._map_pred_id_to_inp_ids[prediction_id]
            for input_id in input_ids:
                del self._results[input_id]

        del self._locks[prediction_id]

        return None

    def _get_log_str_from_unit_results(
        self,
        unit_results: t.List[UnitResult],
    ) -> t.Optional[str]:
        log_id_set: t.Set[str] = set(
            result.log_id for result in unit_results if result.log_id is not None
        )
        if len(log_id_set) == 0:
            return None

        log_str = ""
        for idx, log_id in enumerate(sorted(log_id_set)):
            with open(self._logs[log_id], "r") as f:
                log_str += f.read()
                if idx != len(log_id_set) - 1:
                    log_str += "\n"
        return log_str
