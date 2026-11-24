import asyncio
import logging

from app.config import settings
from app.database import SessionLocal
from app.services.task_service import cancel_overdue_tasks
logger = logging.getLogger('uvicorn.error')


async def cancel_overdue():
    while True:
        try:
            async with SessionLocal() as session:
                count = await cancel_overdue_tasks(session)
            if count:
                logger.info(f"Cancel overdue tasks: {count}")
        except Exception:
            logger.exception("Overdue check fail")
        await asyncio.sleep(settings.overdue_check_interval_seconds)