from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field
from typing_extensions import Literal


class FileUploadResponse(BaseModel):
    id: int
    size: int
    content_type: str
    serving_url: str


class FolderUploadRequest(BaseModel):
    paths: List[Path]


class FolderUploadItem(BaseModel):
    serving_url: str
    upload_url: str


class FolderUploadResponse(BaseModel):
    folder: str
    header: Optional[Dict[str, str]]
    paths: Dict[str, FolderUploadItem]


class FileTreeItem(BaseModel):
    type: Literal["folder", "file"]
    name: str


class FileTree(BaseModel):
    __root__: List[FileTreeItem] = Field(default_factory=list)
