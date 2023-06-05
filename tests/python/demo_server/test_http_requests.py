import time
from io import BytesIO

import requests
from furl import furl
from w3lib.url import parse_data_uri

from tungstenkit._internal import storables
from tungstenkit._internal.demo_server import schemas
from tungstenkit._internal.utils.requests import upload_form_data_by_buffer


def test_get_model_metadata(demo_server_base_url: str, dummy_model_data: storables.ModelData):
    f = furl(demo_server_base_url)
    f.path = f.path / "metadata"
    resp = requests.get(f.url)
    resp.raise_for_status()
    parsed = schemas.Metadata.parse_raw(resp.text)
    assert parsed.input_schema == dummy_model_data.io.input_schema
    assert parsed.output_schema == dummy_model_data.io.output_schema
    assert parsed.demo_output_schema == dummy_model_data.io.demo_output_schema
    assert parsed.input_filetypes == dummy_model_data.io.input_filetypes
    assert parsed.output_filetypes == dummy_model_data.io.output_filetypes
    assert parsed.demo_output_filetypes == dummy_model_data.io.demo_output_filetypes
    assert parsed.name == dummy_model_data.name
    assert parsed.readme and parsed.readme.startswith(
        "My Model\n========\n\n\nHi Tungsten\n-----------\n\n\n![Tungsten](/files/tungsten.png "
        '"Tungsten")'
    )


def test_run_prediction(demo_server_base_url: str, dummy_io_generator):
    inputs, gts = dummy_io_generator(n=1, structure_inputs=False, structure_gts=False)

    input = inputs[0]
    image = input["image"]
    data_uri_parse = parse_data_uri(image)
    image_data = data_uri_parse.data
    image_media_type = data_uri_parse.media_type

    f = furl(demo_server_base_url)
    f.path = f.path / "files"
    resp = upload_form_data_by_buffer(
        method="post",
        url=f.url,
        buffer=BytesIO(image_data),
        file_name="image.png",
        content_type=image_media_type,
        size=len(image_data),
    )
    resp.raise_for_status()
    uploaded = schemas.FileUploadResponse.parse_raw(resp.text)
    input["image"] = uploaded.serving_url

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
