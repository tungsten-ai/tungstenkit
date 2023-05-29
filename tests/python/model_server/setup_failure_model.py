import typing as t

from tungstenkit import BaseIO, TungstenModel, model_config


class Input(BaseIO):
    pass


class Output(BaseIO):
    pass


@model_config(
    include_files=[__file__],
)
class SetupFailureModel(TungstenModel[Input, Output]):
    def setup(self):
        print("failed")
        raise self.exception()

    def predict(self, inputs):
        pass

    @classmethod
    def exception(cls) -> t.Optional[RuntimeError]:
        return RuntimeError("failure")

