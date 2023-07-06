# TODO complete this
# Goal: Prevent fetching metadata everytime

import typing as t
from datetime import datetime
from pathlib import Path

import attrs
import cattrs
from filelock import FileLock

from tungstenkit._internal.containerize.base_images import BaseImage
from tungstenkit._internal.containerize.gpu_pkg_collections import (
    GPUPackageCollection,
    gpu_pkg_collection_class_dict,
)
from tungstenkit._internal.utils.file import write_safely
from tungstenkit._internal.utils.serialize import convert_attrs_to_json, load_attrs_from_json
from tungstenkit.exceptions import StoredDataError

METADATA_DIR = Path(__file__).parent
METADATA_REFRESH_INTERVAL_DAYS = 15
FILELOCK_TIMEOUT = 180.0


@attrs.define
class MetadataInfo:
    path: Path

    updated_at: datetime = attrs.field(factory=datetime.utcnow, init=False)


@attrs.define
class MetadataCollection:
    gpu_pkg_metadata: t.Dict[str, MetadataInfo] = attrs.field(factory=dict)
    docker_image_metadata: t.Dict[str, MetadataInfo] = attrs.field(factory=dict)


class MetadataLoader:
    collection_path: Path = METADATA_DIR / "metadata-collection.json"
    collection_lock_path: Path = METADATA_DIR / "metadata-collection.json.lock"
    gpu_pkg_metadata_dir: Path = METADATA_DIR / "gpu_pkgs"
    base_image_metadata_dir: Path = METADATA_DIR / "base_images"

    def __init__(self) -> None:
        self.collection_filelock = FileLock(self.collection_lock_path, timeout=180.0)

    def load_gpu_pkg_collection(self, collection_name: str) -> GPUPackageCollection:
        metadata_class = gpu_pkg_collection_class_dict[collection_name]
        metadata_collection = self._load_metadata_collection()

        if (
            collection_name not in metadata_collection.gpu_pkg_metadata
            or (
                datetime.utcnow()
                - metadata_collection.gpu_pkg_metadata[collection_name].updated_at
            ).days
            > METADATA_REFRESH_INTERVAL_DAYS
        ):
            self.update_gpu_pkg_collection(metadata_class.from_remote())
        path = metadata_collection.gpu_pkg_metadata[collection_name].path
        return load_attrs_from_json(metadata_class, path)

    def update_gpu_pkg_collection(self, gpu_pkg_collection: GPUPackageCollection):
        filename = gpu_pkg_collection.name() + "-metadata.json"
        blob = blob_store.add_by_writing(
            (convert_attrs_to_json(gpu_pkg_collection).encode("utf-8"), filename)
        )
        with self.collection_filelock:
            metadata_collection = self._load_metadata_collection()
            metadata_collection.gpu_pkg_metadata[gpu_pkg_collection.name()] = StoredMetadata(
                data_json=blob
            )
            self._save_metadata_collection(metadata_collection)

    @classmethod
    def load_gpu_pkg_metadata(cls, collection_name: str):
        path = cls.build_gpu_pkg_metadata_path(gpu_pkg_collection_class_dict[collection_name])

    @classmethod
    def load_metadata(cls, metadata_cls, name: str, base_dir: Path):
        with 
        path = cls.build_metadata_path(name, base_dir)
        try:
            metadata = load_attrs_from_json(metadata_cls, path)
        except cattrs.errors.ClassValidationError:
            cls._raise_data_parse_error()
        return metadata

    @classmethod
    def save_metadata(cls, metadata, name: str, base_dir: Path):
        serialized = convert_attrs_to_json(metadata)
        path = cls.build_metadata_path(name, base_dir)
        write_safely(path, serialized)


    @staticmethod
    def build_metadata_dir(name: str, base_dir: Path):
        return base_dir / (name + ".json")

    @classmethod
    def _load_metadata_collection(cls) -> MetadataCollection:
        with FileLock(cls.collection_lock_path, timeout=FILELOCK_TIMEOUT):
            if not cls.collection_path.exists():
                return MetadataCollection()

            try:
                col = load_attrs_from_json(MetadataCollection, cls.collection_path)
            except cattrs.errors.ClassValidationError:
                cls._raise_data_parse_error()
            return col

    @classmethod
    def _save_metadata_collection(cls, model_collection: MetadataCollection):
        with FileLock(cls.collection_lock_path, timeout=FILELOCK_TIMEOUT):
            serialized = convert_attrs_to_json(model_collection)
            write_safely(cls.collection_path, serialized)

    @staticmethod
    def _raise_data_parse_error():
        raise StoredDataError(
            "Failed to parse stored model data. "
            "The reason might be that an old version of data still remains.\n"
            f"Please remove the directory '{METADATA_DIR}' and retry."
        )
