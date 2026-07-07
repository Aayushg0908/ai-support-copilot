
"""
Custom exceptions and error handlers for the application.

Why custom exceptions?
- Frontend needs structured error responses
- Different HTTP status codes for different problems
- Consistent error format across all endpoints
- Easy to add logging/monitoring to specific errors
"""

from typing import Any, Dict, Optional
from fastapi import HTTPException, status


class AppException(HTTPException):
    """
    Base exception for all application errors.
    
    All custom exceptions inherit from this to ensure
    consistent error response format.
    """
    def __init__(
        self,
        status_code: int,
        detail: str,
        error_code: str = "INTERNAL_ERROR",
        headers: Optional[Dict[str, Any]] = None
    ):
        self.error_code = error_code
        super().__init__(
            status_code=status_code,
            detail={
                "success": False,
                "error": {
                    "code": error_code,
                    "message": detail
                }
            },
            headers=headers
        )


class NotFoundException(AppException):
    """Resource not found (404)."""
    def __init__(self, resource: str, identifier: Any):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource} with id '{identifier}' not found",
            error_code=f"{resource.upper()}_NOT_FOUND"
        )


class UnauthorizedException(AppException):
    """Authentication required (401)."""
    def __init__(self, detail: str = "Authentication required"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            error_code="UNAUTHORIZED"
        )


class ForbiddenException(AppException):
    """Insufficient permissions (403)."""
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            error_code="FORBIDDEN"
        )


class ConflictException(AppException):
    """Resource already exists (409)."""
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
            error_code="CONFLICT"
        )


class ValidationException(AppException):
    """Validation error (422)."""
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
            error_code="VALIDATION_ERROR"
        )


class AIServiceException(AppException):
    """AI service errors (502)."""
    def __init__(self, detail: str = "AI service unavailable"):
        super().__init__(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=detail,
            error_code="AI_SERVICE_ERROR"
        )