import json
import typing as t

import attrs
from fastapi import HTTPException, Request
from fasteners import ReaderWriterLock

from tungstenkit._internal.blob_store import BlobStore
from tungstenkit._internal.json_store import JSONCollection
from tungstenkit._internal.logging import log_error
from tungstenkit._internal.storables import PredExampleData, StoredModelData, StoredPredExampleData
from tungstenkit._internal.utils.json import apply_to_jsonable
from tungstenkit._internal.utils.uri import check_if_file_uri, get_path_from_file_url

from ..schemas import Example
from .file_service import FileService
from .prediction_service import PredictionService


# TODO move low-level operations for examples to tungstenkit._internal.model_store
@attrs.define(kw_only=True)
class LoadedExample:
    id: str

    input: t.Dict
    output: t.Optional[t.Dict] = None
    demo_output: t.Optional[t.Dict] = None
    logs: t.Optional[str] = None

    filenames: t.Set[str]

    @classmethod
    def build(cls, stored: StoredPredExampleData, file_service: FileService) -> "LoadedExample":
        input_json = json.loads(stored.input.file_path.read_text())
        output_json = json.loads(stored.output.file_path.read_text())
        demo_output_json = json.loads(stored.demo_output.file_path.read_text())
        logs = stored.logs.file_path.read_text() if stored.logs else None

        filenames: t.Set[str] = set()
        file_uri_mapping: t.Dict[str, str] = dict()
        for file in stored.files:
            path = file.file_path.resolve()
            filename = file_service.add_link(file.file_path, protected=True)
            filenames.add(filename)
            stored_file_uri = path.as_uri()
            loaded_file_uri = file_service.get_path_by_filename(filename).as_uri()
            file_uri_mapping[stored_file_uri] = loaded_file_uri

        def replace_file_uri(file_uri: str):
            if file_uri in file_uri_mapping:
                return file_uri_mapping[file_uri]
            return file_uri

        input_json = apply_to_jsonable(input_json, cond=check_if_file_uri, fn=replace_file_uri)
        output_json = apply_to_jsonable(output_json, cond=check_if_file_uri, fn=replace_file_uri)
        demo_output_json = apply_to_jsonable(
            demo_output_json, cond=check_if_file_uri, fn=replace_file_uri
        )

        return cls(
            id=stored.id,
            input=input_json,
            output=output_json,
            demo_output=demo_output_json,
            filenames=filenames,
            logs=logs,
        )

    def to_resp(self, request: Request, file_service: FileService) -> Example:
        file_serving_urls: t.List[str] = []

        def convert_file_url_to_http(file_url: str):
            path = get_path_from_file_url(file_url)
            try:
                filename = path.relative_to(file_service.base_dir).name
                if filename not in self.filenames:
                    raise ValueError
            except ValueError:
                log_error(f"Unknown file url in demo's example service: {file_url}")
                raise HTTPException(status_code=500)

            file_serving_url = file_service.build_serving_url(filename, request=request)
            file_serving_urls.append(file_serving_url)
            return file_serving_url

        input = apply_to_jsonable(
            self.input,
            cond=check_if_file_uri,
            fn=convert_file_url_to_http,
        )
        output = apply_to_jsonable(
            self.output,
            cond=check_if_file_uri,
            fn=convert_file_url_to_http,
        )
        demo_output = apply_to_jsonable(
            self.demo_output,
            cond=check_if_file_uri,
            fn=convert_file_url_to_http,
        )

        return Example(
            id=self.id,
            input=input,
            output=output,
            demo_output=demo_output,
            logs=self.logs,
            files=file_serving_urls,
        )


@attrs.define(kw_only=True)
class ExampleService:
    model_name: str
    file_service: FileService
    prediction_service: PredictionService

    _blob_store: BlobStore = attrs.field(factory=BlobStore, init=False)
    _model_store: JSONCollection[StoredModelData] = attrs.field(
        factory=lambda: JSONCollection[StoredModelData](StoredModelData), init=False
    )
    _loaded_examples: t.Dict[str, LoadedExample] = attrs.field(factory=dict, init=False)
    _delete_lock: ReaderWriterLock = attrs.field(factory=ReaderWriterLock, init=False)

    @property
    def count(self):
        self._load_examples()
        with self._delete_lock.read_lock():
            return len(self._loaded_examples)

    def list_examples(self, request: Request) -> t.List[Example]:
        self._load_examples()
        with self._delete_lock.read_lock():
            return [
                e.to_resp(request=request, file_service=self.file_service)
                for e in list(self._loaded_examples.values())
            ]

    def add_example_by_prediction_id(self, prediction_id: str) -> str:
        with self.prediction_service.acquire_read_lock(prediction_id):
            pred = self.prediction_service.saved_predictions[prediction_id]
            assert pred.output and pred.demo_output
            model = self._model_store.get(self.model_name)
            with self._blob_store.prevent_deletion():
                example = PredExampleData(
                    input=pred.input,
                    output=pred.output,
                    demo_output=pred.demo_output,
                    input_files=pred.input_file_paths_in_mount_dir,
                    output_files=pred.output_file_paths_in_mount_dir
                    if pred.output_file_paths_in_mount_dir
                    else [],
                    logs=pred.logs,
                )
                example_in_store = example.save_blobs(blob_store=self._blob_store)
                model.examples[example_in_store.id] = example_in_store
                self._model_store.update(model)

        return example_in_store.id

    def delete_by_example_id(self, example_id: str) -> None:
        with self._delete_lock.write_lock():
            model = self._model_store.get(self.model_name)
            if example_id not in model.examples:
                raise HTTPException(status_code=404)
            del model.examples[example_id]
            self._model_store.update(model)

    def _load_examples(self) -> None:
        model = self._model_store.get(self.model_name)
        with self._delete_lock.read_lock():
            deleted_example_ids = list(self._loaded_examples.keys())
            for example_id, example_data in model.examples.items():
                if example_id in self._loaded_examples.keys():
                    deleted_example_ids.remove(example_id)
                else:
                    self._loaded_examples[example_id] = LoadedExample.build(
                        stored=example_data, file_service=self.file_service
                    )

        with self._delete_lock.write_lock():
            model = self._model_store.get(self.model_name)
            for deleted_example_id in deleted_example_ids:
                if deleted_example_id in self._loaded_examples:
                    filenames = self._loaded_examples[deleted_example_id].filenames
                    for filename in filenames:
                        with self.file_service.acquire_write_lock(filename):
                            self.file_service.change_protected_flag(filename, protected=False)
                    del self._loaded_examples[deleted_example_id]
