from datetime import datetime, UTC
from fastapi import HTTPException, status
from sqlalchemy import and_, case, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import (
    ACTIVE_STATUSES,
    FINAL_STATUSES,
    SortOrder,
    TaskPriority,
    TaskSortField,
    TaskStatus,
)
from app.models import Task, User

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


ALLOWED_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.BACKLOG: {TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED},
    TaskStatus.IN_PROGRESS: {TaskStatus.REVIEW, TaskStatus.CANCELLED},
    TaskStatus.REVIEW: {TaskStatus.DONE, TaskStatus.CANCELLED},
    TaskStatus.DONE: set(),
    TaskStatus.CANCELLED: set(),
}


def ensure_can_transtion(task: Task, new_status: TaskStatus):
    allowed = ALLOWED_TRANSITIONS[task.status]
    if new_status not in allowed:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Cannot move task from '{task.status.value}' to '{new_status.value}'."
        )

    if new_status == TaskStatus.DONE:
        if task.assignee_id is None:
            raise HTTPException(status.HTTP_409_CONFLICT, "Assignee not found")

        if task.deadline < datetime.now(UTC):
            raise HTTPException(status.HTTP_409_CONFLICT, "Cannot complete a task after its deadline")


priority_rank = case(
    (Task.priority == TaskPriority.HIGH, 3),
    (Task.priority == TaskPriority.MEDIUM, 2),
    else_=1,
)


async def search_tasks(
        db: AsyncSession,
        *,
        search: str | None,
        task_status: TaskStatus | None,
        priority: TaskPriority | None,
        assignee_id: int | None,
        deadline_from: datetime | None,
        deadline_to: datetime | None,
        sort_by: TaskSortField | None,
        order: SortOrder,
        limit: int,
        offset: int,
):
    conditions = []
    if search:
        conditions.append(
            or_(
                Task.title.icontains(search, autoescape=True),
                Task.description.icontains(search, autoescape=True),
            )
        )
    if task_status is not None:
        conditions.append(Task.status == task_status)
    if priority is not None:
        conditions.append(Task.priority == priority)
    if assignee_id is not None:
        conditions.append(Task.assignee_id == assignee_id)
    if deadline_from is not None:
        conditions.append(Task.deadline >= deadline_from)
    if deadline_to is not None:
        conditions.append(Task.deadline <= deadline_to)

    if sort_by is None:
        ordering = [priority_rank.desc(), Task.deadline.asc()]
    else:
        column = {
            TaskSortField.CREATED_AT: Task.created_at,
            TaskSortField.DEADLINE: Task.deadline,
            TaskSortField.PRIORITY: priority_rank,
        }[sort_by]
        ordering = [column.asc() if order == SortOrder.ASC else column.desc()]

    ordering.append(Task.id)

    total = await db.scalar(select(func.count()).select_from(Task).where(*conditions))
    result = await db.scalars(
        select(Task).where(*conditions).order_by(*ordering).limit(limit).offset(offset)
    )
    return list(result.all()), total


def overdue_condition():
    return and_(
        Task.deadline < datetime.now(UTC),
        Task.status.not_in(FINAL_STATUSES),
    )


async def get_overdue_tasks(db: AsyncSession, *, limit: int, offset: int):
    total = await db.scalar(
        select(func.count()).select_from(Task).where(overdue_condition())
    )
    result = await db.scalars(
        select(Task)
        .where(overdue_condition())
        .order_by(Task.deadline, Task.id)
        .limit(limit)
        .offset(offset)
    )
    return list(result.all()), total


async def get_stats(db: AsyncSession):
    total = await db.scalar(select(func.count()).select_from(Task))

    status_rows = await db.execute(
        select(Task.status, func.count()).group_by(Task.status)
    )
    by_status = {s: 0 for s in TaskStatus}
    for task_status, count in status_rows:
        by_status[task_status] = count

    priority_rows = await db.execute(
        select(Task.priority, func.count()).group_by(Task.priority)
    )
    by_priority = {p: 0 for p in TaskPriority}
    for priority, count in priority_rows:
        by_priority[priority] = count

    overdue = await db.scalar(
        select(func.count()).select_from(Task).where(overdue_condition())
    )
    active = await db.scalar(
        select(func.count()).select_from(Task).where(Task.status.in_(ACTIVE_STATUSES))
    )

    return {
        "total": total,
        "by_status": by_status,
        "by_priority": by_priority,
        "overdue": overdue,
        "active": active,
    }


async def cancel_overdue_tasks(db: AsyncSession):
    result = await db.execute(update(Task).where(overdue_condition()).values(status=TaskStatus.CANCELLED))
    await db.commit()

    return result.rowcount