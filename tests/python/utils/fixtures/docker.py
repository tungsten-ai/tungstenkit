from pathlib import Path, PurePosixPath
from uuid import uuid4

import attrs
import pytest

from tungstenkit._internal.utils.docker import get_docker_client, remove_docker_image

DUMMY_FS_ROOT = PurePosixPath("/dummy")


@attrs.frozen
class DummyFSImage:
    name: str = attrs.field(factory=lambda: "dummy-fs:" + uuid4().hex)
    dummy_fs_root: PurePosixPath = DUMMY_FS_ROOT

    def check_fs(self, root_dir: Path):
        expected_files = [root_dir / "somefile", root_dir / "somedir" / "somefile2"]
        for f in expected_files:
            # Check if existing and readable
            assert f.exists()
            f.read_bytes()


@pytest.fixture(scope="module")
def dummy_fs_image():
    docker_client = get_docker_client()
    build_dir = Path(__file__).parent / "dummy_fs_image"

    image = DummyFSImage()
    docker_client.images.build(path=str(build_dir), tag=image.name)
    yield image
    remove_docker_image(image.name, force=True, docker_client=docker_client)
