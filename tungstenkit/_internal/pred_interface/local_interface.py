import tempfile
import typing as t
from pathlib import Path

from tungstenkit._internal.containers import start_model_container
from tungstenkit._internal.model_clients import ModelContainerClient
from tungstenkit._internal.storables import ModelData

from .abstract_interface import PredInterface


class LocalModel(PredInterface):
    def __init__(self, name: str):
        self._data = ModelData.load(name)

    def _predict(self, inputs: t.List[t.Dict[str, t.Any]]):
        """
        Run prediction with the model container
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            with start_model_container(self._data, bind_dir_in_host=Path(tmp_dir)) as container:
                container_client = ModelContainerClient(container)
                resp, _ = container_client.predict(inputs)
                return resp


def get(name: str) -> LocalModel:
    return LocalModel(name)
