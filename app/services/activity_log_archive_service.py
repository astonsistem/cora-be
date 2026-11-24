import asyncio
import logging
from datetime import datetime, timedelta

from sqlalchemy import update
from sqlalchemy.orm import sessionmaker

from app.core.config.config import settings
from app.core.database.database import SessionLocal
from app.models.activity_log import ActivityLogs

logger = logging.getLogger("app.activity.archive")


class ActivityLogArchiveService:
    def __init__(
        self,
        session_factory: sessionmaker = SessionLocal,
        archive_after_days: int | None = None,
    ):
        self._session_factory = session_factory
        self.archive_after_days = (
            settings.activity_log_archive_after_days if archive_after_days is None else archive_after_days
        )

    def cutoff(self, now: datetime | None = None) -> datetime:
        return (now or datetime.now()) - timedelta(days=self.archive_after_days)

    def archive_expired(self, now: datetime | None = None) -> int:
        moment = now or datetime.now()
        with self._session_factory() as db:
            result = db.execute(
                update(ActivityLogs)
                .where(ActivityLogs.archived_at.is_(None), ActivityLogs.created_at < self.cutoff(moment))
                .values(archived_at=moment)
            )
            db.commit()
            return result.rowcount or 0


class ActivityLogArchiveScheduler:
    def __init__(self, service: ActivityLogArchiveService, interval_seconds: float = 24 * 60 * 60):
        self.service = service
        self.interval_seconds = interval_seconds

    async def run(self) -> None:
        while True:
            await self.run_once()
            await asyncio.sleep(self.interval_seconds)

    async def run_once(self) -> None:
        try:
            archived = await asyncio.to_thread(self.service.archive_expired)
            if archived:
                logger.info("Archived %s old activity logs", archived)
        except Exception:
            logger.exception("Failed to archive old activity logs")
