from ..config import BaseCacheConfig, LocalCacheConfig
from .abstract_event_bus import AbstractEventBus
from .local_event_bus import LocalEventBus


def create_event_bus(cache_config: BaseCacheConfig) -> AbstractEventBus:
    if isinstance(cache_config, LocalCacheConfig):
        return LocalEventBus()

    raise NotImplementedError()
