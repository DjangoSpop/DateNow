"""
Uniform error envelope (see docs/API_CONTRACT.md "Error envelope").

Every non-2xx response is `{"error": {"code": ..., "message": ..., "fields"?: {...}}}`.
Routes raise `AppError`; legacy `HTTPException`s, validation errors and unhandled exceptions are
converted by the handlers registered in `register_exception_handlers`.
"""
import logging
from typing import Dict, Optional

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppError(Exception):
    """An error with a stable machine-readable code, rendered as the contract's error envelope."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        fields: Optional[Dict[str, str]] = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.fields = fields
        self.headers = headers


# Default codes for HTTPExceptions raised by legacy routes / the framework itself.
_STATUS_CODES = {
    400: "BAD_REQUEST",
    401: "NOT_AUTHENTICATED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMITED",
}


def error_body(code: str, message: str, fields: Optional[Dict[str, str]] = None) -> dict:
    err: dict = {"code": code, "message": message}
    if fields is not None:
        err["fields"] = fields
    return {"error": err}


def _field_key(loc) -> str:
    parts = [str(p) for p in loc]
    # Drop the request-part prefix ("body", "query", ...) so keys are plain field names.
    if len(parts) > 1 and parts[0] in ("body", "query", "path", "header", "cookie"):
        parts = parts[1:]
    return ".".join(parts)


def _clean_msg(msg: str) -> str:
    for prefix in ("Value error, ", "Assertion failed, "):
        if msg.startswith(prefix):
            return msg[len(prefix):]
    return msg


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=error_body(exc.code, exc.message, exc.fields),
        headers=exc.headers,
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = _STATUS_CODES.get(exc.status_code, "INTERNAL_ERROR" if exc.status_code >= 500 else "HTTP_ERROR")
    message = exc.detail if isinstance(exc.detail, str) else code.replace("_", " ").capitalize()
    return JSONResponse(
        status_code=exc.status_code,
        content=error_body(code, message),
        headers=getattr(exc, "headers", None),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    fields: Dict[str, str] = {}
    for err in exc.errors():
        key = _field_key(err.get("loc", ())) or "body"
        fields.setdefault(key, _clean_msg(err.get("msg", "invalid")))
    return JSONResponse(
        status_code=422,
        content=error_body("VALIDATION_ERROR", "Request validation failed", fields),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content=error_body("INTERNAL_ERROR", "Internal server error"))


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
