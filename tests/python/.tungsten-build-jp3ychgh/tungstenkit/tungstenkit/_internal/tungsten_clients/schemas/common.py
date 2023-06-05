from pydantic import BaseModel


class Existence(BaseModel):
    exists: bool
