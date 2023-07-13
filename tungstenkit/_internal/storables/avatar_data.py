import attrs

from tungstenkit._internal.blob_store import Blob, BlobStorable, BlobStore, FileBlobCreatePolicy
from tungstenkit._internal.utils.avatar import fetch_default_avatar_png

DEFAULT_DOMAIN = "avatar.tungsten-ai.com"


@attrs.frozen(kw_only=True)
class StoredAvatar:
    blob: Blob

    @property
    def extension(self) -> str:
        return "." + self.blob.file_path.name.split(".")[-1]


@attrs.define(kw_only=True)
class AvatarData(BlobStorable[StoredAvatar]):
    bytes_: bytes
    extension: str

    @staticmethod
    def fetch_default(hash_key: str, avatar_domain: str = DEFAULT_DOMAIN, **kwargs):
        raw = fetch_default_avatar_png(hash_key=hash_key + "@" + avatar_domain, **kwargs)
        return AvatarData(bytes_=raw, extension=".png")

    def save_blobs(
        self,
        blob_store: BlobStore,
        file_blob_create_policy: FileBlobCreatePolicy = "copy",
    ) -> StoredAvatar:
        filename = "avatar" + self.extension
        blob = blob_store.add_by_writing((self.bytes_, filename))
        return StoredAvatar(blob=blob)

    @classmethod
    def load_blobs(cls, data: StoredAvatar) -> "AvatarData":
        return AvatarData(
            bytes_=data.blob.file_path.read_bytes(),
            extension=data.extension,
        )
