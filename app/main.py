from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.error_handler import register_exception_handlers

from app.routes import (
    auth_route,
    branch_route,
    category_route,
    company_route,
    customer_visit_route,
    source_route,
    user_route,
)

app = FastAPI(title="CORA API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

for module in (
    auth_route,
    category_route,
    source_route,
    company_route,
    branch_route,
    user_route,
    customer_visit_route,
):
    app.include_router(module.router)


@app.get("/")
def root():
    return {"message": "CORA API is running"}


@app.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}