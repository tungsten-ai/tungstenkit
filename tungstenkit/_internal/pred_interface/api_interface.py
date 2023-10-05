import typing as t

from furl import furl

from tungstenkit import exceptions
from tungstenkit._internal.io import build_uri_for_file
from tungstenkit._internal.logging import log_warning
from tungstenkit._internal.model_clients import ModelAPIClient
from tungstenkit._internal.utils.uri import check_if_file_uri, get_path_from_file_url

from .abstract_interface import PredInterface

LARGE_FILE_THRESHOLD = 256 * 1024 * 1024


class ModelServer(PredInterface):
    def __init__(self, base_url: str):
        f = furl(base_url)
        if f.scheme != "http" and f.scheme != "https":
            raise exceptions.InvalidURL(f"expected http(s) url, not {f.scheme}")

        self._client = ModelAPIClient(base_url)

    @property
    def _file_fields(self) -> t.List[str]:
        input_schema = self._client.metadata.input_schema
        file_fields = list()
        for field_name, prop in input_schema["properties"].items():
            if "format" in prop and prop["format"] == "uri":
                file_fields.append(field_name)

        return file_fields

    def _predict(self, inputs: t.List[t.Dict[str, t.Any]]):
        return self._client.predict(inputs)

    def _convert_input_files_to_urls(self, input: t.Dict) -> t.Dict:
        ret = input.copy()
        for field_name in self._file_fields:
            if field_name in ret:
                uri = build_uri_for_file(input[field_name])
                if check_if_file_uri(uri):
                    p = get_path_from_file_url(uri)
                    if p.stat().st_size > LARGE_FILE_THRESHOLD:
                        log_warning(
                            f"File at input field {field_name} yields a too large data uri. "
                            "The input may not be processed."
                        )
                    ret[field_name] = uri.to_data_uri()
        return ret
