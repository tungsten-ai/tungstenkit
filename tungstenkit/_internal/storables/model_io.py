import typing as t

import attrs

from tungstenkit._internal.blob_store import Blob, BlobStorable, BlobStore, FileBlobCreatePolicy
from tungstenkit._internal.io import FieldAnnotation
from tungstenkit._internal.utils import serialize


@attrs.frozen(kw_only=True)
class StoredModelIOData:
    blob: Blob


@attrs.define(kw_only=True)
class ModelIOData(BlobStorable[StoredModelIOData]):
    input_schema: t.Dict
    output_schema: t.Dict
    demo_output_schema: t.Dict

    input_filetypes: t.Optional[t.Dict[str, FieldAnnotation]] = None  # legacy
    output_filetypes: t.Optional[t.Dict[str, FieldAnnotation]] = None  # legacy
    demo_output_filetypes: t.Optional[t.Dict[str, FieldAnnotation]] = None  # legacy

    input_annotations: t.Dict[str, FieldAnnotation] = attrs.field(factory=dict)
    output_annotations: t.Dict[str, FieldAnnotation] = attrs.field(factory=dict)
    demo_output_annotations: t.Dict[str, FieldAnnotation] = attrs.field(factory=dict)

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
        deserailized = serialize.load_attrs_from_json(cls, data.blob.file_path)

        # Update legacy json
        if deserailized.input_filetypes:
            deserailized.input_annotations = deserailized.input_filetypes
            deserailized.input_filetypes = None
        if deserailized.output_filetypes:
            deserailized.output_annotations = deserailized.output_filetypes
            deserailized.output_filetypes = None
        if deserailized.demo_output_filetypes:
            deserailized.demo_output_annotations = deserailized.demo_output_filetypes
            deserailized.demo_output_filetypes = None

        return deserailized
