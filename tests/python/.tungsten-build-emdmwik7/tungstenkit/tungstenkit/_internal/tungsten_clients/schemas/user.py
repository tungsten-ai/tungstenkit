from typing import Optional

from pydantic import AnyHttpUrl, BaseModel


class User(BaseModel):
    id: int
    username: str
    email: str
    name: Optional[str] = None
    avatar_url: Optional[AnyHttpUrl] = None
    namespace_id: Optional[int] = None
