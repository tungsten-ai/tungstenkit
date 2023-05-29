import time
from multiprocessing import Process
from pathlib import Path

import pytest
import requests
import uvicorn

from tungstenkit._internal.containers import ModelContainer
from tungstenkit._internal.demo_server import create_demo_app

DEMO_SERVER_HOST = "localhost"
DEMO_SERVER_PORT = 32483
DEMO_SERVER_BASE_URL = f"http://{DEMO_SERVER_HOST}:{DEMO_SERVER_PORT}"
SETUP_TIMEOUT = 5


@pytest.fixture(scope="session")
def demo_server_base_url(
    dummy_model_container: ModelContainer, tmpdir_factory: pytest.TempdirFactory
):
    app = create_demo_app(
        tmp_dir=Path(tmpdir_factory.mktemp("dummy-model-demo-server")),
        model_container=dummy_model_container,
    )
    proc = Process(
        target=uvicorn.run,
        args=(app,),
        kwargs={"host": DEMO_SERVER_HOST, "port": DEMO_SERVER_PORT},
        daemon=True,
    )
    proc.start()
    start_time = time.monotonic()
    while True:
        assert proc.is_alive()
        assert time.monotonic() - start_time < SETUP_TIMEOUT
        try:
            requests.get(DEMO_SERVER_BASE_URL)
            break
        except requests.ConnectionError:
            time.sleep(0.1)
            continue

    yield DEMO_SERVER_BASE_URL
    proc.kill()


__all__ = ["demo_server_base_url"]
