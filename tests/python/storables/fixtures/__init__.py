import pytest

from tungstenkit._internal import storables


@pytest.fixture(scope="session")
def dummy_model_data(dummy_model_image_name: str) -> storables.ModelData:
    return storables.ModelData.load(dummy_model_image_name)


__all__ = ["dummy_model_data"]
