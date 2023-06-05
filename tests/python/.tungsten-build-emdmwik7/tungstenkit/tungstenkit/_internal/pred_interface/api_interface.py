import typing as t

from furl import furl

from tungstenkit import exceptions
from tungstenkit._internal.model_clients import ModelAPIClient

from .abstract_interface import PredInterface


class ModelServer(PredInterface):
    def __init__(self, base_url: str):
        f = furl(base_url)
        if f.scheme != "http" and f.scheme != "https":
            raise exceptions.InvalidURL(f"expected http(s) url, not {f.scheme}")

        self._client = ModelAPIClient(base_url)

    def _predict(self, inputs: t.List[t.Dict[str, t.Any]]):
        """
        Run prediction with the model container
        """
        return self._client.predict(inputs)
