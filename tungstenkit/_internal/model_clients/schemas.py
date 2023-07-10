import typing as t

from pydantic import BaseModel, validator

from tungstenkit._internal.model_server.result_caches import PredictionStatus
from tungstenkit._internal.model_server.schema import Metadata, PredictionID  # noqa


class PredictionRequest(BaseModel):
    __root__: t.Dict


class PredictionResponse(BaseModel):
    outputs: t.Optional[t.List[t.Dict]] = None
    status: PredictionStatus
    error_message: t.Optional[str] = None

    # Legacy status: failure
    @validator("status", pre=True)
    def overwrite_status(cls, v: str):
        if v == "failure":
            return "failed"
        return v


class DemoResponse(PredictionResponse):
    demo_outputs: t.Optional[t.List[t.Dict]] = None
    logs: t.Optional[str] = None
