import json
import logging
import re
import time
import uuid
from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from datetime import UTC, datetime

from fastapi import Request, Response

request_id: ContextVar[str | None] = ContextVar("request_id", default=None)

access_logger = logging.getLogger("app.access")

# Incoming IDs go into logs and headers.
_SAFE_ID = re.compile(r"[A-Za-z0-9._:;=-]{1,200}")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "time": datetime.fromtimestamp(record.created, UTC).isoformat(
                timespec="milliseconds"
            ),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if current_id := getattr(record, "request_id", None) or request_id.get():
            entry["request_id"] = current_id
        entry.update(getattr(record, "fields", {}))
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str)


def configure_logging(level: str) -> None:
    root = logging.getLogger()
    if not any(isinstance(h.formatter, JsonFormatter) for h in root.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        root.addHandler(handler)
    root.setLevel(level)

    # uvicorn logs through our handler; log_requests replaces its access log.
    for name in ("uvicorn", "uvicorn.error"):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = True
    logging.getLogger("uvicorn.access").disabled = True


def _incoming_id(request: Request) -> str:
    value = request.headers.get("x-request-id")
    if value and _SAFE_ID.fullmatch(value):
        return value
    return uuid.uuid4().hex


async def log_requests(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    current_id = _incoming_id(request)
    # Not reset, so uvicorn's crash traceback still has it. Each request runs in
    # its own task, so it doesn't leak into others.
    request_id.set(current_id)
    started = time.perf_counter()
    status = 500  # Stays 500 if call_next raises.
    try:
        response = await call_next(request)
        status = response.status_code
        response.headers["X-Request-ID"] = current_id
        return response
    finally:
        # Health checks run every few seconds; only log the failing ones.
        if not (request.url.path.startswith("/health/") and status == 200):
            access_logger.info(
                "%s %s %s",
                request.method,
                request.url.path,
                status,
                extra={
                    "request_id": current_id,
                    "fields": {
                        "method": request.method,
                        "path": request.url.path,
                        "status": status,
                        "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                    },
                },
            )
