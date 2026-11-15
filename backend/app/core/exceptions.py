from typing import Optional, Any, Dict
from fastapi import Request
from fastapi.responses import JSONResponse


class SpectraException(Exception):
    def __init__(
        self,
        status_code: int,
        title: str,
        detail: str,
        code: str,
        instance: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ):
        self.status_code = status_code
        self.title = title
        self.detail = detail
        self.code = code
        self.instance = instance
        self.extra = extra or {}
        super().__init__(detail)


class AuthenticationError(SpectraException):
    def __init__(self, detail: str = "Invalid credentials or token expired", code: str = "AUTH_UNAUTHORIZED"):
        super().__init__(
            status_code=401,
            title="Unauthorized",
            detail=detail,
            code=code,
        )


class PermissionDeniedError(SpectraException):
    def __init__(self, detail: str = "Permission denied", code: str = "AUTH_FORBIDDEN"):
        super().__init__(
            status_code=403,
            title="Forbidden",
            detail=detail,
            code=code,
        )


class NotFoundError(SpectraException):
    def __init__(self, detail: str = "Resource not found", code: str = "NOT_FOUND"):
        super().__init__(
            status_code=404,
            title="Not Found",
            detail=detail,
            code=code,
        )


class ConflictError(SpectraException):
    def __init__(self, detail: str = "Resource already exists", code: str = "CONFLICT"):
        super().__init__(
            status_code=409,
            title="Conflict",
            detail=detail,
            code=code,
        )


class ValidationError(SpectraException):
    def __init__(self, detail: str = "Validation failed", code: str = "VALIDATION_ERROR", extra: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=422,
            title="Unprocessable Entity",
            detail=detail,
            code=code,
            extra=extra,
        )


async def spectra_exception_handler(request: Request, exc: SpectraException) -> JSONResponse:
    content = {
        "type": f"https://docs.spectra.chat/errors/{exc.code.lower().replace('_', '-')}",
        "title": exc.title,
        "status": exc.status_code,
        "detail": exc.detail,
        "code": exc.code,
        "instance": exc.instance or str(request.url.path),
    }
    if exc.extra:
        content["extra"] = exc.extra
    return JSONResponse(status_code=exc.status_code, content=content)
