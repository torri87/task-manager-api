import asyncio
from contextlib import asynccontextmanager, suppress
from fastapi import FastAPI, Depends
from app.background.overdue import cancel_overdue
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.routers import auth, tasks, comments


@asynccontextmanager
async def lifespan(app: FastAPI):
    worker = asyncio.create_task(cancel_overdue())
    yield
    worker.cancel()
    with suppress(asyncio.CancelledError):
        await worker


app = FastAPI(title='Task Manager API', lifespan=lifespan)
app.include_router(auth.router)
app.include_router(tasks.router)
app.include_router(comments.router)
@app.get('/')
async def health_check():
    return {'status': 'ok'}


@app.get('/health/db')
async def health_check(db: AsyncSession = Depends(get_db)):
    await db.execute(text('SELECT 1'))
    return {'database': 'ok'}