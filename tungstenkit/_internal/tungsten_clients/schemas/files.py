from pydantic import BaseModel


class FileUploadResponse(BaseModel):
    id: int
    size: int
    content_type: str
    serving_url: str
