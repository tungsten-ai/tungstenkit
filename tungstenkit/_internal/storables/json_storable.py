import typing as t
from uuid import uuid4

from tungstenkit._internal.blob_store import BlobStore, FileBlobCreatePolicy
from tungstenkit._internal.container_metadata_store import (
    ContainerMetadataStore,
    StoredContainerMetadata,
)
from tungstenkit._internal.utils.types import get_superclass_type_args

from .blob_container import BlobContainer

D = t.TypeVar("D", bound=StoredContainerMetadata)
S = t.TypeVar("S", bound="JSONStorable")


class JSONStorable(BlobContainer[D]):
    _store: ContainerMetadataStore[D]

    def save(self, file_blob_create_policy: FileBlobCreatePolicy = "copy") -> D:
        blob_store = BlobStore()
        with blob_store.prevent_deletion():
            data = self.save_blobs(blob_store, file_blob_create_policy)
            store = self._get_store()
            store.add(data)
            store.tag(data.name, data.repo_name + ":latest")
        return data

    @classmethod
    def load(cls: t.Type[S], name: str) -> S:
        data = cls._get_store().get(name)
        return cls.load_blobs(data)

    @staticmethod
    def generate_id() -> str:
        return uuid4().hex

    @classmethod
    def _get_store(cls: t.Type[S]) -> ContainerMetadataStore[D]:
        if not hasattr(cls, "_store"):
            args = get_superclass_type_args(cls, JSONStorable)
            if len(args) == 0:
                raise RuntimeError("Type argument is not set")
            data_cls: t.Type[D] = args[0]
            cls._store = ContainerMetadataStore[data_cls](data_cls)  # type: ignore
        return cls._store
