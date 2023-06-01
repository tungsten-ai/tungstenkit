import time

import requests
from furl import furl

from tungstenkit._internal import storables
from tungstenkit._internal.demo_server import schemas


def test_get_model_metadata(demo_server_base_url: str, dummy_model_data: storables.ModelData):
    f = furl(demo_server_base_url)
    f.path = f.path / "metadata"
    resp = requests.get(f.url)
    resp.raise_for_status()
    parsed = schemas.Metadata.parse_raw(resp.text)
    assert parsed.description == dummy_model_data.description
    assert parsed.input_schema == dummy_model_data.io_schema.input_jsonschema
    assert parsed.output_schema == dummy_model_data.io_schema.output_jsonschema
    assert parsed.name == dummy_model_data.name


def test_run_prediction(demo_server_base_url: str, dummy_io_generator):
    inputs, gts = dummy_io_generator(n=1, structure_inputs=False, structure_gts=False)

    f = furl(demo_server_base_url)
    f.path = f.path / "predictions"
    resp = requests.post(f.url, json=inputs[0])
    resp.raise_for_status()
    parsed = schemas.PostPredictionResponse.parse_raw(resp.text)
    prediction_id = parsed.prediction_id

    f.path = f.path / prediction_id
    resp = requests.get(f.url)
    pred = schemas.Prediction.parse_raw(resp.text)
    while pred.status == "pending" or pred.status == "running":
        resp = requests.get(f.url)
        pred = schemas.Prediction.parse_raw(resp.text)
        time.sleep(0.1)

    assert pred.status == "success"
    assert pred.output == gts[0]
