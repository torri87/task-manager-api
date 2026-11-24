import asyncio
import os


TEST_DB = "postgresql+asyncpg://postgres:postgres@db:5432/tasks_test"
os.environ["DATABASE_URL"] = TEST_DB
os.environ["OVERDUE_CHECK_INTERVAL_SECONDS"] = "3600"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from app import models  # noqa: F401
from app.database import Base
from app.main import app


async def create_tables():
    engine = create_async_engine(TEST_DB, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()


async def clear_tables():
    engine = create_async_engine(TEST_DB, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.execute(
            text("TRUNCATE users, tasks, comments RESTART IDENTITY CASCADE")
        )
    await engine.dispose()


@pytest.fixture(scope="session")
def client():
    asyncio.run(create_tables())
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def clean_db(client):
    asyncio.run(clear_tables())