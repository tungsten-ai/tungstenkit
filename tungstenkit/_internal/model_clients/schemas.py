import typing as t

from pydantic import BaseModel, validator

from tungstenkit._internal.model_server.result_caches import PredictionStatus


class Metadata(BaseModel):
    input_schema: t.Dict
    output_schema: t.Dict
    demo_output_schema: t.Dict


class PredictionID(BaseModel):
    prediction_id: str


class DemoID(BaseModel):
    prediction_id: t.Optional[str] = None
    demo_id: str = ""

    # For legacy API
    @validator("demo_id", always=True)
    def handle_prediction_id(cls, v, values, **kwargs):
        assert bool(v) or ("prediction_id" in values and bool(values["prediction_id"]))
        if not v:
            return values["prediction_id"]
        return v


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
