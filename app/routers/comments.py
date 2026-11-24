from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.database import get_db
from app.models import Comment, User
from app.schemas.comment import CommentCreate, CommentRead
from app.services.task_service import get_task_or_404


router = APIRouter(prefix='/tasks/{task_id}/comments', tags=['comments'])


@router.post('/', status_code=status.HTTP_201_CREATED, response_model=CommentRead)
async def create_comment(task_id: int, data: CommentCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    await get_task_or_404(db, task_id)

    comment = Comment(task_id=task_id, author_id=current_user.id, content=data.content)
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return comment


@router.get('/', status_code=status.HTTP_200_OK, response_model=list[CommentRead])
async def list_comments(
    task_id: int,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    await get_task_or_404(db, task_id)

    result = await db.scalars(
        select(Comment)
        .where(Comment.task_id == task_id)
        .order_by(Comment.created_at, Comment.id)
        .limit(limit)
        .offset(offset)
    )
    return result.all()