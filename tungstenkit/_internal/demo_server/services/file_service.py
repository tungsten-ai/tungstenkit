import os
import signal
import time
import typing as t
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from threading import Thread

import attrs
from fastapi import HTTPException, Request
from fasteners import ReaderWriterLock
from furl import furl

from tungstenkit._internal.logging import log_debug
from tungstenkit._internal.utils.file import convert_to_unique_path
from tungstenkit._internal.utils.string import removeprefix

BUFFER_SIZE = 4 * 1024 * 1024
EXPIRATION_SECONDS = 10 * 60
GARBAGE_COLLECTION_INTERVAL = 10


@attrs.define
class FileMetadata:
    protected: bool
    created_at: datetime = attrs.field(factory=datetime.utcnow)


@attrs.define
class FileService:
    base_dir: Path

    _lock_to_resolve_path: ReaderWriterLock = attrs.field(factory=ReaderWriterLock, init=False)
    _file_access_locks: t.Dict[str, ReaderWriterLock] = attrs.field(factory=dict, init=False)
    _file_metadata_dict: t.Dict[str, FileMetadata] = attrs.field(factory=dict, init=False)

    def __attrs_post_init__(self):
        self.base_dir = self.base_dir.resolve()
        self.base_dir.mkdir(exist_ok=True, parents=True)

    @property
    def filenames(self) -> t.List[str]:
        return list(self._file_access_locks.keys())

    def check_existence(self, filename: str, strict: bool = False) -> bool:
        path = self.base_dir / filename
        if strict:
            return path.exists()
        return path.is_symlink() or path.exists()

    def change_protected_flag(self, filename: str, protected: bool):
        if not self.check_existence(filename):
            raise HTTPException(status_code=404, detail=filename)
        metadata = self._file_metadata_dict[filename]
        metadata.protected = protected

    def add_link(self, path: Path, protected: bool) -> str:
        path_in_blob_dir = self.base_dir / self._register(
            filename=path.name, link_from=path, protected=protected
        )
        return path_in_blob_dir.name

    def add_file_by_path(self, path: Path, protected: bool) -> str:
        filename = path.name
        with open(path, "rb") as f:
            return self.add_file_by_buffer(filename, f, protected=protected)

    def add_file_by_buffer(self, filename: str, buf: t.BinaryIO, protected: bool) -> str:
        file_in_blob_dir = self.base_dir / self._register(filename=filename, protected=protected)
        with self._file_access_locks[filename].write_lock():
            with open(file_in_blob_dir, "wb") as f:
                contents = buf.read(BUFFER_SIZE)
                while contents:
                    f.write(contents)
                    contents = buf.read(BUFFER_SIZE)

        return filename

    def get_path_by_filename(self, filename: str) -> Path:
        path = self.base_dir / filename
        return path

    def start_garbage_collection(self) -> Thread:
        thread = Thread(target=self._run_garbage_collection, daemon=True)
        thread.start()
        return thread

    @contextmanager
    def acquire_write_lock(self, filename: str):
        if not self.check_existence(filename):
            raise HTTPException(status_code=404, detail=filename)
        with self._file_access_locks[filename].write_lock() as lock:
            yield lock

    @contextmanager
    def acquire_read_lock(self, filename: str):
        if not self.check_existence(filename):
            raise HTTPException(status_code=404, detail=filename)
        with self._file_access_locks[filename].read_lock() as lock:
            yield lock

    @classmethod
    def build_serving_url(cls, filename: str, request: Request) -> str:
        return furl(str(request.url_for("files", filename=filename))).url

    @classmethod
    def get_filename_by_serving_url(cls, serving_url: str, files_endpoint: str) -> str:
        return removeprefix(serving_url, files_endpoint + "/")

    def _register(self, filename: str, protected: bool, link_from: t.Optional[Path] = None) -> str:
        file_in_blob_dir = self.base_dir / filename
        with self._lock_to_resolve_path.write_lock():
            file_in_blob_dir = convert_to_unique_path(file_in_blob_dir)
            if link_from:
                os.symlink(link_from, file_in_blob_dir)
            else:
                file_in_blob_dir.touch()

            filename = file_in_blob_dir.name
            self._file_access_locks[filename] = ReaderWriterLock()

        self._file_metadata_dict[filename] = FileMetadata(protected=protected)
        return filename

    def _run_garbage_collection(self):
        try:
            while True:
                time.sleep(GARBAGE_COLLECTION_INTERVAL)
                self._collect_garbages()
                log_debug(f"Remaining files: {', '.join(self.filenames)}")
        except BaseException:
            os.kill(os.getpid(), signal.SIGUSR2)

    def _collect_garbages(self):
        current = datetime.utcnow()
        for filename in self.filenames:
            if filename not in self._file_metadata_dict:
                continue

            metadata = self._file_metadata_dict[filename]
            if (
                not metadata.protected
                and (current - metadata.created_at).total_seconds() > EXPIRATION_SECONDS
            ):
                with self._file_access_locks[filename].write_lock():
                    path = self.base_dir / filename
                    if path.is_symlink() or path.exists():
                        os.remove(path)
                    del self._file_metadata_dict[filename]

                del self._file_access_locks[filename]
