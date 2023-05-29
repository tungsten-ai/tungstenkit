import abc
import typing as t

from tungstenkit._internal.blob_store import BlobStore, FileBlobCreatePolicy

D = t.TypeVar("D")
S = t.TypeVar("S", bound="BlobContainer")


class BlobContainer(t.Generic[D], abc.ABC):
    @abc.abstractmethod
    def save_blobs(
        self, blob_store: BlobStore, file_blob_create_policy: FileBlobCreatePolicy = "copy"
    ) -> D:
        pass

    @classmethod
    @abc.abstractmethod
    def load_blobs(cls: t.Type[S], data: D) -> S:
        pass
