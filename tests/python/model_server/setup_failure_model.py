import typing as t

from tungstenkit import BaseIO, define_model


class Input(BaseIO):
    pass


class Output(BaseIO):
    pass


@define_model(
    input=Input,
    output=Output,
    include_files=[__file__],
)
class SetupFailureModel:
    def setup(self):
        print("failed")
        raise self.exception()

    def predict(self, inputs):
        pass

    @classmethod
    def exception(cls) -> t.Optional[RuntimeError]:
        return RuntimeError("failed")
