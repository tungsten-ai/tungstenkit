import typing as t

import pytest

from tungstenkit import BaseIO, Image
from tungstenkit._internal.model_def import define_model

from .dummy_model import DummyInput, DummyModel, DummyOutput


def test_set_model_attrs():
    assert DummyModel.__tungsten_input__ == DummyInput
    assert DummyModel.__tungsten_output__ == DummyOutput
    assert DummyModel.__tungsten_demo_output__ == DummyOutput

    class DemoOutput(BaseIO):
        image: Image

    @define_model(input=DummyInput, output=DummyOutput, demo_output=DemoOutput)
    class Model:
        def predict(self, inputs):
            pass

        def predict_demo(self, inputs):
            pass

    assert Model.__tungsten_input__ == DummyInput
    assert Model.__tungsten_output__ == DummyOutput
    assert Model.__tungsten_demo_output__ == DemoOutput


def test_io_type_validation():
    class Input:
        pass

    with pytest.raises(TypeError):

        @define_model(input=Input, output=DummyOutput)
        class Model:
            def predict(self, inputs):
                pass

    class Output:
        pass

    with pytest.raises(TypeError):

        @define_model(input=Input, output=DummyOutput)
        class Model_:
            def predict(self, inputs):
                pass


def test_io_field_validation():
    class InputWithList(BaseIO):
        nested: t.List[str]

    with pytest.raises(TypeError):

        @define_model(input=InputWithList, output=DummyOutput)
        class Model:
            def predict(self, inputs):
                pass

    class InputWithBytes(BaseIO):
        bytes_: bytes

    with pytest.raises(TypeError):

        @define_model(input=InputWithBytes, output=DummyOutput)
        class Model_:
            def predict(self, inputs):
                pass

    class OutputWithBytes(BaseIO):
        bytes_: bytes

    with pytest.raises(TypeError):

        @define_model(input=DummyInput, output=OutputWithBytes)
        class Model__:
            def predict(self, inputs):
                pass


def test_demo_output_validation():
    class DemoOutput(BaseIO):
        image: Image

    with pytest.raises(TypeError):

        @define_model(input=DummyInput, output=DummyOutput, demo_output=DemoOutput)
        class Model:
            def predict(self, inputs):
                pass

    with pytest.raises(ValueError):

        @define_model(input=DummyInput, output=DummyOutput)
        class Model_:
            def predict(self, inputs):
                pass

            def predict_demo(self, inputs):
                pass
