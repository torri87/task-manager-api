from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class CommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=1500)

    model_config = ConfigDict(str_strip_whitespace=True)


class CommentRead(BaseModel):
    id: int
    task_id: int
    author_id: int
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)