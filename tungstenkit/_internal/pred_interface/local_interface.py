import os
import shutil
import tempfile
import typing as t
from pathlib import Path

from tungstenkit._internal.containers import start_model_container
from tungstenkit._internal.logging import log_info
from tungstenkit._internal.model_clients import ModelContainerClient
from tungstenkit._internal.storables import ModelData

from .abstract_interface import PredInterface


class LocalModel(PredInterface):
    def __init__(self, name: str):
        self._data = ModelData.load(name)
        self._tmp_dir: Path = Path(tempfile.mkdtemp())

    def _predict(self, inputs: t.List[t.Dict[str, t.Any]]):
        """
        Run prediction with the model container
        """
        with start_model_container(self._data, bind_dir_in_host=self._tmp_dir) as container:
            container_client = ModelContainerClient(container)
            log_info("Predicting")
            resp, _ = container_client.predict(inputs)
            return resp

    def _cleanup(self):
        for p in self._tmp_dir.glob("*"):
            if p.is_dir():
                shutil.rmtree(str(p))
            else:
                os.remove(p)


def get(name: str) -> LocalModel:
    return LocalModel(name)
