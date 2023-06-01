from pathlib import Path, PurePosixPath
from unittest.mock import patch

import tungstenkit._internal.storables.source_file_data
from tungstenkit._internal.blob_store import BlobStore
from tungstenkit._internal.storables.source_file_data import SourceFile, SourceFileCollection

from .. import dummy_model


@patch.object(tungstenkit._internal.storables.source_file_data, "MAX_SOURCE_FILE_SIZE", 10 * 1024)
def test_source_file():
    test_root = Path(__file__).parent.parent
    binary_dir = test_root / "bin"
    host_paths = [p for p in (binary_dir).glob("**/*") if p.is_file()]
    model_fs_paths = [PurePosixPath(p.relative_to(test_root)) for p in host_paths]
    source_files = {
        pm: SourceFile(abs_path_in_host_fs=ph, rel_path_in_model_fs=pm, size=ph.stat().st_size)
        for pm, ph in zip(model_fs_paths, host_paths)
    }
    dummy_model_path_in_host = Path(dummy_model.__file__)
    dummy_model_path_in_model_fs = PurePosixPath(dummy_model_path_in_host.relative_to(test_root))
    source_files[dummy_model_path_in_model_fs] = SourceFile(
        rel_path_in_model_fs=dummy_model_path_in_model_fs,
        abs_path_in_host_fs=dummy_model_path_in_host,
        size=dummy_model_path_in_host.stat().st_size,
    )

    blob_store = BlobStore()
    stored = SourceFileCollection(source_files.values()).save_blobs(blob_store)
    loaded = SourceFileCollection.load_blobs(stored)
    for f in loaded.files:
        assert f.rel_path_in_model_fs in source_files
        assert f.name == source_files[f.rel_path_in_model_fs].name
        if f.name == "tungsten.png":
            assert f.is_skipped and source_files[f.rel_path_in_model_fs].is_skipped
        else:
            assert not f.is_skipped and not source_files[f.rel_path_in_model_fs].is_skipped

        if not f.is_skipped:
            assert isinstance(f.abs_path_in_host_fs, Path)
            assert isinstance(source_files[f.rel_path_in_model_fs].abs_path_in_host_fs, Path)
            assert (
                f.abs_path_in_host_fs.read_bytes()
                == source_files[f.rel_path_in_model_fs].abs_path_in_host_fs.read_bytes()
            )
