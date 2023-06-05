import typing as t

from pydantic import BaseModel, conlist, create_model
from pydantic.typing import Annotated

from tungstenkit._internal.io import BaseIO

from .result_caches import PredictionStatus


class PredictionRequest(BaseModel):
    __root__: Annotated[t.List[BaseIO], conlist(BaseIO, min_items=1)]

    @classmethod
    def with_type(cls, input_cls: t.Type[BaseIO]) -> "t.Type[PredictionRequest]":
        return create_model(
            cls.__name__,
            __base__=cls,
            __root__=(
                Annotated[t.List[input_cls], conlist(input_cls, min_items=1)],  # type: ignore
                ...,
            ),
        )


class PredictionResponse(BaseModel):
    outputs: t.Optional[t.List[BaseIO]] = None
    status: PredictionStatus
    error_message: t.Optional[str] = None

    @classmethod
    def with_type(cls, output_cls: t.Type[BaseIO]) -> "t.Type[PredictionResponse]":
        return create_model(
            cls.__name__,
            __base__=cls,
            outputs=(t.Optional[t.List[output_cls]], None),  # type: ignore
        )


class DemoResponse(PredictionResponse):
    demo_outputs: t.Optional[t.List[t.Dict]] = None
    logs: t.Optional[str] = None


class PredictionID(BaseModel):
    prediction_id: str


class Metadata(BaseModel):
    input_schema: t.Dict
    output_schema: t.Dict
