from pydantic import AnyHttpUrl, BaseModel


class ServerMetadata(BaseModel):
    registry_url: AnyHttpUrl
