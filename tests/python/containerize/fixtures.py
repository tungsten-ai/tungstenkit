from unittest.mock import patch

import pytest

import tungstenkit._internal.storables.source_file_data
from tungstenkit._internal.containerize import build_model
from tungstenkit._internal.utils.docker import remove_docker_image

from .. import dummy_model


@pytest.fixture(scope="session")
# @patch.object(tungstenkit._internal.storables.source_file_data, "MAX_SOURCE_FILE_SIZE", 10 * 1024)
def dummy_model_image_name():
    with patch.object(
        tungstenkit._internal.storables.source_file_data, "MAX_SOURCE_FILE_SIZE", 10 * 1024
    ):
        built = build_model(
            dummy_model.BUILD_DIR,
            module_ref="dummy_model",
            class_name=dummy_model.DummyModel.__name__,
        )
        yield built.name
        remove_docker_image(built.name, force=True)


__all__ = ["dummy_model_image_name"]
