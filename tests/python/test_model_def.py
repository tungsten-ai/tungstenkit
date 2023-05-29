import typing as t

import pytest

from tungstenkit import BaseIO, TungstenModel, exceptions

from .dummy_model import DummyInput, DummyOutput


def test_incorrect_inheritance():
    class Input:
        pass

    with pytest.raises(exceptions.TungstenModelError):

        class Model(TungstenModel[Input, DummyOutput]):  # type: ignore
            def predict(self, inputs):
                pass

    class Output:
        pass

    with pytest.raises(exceptions.TungstenModelError):

        class Model_(TungstenModel[DummyInput, Output]):  # type: ignore
            def predict(self, inputs):
                pass


def test_nested_input_fields():
    class ListInput(BaseIO):
        nested: t.List[str]

    with pytest.raises(exceptions.TungstenModelError):

        class Model(TungstenModel[ListInput, DummyOutput]):
            def predict(self, inputs):
                pass

        raise ValueError


def test_not_allowed_io_fields():
    class InvalidInput(BaseIO):
        bytes_: bytes

    with pytest.raises(exceptions.TungstenModelError):

        class Model(TungstenModel[InvalidInput, DummyOutput]):
            def predict(self, inputs):
                pass

    class InvalidOutput(BaseIO):
        bytes_: bytes

    with pytest.raises(exceptions.TungstenModelError):

        class Model_(TungstenModel[DummyInput, InvalidOutput]):
            def predict(self, inputs):
                pass
