import io
import os
import shutil
import subprocess
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

import attrs
import pytest
import requests

from tungstenkit._internal import model_server
from tungstenkit._internal.model_server.config import (
    BaseModelServerSettings,
    FileTunnelSettings,
    StandaloneSettings,
)
from tungstenkit._internal.model_server.enums import ModelServerMode

from .. import dummy_model


@pytest.fixture(scope="module")
def standalone_model_server():
    with _setup_model_server_context() as ctx:
        settings = StandaloneSettings(
            TUNGSTEN_MODEL_CLASS=ctx.model_class, TUNGSTEN_MODEL_MODULE=ctx.model_module
        )
        with _run_model_server(
            mode=ModelServerMode.STANDALONE, settings=settings, ctx=ctx
        ) as service:
            yield service


@pytest.fixture(scope="module")
def file_tunnel_model_server():
    with _setup_model_server_context() as ctx:
        mount_point = ctx.base_dir / "mount"
        mount_point.mkdir()
        settings = FileTunnelSettings(
            TUNGSTEN_MODEL_CLASS=ctx.model_class,
            TUNGSTEN_MODEL_MODULE=ctx.model_module,
            MOUNT_POINT=mount_point,
        )
        with _run_model_server(
            mode=ModelServerMode.STANDALONE, settings=settings, ctx=ctx
        ) as service:
            yield service


@attrs.define(kw_only=True)
class ModelServerContext:
    base_dir: Path
    working_dir: Path
    log_path: Path
    model_module: str
    model_class: str


@attrs.define(kw_only=True)
class ModelServer:
    url: str
    mount_point: Optional[Path] = None
    ctx: ModelServerContext
    settings: BaseModelServerSettings


@contextmanager
def _setup_model_server_context() -> Generator[ModelServerContext, None, None]:
    with tempfile.TemporaryDirectory() as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)
        working_dir = tmp_dir / "cwd"
        working_dir.mkdir()
        log_path = tmp_dir / "logs"
        shutil.copy(dummy_model.__file__, working_dir)

        yield ModelServerContext(
            base_dir=tmp_dir,
            working_dir=working_dir,
            log_path=log_path,
            model_class=dummy_model.DummyModel.__name__,
            model_module="dummy_model",
        )


@contextmanager
def _run_model_server(
    mode: ModelServerMode, settings: BaseModelServerSettings, ctx: ModelServerContext
) -> Generator[ModelServer, None, None]:
    proc: Optional[subprocess.Popen] = None
    f: Optional[io.BufferedIOBase] = None
    try:
        env = os.environ.copy()
        env.update({key: str(value) for key, value in settings.dict().items()})

        port = 32220

        args = [
            "python",
            "-m",
            model_server.__name__,
            "-p",
            str(port),
            "--max-batch-size",
            "4",
            "-m",
            mode.value,
        ]
        f = open(ctx.log_path, "wb")
        proc = subprocess.Popen(args=args, stdout=f, stderr=f, env=env, cwd=ctx.working_dir)
        is_alive = not proc.poll()
        resp = None
        while is_alive and (resp is None or not resp.ok):
            try:
                resp = requests.get(f"http://localhost:{port}/", timeout=5)
                resp.raise_for_status()
            except requests.ConnectionError:
                time.sleep(0.1)
                is_alive = not proc.poll()
                continue

        if not is_alive:
            raise RuntimeError(
                f"""Model server process terminated.
                logs:
                {ctx.log_path.read_text()}"""
            )
        if resp is None:
            raise RuntimeError("Model server failed to setup")

        yield ModelServer(url=f"http://localhost:{port}", ctx=ctx, settings=settings)
    finally:
        if proc:
            proc.kill()
        if f:
            f.close()


__all__ = ["standalone_model_server", "file_tunnel_model_server"]
