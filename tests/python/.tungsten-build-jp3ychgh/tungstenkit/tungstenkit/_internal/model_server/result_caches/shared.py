import typing as t

import attrs
from typing_extensions import Literal

PredictionStatus = Literal["pending", "running", "success", "failure"]


@attrs.define(kw_only=True)
class Result:
    status: PredictionStatus
    outputs: t.Optional[t.List[t.Dict]] = attrs.field(default=None)
    demo_outputs: t.Optional[t.List[t.Dict]] = attrs.field(default=None)
    logs: t.Optional[str] = attrs.field(default=None)
    error_message: t.Optional[str] = attrs.field(default=None)
