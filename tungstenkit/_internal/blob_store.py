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

FileBlobCreatePolicy: TypeAlias = Literal["copy", "rename"]
BUF_SIZE_FOR_HASHING = 1048576  # 1MB


@attrs.frozen(kw_only=True, order=True)
class Blob:
    digest: str
    file_path: Path = attrs.field(eq=False, order=False)

    def remove(self):
        shutil.rmtree(self.file_path.parent)


class BlobStore:
    _base_dir: Path = DATA_DIR / "blobs"
    _lock_path: Path = LOCK_DIR / "blobs.lock"

    @property
    def _data_dir(self) -> Path:
        return self._base_dir / "data"

    def __init__(self) -> None:
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._lock = InterProcessReaderWriterLock(path=self._lock_path)

    def list_digests(self) -> t.List[str]:
        return [d.name for d in list_dirs(self._data_dir)]

    def get_by_digest(self, digest: str) -> Blob:
        blob_dir = self._data_dir / digest
        if not blob_dir.exists():
            raise KeyError(f"Blob not found: {digest}")

        return Blob(digest=digest, file_path=list_files(blob_dir)[0])

    def check_if_contained(self, digest: str) -> bool:
        return (self._data_dir / digest).exists()

    def add_multiple_by_writing(
        self, *seq_paths_and_named_bytes: t.Union[Path, t.Tuple[bytes, str]]
    ) -> t.List[Blob]:
        """
        Add blobs to the blob cache

        :param blobs: a list of paths and named bytes.
            Each element of list can be either a ``pathlib.Path`` object or
            a tuple of a ``bytes`` object and a file name string.

        :returns: a list of strings representing the blob digests
        """
        if len(seq_paths_and_named_bytes) == 0:
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
            with ThreadPoolExecutor(
                max_workers=min(8, len(seq_paths_and_named_bytes))
            ) as executor:
                for idx, digest in executor.map(
                    _hash, range(len(seq_paths_and_named_bytes)), seq_paths_and_named_bytes
                ):
                    idx_to_digest_mapping[idx] = digest

                list_blob_dir, list_file_name, list_path_or_bytes = [], [], []
                for digest, (file_name, path_or_bytes) in to_be_added.items():
                    list_blob_dir.append(self._data_dir / digest)
                    list_file_name.append(file_name)
                    list_path_or_bytes.append(path_or_bytes)
                for _ in executor.map(
                    _write_blob, list_blob_dir, list_file_name, list_path_or_bytes
                ):
                    pass
        except BaseException as e:
            for digest in to_be_added.keys():
                d = self._data_dir / digest
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
        blob_dir.mkdir()
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
        return self._data_dir / digest

    def _sanitize(self) -> None:
        """
        Remove blobs whose directory is corrupted.
        """
        dirs = self.list_digests()
        to_be_removed = []
        for d in dirs:
            if len(list_files(self._data_dir / d)) == 0:
                to_be_removed.append(str(self._data_dir / d))

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


def _write_blob(blob_dir: Path, file_name: str, blob: t.Union[Path, bytes]):
    blob_dir.mkdir()
    try:
        blob_file_path = blob_dir / file_name
        tmp_file_fd, tmp_file_path_str = tempfile.mkstemp()
        os.close(tmp_file_fd)
        tmp_file_path = Path(tmp_file_path_str)
        if isinstance(blob, bytes):
            tmp_file_path.write_bytes(blob)
        else:
            shutil.copyfile(blob.resolve(), tmp_file_path)
        os.replace(tmp_file_path, blob_file_path)
    except BaseException as e:
        shutil.rmtree(str(blob_dir))
        raise e
