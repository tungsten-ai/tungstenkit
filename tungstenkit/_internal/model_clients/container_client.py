import time
import typing as t
from pathlib import Path

from . import schemas
from .api_client import ModelAPIClient

if t.TYPE_CHECKING:
    from tungstenkit._internal.containers import ModelContainer


class ModelContainerClient:
    def __init__(self, container: "ModelContainer", rename_files: bool = False) -> None:
        self._container = container
        self._api = ModelAPIClient(
            base_url=self._container.url, model_name=self._container.model_name
        )
        self._rename_files = rename_files

    def predict(self, inputs: t.List[t.Dict]) -> t.Tuple[schemas.PredictionResponse, t.List[Path]]:
        files: t.List[Path] = []
        inputs, files_in_inputs = self._container.convert_file_uris_in_inputs(
            inputs, move=self._rename_files
        )
        files.extend(files_in_inputs)
        result = self._api.predict(inputs)
        if result.outputs:
            result.outputs, files_in_outputs = self._container.convert_file_uris_in_outputs(
                result.outputs
            )
            files.extend(files_in_outputs)
        return result, files

    def create_prediction(
        self,
        inputs: t.List[t.Dict],
    ) -> t.Tuple[str, t.List[Path]]:
        inputs, files = self._container.convert_file_uris_in_inputs(
            inputs, move=self._rename_files
        )
        return self._api.create_prediction(inputs), files

    def get_prediction(
        self, prediction_id: str
    ) -> t.Tuple[schemas.PredictionResponse, t.List[Path]]:
        result = self._api.get_prediction(prediction_id=prediction_id)
        files: t.List[Path] = []
        if result.outputs:
            result.outputs, files = self._container.convert_file_uris_in_outputs(result.outputs)

        return result, files

    def cancel_prediction(self, prediction_id: str):
        self._api.cancel_prediction(prediction_id)

    def predict_demo(self, inputs: t.List[t.Dict]) -> t.Tuple[schemas.DemoResponse, t.List[Path]]:
        files: t.List[Path] = []
        inputs, files_in_inputs = self._container.convert_file_uris_in_inputs(
            inputs, move=self._rename_files
        )
        files.extend(files_in_inputs)
        prediction_id = self._api.create_demo(inputs)
        while True:
            result = self._api.get_demo(prediction_id)
            if result.status == "success" or result.status == "failed":
                break

            time.sleep(0.1)

        if result.outputs:
            result.outputs, files_in_outputs = self._container.convert_file_uris_in_outputs(
                result.outputs
            )
            files.extend(files_in_outputs)
        if result.demo_outputs:
            (
                result.demo_outputs,
                files_in_demo_outputs,
            ) = self._container.convert_file_uris_in_outputs(result.demo_outputs)
            files.extend(files_in_demo_outputs)
        return result, files

    def create_demo(self, inputs: t.List[t.Dict]) -> t.Tuple[str, t.List[Path]]:
        inputs, files = self._container.convert_file_uris_in_inputs(
            inputs, move=self._rename_files
        )
        return self._api.create_demo(inputs), files

    def get_demo(self, prediction_id: str) -> t.Tuple[schemas.DemoResponse, t.List[Path]]:
        result = self._api.get_demo(prediction_id=prediction_id)
        files: t.List[Path] = []
        if result.outputs:
            result.outputs, files_in_outputs = self._container.convert_file_uris_in_outputs(
                result.outputs
            )
            files.extend(files_in_outputs)
        if result.demo_outputs:
            (
                result.demo_outputs,
                files_in_demo_outputs,
            ) = self._container.convert_file_uris_in_outputs(result.demo_outputs)
            files.extend(files_in_demo_outputs)

        return result, files

    def cancel_demo(self, prediction_id: str):
        self._api.cancel_demo(prediction_id)
