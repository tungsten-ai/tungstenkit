import tempfile
from pathlib import Path, PurePosixPath
from typing import Dict, List, Optional
from uuid import uuid4

import pytest
from fastapi.encoders import jsonable_encoder
from w3lib.url import parse_data_uri

from tungstenkit import Image
from tungstenkit._internal import storables

from .dummy_model import (
    DUMMY_MODEL_BUILD_DIR,
    DUMMY_MODEL_DATA_DIR,
    DUMMY_MODEL_MODULE_PATH,
    DUMMY_MODEL_README_PATH,
    DummyInput,
    DummyModel,
    DummyOutput,
)

IMAGE_DATA_URI = r"data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAMAAAADCAAAAABzQ+pjAAAAC0lEQVR4nGNgQAAAAAwAAXxMRMIAAAAASUVORK5CYII="  # noqa


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


@pytest.fixture(scope="session")
def dummy_model_all_source_files_dict() -> Dict[PurePosixPath, storables.SourceFile]:
    host_paths = [p for p in DUMMY_MODEL_DATA_DIR.glob("**/*") if p.is_symlink() or p.is_file()]
    host_paths += [DUMMY_MODEL_MODULE_PATH]
    model_fs_paths = [PurePosixPath(p.relative_to(DUMMY_MODEL_BUILD_DIR)) for p in host_paths]
    source_files = {
        pm: storables.SourceFile(
            abs_path_in_host_fs=ph,
            rel_path_in_model_fs=pm,
            size=ph.lstat().st_size if ph.is_symlink() else ph.stat().st_size,
        )
        for pm, ph in zip(model_fs_paths, host_paths)
    }
    return source_files


@pytest.fixture(scope="session")
def dummy_model_readme() -> storables.MarkdownData:
    return storables.MarkdownData.from_path(DUMMY_MODEL_README_PATH)


__all__ = [
    "dummy_model",
    "dummy_io_generator",
    "dummy_model_all_source_files_dict",
]
