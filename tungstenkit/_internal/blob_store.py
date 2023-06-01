import abc
import hashlib
import os
import shutil
import tempfile
import typing as t
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path

import attrs
from fasteners import InterProcessReaderWriterLock
from typing_extensions import Literal, TypeAlias

from tungstenkit._internal.constants import DATA_DIR, LOCK_DIR
from tungstenkit._internal.utils.file import list_dirs, list_files

BlobStorableType = t.TypeVar("BlobStorableType", bound="BlobStorable")
BlobContainerType = t.TypeVar("BlobContainerType")
FileBlobCreatePolicy: TypeAlias = Literal["copy", "rename"]
BUF_SIZE_FOR_HASHING = 1048576  # 1MB


@attrs.frozen(kw_only=True, order=True)
class Blob:
    digest: str
    file_path: Path = attrs.field(eq=False, order=False)

    def remove(self):
        shutil.rmtree(self.file_path.parent)


class BlobStorable(abc.ABC, t.Generic[BlobContainerType]):
    @abc.abstractmethod
    def save_blobs(
        self, blob_store: "BlobStore", file_blob_create_policy: FileBlobCreatePolicy = "copy"
    ) -> BlobContainerType:
        pass

    @classmethod
    @abc.abstractmethod
    def load_blobs(cls: t.Type[BlobStorableType], data: BlobContainerType) -> BlobStorableType:
        pass


class BlobStore:
    _base_dir: t.ClassVar[Path] = DATA_DIR / "blobs"
    _lock_path: t.ClassVar[Path] = LOCK_DIR / "blobs.lock"

    __data_dir: Path

    def __init__(self) -> None:
        self.__data_dir = self._base_dir / "data"
        self.__data_dir.mkdir(parents=True, exist_ok=True)
        self._lock = InterProcessReaderWriterLock(path=self._lock_path)

    def list_digests(self) -> t.List[str]:
        return [d.name for base_dir in list_dirs(self.__data_dir) for d in list_dirs(base_dir)]

    def get_by_digest(self, digest: str) -> Blob:
        blob_dir = self._build_blob_dir_path(digest)
        if not blob_dir.exists():
            raise KeyError(f"Blob not found: {digest}")

        return Blob(digest=digest, file_path=list_files(blob_dir)[0])

    def check_if_contained(self, digest: str) -> bool:
        return self._build_blob_dir_path(digest).exists()

    def add_multiple_by_writing(self, *args: t.Union[Path, t.Tuple[bytes, str]]) -> t.List[Blob]:
        """
        Add blobs to the blob cache

        :param args: a sequence of paths and named bytes.
            Each element of list can be either a ``pathlib.Path`` object or
            a tuple of a ``bytes`` object and a file name string.

        :returns: a list of strings representing the blob digests
        """
        if len(args) == 0:
            return []

        to_be_added: t.Dict[str, t.Tuple[str, t.Union[Path, bytes]]] = dict()

        def _hash(idx: int, path_or_named_bytes: t.Union[Path, t.Tuple[bytes, str]]):
            if isinstance(path_or_named_bytes, tuple):
                digest = _hash_bytes(path_or_named_bytes[0])
                new_blob: t.Tuple[str, t.Union[Path, bytes]] = (
                    path_or_named_bytes[1],
                    path_or_named_bytes[0],
                )

            else:
                digest = _hash_file(path_or_named_bytes.resolve())
                new_blob = (path_or_named_bytes.name, path_or_named_bytes)

            if not self.check_if_contained(digest):
                to_be_added[digest] = new_blob

            return idx, digest

        idx_to_digest_mapping: t.Dict[int, str] = dict()
        try:
            with ThreadPoolExecutor(max_workers=min(8, len(args))) as executor:
                for idx, digest in executor.map(_hash, range(len(args)), args):
                    idx_to_digest_mapping[idx] = digest

                list_blob_dir, list_file_name, list_path_or_bytes = [], [], []
                for digest, (file_name, path_or_bytes) in to_be_added.items():
                    list_blob_dir.append(self._build_blob_dir_path(digest))
                    list_file_name.append(file_name)
                    list_path_or_bytes.append(path_or_bytes)
                for _ in executor.map(
                    _write_blob, list_blob_dir, list_file_name, list_path_or_bytes
                ):
                    pass
        except BaseException as e:
            for digest in to_be_added.keys():
                d = self._build_blob_dir_path(digest)
                if d.exists():
                    shutil.rmtree(d)

            raise e

        return [
            self.get_by_digest(idx_to_digest_mapping[idx]) for idx in sorted(idx_to_digest_mapping)
        ]

    def add_by_writing(self, path_or_named_bytes: t.Union[Path, t.Tuple[bytes, str]]) -> Blob:
        return self.add_multiple_by_writing(path_or_named_bytes)[0]

    def add_by_renaming(self, path: Path) -> Blob:
        path = path.resolve()
        digest = _hash_file(path)
        if self.check_if_contained(digest):
            return self.get_by_digest(digest)
        blob_dir = self._build_blob_dir_path(digest)
        blob_dir.mkdir(parents=True)
        os.replace(path.resolve(), blob_dir / path.name)
        return Blob(digest=digest, file_path=path)

    def delete_unused(self, used: t.Set[Blob]) -> None:
        with self._lock.write_lock():
            self._sanitize()
            digests = self.list_digests()
            to_be_removed = []
            for digest in digests:
                blob = self.get_by_digest(digest)
                if blob not in used:
                    to_be_removed.append(blob)

            def remove_blob(blob: Blob):
                shutil.rmtree(blob.file_path.parent)

            with ThreadPoolExecutor(max_workers=8) as executor:
                executor.map(remove_blob, to_be_removed)

    @contextmanager
    def prevent_deletion(self):
        try:
            self._lock.acquire_read_lock()
            yield
        finally:
            self._lock.release_read_lock()

    def _build_blob_dir_path(self, digest: str) -> Path:
        return self.__data_dir / digest[:2] / digest

    def _sanitize(self) -> None:
        """
        Remove blobs whose directory is corrupted.
        """
        digests = self.list_digests()
        to_be_removed = []
        for digest in digests:
            directory = self._build_blob_dir_path(digest)
            if len(list_files(directory)) == 0:
                to_be_removed.append(str(directory))
        if to_be_removed:
            with ThreadPoolExecutor(max_workers=8) as executor:
                executor.map(shutil.rmtree, to_be_removed)


def _hash_bytes(bytes_: bytes) -> str:
    hash_ = hashlib.sha256()
    hash_.update(bytes_)
    return hash_.hexdigest()


def _hash_file(path: Path) -> str:
    hash_ = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            data = f.read(BUF_SIZE_FOR_HASHING)
            if not data:
                break
            hash_.update(data)
    return hash_.hexdigest()


def _write_blob(blob_dir: Path, file_name: str, path_or_bytes: t.Union[Path, bytes]):
    blob_dir.mkdir(parents=True)
    try:
        blob_file_path = blob_dir / file_name
        tmp_file_fd, tmp_file_path_str = tempfile.mkstemp()
        os.close(tmp_file_fd)
        tmp_file_path = Path(tmp_file_path_str)
        if isinstance(path_or_bytes, bytes):
            tmp_file_path.write_bytes(path_or_bytes)
        else:
            shutil.copyfile(path_or_bytes.resolve(), tmp_file_path)
        os.replace(tmp_file_path, blob_file_path)
    except BaseException as e:
        shutil.rmtree(str(blob_dir))
        raise e
