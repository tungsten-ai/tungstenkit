from datetime import datetime
from typing import List, Optional, Union

from pydantic import BaseModel, Field
from typing_extensions import Literal


class SourceFileDecl(BaseModel):
    path: str
    upload_id: int


class SkippedSourceFileDecl(BaseModel):
    path: str
    size: int


class ModelCreate(BaseModel):
    docker_image: str

    input_schema: dict
    output_schema: dict
    demo_output_schema: dict

    input_filetypes: dict
    output_filetypes: dict
    demo_output_filetypes: dict

    source_files: List[SourceFileDecl] = Field(default_factory=list)
    skipped_source_files: List[SkippedSourceFileDecl] = Field(default_factory=list)

    gpu_memory: int
    vm: Optional[str] = None
    version: Optional[str] = None


class ModelCreator(BaseModel):
    id: int
    username: str
    name: str
    avatar_url: str


class Model(BaseModel):
    id: int
    project_id: int
    project_full_slug: str

    version: str

    docker_image: str
    docker_image_size: int

    input_schema: dict
    output_schema: dict
    demo_output_schema: dict
    input_filetypes: dict
    output_filetypes: dict
    demo_output_filetypes: dict

    os: str
    architecture: str
    gpu_memory: int

    readme_url: Optional[str]

    source_files_count: int
    examples_count: int

    creator: ModelCreator
    created_at: datetime


class ModelList(BaseModel):
    __root__: List[Model]


class ModelReadmeUpdate(BaseModel):
    content: str


class ModelPredictionExampleCreate(BaseModel):
    input: dict
    output: dict
    demo_output: dict
    input_files: List[str]
    output_files: List[str]


class ModelPredictionExample(BaseModel):
    id: int

    input: dict
    output: dict
    demo_output: dict

    creator: ModelCreator
    created_at: datetime


class ListModelPredictionExamples(BaseModel):
    __root__: List[ModelPredictionExample]


class SourceTreeFile(BaseModel):
    type: Literal["file"] = "file"
    name: str
    size: int
    skipped: bool = False


class SourceTreeFolder(BaseModel):
    type: Literal["folder"] = "folder"
    name: str
    contents: "List[Union[SourceTreeFile, SourceTreeFolder]]" = []
