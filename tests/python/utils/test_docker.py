from pathlib import Path

import pytest

from tungstenkit._internal.utils.docker import copy_from_image
from tungstenkit.exceptions import DockerError

from .fixtures.docker import DummyFSImage


def test_extract_files(dummy_fs_image: DummyFSImage, tmp_path: Path):
    # To existing directory
    copy_from_image(
        dummy_fs_image.name, path_in_image=dummy_fs_image.dummy_fs_root, path_in_host=tmp_path
    )
    dummy_fs_image.check_fs(tmp_path / dummy_fs_image.dummy_fs_root.name)

    # To non-existing directory
    root = tmp_path / "root"
    copy_from_image(
        dummy_fs_image.name, path_in_image=dummy_fs_image.dummy_fs_root, path_in_host=root
    )
    dummy_fs_image.check_fs(tmp_path / dummy_fs_image.dummy_fs_root.name)

    # To file (failure)
    file = tmp_path / "file"
    file.touch()
    with pytest.raises(DockerError):
        copy_from_image(
            dummy_fs_image.name, path_in_image=dummy_fs_image.dummy_fs_root, path_in_host=file
        )
