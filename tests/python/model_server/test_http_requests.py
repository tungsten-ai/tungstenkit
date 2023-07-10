import time
from typing import List, Type, TypeVar
from urllib.parse import urljoin

import pytest
import requests
from fastapi.encoders import jsonable_encoder

from tungstenkit._internal.model_server.schema import (
    DemoResponse,
    PredictionID,
    PredictionRequest,
    PredictionResponse,
)

from ..dummy_model import DummyInput, DummyModel, DummyOutput
from .fixtures import ModelServer

T = TypeVar("T", bound=PredictionResponse)

DummyModelPredictionRequest = PredictionRequest.with_type(DummyInput)
DummyModelPredictionResponse = PredictionResponse.with_type(DummyOutput)
DummyModelDemoResponse = DemoResponse.with_type(DummyOutput)


@pytest.mark.timeout(10)
def test_standalone_server_endpoints(dummy_io_generator, standalone_model_server):
    _test_endpoints(dummy_io_generator, standalone_model_server)


@pytest.mark.timeout(10)
def test_file_tunnel_server_endpoints(dummy_io_generator, file_tunnel_model_server):
    _test_endpoints(dummy_io_generator, file_tunnel_model_server)


def _test_endpoints(dummy_io_generator, server: ModelServer):
    _test_predict(dummy_io_generator, server)
    _test_predict_async(dummy_io_generator, server)
    _test_demo(dummy_io_generator, server)


def _test_predict(dummy_io_generator, server: ModelServer):
    """Test synchronous prediction endpoint"""

    def _predict(inputs) -> PredictionResponse:
        raw_resp = _create_pred(inputs=inputs, server_url=server.url, endpoint="/predict")
        resp = DummyModelPredictionResponse.parse_raw(raw_resp.text)
        return resp

    # Success
    inputs, gts = dummy_io_generator(n=4, structure_gts=True)
    resp = _predict(inputs)
    assert resp.status == "success"
    assert resp.outputs == gts

    # Failure
    inputs, gts = dummy_io_generator(n=4, structure_gts=True, failure=True)
    resp = _predict(inputs)
    assert resp.status == "failed"
    assert resp.outputs is None
    assert resp.error_message


def _test_predict_async(dummy_io_generator, server: ModelServer):
    """Test asynchronous prediction endpoint"""

    endpoint = "/predict_async"

    def create_pred(inputs) -> str:
        raw_resp = _create_pred(inputs, server.url, endpoint)
        resp = PredictionID.parse_raw(raw_resp.text)
        return resp.prediction_id

    def wait_pred(prediction_id: str):
        return _wait_pred(prediction_id, server.url, endpoint, PredictionResponse)

    def cancel_pred(prediction_id: str):
        return _cancel_pred(prediction_id, server.url, endpoint)

    # Success
    inputs, gts = dummy_io_generator(n=4, structure_gts=True)
    prediction_id = create_pred(inputs)
    resps = wait_pred(prediction_id)
    assert resps[-1].status == "success"
    assert resps[-1].outputs == gts

    # Failure
    inputs, gts = dummy_io_generator(n=4, structure_gts=True, failure=True)
    prediction_id = create_pred(inputs)
    resps = wait_pred(prediction_id)
    assert resps[-1].status == "failed"
    assert resps[-1].outputs is None
    assert resps[-1].error_message

    # Cancelation
    inputs, gts = dummy_io_generator(n=4, delay=10, structure_gts=True)
    prediction_id = create_pred(inputs)
    cancel_pred(prediction_id)
    resps = wait_pred(prediction_id)
    assert resps[-1].status == "failed"
    assert resps[-1].outputs is None
    assert resps[-1].error_message
    inputs, gts = dummy_io_generator(n=4, structure_gts=True)
    prediction_id = create_pred(inputs)
    resps = wait_pred(prediction_id)
    assert resps[-1].status == "success"
    assert resps[-1].outputs == gts


def _test_demo(dummy_io_generator, server: ModelServer):
    """Test demo endpoint"""

    endpoint = "/demo"

    def create_pred(inputs) -> str:
        raw_resp = _create_pred(inputs, server.url, endpoint)
        resp = PredictionID.parse_raw(raw_resp.text)
        return resp.prediction_id

    def wait_pred(prediction_id: str):
        return _wait_pred(prediction_id, server.url, endpoint, DemoResponse)

    def cancel_pred(prediction_id: str):
        return _cancel_pred(prediction_id, server.url, endpoint)

    # Success
    inputs, gts = dummy_io_generator(n=4, delay=1, structure_gts=True, print_log=True)
    prediction_id = create_pred(inputs)
    resps = wait_pred(prediction_id)
    assert resps[-1].status == "success"
    assert resps[-1].outputs == gts
    assert resps[-1].demo_outputs == jsonable_encoder(gts)
    assert any(
        resp.status == "running" and resp.logs.strip() == DummyModel.build_log(4) for resp in resps
    )

    # Failure
    inputs, gts = dummy_io_generator(
        n=4, delay=1, structure_gts=True, failure=True, print_log=True
    )
    prediction_id = create_pred(inputs)
    resps = wait_pred(prediction_id)
    assert resps[-1].status == "failed"
    assert resps[-1].outputs is None
    assert resps[-1].error_message
    assert any(
        resp.status == "running" and resp.logs.strip() == DummyModel.build_log(4) for resp in resps
    )

    # Cancelation
    inputs, gts = dummy_io_generator(n=4, delay=10, structure_gts=True, print_log=True)
    prediction_id = create_pred(inputs)
    cancel_pred(prediction_id)
    resps = wait_pred(prediction_id)
    assert resps[-1].status == "failed"
    assert resps[-1].outputs is None
    assert resps[-1].error_message
    inputs, gts = dummy_io_generator(n=4, delay=1, structure_gts=True, print_log=True)
    prediction_id = create_pred(inputs)
    resps = wait_pred(prediction_id)
    assert resps[-1].status == "success"
    assert resps[-1].outputs == gts
    assert resps[-1].demo_outputs == jsonable_encoder(gts)
    assert any(
        resp.status == "running" and resp.logs.strip() == DummyModel.build_log(4) for resp in resps
    )


def _create_pred(inputs, server_url: str, endpoint: str) -> requests.Response:
    req = DummyModelPredictionRequest(__root__=inputs)
    raw_resp = requests.post(urljoin(server_url, endpoint), json=jsonable_encoder(req), timeout=5)
    raw_resp.raise_for_status()
    return raw_resp


def _wait_pred(
    prediction_id: str, server_url: str, endpoint: str, base_response_model: Type[T]
) -> List[T]:
    responses: List[T] = []
    while True:
        url = urljoin(server_url, f"{endpoint}/{prediction_id}")
        raw_resp = requests.get(url, timeout=5)
        raw_resp.raise_for_status()
        if base_response_model == PredictionResponse:
            resp = DummyModelPredictionResponse.parse_raw(raw_resp.text)
        elif base_response_model == DemoResponse:
            resp = DummyModelDemoResponse.parse_raw(raw_resp.text)
        else:
            raise NotImplementedError
        responses.append(resp)  # type: ignore
        if resp.status == "success" or resp.status == "failed":
            break
        time.sleep(0.05)
    return responses


def _cancel_pred(prediction_id: str, server_url: str, endpoint: str):
    url = urljoin(server_url, f"{endpoint}/{prediction_id}/cancel")
    resp = requests.post(url, timeout=5)
    resp.raise_for_status()
