import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from tungstenkit._internal.model_server.ids import get_input_ids_from_prediction_id
from tungstenkit._internal.model_server.result_caches import AbstractResultCache
from tungstenkit._internal.model_server.server_exceptions import (
    PredictionIDNotFound,
    PredictionTimeout,
)


def _test_success(dummy_io_generator, result_cache: AbstractResultCache):
    with tempfile.NamedTemporaryFile(mode="w", buffering=1) as first_log:
        with tempfile.NamedTemporaryFile(mode="w", buffering=1) as second_log:
            outputs = dummy_io_generator(n=2)[1]

            prediction_id = result_cache.register(num_inputs=2)
            input_ids = get_input_ids_from_prediction_id(prediction_id, 2)
            result = result_cache.get_result(prediction_id=prediction_id)
            assert result.status == "pending"

            result_cache.set_log_path(input_ids=input_ids[:1], log_path=Path(first_log.name))
            first_log.write("first log\n")
            result_cache.set_running(input_ids=input_ids[:1])
            result = result_cache.get_result(prediction_id=prediction_id)
            assert result.status == "running"
            assert result.logs == "first log\n"

            result_cache.set_success(
                input_ids=input_ids[:1], outputs=outputs[:1], demo_outputs=outputs[:1]
            )
            result = result_cache.get_result(prediction_id=prediction_id)
            assert result.status == "running"

            result_cache.set_log_path(input_ids=input_ids[1:], log_path=Path(second_log.name))
            second_log.write("second log\n")
            result_cache.set_running(input_ids=input_ids[1:])
            result = result_cache.get_result(prediction_id=prediction_id)
            assert result.status == "running"
            assert result.logs == "first log\n\nsecond log\n"

            result_cache.set_success(
                input_ids=input_ids[1:], outputs=outputs[1:], demo_outputs=outputs[:1]
            )
            result = result_cache.get_result(prediction_id=prediction_id)
            assert result.status == "success"
            assert result.logs == "first log\n\nsecond log\n"
            assert result.outputs is not None
            assert len(outputs) == len(result.outputs)
            assert all(result.outputs[i] == outputs[i] for i in range(len(outputs)))

    result_cache.remove(prediction_id=prediction_id)
    try:
        result_cache.get_result(prediction_id=prediction_id)
        raise ValueError()
    except PredictionIDNotFound:
        pass


def _test_wait(dummy_io_generator, result_cache: AbstractResultCache):
    outputs = dummy_io_generator(n=2)[1]
    prediction_id = result_cache.register(num_inputs=2)
    input_ids = get_input_ids_from_prediction_id(prediction_id, 2)
    with ThreadPoolExecutor(max_workers=2) as executor:
        wait_long = executor.submit(result_cache.wait_until_done, prediction_id, 10.0)
        wait_short = executor.submit(result_cache.wait_until_done, prediction_id, 0.1)

        result_cache.set_running(input_ids=input_ids[:1])
        assert not wait_long.done()
        result_cache.set_success(
            input_ids=input_ids[:1], outputs=outputs[:1], demo_outputs=outputs[:1]
        )
        assert not wait_long.done()
        result_cache.set_running(input_ids=input_ids[1:])
        assert not wait_long.done()
        time.sleep(0.5)
        result_cache.set_success(
            input_ids=input_ids[1:], outputs=outputs[1:], demo_outputs=outputs[1:]
        )
        time.sleep(0.5)
        assert wait_long.done()
        try:
            wait_short.result()
            raise ValueError
        except PredictionTimeout:
            pass

        wait_long.result()
        result = result_cache.get_result(prediction_id)
        assert result.status == "success"
        assert result.outputs is not None
        assert len(outputs) == len(result.outputs)
        assert all(result.outputs[i] == outputs[i] for i in range(len(outputs)))


def _test_failure(dummy_io_generator, result_cache: AbstractResultCache):
    outputs = dummy_io_generator(n=2)[1]
    prediction_id = result_cache.register(num_inputs=2)
    input_ids = get_input_ids_from_prediction_id(prediction_id, 2)
    result = result_cache.get_result(prediction_id=prediction_id)
    assert result.status == "pending"

    result_cache.set_running(input_ids=input_ids[:1])
    result_cache.set_success(
        input_ids=input_ids[:1], outputs=outputs[:1], demo_outputs=outputs[:1]
    )
    result = result_cache.get_result(prediction_id=prediction_id)
    assert result.status == "running"

    result_cache.set_running(input_ids=input_ids[1:])
    result_cache.set_failure(prediction_id=prediction_id, error_message="error")
    result = result_cache.get_result(prediction_id=prediction_id)
    assert result.status == "failure"
    assert result.error_message == "error"
    assert result.outputs is None

    return prediction_id


def _test_cleanup(to_be_removed: str, cache: AbstractResultCache):
    time.sleep(0.5)
    cache.cleanup()
    try:
        cache.get_result(prediction_id=to_be_removed)
        raise ValueError()
    except PredictionIDNotFound:
        pass


def test_result_cache(dummy_io_generator):
    assert len(AbstractResultCache.__subclasses__()) > 0
    for c in AbstractResultCache.__subclasses__():
        cache = c(0.5)
        _test_success(dummy_io_generator, cache)
        _test_wait(dummy_io_generator, cache)
        to_be_removed = _test_failure(dummy_io_generator, cache)
        _test_cleanup(to_be_removed, cache)
