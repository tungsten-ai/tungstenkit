import json
import typing as t

from fastapi import Request
from pydantic import BaseModel

from tungstenkit._internal.model_server.schema import PredictionStatus
from tungstenkit._internal.storables import StoredModelData
from tungstenkit._internal.utils.markdown import change_local_image_links_in_markdown

if t.TYPE_CHECKING:
    from .services import FileService

# ==================== metadata ====================

_input_schema: t.Optional[t.Dict] = None
_output_schema: t.Optional[t.Dict] = None
_readme: t.Optional[str] = None
_avatar_filename: t.Optional[str] = None


class Metadata(BaseModel):
    name: str
    description: str
    input_schema: t.Dict
    output_schema: t.Dict
    avatar_url: str
    examples_count: int
    readme: t.Optional[str] = None

    @classmethod
    def build(cls, model: StoredModelData, file_service: "FileService", request: Request):
        global _input_schema, _output_schema, _readme, _avatar_filename
        # Load schemas
        _input_schema = (
            json.loads(model.io_schema.input_jsonschema.file_path.read_text())
            if _input_schema is None
            else _input_schema
        )
        _output_schema = (
            json.loads(model.io_schema.output_jsonschema.file_path.read_text())
            if _output_schema is None
            else _output_schema
        )

        # Prepare the readme
        if model.readme and _readme is None:
            file_paths = [im.file_path.resolve() for im in model.readme.images]
            filenames_in_server = [file_service.add_link(p, protected=True) for p in file_paths]
            readme = model.readme.markdown.file_path.read_text()
            _readme = change_local_image_links_in_markdown(
                md=readme,
                local_img_paths=file_paths,
                updates=["/files/" + n for n in filenames_in_server],
            )

        # Prepare the avatar
        _avatar_filename = (
            file_service.add_link(model.avatar.blob.file_path, protected=True)
            if _avatar_filename is None
            else _avatar_filename
        )

        return cls(
            name=model.name,
            description=model.description,
            avatar_url=file_service.build_serving_url(_avatar_filename, request=request),
            readme=_readme,
            input_schema=_input_schema,
            output_schema=_output_schema,
            examples_count=len(model.examples),
        )


# ==================== predictions ====================


class PostPredictionRequest(BaseModel):
    __root__: t.Dict


class PostPredictionResponse(BaseModel):
    prediction_id: str


class Prediction(BaseModel):
    id: str
    status: PredictionStatus
    input: t.Dict
    output: t.Optional[t.Dict] = None
    demo_output: t.Optional[t.Dict] = None
    logs: t.Optional[str] = None
    files: t.Optional[t.List[str]] = None


# ==================== examples ====================


class PostExampleResponse(BaseModel):
    example_id: str


class Example(BaseModel):
    id: str
    input: t.Dict
    output: t.Dict
    demo_output: t.Dict
    files: t.Optional[t.List[str]] = None
    logs: t.Optional[str] = None


# ==================== files ====================


class FileUploadResponse(BaseModel):
    serving_url: str
