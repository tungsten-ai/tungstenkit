import typing as t
from queue import Queue

from .abstract_event_bus import AbstractEventBus
from .event import EventMessage


class LocalEventBus(AbstractEventBus):
    def __init__(self) -> None:
        self._event_queue: Queue[EventMessage] = Queue()
        super().__init__()

    def post(self, event_type: str, payload: t.Optional[str] = None) -> None:
        self._event_queue.put_nowait(EventMessage(event_type=event_type, payload=payload))

    def get(self):
        return self._event_queue.get()
