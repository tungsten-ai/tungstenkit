import time
import typing as t
from pathlib import Path

from tungstenkit import BaseIO, Field, Image, Option, define_model

DUMMY_MODEL_MODULE_PATH = Path(__file__)
DUMMY_MODEL_BUILD_DIR = DUMMY_MODEL_MODULE_PATH.parent
DUMMY_MODEL_DATA_DIR = DUMMY_MODEL_BUILD_DIR / "dummy_model_data"
DUMMY_MODEL_README_PATH = DUMMY_MODEL_DATA_DIR / "markdown.md"
DUMMY_MODEL_INCLUDE_FILES = ["./dummy_model.py", DUMMY_MODEL_DATA_DIR.name]


class DummyInput(BaseIO):
    text: str
    image: Image
    delay: float = Field(ge=0.0, le=10.0)
    print_log: bool
    failure: bool
    option: str = Option(default="option")


class DummyOutput(BaseIO):
    output: str


@define_model(
    input=DummyInput,
    output=DummyOutput,
    batch_size=4,
    readme_md=str(DUMMY_MODEL_README_PATH),
    include_files=DUMMY_MODEL_INCLUDE_FILES,
)
class DummyModel:
    failure: bool = False

    def setup(self):
        time.sleep(2)
        self.dummy = "dummy"

        if self.failure:
            print("failed")
            raise RuntimeError("failed")

    def predict(self, inputs: t.List[DummyInput]) -> t.List[DummyOutput]:
        option = inputs[0].option
        assert all(inp.option == option for inp in inputs[1:])
        assert self.dummy == "dummy"
        if any(inp.print_log for inp in inputs):
            print(self.build_log(len(inputs)))
        delay = max(inp.delay for inp in inputs)
        num_sleeps = int(delay / 0.1)
        for _ in range(num_sleeps):
            time.sleep(0.1)
        if any(inp.failure for inp in inputs):
            raise RuntimeError("failed")
        return [DummyOutput(output=input.text + "output") for input in inputs]

    @classmethod
    def exception(cls) -> t.Optional[RuntimeError]:
        if cls.failure:
            return RuntimeError("failed")
        return None

    @staticmethod
    def build_log(num_inputs: int):
        return f"Process {num_inputs} inputs"
