import shutil
import time
import typing as t
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

from tungstenkit import exceptions
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
                future_dict[idx] = executor.submit(shutil.copy, str(src), str(dest))

            saved_paths: t.List[Path] = [
                Path(future_dict[i].result(timeout=60)) for i in range(len(files))
            ]

        # Wait for sync with docker volume
        start_time = time.monotonic()
        all_files_exist = all(p.exists() for p in saved_paths)
        while all_files_exist and time.monotonic() - start_time < 10:
            all_files_exist = all(p.exists() for p in saved_paths)
            if all_files_exist:
                break
            else:
                time.sleep(0.1)

        for p in saved_paths:
            p.chmod(0o666)

        if not all_files_exist:
            raise exceptions.UploadError("Failed to save files to the volume")

        out = [type_dict[i].from_path(p) for i, p in enumerate(saved_paths)]
        return out

    def _save(self, idx: int, file: io.File) -> t.Tuple[int, Path]:
        file_uri = io.URIForFile(file.__root__).to_file_uri()
        path = get_path_from_file_url(file_uri)
        return idx, path
