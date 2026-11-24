from fastapi import FastAPI, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.routers import auth, tasks, comments
app = FastAPI(title='Task Manager API')
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