from pydantic import AnyHttpUrl, BaseModel


class ServerMetadata(BaseModel):
    version: str
    registry_url: AnyHttpUrl
