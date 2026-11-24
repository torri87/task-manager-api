from datetime import UTC, datetime

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.models.enums import TaskPriority, TaskStatus


def deadline_not_in_past(value: datetime | None) -> datetime | None:
    if value is not None and value < datetime.now(UTC):
        raise ValueError("Deadline cannot be in the past")
    return value


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    priority: TaskPriority = TaskPriority.MEDIUM
    assignee_id: int | None = None
    deadline: AwareDatetime

    _check_deadline = field_validator("deadline")(deadline_not_in_past)


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    priority: TaskPriority | None = None
    assignee_id: int | None = None
    deadline: AwareDatetime | None = None

    _check_deadline = field_validator("deadline")(deadline_not_in_past)

    @model_validator(mode="after")
    def required_fields_not_null(self):
        for name in ("title", "priority", "deadline"):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null")
        return self


class TaskRead(BaseModel):
    id: int
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    assignee_id: int | None
    author_id: int
    deadline: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TaskPage(BaseModel):
    items: list[TaskRead]
    total: int
    limit: int
    offset: int


class TaskStatusUpdate(BaseModel):
    status: TaskStatus