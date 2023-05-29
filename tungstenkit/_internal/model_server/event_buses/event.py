import typing as t

import attrs


@attrs.frozen
class EventMessage:
    event_type: str
    payload: t.Optional[str] = None
