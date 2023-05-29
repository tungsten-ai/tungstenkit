from typing import Optional

from pydantic import BaseModel


class DatasetCreate(BaseModel):
    folder: str
    message: str


class DatasetCreateResponse(BaseModel):
    version: int
    ready: bool
    progress_pct: int


class Dataset(BaseModel):
    project_id: int
    version: int

    n_datapoints: int
    n_annotations: int
    n_annotated_datapoints: int

    creator_id: int
    creator_message: Optional[str]
