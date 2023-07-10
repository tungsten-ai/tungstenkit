import json
import os
import signal
import time
import typing as t
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from threading import Event, Thread

import attrs
from fastapi import HTTPException, Request
from fasteners import ReaderWriterLock
from furl import furl

from tungstenkit._internal.logging import log_debug, log_error
from tungstenkit._internal.model_clients import ModelContainerClient
from tungstenkit._internal.utils.json import apply_to_jsonable
from tungstenkit._internal.utils.uri import check_if_file_uri, get_path_from_file_url
from tungstenkit.exceptions import ModelClientError

from ..schemas import Prediction, PredictionStatus
from .file_service import FileService

EXPIRATION_SECONDS = 10 * 60
GARBAGE_COLLECTION_INTERVAL = 10


@attrs.define(kw_only=True)
class SavedPrediction:
    id: str
    status: PredictionStatus

    input: t.Dict
    filenames: t.Set[str]
    input_file_paths_in_mount_dir: t.List[Path]

    output: t.Optional[t.Dict] = None
    demo_output: t.Optional[t.Dict] = None
    logs: t.Optional[str] = None
    output_file_paths_in_mount_dir: t.Optional[t.List[Path]] = None

    created_at: datetime = attrs.field(factory=datetime.utcnow, init=False)

    def to_resp(
        self, request: Request, file_service: FileService, input_filetypes: t.Dict
    ) -> Prediction:
        file_serving_urls: t.List[str] = []

        def convert_file_url_to_http(file_url: str, allow_unknown_file_url: bool):
            path = get_path_from_file_url(file_url)
            try:
                filename = path.relative_to(file_service.base_dir).name
                if filename not in self.filenames:
                    raise ValueError
            except ValueError:
                if allow_unknown_file_url:
                    return file_url
                else:
                    log_error(
                        f"Unknown file url in demo's prediction service: {file_url} / {path}"
                    )
                    raise HTTPException(status_code=500)

            file_serving_url = file_service.build_serving_url(filename, request=request)
            file_serving_urls.append(file_serving_url)
            return file_serving_url

        input = self.input.copy()
        for field_name in input_filetypes:
            if input[field_name] is not None:
                input[field_name] = convert_file_url_to_http(
                    input[field_name], allow_unknown_file_url=False
                )
        output = (
            None
            if self.output is None
            else apply_to_jsonable(
                self.output,
                cond=check_if_file_uri,
                fn=lambda s: convert_file_url_to_http(s, allow_unknown_file_url=True),
            )
        )
        demo_output = (
            None
            if self.demo_output is None
            else apply_to_jsonable(
                self.demo_output,
                cond=check_if_file_uri,
                fn=lambda s: convert_file_url_to_http(s, allow_unknown_file_url=True),
            )
        )

        return Prediction(
            id=self.id,
            status=self.status,
            input=input,
            output=output,
            demo_output=demo_output,
            logs=self.logs,
        )


@attrs.define(kw_only=True)
class PredictionService:
    file_service: FileService
    model_client: ModelContainerClient
    input_schema: t.Dict
    input_filetypes: t.Dict

    saved_predictions: t.Dict[str, SavedPrediction] = attrs.field(factory=dict, init=False)
    _locks: t.Dict[str, ReaderWriterLock] = attrs.field(factory=dict, init=False)
    _gc_term_event: t.Optional[Event] = attrs.field(default=None, init=False)

    def check_existence(self, prediction_id: str) -> bool:
        return prediction_id in list(self.saved_predictions.keys())

    def create_prediction(self, input: t.Dict) -> str:
        _fill_omitted_input_fields_as_defaults(input, self.input_schema)
        input_filenames: t.Set[str] = set()

        try:
            for field_name in self.input_filetypes:
                if field_name in input.keys() and input[field_name] is not None:
                    fileurl, filename = self._convert_file_serving_url_to_file_url(
                        input[field_name]
                    )
                    input[field_name] = fileurl
                    input_filenames.add(filename)
            try:
                prediction_id, file_paths = self.model_client.create_demo(inputs=[input])
            except ModelClientError as e:
                _raise_http_exc_by_model_client_err(e)
            pred = SavedPrediction(
                id=prediction_id,
                status="pending",
                input=input,
                filenames=input_filenames,
                input_file_paths_in_mount_dir=file_paths,
            )
            self.saved_predictions[prediction_id] = pred
            self._locks[prediction_id] = ReaderWriterLock()
            return prediction_id

        except BaseException as e:
            for filename in input_filenames:
                with self.file_service.acquire_write_lock(filename):
                    self.file_service.change_protected_flag(filename=filename, protected=False)

            raise e

    def get_prediction_by_id(self, prediction_id: str, request: Request) -> Prediction:
        with self.acquire_read_lock(prediction_id):
            last_status = self.saved_predictions[prediction_id].status
            if last_status == "success" or last_status == "failed":
                return self.saved_predictions[prediction_id].to_resp(
                    request=request,
                    file_service=self.file_service,
                    input_filetypes=self.input_filetypes,
                )

            pred = self.saved_predictions[prediction_id]

        try:
            pred_from_client, file_paths = self.model_client.get_demo(prediction_id)
        except ModelClientError as e:
            _raise_http_exc_by_model_client_err(e)

        output_filenames: t.Set[str] = set()

        def convert_file_url(file_url: str):
            path = get_path_from_file_url(file_url)
            if path in file_paths:
                filename = self.file_service.add_file_by_path(path=path, protected=True)
                output_filenames.add(filename)
                file_url = self.file_service.get_path_by_filename(filename).as_uri()

            return file_url

        with self._acquire_write_lock(prediction_id):
            pred.status = pred_from_client.status
            pred.logs = pred_from_client.logs
            if pred_from_client.error_message:
                pred.logs = (
                    pred_from_client.error_message
                    if pred.logs is None
                    else pred.logs + "\n" + pred_from_client.error_message
                )
            pred.output = (
                None
                if pred_from_client.outputs is None
                else apply_to_jsonable(
                    pred_from_client.outputs[0], cond=check_if_file_uri, fn=convert_file_url
                )
            )
            pred.demo_output = (
                None
                if pred_from_client.demo_outputs is None
                else apply_to_jsonable(
                    pred_from_client.demo_outputs[0],
                    cond=check_if_file_uri,
                    fn=convert_file_url,
                )
            )
            pred.filenames = pred.filenames.union(output_filenames)
            pred.output_file_paths_in_mount_dir = file_paths
            return pred.to_resp(
                request=request,
                file_service=self.file_service,
                input_filetypes=self.input_filetypes,
            )

    def cancel_prediction_by_id(self, prediction_id: str):
        with self.acquire_read_lock(prediction_id):
            pred = self.saved_predictions[prediction_id]
            if pred.status == "failed" or pred.status == "success":
                return
        try:
            self.model_client.cancel_demo(prediction_id)
        except ModelClientError as e:
            _raise_http_exc_by_model_client_err(e)

        with self._acquire_write_lock(prediction_id):
            if pred.status != "failed":
                pred.status == "failed"
                pred.logs = pred.logs + "\nCanceled" if pred.logs else "Canceled"

    def start_garbage_collection(self, gc_term_event: Event) -> Thread:
        self._gc_term_event = gc_term_event
        thread = Thread(target=self._run_garbage_collection, daemon=True)
        thread.start()
        return thread

    @contextmanager
    def acquire_read_lock(self, prediction_id: str):
        if not self.check_existence(prediction_id):
            _raise_not_found(prediction_id)
        with self._locks[prediction_id].read_lock() as lock:
            yield lock

    @contextmanager
    def _acquire_write_lock(self, prediction_id: str):
        if not self.check_existence(prediction_id):
            _raise_not_found(prediction_id)
        with self._locks[prediction_id].write_lock() as lock:
            yield lock

    def _run_garbage_collection(self):
        try:
            while True:
                time.sleep(GARBAGE_COLLECTION_INTERVAL)
                self._collect_garbages()
                prediction_ids = list(self.saved_predictions.keys())
                log_debug(f"Remaining predictions: {prediction_ids}")
        except BaseException:
            self._gc_term_event.set()
            os.kill(os.getpid(), signal.SIGTERM)

    def _collect_garbages(self):
        prediction_ids = list(self.saved_predictions.keys())
        current = datetime.utcnow()
        for prediction_id in prediction_ids:
            pred = self.saved_predictions[prediction_id]
            if (pred.created_at - current).total_seconds() > EXPIRATION_SECONDS:
                with self._acquire_write_lock(prediction_id):
                    paths = pred.input_file_paths_in_mount_dir
                    if pred.output_file_paths_in_mount_dir:
                        paths += pred.output_file_paths_in_mount_dir
                    for p in paths:
                        if p.exists():
                            os.remove(p)
                    del self.saved_predictions[prediction_id]

                for filename in pred.filenames:
                    with self.file_service.acquire_write_lock(filename):
                        self.file_service.change_protected_flag(filename, protected=False)

                del self._locks[prediction_id]

    def _convert_file_serving_url_to_file_url(self, serving_url: str) -> t.Tuple[str, str]:
        f = furl(serving_url)
        if f.scheme not in ["http", "https"] or not f.path.segments or len(f.path.segments) == 0:
            raise HTTPException(status_code=422, detail=f"Invalid file serving url: {serving_url}")

        filename: str = f.path.segments[-1]
        if not self.file_service.check_existence(filename):
            raise HTTPException(status_code=404, detail=f"File not found: {serving_url}")

        with self.file_service.acquire_write_lock(filename):
            self.file_service.change_protected_flag(filename=filename, protected=True)
        with self.file_service.acquire_read_lock(filename):
            path = self.file_service.get_path_by_filename(filename)
            url = path.as_uri()

        return url, filename


def _raise_http_exc_by_model_client_err(e: ModelClientError):
    detail = e.detail
    try:
        detail = json.loads(e.detail)
    except json.decoder.JSONDecodeError:
        pass
    raise HTTPException(status_code=e.status_code, detail=detail)


def _raise_not_found(prediction_id: str):
    raise HTTPException(status_code=404, detail="No such prediction: " + prediction_id)


def _fill_omitted_input_fields_as_defaults(input: t.Dict, input_schema: t.Dict):
    if "required" not in input_schema:
        required_field_names = []
    else:
        required_field_names = input_schema["required"]

    required_field_names = list(filter(lambda key: key in required_field_names, input.keys()))
    for field_name, field_property in input_schema["properties"].items():
        if field_name not in input:
            if "default" in field_property:
                input[field_name] = field_property["default"]
            elif field_name not in required_field_names:
                input[field_name] = None
            else:
                HTTPException(status_code=422, detail=f"Field {field_name} is required.")
