import typing as t
from io import BytesIO

from fastapi import Request
from pydantic import BaseModel, Field, validator
from typing_extensions import Literal

from tungstenkit._internal import storables
from tungstenkit._internal.model_server.schema import PredictionStatus
from tungstenkit._internal.utils.markdown import change_local_image_links_in_markdown

if t.TYPE_CHECKING:
    from .services import FileService

# ==================== metadata ====================


class Metadata(BaseModel):
    name: str
    input_schema: t.Dict
    output_schema: t.Dict
    demo_output_schema: t.Dict
    input_filetypes: t.Dict
    output_filetypes: t.Dict
    demo_output_filetypes: t.Dict
    avatar_url: str
    readme: t.Optional[str] = None

    @classmethod
    def build(cls, model: storables.ModelData, file_service: "FileService", request: Request):
        # Prepare the readme
        if model.readme:
            file_paths = model.readme.image_files
            filenames_in_server = [
                file_service.add_file_by_path(p, protected=True) for p in file_paths
            ]
            readme = model.readme.content
            readme = change_local_image_links_in_markdown(
                md=readme,
                local_img_paths=file_paths,
                updates=["/files/" + n for n in filenames_in_server],
            )
        else:
            readme = None

        # Prepare the avatar
        avatar_filename = file_service.add_file_by_buffer(
            "avatar" + model.avatar.extension, buf=BytesIO(model.avatar.bytes_), protected=True
        )

        return cls(
            name=model.name,
            avatar_url=file_service.build_serving_url(avatar_filename, request=request),
            readme=readme,
            input_schema=model.io.input_schema,
            output_schema=model.io.output_schema,
            demo_output_schema=model.io.demo_output_schema,
            input_filetypes=model.io.input_filetypes,
            output_filetypes=model.io.output_filetypes,
            demo_output_filetypes=model.io.demo_output_filetypes,
        )


# ==================== predictions ====================


class PostPredictionRequest(BaseModel):
    __root__: t.Dict


class Prediction(BaseModel):
    id: str
    status: PredictionStatus
    input: t.Dict
    output: t.Optional[t.Dict] = None
    demo_output: t.Optional[t.Dict] = None
    logs: t.Optional[str] = None
    failure_reason: t.Optional[str] = None

    # Legacy status: failure
    @validator("status", pre=True)
    def overwrite_status(cls, v: str):
        if v == "failure":
            return "failed"
        return v


# ==================== files ====================


class FileUploadResponse(BaseModel):
    serving_url: str
