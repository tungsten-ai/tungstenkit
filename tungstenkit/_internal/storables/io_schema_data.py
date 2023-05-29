import json
import typing as t

import attrs

from tungstenkit._internal.blob_store import Blob, BlobStore, FileBlobCreatePolicy
from tungstenkit._internal.io import FileType

from .blob_container import BlobContainer


@attrs.frozen(kw_only=True)
class StoredIOSchemaData:
    input: Blob
    output: Blob
    input_filetypes: Blob
    output_filetypes: Blob


@attrs.define(kw_only=True)
class IOSchemaData(BlobContainer[StoredIOSchemaData]):
    input: t.Dict
    output: t.Dict
    input_filetypes: t.Dict[str, FileType]
    output_filetypes: t.Dict[str, FileType]

    def save_blobs(
        self,
        blob_store: BlobStore,
        file_blob_create_policy: FileBlobCreatePolicy = "copy",
    ) -> StoredIOSchemaData:
        input_schema_blob = blob_store.add_by_writing(
            (json.dumps(self.input).encode("utf-8"), "input_schema.json")
        )
        output_schema_blob = blob_store.add_by_writing(
            (json.dumps(self.output).encode("utf-8"), "output_schema.json")
        )
        input_filetypes_blob = blob_store.add_by_writing(
            (json.dumps(self.input_filetypes).encode("utf-8"), "input_filetypes.json"),
        )
        output_filetypes_blob = blob_store.add_by_writing(
            (json.dumps(self.output_filetypes).encode("utf-8"), "output_filetypes.json"),
        )
        return StoredIOSchemaData(
            input=input_schema_blob,
            output=output_schema_blob,
            input_filetypes=input_filetypes_blob,
            output_filetypes=output_filetypes_blob,
        )

    @classmethod
    def load_blobs(cls, data: StoredIOSchemaData) -> "IOSchemaData":
        return IOSchemaData(
            input=json.loads(data.input.file_path.read_bytes()),
            output=json.loads(data.output.file_path.read_bytes()),
            input_filetypes={
                k: FileType(v)
                for k, v in json.loads(data.input_filetypes.file_path.read_bytes()).items()
            },
            output_filetypes={
                k: FileType(v)
                for k, v in json.loads(data.output_filetypes.file_path.read_bytes()).items()
            },
        )
