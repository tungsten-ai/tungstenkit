import typing as t
from pathlib import Path
from uuid import uuid4

import attrs
import pytest

from tungstenkit._internal.blob_store import Blob, BlobStore, FileBlobCreatePolicy
from tungstenkit._internal.json_store import JSONItem, JSONStore
from tungstenkit._internal.storables.json_storable import JSONStorable

hashes: t.Set[str] = set()


@attrs.define
class Item(JSONItem):
    id: str
    repo_name: str
    tag: str
    hash: str
    blob: Blob

    @property
    def blobs(self) -> t.Set[Blob]:
        return {self.blob}

    @property
    def name(self) -> str:
        return self.repo_name + ":" + self.tag

    def cleanup(self):
        hashes.remove(self.hash)

    @staticmethod
    def parse_name(name: str) -> t.Tuple[str, str]:
        splitted = name.split(":")
        if len(splitted) == 1:
            return name, "latest"

        if len(splitted) == 2:
            return splitted[0], splitted[1]

        else:
            raise ValueError


@attrs.define(kw_only=True)
class Storable(JSONStorable[Item]):
    id: str
    repo_name: str
    tag: str
    hash: str
    file: Path

    def save_blobs(
        self, blob_store: BlobStore, file_blob_create_policy: FileBlobCreatePolicy = "copy"
    ) -> Item:
        blob = blob_store.add_by_writing(self.file)
        return Item(id=self.id, repo_name=self.repo_name, tag=self.tag, hash=self.hash, blob=blob)

    @classmethod
    def load_blobs(cls, data: Item):
        path = data.blob.file_path
        return cls(id=data.id, repo_name=data.repo_name, tag=data.tag, hash=data.hash, file=path)


@pytest.fixture
def json_store():
    json_store = JSONStore[Item](Item)
    yield json_store
    json_store.clear_repo(None)


def test_json_store(json_store: JSONStore[Item], tmp_path: Path):
    file1 = tmp_path / "filer1"
    file1.touch()
    file2 = tmp_path / "file2"
    file2.touch()
    item1 = Storable(id=uuid4().hex, repo_name="repo1", tag="tag1", hash="hash1", file=file1)
    item2 = Storable(id=uuid4().hex, repo_name="repo1", tag="tag2", hash="hash1", file=file1)
    item3 = Storable(id=uuid4().hex, repo_name="repo2", tag="tag3", hash="hash2", file=file2)
    hashes.add("hash1")
    hashes.add("hash2")

    blob_store = BlobStore()
    saved = item1.save_blobs(blob_store)
    json_store.add(saved)
    items = json_store.list()
    assert len(items) == 1
    assert {i.tag for i in items} == {item1.tag}

    item1_ = Storable.load_blobs(json_store.get(item1.repo_name + ":" + item1.tag))
    assert item1_.id == item1.id
    assert item1_.tag == item1.tag
    assert item1_.hash == item1.hash

    json_store.add(item2.save_blobs(blob_store))
    json_store.add(item3.save_blobs(blob_store))
    items = json_store.list()
    assert len(items) == 3
    assert {i.repo_name for i in items} == {"repo1", "repo2"}
    assert {i.tag for i in items} == {"tag1", "tag2", "tag3"}

    json_store.delete(item2.repo_name + ":" + item2.tag)
    assert len(json_store.list()) == 2

    json_store.clear_repo("repo1")
    assert item1.hash not in hashes
    assert len(json_store.list()) == 1

    json_store.clear_repo(None)
    assert len(json_store.list()) == 0
