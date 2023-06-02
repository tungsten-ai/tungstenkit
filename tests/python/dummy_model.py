import time
import typing as t
from pathlib import Path

from tungstenkit import BaseIO, Field, Image, Option, define_model

BUILD_DIR = Path(__file__).parent
README_PATH = BUILD_DIR / "bin" / "markdown.md"
INCLUDE_FILES = ["./dummy_model.py", "./bin"]


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
    readme_md=str(README_PATH),
    include_files=INCLUDE_FILES,
)
class DummyModel:
    failure: bool = False

    def setup(self):
        time.sleep(2)
        self.dummy = "dummy"

        if self.failure:
            print("failed")
            raise RuntimeError("failure")

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
            raise RuntimeError("failure")
        return [DummyOutput(output=input.text + "output") for input in inputs]

    @classmethod
    def exception(cls) -> t.Optional[RuntimeError]:
        if cls.failure:
            return RuntimeError("failure")
        return None

    @staticmethod
    def build_log(num_inputs: int):
        return f"Process {num_inputs} inputs"
