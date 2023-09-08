import typing as t

import attrs

from tungstenkit._internal.blob_store import Blob, BlobStorable, BlobStore, FileBlobCreatePolicy
from tungstenkit._internal.io import FileType
from tungstenkit._internal.utils import serialize


@attrs.frozen(kw_only=True)
class StoredModelIOData:
    blob: Blob


@attrs.define(kw_only=True)
class ModelIOData(BlobStorable[StoredModelIOData]):
    input_schema: t.Dict
    output_schema: t.Dict
    demo_output_schema: t.Dict
    input_filetypes: t.Dict[str, FileType]
    output_filetypes: t.Dict[str, FileType]
    demo_output_filetypes: t.Dict[str, FileType]

    def save_blobs(
        self,
        blob_store: BlobStore,
        file_blob_create_policy: FileBlobCreatePolicy = "copy",
    ) -> StoredModelIOData:
        bytes_ = serialize.convert_attrs_to_json(self).encode("utf-8")
        blob = blob_store.add_by_writing((bytes_, "model-io.json"))
        return StoredModelIOData(blob=blob)

    @classmethod
    def load_blobs(cls, data: StoredModelIOData) -> "ModelIOData":
        return serialize.load_attrs_from_json(cls, data.blob.file_path)
