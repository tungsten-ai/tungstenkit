from pathlib import Path

import pytest

from tungstenkit._internal.containers import start_model_container
from tungstenkit._internal.storables import ModelData


@pytest.fixture(scope="session")
def dummy_model_container(dummy_model_image_name: str, tmpdir_factory: pytest.TempdirFactory):
    with start_model_container(
        ModelData.load(dummy_model_image_name),
        Path(tmpdir_factory.mktemp("dummy-model-container")),
    ) as container:
        yield container


__all__ = ["dummy_model_container"]
