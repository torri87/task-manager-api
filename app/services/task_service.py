from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Task, User
from app.models.enums import ACTIVE_STATUSES, FINAL_STATUSES

MAX_ACTIVE_TASKS = 10


async def get_task_or_404(db: AsyncSession, task_id: int):
    task = await db.get(Task, task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    return task


def ensure_editable(task: Task):
    if task.status in FINAL_STATUSES:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Task in status '{task.status.value}' cannot be edited",
        )


async def ensure_can_assign(db: AsyncSession, user_id: int):
    if await db.get(User, user_id) is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Assignee not found")

    active_count = await db.scalar(
        select(func.count())
        .select_from(Task)
        .where(Task.assignee_id == user_id, Task.status.in_(ACTIVE_STATUSES))
    )
    if active_count >= MAX_ACTIVE_TASKS:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"User already has {MAX_ACTIVE_TASKS} active tasks",
        )