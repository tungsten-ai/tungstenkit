import multiprocessing as mp
import os
import signal
import tempfile
import time
import typing as t
from pathlib import Path
from threading import Lock

from fastapi.encoders import jsonable_encoder

from tungstenkit._internal.io import BaseIO
from tungstenkit._internal.model_def_loader import ModelDefLoader
from tungstenkit._internal.utils.console import LogFileRedirector

from .. import server_exceptions
from .subproc import PredictionFailure, PredictionRequest, PredictionSuccess, WorkerSubprocess

ACK_TIMEOUT_SEC = 1


class Executor:
    def __init__(
        self,
        model_def_loader: ModelDefLoader,
        setup_timeout: float,
        prediction_timeout: float,
    ) -> None:
        self._setup_timeout = float(setup_timeout)
        self._predict_timeout = float(prediction_timeout)

        self._conn, conn_in_subproc = mp.Pipe(duplex=True)
        self._lock = Lock()
        self._is_running: bool = False

        self._model: t.Optional[t.Any] = None
        self._input_cls: t.Optional[t.Type[BaseIO]] = None
        self._output_cls: t.Optional[t.Type[BaseIO]] = None

        fd, path_str = tempfile.mkstemp()
        os.close(fd)
        self._setup_log_path = Path(path_str)
        fd, path_str = tempfile.mkstemp()
        self._predict_log_path = Path(path_str)
        os.close(fd)

        self._subproc = WorkerSubprocess(
            model_def_loader,
            conn_in_subproc,
            self._setup_log_path,
            self._predict_log_path,
        )

    def setup(self) -> bool:
        start_time = time.monotonic()

        try:
            log_file_redirector = LogFileRedirector(self._setup_log_path)
            while self._subproc.is_alive() and not self._conn.poll(0.1):
                log_file_redirector.update()
                if time.monotonic() - start_time > self._setup_timeout:
                    self._subproc.terminate()
                    raise server_exceptions.SetupFailed("Timeout")

            if self._subproc.is_alive():
                self._conn.recv()
            log_file_redirector.update()
            if not self._subproc.is_alive():
                return False
            return True
        except BaseException:
            return False

    def predict(
        self,
        inputs: t.List[t.Dict],
        is_demo: bool,
        log_path: t.Optional[Path],
    ) -> t.Union[PredictionSuccess, PredictionFailure]:
        assert self._subproc.pid is not None

        # Acquire lock to block cancelation
        with self._lock:
            req = PredictionRequest(
                inputs=[jsonable_encoder(inp) for inp in inputs],
                is_demo=is_demo,
                log_path=log_path,
            )
            self._conn.send(req)

            start_time = time.monotonic()

            # Wait unitl ack received
            while self._subproc.is_alive() and not self._conn.poll(0.01):
                pass
            if not self._subproc.is_alive():
                raise server_exceptions.SubprocessTerminated(self._predict_log_path.read_text())
            self._conn.recv()

        # Wait until result received
        while self._subproc.is_alive() and not self._conn.poll(0.05):
            if time.monotonic() - start_time > self._predict_timeout:
                os.kill(self._subproc.pid, signal.SIGUSR2)
                break

        if not self._subproc.is_alive():
            raise server_exceptions.SubprocessTerminated(self._predict_log_path.read_text())

        return self._conn.recv()

    def cancel(self):
        with self._lock:
            assert self._subproc.pid is not None
            os.kill(self._subproc.pid, signal.SIGUSR1)

    def start(self):
        self._subproc.start()

    def terminate(self):
        self._subproc.terminate()
