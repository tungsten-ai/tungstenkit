import multiprocessing as mp
import signal
import traceback
import typing as t
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from multiprocessing.connection import Connection
from pathlib import Path

import attrs
import pydantic
from fastapi.encoders import jsonable_encoder

from tungstenkit import exceptions
from tungstenkit._internal.io import BaseIO, File
from tungstenkit._internal.model_def import TungstenModel
from tungstenkit._internal.model_def_loader import ModelDefLoader
from tungstenkit._internal.utils.pydantic import run_validation
from tungstenkit._internal.utils.types import get_qualname

from .. import server_exceptions


@attrs.define
class PredictionRequest:
    inputs: t.List[t.Dict]
    is_demo: bool
    log_path: t.Optional[Path] = None


@attrs.define(kw_only=True)
class PredictionSuccess:
    outputs: t.List[t.Dict]
    demo_outputs: t.List[t.Optional[t.Dict]]
    files: t.List[File]


@attrs.define
class PredictionFailure:
    err_msg: str


class WorkerSubprocess(mp.Process):
    def __init__(
        self,
        model_def_loader: ModelDefLoader,
        conn: Connection,
        setup_log_path: Path,
        predict_log_path: Path,
    ) -> None:
        self._model_def_loader = model_def_loader
        self._conn = conn
        self._setup_log_path = setup_log_path
        self._predict_log_path = predict_log_path

        self._is_running: bool = False
        self._model: t.Optional[TungstenModel] = None
        self._input_cls: t.Optional[t.Type[BaseIO]] = None
        self._output_cls: t.Optional[t.Type[BaseIO]] = None

        super().__init__(daemon=True, name="worker-subprocess")

    def run(self):
        with ExitStack() as exit_stack:
            _redirect_stream(exit_stack, self._setup_log_path, flush=True)

            signal.signal(signal.SIGUSR1, self._handle_cancellation)
            signal.signal(signal.SIGUSR2, self._handle_timeout)

            self._model = self._model_def_loader.model
            self._model.setup()
            self._input_cls = self._model_def_loader.input_class
            self._output_cls = self._model_def_loader.output_class
            self._demo_output_cls = self._model_def_loader.demo_output_class
            self._conn.send(None)

        with ExitStack() as exit_stack:
            _redirect_stream(exit_stack, self._predict_log_path, flush=True)
            while True:
                received: PredictionRequest = self._conn.recv()
                inputs = [self._input_cls.parse_obj(inp) for inp in received.inputs]
                is_demo = received.is_demo
                log_path = received.log_path
                if log_path:
                    exit_stack.pop_all()
                    _redirect_stream(exit_stack, log_path, flush=False)
                prediction_result = self._predict(inputs=inputs, is_demo=is_demo)
                exit_stack.pop_all()
                _redirect_stream(exit_stack, self._predict_log_path, flush=True)
                self._conn.send(prediction_result)

    def _predict(
        self,
        inputs: t.List[t.Dict],
        is_demo: bool,
    ) -> t.Union[PredictionSuccess, PredictionFailure]:
        assert self._model
        assert self._input_cls
        assert self._output_cls
        assert self._demo_output_cls

        try:
            self._is_running = True
            # Send ACK to the main proc and release lock blocking cancelation
            self._conn.send(None)

            # print(f"working dir: {Path('.').resolve()}")
            parsed_inputs = [self._input_cls.parse_obj(inp) for inp in inputs]
            if is_demo:
                fn_name = self._model.__class__.__name__ + "." + self._model.predict_demo.__name__
                tup = self._model.predict_demo(parsed_inputs)
                try:
                    it = iter(tup)
                except TypeError:
                    raise exceptions.InvalidOutput(
                        f"Return of '{fn_name}' is not iterable. "
                        "It should return both 'outputs' and 'demo_outputs'."
                    )
                try:
                    outputs = next(it)
                except StopIteration:
                    raise exceptions.InvalidOutput(f"Return of '{fn_name}' has no element. ")
                try:
                    demo_outputs: t.Sequence[t.Any] = next(it)
                except StopIteration:
                    raise exceptions.InvalidOutput(
                        f"Return of '{fn_name}' has only 1 element. "
                        "It should return both 'outputs' and 'demo_outputs'."
                    )
                try:
                    iter(outputs)
                except TypeError:
                    raise exceptions.InvalidOutput(
                        f"Outputs (the first return value of '{fn_name}') are not iterable."
                    )
                try:
                    iter(demo_outputs)
                except TypeError:
                    raise exceptions.InvalidOutput(
                        f"Demo outputs (the second return value of '{fn_name}') are not "
                        "iterable."
                    )

            else:
                fn_name = self._model.__class__.__name__ + self._model.predict.__name__
                outputs = self._model.predict(parsed_inputs)
                try:
                    iter(outputs)
                except TypeError:
                    raise exceptions.InvalidOutput(
                        f"Outputs (the return value of '{fn_name}') are not iterable."
                    )
                demo_outputs = [None] * len(outputs)

            files = _get_files([outputs, demo_outputs])

            validated_outputs = _validate_and_serialize_outputs(outputs, self._output_cls)
            validated_demo_outputs = _validate_and_serialize_demo_outputs(
                demo_outputs, self._demo_output_cls
            )

            self._is_running = False
            return PredictionSuccess(
                outputs=validated_outputs, demo_outputs=validated_demo_outputs, files=files
            )

        except BaseException as e:
            self._is_running = False
            if isinstance(e, server_exceptions.PredictionCanceled):
                err_msg = "Canceled"
            elif isinstance(e, server_exceptions.PredictionTimeout):
                err_msg = "Timeout"
            else:
                err_msg = traceback.format_exc()
            print(err_msg)
            return PredictionFailure(err_msg=err_msg)

    def _handle_cancellation(self, *args, **argv):
        if self._is_running:
            raise server_exceptions.PredictionCanceled

    def _handle_timeout(self, *args, **argv):
        if self._is_running:
            raise server_exceptions.PredictionTimeout


def _get_files(outputs: t.Any) -> t.List[File]:
    files = []
    if isinstance(outputs, File):
        files.append(outputs)

    elif isinstance(outputs, list) or isinstance(outputs, tuple):
        for item in outputs:
            files.extend(_get_files(item))

    elif isinstance(outputs, dict):
        for item in outputs.values():
            files.extend(_get_files(item))

    elif isinstance(outputs, BaseIO):
        for field_name in outputs.__fields__.keys():
            files.extend(_get_files(getattr(outputs, field_name)))

    return files


def _validate_and_serialize_demo_outputs(
    demo_outputs: t.Iterable,
    demo_output_cls: t.Type[BaseIO],
) -> t.List[t.Optional[t.Dict]]:
    validated_demo_outputs: t.List[t.Optional[t.Dict]] = []
    for o in demo_outputs:
        try:
            if o is None:
                validated_demo_outputs.append(o)
            elif isinstance(o, demo_output_cls):
                validated_demo_outputs.append(jsonable_encoder(run_validation(o)))
            elif isinstance(o, dict):
                validated_demo_outputs.append(jsonable_encoder(demo_output_cls(**o)))
            else:
                raise exceptions.InvalidDemoOutput(
                    f"Invalid demo output type: {type(o)}. "
                    f"Allowed types: 'dict' and '{BaseIO}'"
                )
        except pydantic.error_wrappers.ValidationError as e:
            raise exceptions.InvalidDemoOutput(str(e))

    return validated_demo_outputs


def _validate_and_serialize_outputs(
    outputs: t.Iterable, output_cls: t.Type[BaseIO]
) -> t.List[t.Dict]:
    validated_outputs: t.List[t.Dict] = []
    for o in outputs:
        try:
            if isinstance(o, output_cls):
                validated_outputs.append(jsonable_encoder(run_validation(o)))
            elif isinstance(o, dict):
                validated_outputs.append(jsonable_encoder(output_cls(**o)))
            else:
                raise exceptions.InvalidOutput(
                    f"Invalid output type: {type(o)}. Allowed types: 'dict' and "
                    f"'{get_qualname(output_cls)}'"
                )
        except pydantic.error_wrappers.ValidationError as e:
            raise exceptions.InvalidOutput(str(e))

    return validated_outputs


# def _validate_and_serialize_demo_outputs(
#     outputs: t.Iterable, output_cls: t.Type[BaseIO]
# ) -> t.List[t.Dict]:
#     validated_outputs: t.List[t.Dict] = []
#     for o in outputs:
#         try:
#             if isinstance(o, output_cls):
#                 validated_outputs.append(jsonable_encoder(run_validation(o)))
#             elif isinstance(o, dict):
#                 validated_outputs.append(jsonable_encoder(output_cls.parse_obj(o)))
#             else:
#                 raise exceptions.InvalidDemoOutput(
#                     f"Invalid output type: {type(o)}. Allowed types: 'dict' and '{output_cls}'"
#                 )
#         except pydantic.error_wrappers.ValidationError as e:
#             raise exceptions.InvalidDemoOutput(str(e))

#     return validated_outputs


def _redirect_stream(exit_stack: ExitStack, path: Path, flush: bool = True):
    f = exit_stack.enter_context(open(path, "w+", buffering=1))
    if flush:
        f.flush()
    exit_stack.enter_context(redirect_stderr(f))
    exit_stack.enter_context(redirect_stdout(f))
