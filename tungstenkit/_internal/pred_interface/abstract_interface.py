import abc
import typing as t
from pathlib import Path

from tungstenkit import exceptions
from tungstenkit._internal.io import build_uri_for_file
from tungstenkit._internal.model_clients import schemas
from tungstenkit._internal.storables import ModelData
from tungstenkit._internal.utils.file import copy_multiple_files
from tungstenkit._internal.utils.json import change_strings_in_jsonable, get_uris_in_jsonable
from tungstenkit._internal.utils.requests import download_files_in_threadpool
from tungstenkit._internal.utils.uri import get_path_from_file_url, save_data_url

if t.TYPE_CHECKING:
    from _typeshed import StrPath

DEFAULT_OUTPUT_FILE_DIR = Path(".")


# TODO predict_async, create_prediction, cancel_prediction, get_prediction
class PredInterface(abc.ABC):
    _data: ModelData
    _default_output_file_dir: t.Optional[Path] = None

    @t.overload
    def predict(
        self,
        inputs: t.Dict,
        output_file_dir: "t.Optional[StrPath]" = None,
    ) -> t.Dict:
        ...

    @t.overload
    def predict(
        self,
        inputs: t.List[t.Dict],
        output_file_dir: "t.Optional[StrPath]" = None,
    ) -> t.List[t.Dict]:
        ...

    def predict(
        self,
        inputs: t.Union[t.Dict, t.List[t.Dict]],
        output_file_dir: "t.Optional[StrPath]" = None,
    ) -> t.Union[t.Dict, t.List[t.Dict]]:
        output_file_path = Path(output_file_dir) if output_file_dir else None

        # Prepare inputs
        input_list = self._validate_inputs(inputs)
        input_list = [self._convert_input_files_to_urls(inp) for inp in input_list]

        # Predict
        resp = self._predict(input_list)
        if resp.status == "failed":
            raise exceptions.PredictionFailure(
                resp.error_message if resp.error_message else "unknown reason"
            )

        assert resp.outputs is not None
        output_list = resp.outputs

        # Prepare outputs
        output_list = self._save_output_files(output_list, output_file_path)

        # Cleanup
        self._cleanup_prediction()

        if isinstance(inputs, list):
            return output_list
        return output_list[0]

    @abc.abstractmethod
    def _predict(self, inputs: t.List[t.Dict]) -> schemas.PredictionResponse:
        pass

    def _cleanup_prediction(self):
        pass

    def _validate_inputs(self, inputs: t.Any) -> t.List[t.Dict]:
        """
        Validate inputs and returns list of input dictionaries.

        ``inputs`` should be ``dict[str, t.Any]`` or ``list[dict[str, t.Any]]``
        """
        if isinstance(inputs, dict):
            input_list = [inputs]
        elif isinstance(inputs, list):
            input_list = inputs
        else:
            raise TypeError(f"expected 'dict' or 'list[dict]', not '{type(inputs)}")
        for inp in input_list:
            if not isinstance(inp, dict):
                raise ValueError(f"expected type of list items is 'dict', not '{type(inp)}'")
            for key in inp.keys():
                if not isinstance(key, str):
                    raise ValueError(f"expected input dictionary key is 'str', not '{type(key)}")
        return input_list

    def _convert_input_files_to_urls(self, input: t.Dict) -> t.Dict:
        """
        Convert files in input dict to urls.

        Supported types: ``str``, ``pathlib.Path``, ``tungstenkit._internal.io.File``,
        ``io.BufferedIOBase``, ``io.TextIOBase``
        """
        ret = input.copy()
        input_filetypes = self._data.io.input_filetypes
        for field_name in input_filetypes.keys():
            if field_name in ret:
                ret[field_name] = build_uri_for_file(input[field_name])
        return ret

    def _save_output_files(
        self, outputs: t.List[t.Dict], output_file_dir: t.Optional[Path] = None
    ):
        """
        Convert output urls to ``pathlib.Path`` if required.

        If ``output_file_dir`` is None, preserve http urls and save and convert only
        file/data urls.

        Otherwise, all urls are saved and converted to ``pathlib.Path``.
        """
        # TODO check urls only in file fields of output
        http_urls = get_uris_in_jsonable(outputs, ["http", "https"])
        if output_file_dir:
            downloaded = self._download_multiple_files(http_urls, output_file_dir)
            outputs = change_strings_in_jsonable(outputs, http_urls, downloaded)

        file_urls = get_uris_in_jsonable(outputs, ["file"])
        paths = [get_path_from_file_url(url) for url in file_urls]
        copied = copy_multiple_files(
            paths, output_file_dir if output_file_dir else DEFAULT_OUTPUT_FILE_DIR
        )
        outputs = change_strings_in_jsonable(outputs, file_urls, copied)

        data_urls = get_uris_in_jsonable(outputs, ["data"])
        saved: t.List[Path] = []
        for d in data_urls:
            saved.append(save_data_url(d, DEFAULT_OUTPUT_FILE_DIR))
        outputs = change_strings_in_jsonable(outputs, data_urls, saved)

        return outputs

    def _download_multiple_files(self, http_urls: t.List[str], download_dir: Path):
        return download_files_in_threadpool(*http_urls, out=download_dir, progress_bar=False)
