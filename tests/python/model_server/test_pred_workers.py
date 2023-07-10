import time
import typing as t
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from tungstenkit._internal.model_def_loader import create_model_def_loader
from tungstenkit._internal.model_server.config import MODE_TO_SETTING_MAPPING
from tungstenkit._internal.model_server.enums import ModelServerMode
from tungstenkit._internal.model_server.prediction_worker import PredictionWorker
from tungstenkit._internal.model_server.result_caches import Result

from ..dummy_model import DummyModel

BATCH_SIZE = 4


def _watch_prediction(
    worker: PredictionWorker, prediction_id: str, *, interval: float, timeout: t.Optional[float]
) -> t.List[Result]:
    timeout = timeout if timeout else 300.0
    start_time = time.monotonic()
    results = [worker.get_prediction_result(prediction_id)]
    last_result = results[0]
    while (
        time.monotonic() - start_time < timeout
        and last_result.status == "pending"
        or last_result.status == "running"
    ):
        results.append(worker.get_prediction_result(prediction_id))
        last_result = results[-1]
        if last_result.status == "success" or last_result.status == "failed":
            return results
        time.sleep(interval)

    raise TimeoutError


def _test_success(dummy_io_generator, worker: PredictionWorker):
    inputs, gts = dummy_io_generator(n=BATCH_SIZE)
    prediction_id = worker.create_prediction(inputs=inputs, is_demo=False)
    worker.wait_for_prediction(prediction_id=prediction_id)
    res = worker.get_prediction_result(prediction_id=prediction_id)
    assert res.outputs
    assert len(res.outputs) == len(gts)
    assert all(res.outputs[i] == gts[i] for i in range(len(gts)))


def _test_failure(dummy_io_generator, worker: PredictionWorker):
    with patch.object(DummyModel, "failure", True):
        inputs = dummy_io_generator(n=BATCH_SIZE, failure=True)[0]
        prediction_id = worker.create_prediction(inputs=inputs, is_demo=False)
        worker.wait_for_prediction(prediction_id=prediction_id)
        res = worker.get_prediction_result(prediction_id=prediction_id)
        assert res.status == "failed"
        assert res.error_message is not None
        assert res.error_message.startswith("Traceback")
        exc = DummyModel.exception()
        assert exc is not None
        for line in res.error_message.split("\n"):
            if line.startswith(exc.__class__.__name__):
                assert line == f"{exc.__class__.__name__}: {str(exc)}"
                return


def _test_logging(dummy_io_generator, worker: PredictionWorker):
    inputs = dummy_io_generator(n=BATCH_SIZE, delay=1.0, print_log=True)[0]
    prediction_id = worker.create_prediction(inputs=inputs, is_demo=True)
    results = _watch_prediction(worker, prediction_id, interval=0.1, timeout=5.0)
    log_while_running = False
    for res in results:
        if res.status == "running" and res.logs:
            log_while_running = True

    assert log_while_running
    assert results[-1].logs
    assert results[-1].logs.strip() == DummyModel.build_log(4)


def _test_dynamic_batching(dummy_io_generator, worker: PredictionWorker):
    inputs = dummy_io_generator(n=BATCH_SIZE, delay=0.5, print_log=True)[0]
    prediction_id = worker.create_prediction(inputs=inputs, is_demo=True)

    inputs = dummy_io_generator(n=BATCH_SIZE // 2, delay=0.1, print_log=True)[0]
    prediction_id = worker.create_prediction(inputs=inputs, is_demo=True)

    inputs = dummy_io_generator(n=BATCH_SIZE // 4, delay=0.1, print_log=True)[0]
    worker.create_prediction(inputs=inputs, is_demo=True)

    inputs = dummy_io_generator(n=BATCH_SIZE // 4, delay=0.1, print_log=True)[0]
    prediction_id = worker.create_prediction(inputs=inputs, is_demo=True)

    worker.wait_for_prediction(prediction_id)
    res = worker.get_prediction_result(prediction_id)
    assert res.logs
    assert res.logs.strip().startswith(DummyModel.build_log(BATCH_SIZE))

    # Check if inputs with different options are splitted
    inputs = dummy_io_generator(n=BATCH_SIZE, delay=0.5, print_log=True)[0]
    worker.create_prediction(inputs=inputs, is_demo=True)

    inputs = dummy_io_generator(n=BATCH_SIZE // 2, delay=0.1, print_log=True, option="option1")[0]
    worker.create_prediction(inputs=inputs, is_demo=True)

    inputs = dummy_io_generator(n=BATCH_SIZE // 2, delay=0.1, print_log=True, option="option2")[0]
    prediction_id = worker.create_prediction(inputs=inputs, is_demo=True)

    worker.wait_for_prediction(prediction_id)

    res = worker.get_prediction_result(prediction_id)
    assert res.logs
    assert res.logs.strip().startswith(DummyModel.build_log(BATCH_SIZE // 2))

    # Check if demo and non-demo inputs are splitted
    inputs = dummy_io_generator(n=BATCH_SIZE, delay=0.5, print_log=True)[0]
    worker.create_prediction(inputs=inputs, is_demo=True)

    inputs = dummy_io_generator(n=BATCH_SIZE // 2, delay=0.1)[0]
    worker.create_prediction(inputs=inputs, is_demo=False)

    inputs = dummy_io_generator(n=BATCH_SIZE // 2, delay=0.1, print_log=True)[0]
    prediction_id = worker.create_prediction(inputs=inputs, is_demo=True)

    worker.wait_for_prediction(prediction_id)

    res = worker.get_prediction_result(prediction_id)
    assert res.logs
    assert res.logs.strip().startswith(DummyModel.build_log(BATCH_SIZE // 2))


def _test_cancel_running_prediction(dummy_io_generator, worker: PredictionWorker):
    inputs = dummy_io_generator(n=BATCH_SIZE, delay=10.0, print_log=True)[0]
    prediction_id = worker.create_prediction(inputs=inputs, is_demo=True)

    with ThreadPoolExecutor(max_workers=1) as executor:
        worker.cancel_prediction(prediction_id=prediction_id)
        fut = executor.submit(worker.wait_for_prediction, prediction_id)
        fut.result(timeout=1.0)

    res = worker.get_prediction_result(prediction_id)

    assert res.status == "failed"
    assert res.error_message
    assert res.error_message.strip().endswith("Canceled")


def _test_cancel_queued_prediction(dummy_io_generator, worker: PredictionWorker):
    inputs = dummy_io_generator(n=BATCH_SIZE, delay=1.0, print_log=True)[0]
    worker.create_prediction(inputs=inputs, is_demo=True)

    inputs = dummy_io_generator(n=BATCH_SIZE, delay=1.0, print_log=True)[0]
    canceled_prediction_id = worker.create_prediction(inputs=inputs, is_demo=True)

    with ThreadPoolExecutor(max_workers=1) as executor:
        worker.cancel_prediction(prediction_id=canceled_prediction_id)
        fut = executor.submit(worker.wait_for_prediction, canceled_prediction_id)
        fut.result(1.0)

    res = worker.get_prediction_result(canceled_prediction_id)

    assert res.status == "failed"
    assert res.error_message
    assert res.error_message.strip().endswith("Canceled")


def _test_correctness(dummy_io_generator, worker: PredictionWorker):
    worker.start()
    worker.wait_for_setup()
    _test_success(dummy_io_generator, worker)
    _test_failure(dummy_io_generator, worker)
    _test_logging(dummy_io_generator, worker)
    _test_dynamic_batching(dummy_io_generator, worker)
    _test_cancel_running_prediction(dummy_io_generator, worker)
    _test_cancel_queued_prediction(dummy_io_generator, worker)


def _test_performance(dummy_io_generator, worker: PredictionWorker, max_latency: float):
    inputs = dummy_io_generator(n=1, delay=0.0)[0]

    history = []
    for _ in range(100):
        start_time = time.monotonic()
        prediction_id = worker.create_prediction(inputs=inputs, is_demo=False)
        worker.wait_for_prediction(prediction_id=prediction_id)
        worker.get_prediction_result(prediction_id=prediction_id)
        latency = time.monotonic() - start_time
        history.append(latency)

    assert sum(history) / len(history) < max_latency


def _test_worker(dummy_io_generator, mode: ModelServerMode, envvars: t.Dict):
    settings = MODE_TO_SETTING_MAPPING[mode](
        TUNGSTEN_MODEL_CLASS=DummyModel.__name__,
        TUNGSTEN_MODEL_MODULE=DummyModel.__module__,
        **envvars,
    )
    worker = PredictionWorker(
        create_model_def_loader(settings.TUNGSTEN_MODEL_MODULE, settings.TUNGSTEN_MODEL_CLASS),
        cache_config=settings.cache_config,
        storage_config=settings.storage_config,
        max_batch_size=BATCH_SIZE,
        prediction_timeout=10.0,
        setup_timeout=10.0,
    )
    _test_correctness(dummy_io_generator, worker)
    _test_performance(dummy_io_generator, worker, 0.05)


def test_standalone_worker(dummy_io_generator):
    mode = ModelServerMode.STANDALONE
    return _test_worker(dummy_io_generator, mode=mode, envvars=dict())
