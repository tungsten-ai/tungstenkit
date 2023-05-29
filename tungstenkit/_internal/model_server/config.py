from pathlib import Path
from typing import Any, Dict, Optional, Type, Union

import attrs
import pydantic

from .enums import ModelServerMode

# ========================================================
# Cache config
# ========================================================


@attrs.define(kw_only=True)
class BaseCacheConfig:
    result_expiration: float


class LocalCacheConfig(BaseCacheConfig):
    pass


@attrs.define(kw_only=True)
class RedisConfig(BaseCacheConfig):
    redis_url: str


# ========================================================
# Storage config
# ========================================================


class BaseStorageConfig:
    pass


class InMemoryStorageConfig(BaseStorageConfig):
    pass


@attrs.define(kw_only=True)
class LocalFSStorageConfig(BaseStorageConfig):
    mount_point: Path


@attrs.define(kw_only=True)
class S3StorageConfig(BaseStorageConfig):
    url: str
    # TODO


@attrs.define(kw_only=True)
class AzureBlobStorageConfig(BaseStorageConfig):
    url: str
    # TODO


# ========================================================
# Settings
# ========================================================


class BaseModelServerSettings(pydantic.BaseSettings):
    TUNGSTEN_MODEL_MODULE: str
    TUNGSTEN_MODEL_CLASS: str

    SETUP_TIMEOUT: float = 600.0
    PREDICTION_TIMEOUT: float = 600.0

    RESULT_EXPIRATION: float = 600.0

    @property
    def cache_config(self) -> BaseCacheConfig:
        raise NotImplementedError

    @property
    def storage_config(self) -> BaseStorageConfig:
        raise NotImplementedError


class StandaloneSettings(BaseModelServerSettings):
    @property
    def cache_config(self):
        return LocalCacheConfig(
            result_expiration=self.RESULT_EXPIRATION,
        )

    @property
    def storage_config(self):
        return InMemoryStorageConfig()


class FileTunnelSettings(BaseModelServerSettings):
    MOUNT_POINT: pydantic.DirectoryPath

    @property
    def cache_config(self):
        return LocalCacheConfig(
            result_expiration=self.RESULT_EXPIRATION,
        )

    @property
    def storage_config(self) -> LocalFSStorageConfig:
        return LocalFSStorageConfig(mount_point=self.MOUNT_POINT)


class ClusterSettings(BaseModelServerSettings):
    REDIS_URL: pydantic.AnyHttpUrl
    S3_URL: Optional[pydantic.AnyHttpUrl] = None
    AZURE_BLOB_STORAGE_URL: Optional[pydantic.AnyHttpUrl] = None

    @property
    def cache_config(self) -> RedisConfig:
        return RedisConfig(
            result_expiration=self.RESULT_EXPIRATION,
            redis_url=str(self.REDIS_URL),
        )

    @property
    def storage_config(
        self,
    ) -> Union[S3StorageConfig, AzureBlobStorageConfig, InMemoryStorageConfig]:
        if self.S3_URL:
            return S3StorageConfig(url=self.S3_URL)

        if self.AZURE_BLOB_STORAGE_URL:
            return AzureBlobStorageConfig(url=self.AZURE_BLOB_STORAGE_URL)

        return InMemoryStorageConfig()

    @pydantic.root_validator()
    def validate_storage(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        if values.get("S3_URL") and values.get("BLOB_STORAGE_URL"):
            raise ValueError(
                "Expected only one, either `S3_URL` or `BLOB_STORAGE_URL`, not together"
            )
        return values


MODE_TO_SETTING_MAPPING: Dict[ModelServerMode, Type[BaseModelServerSettings]] = {
    ModelServerMode.STANDALONE: StandaloneSettings,
    ModelServerMode.FILE_TUNNEL: FileTunnelSettings,
    ModelServerMode.CLUSTER: ClusterSettings,
}
