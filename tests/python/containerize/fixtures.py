import pytest

from tungstenkit._internal.containerize import containerize_model
from tungstenkit._internal.utils.docker_client import remove_docker_image

from .. import dummy_model


@pytest.fixture(scope="session")
def dummy_model_image_name():
    built = containerize_model(
        dummy_model.DUMMY_MODEL_BUILD_DIR,
        module_ref="dummy_model",
        class_name=dummy_model.DummyModel.__name__,
    )
    yield built.name
    remove_docker_image(built.name, force=True)


__all__ = ["dummy_model_image_name"]
