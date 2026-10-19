from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    status_code = 500
    code = "internal_error"
    detail = "Internal error"


class BookNotFound(AppError):
    status_code = 404
    code = "book_not_found"
    detail = "Book not found"


class UnknownAuthors(AppError):
    status_code = 422
    code = "unknown_authors"

    def __init__(self, author_ids: list[str]) -> None:
        super().__init__()
        self.detail = f"Unknown author ids: {', '.join(author_ids)}"


def error_response(
    status_code: int,
    code: str,
    detail: str,
    errors: list[dict] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    content: dict = {"code": code, "detail": detail}
    if errors is not None:
        content["errors"] = errors
    return JSONResponse(status_code=status_code, content=content, headers=headers)


async def _app_error(request: Request, exc: AppError) -> JSONResponse:
    return error_response(exc.status_code, exc.code, exc.detail)


async def _validation_error(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    # Keep only loc and msg: Pydantic's input/ctx/url echo client data back.
    errors = [{"loc": list(e["loc"]), "msg": e["msg"]} for e in exc.errors()]
    return error_response(422, "validation_error", "Request validation failed", errors)


async def _http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    # Framework errors such as unknown routes (404) and wrong methods (405).
    code = HTTPStatus(exc.status_code).name.lower()
    return error_response(exc.status_code, code, exc.detail, headers=exc.headers)


async def _unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    # Starlette re-raises after this handler, so the server still logs the
    # traceback; the client only gets the generic envelope.
    return error_response(500, AppError.code, AppError.detail)


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(StarletteHTTPException, _http_error)
    app.add_exception_handler(Exception, _unexpected_error)
