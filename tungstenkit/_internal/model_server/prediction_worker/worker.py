import os
import signal
import tempfile
import time
import traceback
import typing as t
from pathlib import Path
from threading import Event, Thread

from loguru import logger

from tungstenkit._internal.io import BaseIO, File
from tungstenkit._internal.model_def_loader import ModelDefLoader
from tungstenkit._internal.utils.json import apply_to_jsonable

from .. import server_exceptions
from ..config import BaseCacheConfig, BaseStorageConfig
from ..event_buses import create_event_bus
from ..file_uploaders import create_file_uploader
from ..ids import check_input_in_prediction, get_prediction_id_from_input_id
from ..input_queues import create_input_queue
from ..result_caches import Result, create_result_cache
from .executor import Executor, PredictionFailure, PredictionSuccess


# TODO Upload after prediction done if requested
# TODO Split this to PredictionService and WorkerThread
class PredictionWorker(Thread):
    """
    Worker for running model setup and predictions.

    A worker communicates with five components:
    - subprocess: a child process to run predictions
    - input queue: a queue to push inputs and pop a batch
    - result cache: a cache containing 'predictions'
    - event bus: propagates and listens on events
    - file uploader: upload files in outputs
    """

    def __init__(
        self,
        model_def_loader: ModelDefLoader,
        cache_config: BaseCacheConfig,
        storage_config: BaseStorageConfig,
        max_batch_size: int,
        setup_timeout: float,
        prediction_timeout: float,
    ):
        self._setup_timeout = setup_timeout
        self._prediction_timeout = prediction_timeout

        self._max_batch_size = max_batch_size
        self._running_input_ids: t.List[str] = []
        self._setup_done: Event = Event()
        self._is_setup_succeeded = False

        self._input_queue = create_input_queue(cache_config)
        self._result_cache = create_result_cache(cache_config)
        self._event_bus = create_event_bus(cache_config)
        self._executor = Executor(
            model_def_loader,
            setup_timeout=setup_timeout,
            prediction_timeout=prediction_timeout,
        )
        self._file_uploader = create_file_uploader(storage_config)
        super().__init__(daemon=True, name="prediction-worker")

    @property
    def max_batch_size(self) -> int:
        return self._max_batch_size

    def wait_for_setup(self):
        """Wait until setup in the subprocess is done"""
        self._setup_done.wait()
        if not self._is_setup_succeeded:
            raise server_exceptions.SetupFailed

    def create_prediction(self, inputs: t.List[BaseIO], is_demo: bool) -> str:
        """Create a prediction by pushing inputs to the input queue"""
        prediction_id = self._result_cache.register(num_inputs=len(inputs))
        self._input_queue.push(
            prediction_id=prediction_id,
            inputs=inputs,
            is_demo=is_demo,
        )
        return prediction_id

    def wait_for_prediction(self, prediction_id: str) -> None:
        """Wait until the prediction result is ready in the result cache"""
        self._result_cache.wait_until_done(
            prediction_id=prediction_id, timeout=self._prediction_timeout
        )

    def cancel_prediction(self, prediction_id: str, failure_message: str = "Canceled") -> None:
        """
        Cancel the prediction request
        1. Remove the inputs in the input queue
        2. Propagate the cancelation event through the event bus
            to cancel running predictions
        3. Set the prediction result in the result cache as failure
        """
        result = self._result_cache.get_result(prediction_id)
        status = result.status
        try:
            if status == "failed" or status == "success":
                return

            removed_input_ids = self._input_queue.remove(prediction_id=prediction_id)
            num_inputs = self._result_cache.get_num_inputs(prediction_id)
            if len(removed_input_ids) == num_inputs:
                return

            start_time = time.monotonic()
            while status == "pending" and time.monotonic() - start_time < 60.0:
                # For the case when server poped inputs from input queue,
                # but didn't started prediction yet
                time.sleep(0.05)
                status = self._result_cache.get_result(prediction_id).status
            if status == "running":
                self._event_bus.post(event_type="cancel", payload=prediction_id)
        finally:
            if status == "running" or status == "pending":
                self._result_cache.set_failure(prediction_id, failure_message)

    def get_prediction_result(self, prediction_id: str) -> Result:
        """Get the prediction result from the result cache"""
        return self._result_cache.get_result(prediction_id=prediction_id)

    def remove_prediction_result(self, prediction_id: str):
        """Remove the prediction result in the result cache"""
        return self._result_cache.remove(prediction_id=prediction_id)

    def run(self):
        """Start child threads and run predictions"""
        try:
            self._event_bus.add_handler("cancel", self._handle_cancel_event)
            self._result_cache.start()
            self._event_bus.start()
            self._executor.start()
            self._is_setup_succeeded = self._executor.setup()
        finally:
            self._setup_done.set()

        if not self._is_setup_succeeded:
            return

        try:
            self._predict_forever()
        finally:
            # Unexpected termination. Terminate both this and main thread.
            self._executor.terminate()
            os.kill(os.getpid(), signal.SIGTERM)

    def _predict_forever(self):
        """
        Loop for running predictions
        1. Pop a batch from the input queue
        2. Run a prediction
        3. Save the result
        """
        while True:
            result = None
            logger.info("Getting inputs from the input queue")
            batch = self._input_queue.pop(self.max_batch_size)
            input_ids = batch.input_ids
            try:
                logger.info("Starting a batch prediction")
                logger.debug("Batch: " + str(batch))
                result = self._do_prediction(
                    input_ids=input_ids,
                    inputs=batch.data,
                    is_demo=batch.is_demo,
                )
            finally:
                logger.info("Saving results")
                self._save_result(
                    input_ids=input_ids,
                    result=PredictionFailure(err_msg=traceback.format_exc())
                    if result is None
                    else result,
                )

    def _do_prediction(
        self, input_ids: t.List[str], inputs: t.List[t.Dict], is_demo: bool
    ) -> t.Union[PredictionSuccess, PredictionFailure]:
        """Request a prediction to the subprocess and get the result"""
        self._running_input_ids = input_ids

        if is_demo:
            fd, name = tempfile.mkstemp(prefix="prediction-log-")
            log_path = Path(name)
            os.close(fd)
            self._result_cache.set_log_path(input_ids=input_ids, log_path=log_path)
        else:
            log_path = None

        self._result_cache.set_running(input_ids=input_ids)

        result = self._executor.predict(inputs=inputs, is_demo=is_demo, log_path=log_path)

        if isinstance(result, PredictionFailure):
            logger.warning(f"Prediction on {input_ids} was failed:\n{result.err_msg}")
        else:
            logger.info(f"Prediction on {input_ids} was successful")
            logger.debug(f"Result: {result}")

        self._running_input_ids = []
        return result

    def _save_result(
        self,
        input_ids: t.List[str],
        result: t.Union[PredictionSuccess, PredictionFailure],
    ) -> None:
        """Save the result to the result cache"""
        pred_ids = set(get_prediction_id_from_input_id(input_id) for input_id in input_ids)
        if isinstance(result, PredictionSuccess):
            try:
                uploaded = self._file_uploader.upload(result.files)
                result.outputs, result.demo_outputs = _replace_files_in_outputs(
                    [result.outputs, result.demo_outputs], result.files, uploaded
                )
                self._result_cache.set_success(
                    input_ids=input_ids, outputs=result.outputs, demo_outputs=result.demo_outputs
                )
            except Exception:
                result = PredictionFailure(err_msg=traceback.format_exc())

        if isinstance(result, PredictionFailure):
            for pred_id in pred_ids:
                self._input_queue.remove(pred_id)
                self._result_cache.set_failure(
                    pred_id,
                    result.err_msg,
                )

    def _handle_cancel_event(self, pred_id: t.Optional[str]):
        """Handle cancel event. This is called by the event bus."""
        if (
            pred_id
            and self._running_input_ids
            and all(
                check_input_in_prediction(input_id=input_id, prediction_id=pred_id)
                for input_id in self._running_input_ids
            )
        ):
            self._executor.cancel()


def _replace_files_in_outputs(
    serialized_outputs: t.Any, targets: t.List[File], updates: t.List[File]
):
    def replace(value):
        if isinstance(value, str):
            for i, target in enumerate(targets):
                if str(target.__root__) == value:
                    return str(updates[i].__root__)
        return value

    return apply_to_jsonable(
        jsonable=serialized_outputs,
        cond=lambda _: True,
        fn=replace,
    )
