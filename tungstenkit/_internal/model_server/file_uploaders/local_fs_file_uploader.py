import typing as t
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

from tungstenkit._internal import io
from tungstenkit._internal.utils.uri import get_path_from_file_url

from .abstract_file_uploader import AbstractFileUploader

BUFFER_SIZE = 4 * 1024 * 1024


class LocalFSFileUploader(AbstractFileUploader):
    def __init__(self, mount_point: Path) -> None:
        self.mount_point = mount_point

    def upload(self, files: t.List[io.File]) -> t.List[io.File]:
        """Save files to the mount point"""
        # TODO cleanup
        type_dict = {i: f.__class__ for i, f in enumerate(files)}
        future_dict: t.Dict[int, Future] = dict()
        with ThreadPoolExecutor(max_workers=8) as executor:
            for idx, src in executor.map(self._save, range(len(files)), files):
                dest = self.mount_point / ("output-" + uuid4().hex + "-" + src.name)
                future_dict[idx] = executor.submit(self._copy, src, dest)

            saved_paths: t.List[Path] = [
                future_dict[i].result(timeout=60) for i in range(len(files))
            ]
        assert all(p.exists() for p in saved_paths), "Failed to save files: " + ", ".join(
            [f.__root__ for f in files]
        )
        out = [type_dict[i].from_path(p) for i, p in enumerate(saved_paths)]
        return out

    def _save(self, idx: int, file: io.File) -> t.Tuple[int, Path]:
        file_uri = io.URIForFile(file.__root__).to_file_uri()
        path = get_path_from_file_url(file_uri)
        return idx, path

    def _copy(self, src: Path, dest: Path) -> Path:
        with src.open("rb") as f_read:
            with dest.open("wb") as f_write:
                b = f_read.read(BUFFER_SIZE)
                f_write.write(b)

        return dest
