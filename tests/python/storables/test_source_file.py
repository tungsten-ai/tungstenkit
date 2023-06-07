import typing as t
from pathlib import Path, PurePosixPath

from tungstenkit._internal import constants
from tungstenkit._internal.blob_store import BlobStore
from tungstenkit._internal.storables.source_file_data import SourceFile, SourceFileCollection


def test_source_file(dummy_model_all_source_files_dict: t.Dict[PurePosixPath, SourceFile]):
    blob_store = BlobStore()
    stored = SourceFileCollection(dummy_model_all_source_files_dict.values()).save_blobs(
        blob_store
    )
    loaded = SourceFileCollection.load_blobs(stored)
    for f in loaded.files:
        assert f.rel_path_in_model_fs in dummy_model_all_source_files_dict
        assert f.name == dummy_model_all_source_files_dict[f.rel_path_in_model_fs].name
        if (
            dummy_model_all_source_files_dict[f.rel_path_in_model_fs]  # type: ignore
            .abs_path_in_host_fs.stat()
            .st_size
            > constants.MAX_SOURCE_FILE_SIZE
        ):
            assert f.is_skipped
        else:
            assert not f.is_skipped

        if not f.is_skipped:
            assert isinstance(f.abs_path_in_host_fs, Path)
            assert isinstance(
                dummy_model_all_source_files_dict[f.rel_path_in_model_fs].abs_path_in_host_fs, Path
            )
            assert (
                f.abs_path_in_host_fs.read_bytes()
                == dummy_model_all_source_files_dict[  # type: ignore
                    f.rel_path_in_model_fs
                ].abs_path_in_host_fs.read_bytes()
            )
