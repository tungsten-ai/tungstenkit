import attrs

from tungstenkit._internal.blob_store import Blob, BlobStore, FileBlobCreatePolicy
from tungstenkit._internal.utils.avatar import fetch_default_avatar_png

from .blob_container import BlobContainer


@attrs.frozen(kw_only=True)
class StoredAvatarData:
    blob: Blob

    @property
    def extension(self) -> str:
        return self.blob.file_path.name.split(".")[-1]


@attrs.define(kw_only=True)
class AvatarData(BlobContainer[StoredAvatarData]):
    bytes_: bytes
    extension: str

    @staticmethod
    def fetch_default(hash_key: str, **kwargs):
        raw = fetch_default_avatar_png(name=hash_key, **kwargs)
        return AvatarData(bytes_=raw, extension=".png")

    def save_blobs(
        self,
        blob_store: BlobStore,
        file_blob_create_policy: FileBlobCreatePolicy = "copy",
    ) -> StoredAvatarData:
        blob = blob_store.add_by_writing((self.bytes_, "avatar" + self.extension))
        return StoredAvatarData(blob=blob)

    @classmethod
    def load_blobs(cls, data: StoredAvatarData) -> "AvatarData":
        return AvatarData(
            bytes_=data.blob.file_path.read_bytes(),
            extension=data.extension,
        )
