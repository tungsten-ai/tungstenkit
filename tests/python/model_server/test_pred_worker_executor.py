import tempfile
import time
from contextlib import contextmanager, redirect_stdout
from io import StringIO
from pathlib import Path
from threading import Thread
from unittest.mock import patch

from fastapi.encoders import jsonable_encoder

from tungstenkit._internal.model_def_loader import create_model_def_loader
from tungstenkit._internal.model_server.prediction_worker.executor import (
    Executor,
    PredictionFailure,
    PredictionSuccess,
)

from .. import dummy_model
from . import setup_failure_model


def test_executor_setup():
    buf = StringIO()
    with redirect_stdout(buf):
        executor = Executor(
            create_model_def_loader(
                setup_failure_model.__name__, setup_failure_model.SetupFailureModel.__name__
            ),
            setup_timeout=5.0,
            prediction_timeout=1.0,
        )
        with _start_executor(executor) as executor:
            assert not executor.setup()
            gt_err_msg = setup_failure_model.SetupFailureModel.exception().args[0]
            buf.getvalue().strip().endswith(gt_err_msg)


def test_executor_predictions(dummy_io_generator, tmp_path):
    with patch("tempfile.tempdir", str(tmp_path)):
        executor = Executor(
            create_model_def_loader(dummy_model.__name__, dummy_model.DummyModel.__name__),
            setup_timeout=10.0,
            prediction_timeout=5.0,
        )
        with _start_executor(executor) as exec:
            exec.setup()

            # plain predictions
            inputs, gts = dummy_io_generator(n=8, delay=0.1, print_log=False, failure=False)
            result = exec.predict(inputs=jsonable_encoder(inputs), is_demo=False, log_path=None)
            assert isinstance(result, PredictionSuccess)
            assert all(
                output == gt and demo_output is None
                for output, demo_output, gt in zip(result.outputs, result.demo_outputs, gts)
            )

            # demo predictions
            with tempfile.NamedTemporaryFile("r") as tmp_file:
                inputs, gts = dummy_io_generator(n=8, delay=0.1, print_log=True, failure=False)
                result = exec.predict(
                    inputs=jsonable_encoder(inputs), is_demo=True, log_path=Path(tmp_file.name)
                )
                assert isinstance(result, PredictionSuccess)
                assert all(
                    output == gt and demo_output == gt
                    for output, demo_output, gt in zip(result.outputs, result.demo_outputs, gts)
                )
                assert tmp_file.read().strip() == dummy_model.DummyModel.build_log(8)

            # predictions to be failed because of user error
            with patch.object(dummy_model.DummyModel, "failure", True):
                inputs, gts = dummy_io_generator(n=8, delay=0.1, print_log=False, failure=True)
                result = exec.predict(
                    inputs=jsonable_encoder(inputs), is_demo=False, log_path=None
                )
                assert isinstance(result, PredictionFailure)
                assert result.err_msg.strip().endswith(dummy_model.DummyModel.exception().args[0])

            # predictions to be failed because of timeout
            inputs, gts = dummy_io_generator(n=8, delay=10, print_log=False, failure=False)
            result = exec.predict(inputs=jsonable_encoder(inputs), is_demo=False, log_path=None)
            assert isinstance(result, PredictionFailure)
            assert result.err_msg.strip().endswith("Timeout")

            # cancel predictions
            inputs, gts = dummy_io_generator(n=8, delay=10, print_log=False, failure=False)
            Thread(target=_cancel_executor, args=(1, exec), daemon=True).start()
            result = exec.predict(inputs=jsonable_encoder(inputs), is_demo=False, log_path=None)
            assert isinstance(result, PredictionFailure)
            assert result.err_msg.strip().endswith("Canceled")


def _cancel_executor(after: float, executor: Executor):
    time.sleep(after)
    executor.cancel()


@contextmanager
def _start_executor(executor: Executor):
    try:
        executor.start()
        yield executor
    finally:
        executor.terminate()
