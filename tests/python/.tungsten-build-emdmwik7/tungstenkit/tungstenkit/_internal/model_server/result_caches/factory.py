from ..config import BaseCacheConfig, LocalCacheConfig
from .abstract_result_cache import AbstractResultCache
from .local_result_cache import LocalResultCache


def create_result_cache(cache_config: BaseCacheConfig) -> AbstractResultCache:
    if isinstance(cache_config, LocalCacheConfig):
        return LocalResultCache(expiration=cache_config.result_expiration)

    raise NotADirectoryError
