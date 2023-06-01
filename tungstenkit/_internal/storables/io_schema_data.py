import json
import typing as t

import attrs

from tungstenkit._internal.blob_store import Blob, BlobStorable, BlobStore, FileBlobCreatePolicy
from tungstenkit._internal.io import FileType


@attrs.frozen(kw_only=True)
class StoredIOSchema:
    input_jsonschema: Blob
    output_jsonschema: Blob
    input_filetypes: Blob
    output_filetypes: Blob


@attrs.define(kw_only=True)
class IOSchemaData(BlobStorable[StoredIOSchema]):
    input_jsonschema: t.Dict
    output_jsonschema: t.Dict
    input_filetypes: t.Dict[str, FileType]
    output_filetypes: t.Dict[str, FileType]

    def save_blobs(
        self,
        blob_store: BlobStore,
        file_blob_create_policy: FileBlobCreatePolicy = "copy",
    ) -> StoredIOSchema:
        input_schema_blob = blob_store.add_by_writing(
            (json.dumps(self.input_jsonschema).encode("utf-8"), "input_schema.json")
        )
        output_schema_blob = blob_store.add_by_writing(
            (json.dumps(self.output_jsonschema).encode("utf-8"), "output_schema.json")
        )
        input_filetypes_blob = blob_store.add_by_writing(
            (json.dumps(self.input_filetypes).encode("utf-8"), "input_filetypes.json"),
        )
        output_filetypes_blob = blob_store.add_by_writing(
            (json.dumps(self.output_filetypes).encode("utf-8"), "output_filetypes.json"),
        )
        return StoredIOSchema(
            input_jsonschema=input_schema_blob,
            output_jsonschema=output_schema_blob,
            input_filetypes=input_filetypes_blob,
            output_filetypes=output_filetypes_blob,
        )

    @classmethod
    def load_blobs(cls, data: StoredIOSchema) -> "IOSchemaData":
        return IOSchemaData(
            input_jsonschema=json.loads(data.input_jsonschema.file_path.read_bytes()),
            output_jsonschema=json.loads(data.output_jsonschema.file_path.read_bytes()),
            input_filetypes={
                k: FileType(v)
                for k, v in json.loads(data.input_filetypes.file_path.read_bytes()).items()
            },
            output_filetypes={
                k: FileType(v)
                for k, v in json.loads(data.output_filetypes.file_path.read_bytes()).items()
            },
        )
