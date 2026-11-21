import asyncio
import logging
from datetime import datetime, timedelta

from sqlalchemy import or_, update
from sqlalchemy.orm import sessionmaker

from app.core.config.config import settings
from app.core.database.database import SessionLocal
from app.models.voucher import Vouchers

logger = logging.getLogger("app.archive")

class VoucherArchiveService:
    def __init__(
        self,
        session_factory: sessionmaker = SessionLocal,
        archive_after_days: int | None = None,
    ):
        self._session_factory = session_factory
        self.archive_after_days = (
            settings.voucher_archive_after_days if archive_after_days is None else archive_after_days
        )

    def cutoff(self, now: datetime | None = None) -> datetime:
        return (now or datetime.now()) - timedelta(days=self.archive_after_days)

    def archive_finished(self, now: datetime | None = None) -> int:
        moment = now or datetime.now()
        cutoff = self.cutoff(moment)
        finished = or_(
            Vouchers.date_expired < cutoff.date(),
            Vouchers.sold_out_at < cutoff,
        )
        with self._session_factory() as db:
            result = db.execute(
                update(Vouchers)
                .where(Vouchers.archived_at.is_(None), finished)
                .values(archived_at=moment)
            )
            db.commit()
            return result.rowcount or 0

class VoucherArchiveScheduler:
    def __init__(self, service: VoucherArchiveService, interval_seconds: float = 24 * 60 * 60):
        self.service = service
        self.interval_seconds = interval_seconds

    async def run(self) -> None:
        while True:
            await self.run_once()
            await asyncio.sleep(self.interval_seconds)

    async def run_once(self) -> None:
        try:
            archived = await asyncio.to_thread(self.service.archive_finished)
            if archived:
                logger.info("Archived %s finished vouchers", archived)
        except Exception:
            logger.exception("Failed to archive finished vouchers")
