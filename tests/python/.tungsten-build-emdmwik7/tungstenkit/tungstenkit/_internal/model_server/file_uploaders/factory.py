from ..config import BaseStorageConfig, InMemoryStorageConfig, LocalFSStorageConfig
from .abstract_file_uploader import AbstractFileUploader
from .in_memory_file_uploader import InMemoryFileUploader
from .local_fs_file_uploader import LocalFSFileUploader


def create_file_uploader(storage_config: BaseStorageConfig) -> AbstractFileUploader:
    if isinstance(storage_config, InMemoryStorageConfig):
        return InMemoryFileUploader()

    if isinstance(storage_config, LocalFSStorageConfig):
        return LocalFSFileUploader(mount_point=storage_config.mount_point)

    raise NotImplementedError
