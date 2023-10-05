import os
import shutil
import tempfile
import typing as t
from pathlib import Path

from tungstenkit._internal.containers import start_model_container
from tungstenkit._internal.io import build_uri_for_file
from tungstenkit._internal.logging import log_info
from tungstenkit._internal.model_clients import ModelContainerClient
from tungstenkit._internal.storables import ModelData
from tungstenkit._internal.utils.uri import check_if_http_or_https_uri

from .abstract_interface import PredInterface


class LocalModel(PredInterface):
    def __init__(self, name: str):
        self._data = ModelData.load(name)
        self._tmp_dir: Path = Path(tempfile.mkdtemp())

    def _predict(self, inputs: t.List[t.Dict[str, t.Any]]):
        with start_model_container(self._data, bind_dir_in_host=self._tmp_dir) as container:
            container_client = ModelContainerClient(container)
            log_info("Predicting")
            resp, _ = container_client.predict(inputs)
            return resp

    def _convert_input_files_to_urls(self, input: t.Dict) -> t.Dict:
        ret = input.copy()
        input_filetypes = self._data.io.input_filetypes
        for field_name in input_filetypes.keys():
            if field_name in ret:
                uri = build_uri_for_file(input[field_name])
                if check_if_http_or_https_uri(uri):
                    uri = uri.to_file_uri()
                ret[field_name] = uri
        return ret

    def _cleanup(self):
        for p in self._tmp_dir.glob("*"):
            if p.is_dir():
                shutil.rmtree(str(p))
            else:
                os.remove(p)


def get(name: str) -> LocalModel:
    return LocalModel(name)
