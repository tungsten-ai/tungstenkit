import typing as t
from pathlib import Path, PurePosixPath

import attrs

from tungstenkit._internal import constants
from tungstenkit._internal.blob_store import Blob, BlobStorable, BlobStore, FileBlobCreatePolicy
from tungstenkit._internal.utils.serialize import convert_attrs_to_json, load_attrs_from_json


@attrs.define(kw_only=True, hash=True)
class StoredSourceFile:
    path: PurePosixPath
    blob: t.Optional[Blob]
    size: int

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def is_skipped(self) -> bool:
        return self.blob is None


@attrs.frozen(kw_only=True)
class StoredSourceFileCollection:
    files: t.List[StoredSourceFile] = attrs.field(factory=list)

    def add(self, file: StoredSourceFile) -> None:
        self.files.append(file)


@attrs.frozen(kw_only=True)
class SerializedSourceFileCollection:
    blob: Blob


@attrs.define(kw_only=True, hash=True)
class SourceFile:
    rel_path_in_model_fs: PurePosixPath
    abs_path_in_host_fs: t.Optional[Path] = None
    size: int

    @property
    def name(self) -> str:
        return self.rel_path_in_model_fs.name

    @property
    def folder(self) -> t.Optional[PurePosixPath]:
        parent = self.rel_path_in_model_fs.parent
        if parent == PurePosixPath("."):
            return None
        return parent

    @property
    def is_skipped(self) -> bool:
        return self.abs_path_in_host_fs is None


@attrs.define(kw_only=True, init=False)
class SourceFileCollection(BlobStorable[SerializedSourceFileCollection]):
    files: t.Set[SourceFile] = attrs.field(factory=set)

    def __init__(self, files: t.Optional[t.Iterable[SourceFile]] = None) -> None:
        self.__attrs_init__()
        if files is None:
            return

        for f in files:
            if not isinstance(f, SourceFile):
                raise TypeError(f"expected 'SourceFile', not {type(f)}")

            if (
                f.abs_path_in_host_fs is None
                or f.size > constants.MAX_SOURCE_FILE_SIZE
                or f.abs_path_in_host_fs.is_symlink()
            ):
                self.add(SourceFile(rel_path_in_model_fs=f.rel_path_in_model_fs, size=f.size))
            else:
                self.add(f)

    def add(self, file: SourceFile) -> None:
        self.files.add(file)

    def save_blobs(
        self, blob_store: BlobStore, file_blob_create_policy: FileBlobCreatePolicy = "copy"
    ) -> SerializedSourceFileCollection:
        saved_path_dict = {
            f.rel_path_in_model_fs: f.abs_path_in_host_fs
            for f in self.files
            if f.abs_path_in_host_fs is not None
        }
        if file_blob_create_policy == "copy":
            blobs = blob_store.add_multiple_by_writing(*saved_path_dict.values())
            blob_dict = {n: b for n, b in zip(saved_path_dict.keys(), blobs)}
        else:
            blob_dict = dict()
            for n, p in saved_path_dict.items():
                blob_dict[n] = blob_store.add_by_renaming(p)

        stored = StoredSourceFileCollection()
        for f in self.files:
            blob = None
            if f.rel_path_in_model_fs in blob_dict:
                blob = blob_dict[f.rel_path_in_model_fs]

            stored.add(
                StoredSourceFile(
                    path=f.rel_path_in_model_fs,
                    blob=blob,
                    size=f.size,
                )
            )

        serialized = blob_store.add_by_writing(
            (convert_attrs_to_json(stored).encode("utf-8"), "source_files.json")
        )

        return SerializedSourceFileCollection(blob=serialized)

    @classmethod
    def load_blobs(cls, data: SerializedSourceFileCollection) -> "SourceFileCollection":
        try:
            stored_col = load_attrs_from_json(StoredSourceFileCollection, data.blob.file_path)
        except Exception as e:
            print(data.blob.file_path)
            raise e
        col = cls()
        for stored_src_file in stored_col.files:
            abs_path_in_host_fs = (
                None if stored_src_file.blob is None else stored_src_file.blob.file_path
            )
            col.add(
                SourceFile(
                    rel_path_in_model_fs=stored_src_file.path,
                    abs_path_in_host_fs=abs_path_in_host_fs,
                    size=stored_src_file.size,
                )
            )

        return col
