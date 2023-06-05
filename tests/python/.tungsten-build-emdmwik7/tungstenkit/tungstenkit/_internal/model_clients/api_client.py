import typing as t

import requests
from fastapi.encoders import jsonable_encoder
from furl import furl

from tungstenkit._internal.io import BaseIO
from tungstenkit._internal.utils.requests import check_resp, log_request
from tungstenkit.exceptions import ModelClientError

from . import schemas

CONNECTION_TIMEOUT = 5


class ModelAPIClient:
    def __init__(self, base_url: str, model_name: t.Optional[str] = None) -> None:
        self.base_url = base_url
        self.model_name = model_name
        self.sess = requests.Session()

        self._metadata: t.Optional[schemas.Metadata] = None

    @property
    def metadata(self) -> schemas.Metadata:
        if self._metadata is None:
            self._metadata = self.get_metadata()
        return self._metadata

    def get_metadata(self) -> schemas.Metadata:
        log_request(url=self.base_url, method="GET")
        r = self.sess.get(self.base_url, timeout=CONNECTION_TIMEOUT)
        self._check_resp(r, self.base_url, self.get_metadata)
        return schemas.Metadata.parse_raw(r.text)

    def predict(self, inputs: t.Sequence[t.Union[t.Dict, BaseIO]]) -> schemas.PredictionResponse:
        f = furl(self.base_url)
        f.path = f.path / "predict"
        r = self._post_prediction(url=f.url, inputs=inputs, timeout=None)
        self._check_resp(r, f.url, self.predict)
        return schemas.PredictionResponse.parse_raw(r.text)

    def create_prediction(self, inputs: t.Sequence[t.Union[t.Dict, BaseIO]]) -> str:
        f = furl(self.base_url)
        f.path = f.path / "predict_async"
        r = self._post_prediction(url=f.url, inputs=inputs)
        self._check_resp(r, f.url, self.create_prediction)
        parsed = schemas.PredictionID.parse_raw(r.text)
        return parsed.prediction_id

    def get_prediction(self, prediction_id: str) -> schemas.PredictionResponse:
        f = furl(self.base_url)
        f.path = f.path / "predict_async" / prediction_id
        log_request(url=f.url, method="GET")
        r = self.sess.get(url=f.url, timeout=CONNECTION_TIMEOUT)
        self._check_resp(r, f.url, self.get_prediction)
        return schemas.PredictionResponse.parse_raw(r.text)

    def cancel_prediction(self, prediction_id: str) -> None:
        f = furl(self.base_url)
        f.path = f.path / "predict_async" / prediction_id / "cancel"
        log_request(url=f.url, method="POST")
        r = self.sess.post(url=f.url, timeout=CONNECTION_TIMEOUT)
        self._check_resp(r, f.url, self.cancel_prediction)

    def create_demo(self, inputs: t.Sequence[t.Union[t.Dict, BaseIO]]) -> str:
        f = furl(self.base_url)
        f.path = f.path / "demo"
        r = self._post_prediction(url=f.url, inputs=inputs)
        self._check_resp(r, f.url, self.create_demo)
        parsed = schemas.PredictionID.parse_raw(r.text)
        return parsed.prediction_id

    def get_demo(self, prediction_id: str) -> schemas.DemoResponse:
        f = furl(self.base_url)
        f.path = f.path / "demo" / prediction_id
        log_request(url=f.url, method="GET")
        r = self.sess.get(url=f.url, timeout=CONNECTION_TIMEOUT)
        self._check_resp(r, f.url, self.get_demo)
        return schemas.DemoResponse.parse_raw(r.text)

    def cancel_demo(self, prediction_id: str) -> None:
        f = furl(self.base_url)
        f.path = f.path / "demo" / prediction_id / "cancel"
        log_request(url=f.url, method="POST")
        r = self.sess.post(url=f.url, timeout=CONNECTION_TIMEOUT)
        self._check_resp(r, f.url, self.cancel_demo)

    def _post_prediction(
        self,
        url: str,
        inputs: t.Sequence[t.Union[t.Dict, BaseIO]],
        timeout: t.Optional[float] = CONNECTION_TIMEOUT,
    ) -> requests.Response:
        jsonable = jsonable_encoder(inputs)
        log_request(url=url, method="POST", data=jsonable)
        return self.sess.post(url=url, json=jsonable, timeout=timeout)

    def _check_resp(self, resp: requests.Response, url: str, method: t.Callable):
        name = " ".join(method.__name__.split("_"))
        err_msg_prefix = f"Failed to {name} "
        if self.model_name:
            err_msg_prefix += f"in model {self.model_name} server"
        else:
            err_msg_prefix += f"in model server at {self.base_url}"
        check_resp(resp=resp, url=url, exc_type=ModelClientError, err_msg_prefix=err_msg_prefix)
