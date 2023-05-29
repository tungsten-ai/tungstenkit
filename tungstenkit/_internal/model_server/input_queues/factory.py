from ..config import BaseCacheConfig, LocalCacheConfig
from .abstract_input_queue import AbstractInputQueue
from .local_input_queue import LocalInputQueue


def create_input_queue(cache_config: BaseCacheConfig) -> AbstractInputQueue:
    if isinstance(cache_config, LocalCacheConfig):
        return LocalInputQueue()

    raise NotADirectoryError
