from pydantic import BaseModel


class Datapoint(BaseModel):
    filename: str
    blobname: str
