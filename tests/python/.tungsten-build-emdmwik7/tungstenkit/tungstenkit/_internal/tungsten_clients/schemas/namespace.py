from pydantic import BaseModel


class Namespace(BaseModel):
    id: int
    slug: str
    type: str
