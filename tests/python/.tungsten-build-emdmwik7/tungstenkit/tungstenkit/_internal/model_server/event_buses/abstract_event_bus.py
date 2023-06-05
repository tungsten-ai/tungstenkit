import abc
import typing as t
from threading import Thread

from .event import EventMessage


class AbstractEventBus(Thread):
    def __init__(self):
        self._handlers: t.Dict[str, t.Callable] = dict()
        super().__init__(daemon=True)

    @abc.abstractmethod
    def post(self, event_type: str, payload: t.Optional[str] = None) -> None:
        pass

    @abc.abstractmethod
    def get(self) -> EventMessage:
        pass

    def add_handler(self, event_type: str, handler: t.Callable[[t.Optional[str]], t.Any]) -> None:
        self._handlers[event_type] = handler

    def run(self):
        while True:
            event = self.get()
            if event.event_type in self._handlers.keys():
                self._handlers[event.event_type](event.payload)
