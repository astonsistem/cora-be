import logging

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.asis_client import AsisError

logger = logging.getLogger("app.errors")

def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AsisError)
    async def asis_error_handler(request: Request, exc: AsisError):
        logger.warning("ASIS error on %s %s: %s", request.method, request.url.path, exc)
        return JSONResponse(status_code=502, content={"detail": f"ASIS error: {exc}"})

    @app.exception_handler(httpx.HTTPError)
    async def asis_network_error_handler(request: Request, exc: httpx.HTTPError):
        logger.warning("Network error on %s %s: %s", request.method, request.url.path, exc)
        return JSONResponse(status_code=502, content={"detail": "Cannot reach ASIS"})

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(request: Request, exc: IntegrityError):
        logger.warning("Integrity error on %s %s: %s", request.method, request.url.path, exc.orig)
        return JSONResponse(
            status_code=409,
            content={"detail": "Data conflicts with existing records or references"},
        )

    @app.exception_handler(SQLAlchemyError)
    async def database_error_handler(request: Request, exc: SQLAlchemyError):
        logger.exception("Database error on %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Database error"})

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception):
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})
