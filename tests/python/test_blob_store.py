from pathlib import Path

import pytest

from tungstenkit._internal.blob_store import BlobStore


@pytest.fixture(scope="module")
def blob_store():
    blob_store = BlobStore()
    yield blob_store
    blob_store.delete_unused(set())


def test_blob_store(blob_store: BlobStore, tmp_path: Path):
    first_blob_path = tmp_path / "a b c"
    first_blob_path.write_bytes(b"blob1")
    blobs = blob_store.add_multiple_by_writing((b"blob1", "a b c"), first_blob_path)
    assert first_blob_path.exists()
    assert blobs[0] == blobs[1]

    blobs.append(blob_store.add_by_writing((b"blob2", "a b c")))
    assert blobs[0] != blobs[2]

    second_blob_dir = tmp_path / "my folder"
    second_blob_dir.mkdir()
    second_blob_path = second_blob_dir / "a b c"
    second_blob_path.write_bytes(b"blob2")
    blobs.append(blob_store.add_by_renaming(second_blob_path))
    assert blobs[0] != blobs[3]
    assert blobs[2] == blobs[3]

    assert len(blob_store.list_digests()) == 2
    assert blobs[0].file_path.read_bytes() == b"blob1"
    assert blobs[1].file_path.read_bytes() == b"blob1"
    assert blobs[2].file_path.read_bytes() == b"blob2"
    assert blobs[3].file_path.read_bytes() == b"blob2"

    blob_store.delete_unused(used={blobs[0]})
    assert len(blob_store.list_digests()) == 1
