"""
Standardised error envelope for the whole API

Every error response uses the shape:

    {"error": {"code": "<machine_code>", "message": "<human>", "details": <any | null>}}

Applied via FastAPI exception handlers so even Pydantic validation errors
(which use a different default shape) come out wrapped consistently.
"""
from fastapi.encoders import jsonable_encoder
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


_STATUS_TO_CODE: dict[int, str] = {
    status.HTTP_400_BAD_REQUEST: "bad_request",
    status.HTTP_404_NOT_FOUND: "not_found",
    status.HTTP_409_CONFLICT: "conflict",
    status.HTTP_422_UNPROCESSABLE_ENTITY: "unprocessable_entity",
    status.HTTP_500_INTERNAL_SERVER_ERROR: "internal_server_error",
}


def _envelope(code: str, message: str, details: object = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details}}


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=jsonable_encoder(_envelope(
            code=_STATUS_TO_CODE.get(exc.status_code, "error"),
            message=str(exc.detail),
        )),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder(_envelope(
            code="validation_error",
            message="Request validation failed.",
            details=exc.errors(),
        )),
    )


def register_error_handlers(app: FastAPI) -> None:
    """Wire the standardised handlers into a FastAPI app."""
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)