import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import Depends, FastAPI

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.CORS_middleware import register_cors
from app.middleware.error_handler import register_exception_handlers
from app.services.customer_purge_service import CustomerPurgeScheduler, CustomerPurgeService

from app.routes import (
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
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    purge_task = asyncio.create_task(CustomerPurgeScheduler(CustomerPurgeService()).run())
    try:
        yield
    finally:
        purge_task.cancel()
        with suppress(asyncio.CancelledError):
            await purge_task

app = FastAPI(title="CORA API", lifespan=lifespan)

register_cors(app)
register_exception_handlers(app)

for module in (
    auth_route,
    category_route,
    source_route,
    company_route,
    branch_route,
    user_route,
    customer_route,
    customer_visit_route,
    asis_route,
    public_route,
    report_route,
):
    app.include_router(module.router)

@app.get("/")
def root():
    return {"message": "CORA API is running"}

@app.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}