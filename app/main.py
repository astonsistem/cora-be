import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import Depends, FastAPI

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database.database import get_db
from app.core.log.logging_config import AppLogging
from app.middleware.CORS_middleware import register_cors
from app.middleware.error_handler import register_exception_handlers
from app.services.activity_log_archive_service import ActivityLogArchiveScheduler, ActivityLogArchiveService
from app.services.customer_purge_service import CustomerPurgeScheduler, CustomerPurgeService
from app.services.voucher_archive_service import VoucherArchiveScheduler, VoucherArchiveService

from app.routes import (
    activity_log_route,
    asis_credential_route,
    asis_route,
    auth_route,
    branch_route,
    category_route,
    company_route,
    customer_route,
    customer_visit_route,
    public_route,
    report_route,
    source_route,
    user_route,
    visit_question_route,
    voucher_claim_route,
    voucher_public_route,
    voucher_qr_route,
    voucher_route,
)

AppLogging.configure()

@asynccontextmanager
async def lifespan(app: FastAPI):
    tasks = [
        asyncio.create_task(CustomerPurgeScheduler(CustomerPurgeService()).run()),
        asyncio.create_task(VoucherArchiveScheduler(VoucherArchiveService()).run()),
        asyncio.create_task(ActivityLogArchiveScheduler(ActivityLogArchiveService()).run()),
    ]
    try:
        yield
    finally:
        for task in tasks:
            task.cancel()
        for task in tasks:
            with suppress(asyncio.CancelledError):
                await task

app = FastAPI(title="CORA API", lifespan=lifespan)

register_cors(app)
register_exception_handlers(app)

for module in (
    activity_log_route,
    auth_route,
    category_route,
    source_route,
    company_route,
    branch_route,
    user_route,
    customer_route,
    customer_visit_route,
    asis_credential_route,
    asis_route,
    public_route,
    report_route,
    voucher_route,
    voucher_claim_route,
    voucher_qr_route,
    visit_question_route,
    voucher_public_route,
):
    app.include_router(module.router)

@app.get("/")
def root():
    return {"message": "CORA API is running"}

@app.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}