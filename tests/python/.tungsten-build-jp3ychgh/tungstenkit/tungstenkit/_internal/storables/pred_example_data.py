import hashlib
import json
import typing as t
from pathlib import Path

import attrs

from tungstenkit._internal.blob_store import Blob, BlobStorable, BlobStore, FileBlobCreatePolicy
from tungstenkit._internal.utils.json import apply_to_jsonable
from tungstenkit._internal.utils.uri import get_path_from_file_url


@attrs.frozen(kw_only=True)
class StoredPredExampleData:
    id: str
    input: Blob
    output: Blob
    demo_output: Blob
    input_files: t.List[Blob] = attrs.field(factory=list)
    output_files: t.List[Blob] = attrs.field(factory=list)
    logs: t.Optional[Blob] = None

    @property
    def files(self):
        return self.input_files + self.output_files


@attrs.define(kw_only=True)
class PredExampleData(BlobStorable[StoredPredExampleData]):
    input: t.Dict
    output: t.Dict
    demo_output: t.Dict
    input_files: t.List[Path] = attrs.field(factory=list)
    output_files: t.List[Path] = attrs.field(factory=list)
    logs: t.Optional[str] = None

    def save_blobs(
        self,
        blob_store: BlobStore,
        file_blob_create_policy: FileBlobCreatePolicy = "copy",
    ) -> StoredPredExampleData:
        input_file_uris = []
        output_file_uris = []

        def append_input_file(file_uri: str) -> str:
            input_file_uris.append(file_uri)
            return file_uri

        def append_output_file(file_uri: str) -> str:
            output_file_uris.append(file_uri)
            return file_uri

        input_json = apply_to_jsonable(
            self.input,
            cond=lambda value: isinstance(value, str) and value.startswith("file:///"),
            fn=append_input_file,
        )
        output_json = apply_to_jsonable(
            self.output,
            cond=lambda value: isinstance(value, str) and value.startswith("file:///"),
            fn=append_output_file,
        )
        demo_output_json = apply_to_jsonable(
            self.demo_output,
            cond=lambda value: isinstance(value, str) and value.startswith("file:///"),
            fn=append_output_file,
        )

        input_file_uri_mapping: t.Dict[str, str] = dict()
        output_file_uri_mapping: t.Dict[str, str] = dict()
        input_file_paths = [get_path_from_file_url(file_uri) for file_uri in input_file_uris]
        if file_blob_create_policy == "copy":
            input_file_blobs = blob_store.add_multiple_by_writing(*input_file_paths)
        else:
            input_file_blobs = [blob_store.add_by_renaming(p) for p in input_file_paths]
        for file_uri, blob in zip(input_file_uris, input_file_blobs):
            input_file_uri_mapping[file_uri] = blob.file_path.as_uri()

        output_file_paths = [get_path_from_file_url(file_uri) for file_uri in output_file_uris]
        if file_blob_create_policy == "copy":
            output_file_blobs = blob_store.add_multiple_by_writing(*output_file_paths)
        else:
            output_file_blobs = [blob_store.add_by_renaming(p) for p in output_file_paths]
        for file_uri, blob in zip(output_file_uris, output_file_blobs):
            output_file_uri_mapping[file_uri] = blob.file_path.as_uri()

        input_json = apply_to_jsonable(
            input_json,
            cond=lambda value: value in input_file_uri_mapping,
            fn=lambda value: input_file_uri_mapping[value],
        )
        output_json = apply_to_jsonable(
            output_json,
            cond=lambda value: value in output_file_uri_mapping,
            fn=lambda value: output_file_uri_mapping[value],
        )
        demo_output_json = apply_to_jsonable(
            demo_output_json,
            cond=lambda value: value in output_file_uri_mapping,
            fn=lambda value: output_file_uri_mapping[value],
        )

        input_bytes = json.dumps(input_json).encode("utf-8")
        output_bytes = json.dumps(output_json).encode("utf-8")
        demo_bytes = json.dumps(demo_output_json).encode("utf-8")
        input_blob, output_blob, demo_blob = blob_store.add_multiple_by_writing(
            (input_bytes, "input.json"),
            (output_bytes, "output.json"),
            (demo_bytes, "output.json"),
        )
        if self.logs:
            logs_bytes = self.logs.encode("utf-8")
            logs_blob = blob_store.add_by_writing((logs_bytes, "logs"))
        else:
            logs_blob = None

        # Compute example id
        hash_ = hashlib.sha1()
        hash_.update(input_bytes)
        hash_.update(output_bytes)
        hash_.update(demo_bytes)
        if self.logs:
            hash_.update(logs_bytes)

        example_id = hash_.hexdigest()

        stored = StoredPredExampleData(
            id=example_id,
            input=input_blob,
            output=output_blob,
            demo_output=demo_blob,
            input_files=input_file_blobs,
            output_files=output_file_blobs,
            logs=logs_blob,
        )
        return stored

    @classmethod
    def load_blobs(cls, data: StoredPredExampleData) -> "PredExampleData":
        input = json.loads(data.input.file_path.read_bytes())
        output = json.loads(data.output.file_path.read_bytes())
        demo_output = json.loads(data.demo_output.file_path.read_bytes())
        input_files = [f.file_path for f in data.input_files]
        output_files = [f.file_path for f in data.output_files]
        return PredExampleData(
            input=input,
            output=output,
            demo_output=demo_output,
            input_files=input_files,
            output_files=output_files,
        )
