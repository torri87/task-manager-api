from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import AwareDatetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.database import get_db
from app.models import Task, User
from app.models.enums import SortOrder, TaskPriority, TaskSortField, TaskStatus
from app.schemas.task import (
    TaskCreate,
    TaskPage,
    TaskRead,
    TaskStats,
    TaskStatusUpdate,
    TaskUpdate,
)

from app.services.task_service import (
    ensure_can_assign,
    ensure_can_transtion,
    ensure_editable,
    get_overdue_tasks,
    get_stats,
    get_task_or_404,
    search_tasks,
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
    search: str | None = Query(None, min_length=1, max_length=100),
    task_status: TaskStatus | None = Query(None, alias="status"),
    priority: TaskPriority | None = None,
    assignee_id: int | None = None,
    deadline_from: AwareDatetime | None = None,
    deadline_to: AwareDatetime | None = None,
    sort_by: TaskSortField | None = None,
    order: SortOrder = SortOrder.ASC,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    if deadline_from and deadline_to and deadline_from > deadline_to:
        raise HTTPException(422, "deadline_from must not be later than deadline_to")

    items, total = await search_tasks(
        db,
        search=search,
        task_status=task_status,
        priority=priority,
        assignee_id=assignee_id,
        deadline_from=deadline_from,
        deadline_to=deadline_to,
        sort_by=sort_by,
        order=order,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/overdue", response_model=TaskPage)
async def list_overdue_tasks(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await get_overdue_tasks(db, limit=limit, offset=offset)

    items = result[0]
    total = result[1]

    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/stats", response_model=TaskStats)
async def task_stats(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await get_stats(db)


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

@router.patch("/{task_id}/status", response_model=TaskRead)
async def change_status(task_id: int, data: TaskStatusUpdate, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    task = await get_task_or_404(db, task_id)
    ensure_can_transtion(task, data.status)
    task.status = data.status
    await db.commit()
    await db.refresh(task)
    return task