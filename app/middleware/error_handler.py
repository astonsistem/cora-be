import logging

import httpx
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.integrations.asis_client import AsisError
from app.exceptions import DomainError

logger = logging.getLogger("app.errors")

def error_response(status_code: int, message: str, data=None, headers: dict | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"success": False, "message": message, "data": data},
        headers=headers,
    )

def validation_message(errors: list[dict]) -> str:
    parts = []
    for error in errors:
        location = ".".join(str(part) for part in error.get("loc", ())[1:])
        text = str(error.get("msg", "Invalid value")).removeprefix("Value error, ")
        parts.append(f"{location}: {text}" if location else text)
    return "; ".join(parts) or "Validation failed"

def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError):
        return error_response(exc.status_code, exc.detail)

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        message = exc.detail if isinstance(exc.detail, str) else "Request failed"
        return error_response(exc.status_code, message, headers=getattr(exc, "headers", None))

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        errors = jsonable_encoder(exc.errors())
        return error_response(422, validation_message(errors), data=errors)

    @app.exception_handler(AsisError)
    async def asis_error_handler(request: Request, exc: AsisError):
        logger.warning("ASIS error on %s %s: %s", request.method, request.url.path, exc)
        return error_response(502, f"ASIS error: {exc}")

    @app.exception_handler(httpx.HTTPError)
    async def asis_network_error_handler(request: Request, exc: httpx.HTTPError):
        logger.warning("Network error on %s %s: %s", request.method, request.url.path, exc)
        return error_response(502, "Cannot reach ASIS")

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(request: Request, exc: IntegrityError):
        logger.warning("Integrity error on %s %s: %s", request.method, request.url.path, exc.orig)
        return error_response(409, "Data conflicts with existing records or references")

    @app.exception_handler(SQLAlchemyError)
    async def database_error_handler(request: Request, exc: SQLAlchemyError):
        logger.exception("Database error on %s %s", request.method, request.url.path)
        return error_response(500, "Database error")

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception):
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return error_response(500, "Internal server error")
