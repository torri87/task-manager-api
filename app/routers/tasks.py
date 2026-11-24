from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.database import get_db
from app.models import Task, User
from app.models.enums import TaskStatus
from app.schemas.task import TaskCreate, TaskPage, TaskRead, TaskUpdate
from app.services.task_service import (
    ensure_can_assign,
    ensure_editable,
    get_task_or_404,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
async def create_task(
    data: TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if data.assignee_id is not None:
        await ensure_can_assign(db, data.assignee_id)

    task = Task(**data.model_dump(), author_id=current_user.id)
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


@router.get("", response_model=TaskPage)
async def list_tasks(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    total = await db.scalar(select(func.count()).select_from(Task))
    result = await db.scalars(select(Task).order_by(Task.id).limit(limit).offset(offset))
    return {"items": result.all(), "total": total, "limit": limit, "offset": offset}


@router.get("/{task_id}", response_model=TaskRead)
async def get_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await get_task_or_404(db, task_id)


@router.patch("/{task_id}", response_model=TaskRead)
async def update_task(
    task_id: int,
    data: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    task = await get_task_or_404(db, task_id)
    ensure_editable(task)

    changes = data.model_dump(exclude_unset=True)

    new_assignee = changes.get("assignee_id", task.assignee_id)
    if new_assignee != task.assignee_id:
        if task.status == TaskStatus.REVIEW:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Assignee cannot be changed once the task is in Review",
            )
        if new_assignee is not None:
            await ensure_can_assign(db, new_assignee)

    for field, value in changes.items():
        setattr(task, field, value)

    await db.commit()
    await db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    task = await get_task_or_404(db, task_id)
    if task.status in (TaskStatus.IN_PROGRESS, TaskStatus.REVIEW):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Move the task to Cancelled or Done before deleting it",
        )
    await db.delete(task)
    await db.commit()