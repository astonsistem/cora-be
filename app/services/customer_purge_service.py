import asyncio
import logging
from datetime import datetime, timedelta

from sqlalchemy import delete, select, update
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database import SessionLocal
from app.models.customer_visits import CustomerVisits
from app.models.customers import Customers

logger = logging.getLogger("app.purge")

class CustomerPurgeService:
    def __init__(
        self,
        session_factory: sessionmaker = SessionLocal,
        retention_days: int | None = None,
    ):
        self._session_factory = session_factory
        self.retention_days = settings.customer_trash_retention_days if retention_days is None else retention_days

    def cutoff(self, now: datetime | None = None) -> datetime:
        return (now or datetime.now()) - timedelta(days=self.retention_days)

    def purge_expired(self, now: datetime | None = None) -> int:
        expired = select(Customers.customer_id).where(
            Customers.deleted_at.isnot(None),
            Customers.deleted_at < self.cutoff(now),
        )
        with self._session_factory() as db:
            db.execute(update(CustomerVisits).where(CustomerVisits.customer_id.in_(expired)).values(customer_id=None))
            result = db.execute(delete(Customers).where(Customers.customer_id.in_(expired)))
            db.commit()
            return result.rowcount or 0

class CustomerPurgeScheduler:
    def __init__(self, service: CustomerPurgeService, interval_seconds: float = 24 * 60 * 60):
        self.service = service
        self.interval_seconds = interval_seconds

    async def run(self) -> None:
        while True:
            await self.run_once()
            await asyncio.sleep(self.interval_seconds)

    async def run_once(self) -> None:
        try:
            purged = await asyncio.to_thread(self.service.purge_expired)
            if purged:
                logger.info("Purged %s expired deleted customers", purged)
        except Exception:
            logger.exception("Failed to purge expired deleted customers")
