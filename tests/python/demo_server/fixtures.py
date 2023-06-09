import time
from multiprocessing import Process
from pathlib import Path

import pytest
import requests

from tungstenkit._internal import storables
from tungstenkit._internal.demo_server import start_demo_server

DEMO_SERVER_HOST = "localhost"
DEMO_SERVER_PORT = 32483
DEMO_SERVER_BASE_URL = f"http://{DEMO_SERVER_HOST}:{DEMO_SERVER_PORT}"
SETUP_TIMEOUT = 5


@pytest.fixture(scope="session")
def demo_server_base_url(
    dummy_model_data: storables.ModelData, tmpdir_factory: pytest.TempdirFactory
):
    tmp_dir = Path(tmpdir_factory.mktemp("dummy-model-demo-server"))
    proc = Process(
        target=_run,
        args=(dummy_model_data, tmp_dir),
        daemon=True,
    )
    proc.start()
    start_time = time.monotonic()
    while True:
        if not proc.is_alive():
            proc.join()

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


def _run(model_data: storables.ModelData, tmp_dir: Path):
    start_demo_server(
        tmp_dir=tmp_dir,
        model_data=model_data,
        host=DEMO_SERVER_HOST,
        port=DEMO_SERVER_PORT,
    )


__all__ = ["demo_server_base_url"]
