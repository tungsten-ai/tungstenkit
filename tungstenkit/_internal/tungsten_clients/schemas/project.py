from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from .namespace import Namespace


class Project(BaseModel):
    id: int
    slug: str
    full_slug: str
    namespace: Namespace

    description: Optional[str] = Field(default=None)
    public: bool
    nsfw: bool
    tags: List[str] = Field(default_factory=list)

    avatar_url: Optional[str] = None
    readme_url: Optional[str] = None
    github_url: Optional[str] = None
    paper_url: Optional[str] = None

    models_count: int
    predictions_count: int
    pulls_count: int
    stargazers_count: int

    created_at: datetime
    last_model_uploaded_at: Optional[datetime] = None

    access_level: Optional[int] = None
