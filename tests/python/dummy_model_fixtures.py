import tempfile
from pathlib import Path
from typing import List, Optional
from uuid import uuid4

import pytest
from fastapi.encoders import jsonable_encoder
from w3lib.url import parse_data_uri

from tungstenkit import Image

from .dummy_model import DummyInput, DummyModel, DummyOutput

IMAGE_DATA_URI = r"data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAMAAAADCAAAAABzQ+pjAAAAC0lEQVR4nGNgQAAAAAwAAXxMRMIAAAAASUVORK5CYII="  # noqa
BUILD_DIR = Path(__file__).parent
README_PATH = BUILD_DIR / "bin" / "markdown.md"


@pytest.fixture
def dummy_io_generator():
    def _generate(
        n: int,
        delay: float = 0.05,
        print_log: bool = False,
        failure: bool = False,
        option: str = "option",
        structure_gts: bool = False,
        structure_inputs: bool = True,
        input_file_dir: Optional[Path] = None,
    ):
        inputs: List[DummyInput] = []
        for _ in range(n):
            if input_file_dir:
                fd, path_str = tempfile.mkstemp(suffix="image.png", dir=input_file_dir)
                with open(fd, "wb") as f:
                    b = parse_data_uri(IMAGE_DATA_URI).data
                    f.write(b)
                image = Image.from_path(path_str)
            else:
                image = Image.parse_obj(IMAGE_DATA_URI)
            inputs.append(
                DummyInput(
                    text=uuid4().hex,
                    image=image,
                    delay=delay,
                    print_log=print_log,
                    failure=failure,
                    option=option,
                )
            )
        gts = [DummyOutput(output=inp.text + "output") for inp in inputs]
        if not structure_gts:
            gts = jsonable_encoder(gts)
        if not structure_inputs:
            inputs = jsonable_encoder(inputs)
        return inputs, gts

    return _generate


@pytest.fixture
def dummy_model() -> DummyModel:
    return DummyModel()


__all__ = [
    "dummy_model",
    "dummy_io_generator",
]
