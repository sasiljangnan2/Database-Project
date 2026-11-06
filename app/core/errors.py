import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException

from app.schemas.common import Error, ErrorContent, ErrorDetail

logger = logging.getLogger(__name__)


class AppError(Exception):
    def __init__(self, status: int, code: str, message: str, *, details=None, headers=None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.details = details or []
        self.headers = headers


def error_response(status: int, code: str, message: str, details=None, headers=None):
    payload = Error(error=ErrorContent(code=code, message=message, details=details or []))
    return JSONResponse(status_code=status, content=payload.model_dump(), headers=headers)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def application_error(_request: Request, error: AppError):
        return error_response(error.status, error.code, error.message, error.details, error.headers)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, error: RequestValidationError):
        # input/ctx를 응답하지 않는다. 비밀번호·토큰이 입력 오류에 포함될 수 있다.
        details = [
            ErrorDetail(
                field=".".join(map(str, item["loc"])) or "request",
                message=item["msg"],
            )
            for item in error.errors()
        ]
        return error_response(422, "VALIDATION_ERROR", "입력값을 확인해 주세요.", details)

    @app.exception_handler(HTTPException)
    async def http_error(_request: Request, error: HTTPException):
        code = {401: "AUTH_REQUIRED", 403: "ADMIN_REQUIRED", 404: "RESOURCE_NOT_FOUND"}.get(
            error.status_code, "HTTP_ERROR"
        )
        return error_response(
            error.status_code, code, "요청을 처리할 수 없습니다.", headers=error.headers
        )

    @app.exception_handler(SQLAlchemyError)
    async def database_error(_request: Request, _error: SQLAlchemyError):
        logger.warning("Database request failed; connection credentials are omitted")
        return error_response(503, "DATABASE_UNAVAILABLE", "DB 연결 또는 스키마를 확인해 주세요.")

    @app.exception_handler(Exception)
    async def unexpected_error(_request: Request, _error: Exception):
        logger.error("Unexpected request failure; exception payload is omitted")
        return error_response(500, "INTERNAL_ERROR", "요청 처리 중 오류가 발생했습니다.")
