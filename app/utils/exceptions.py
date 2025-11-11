"""Custom exceptions and error handlers"""
from typing import Optional, Dict, Any
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException


# ==================================================================
# CUSTOM EXCEPTIONS
# ==================================================================

class ARVIHealthLinkException(Exception):
    """Base exception for all ARVI HealthLink errors"""

    def __init__(
        self,
        message: str,
        error_code: str = "ARVI_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class TenantNotFoundException(ARVIHealthLinkException):
    """Raised when tenant is not found"""

    def __init__(self, tenant_id: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Tenant {tenant_id} not found",
            error_code="TENANT_NOT_FOUND",
            details=details
        )


class TenantInactiveException(ARVIHealthLinkException):
    """Raised when tenant is inactive"""

    def __init__(self, tenant_id: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Tenant {tenant_id} is not active",
            error_code="TENANT_INACTIVE",
            details=details
        )


class DatabaseConnectionException(ARVIHealthLinkException):
    """Raised when database connection fails"""

    def __init__(self, database_name: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Failed to connect to database {database_name}",
            error_code="DATABASE_CONNECTION_ERROR",
            details=details
        )


class HL7ParseException(ARVIHealthLinkException):
    """Raised when HL7 message parsing fails"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"HL7 parsing failed: {message}",
            error_code="HL7_PARSE_ERROR",
            details=details
        )


class HL7GenerationException(ARVIHealthLinkException):
    """Raised when HL7 message generation fails"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"HL7 generation failed: {message}",
            error_code="HL7_GENERATION_ERROR",
            details=details
        )


class MessageRoutingException(ARVIHealthLinkException):
    """Raised when message routing fails"""

    def __init__(self, message_id: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Failed to route message {message_id}",
            error_code="MESSAGE_ROUTING_ERROR",
            details=details
        )


class PatientNotFoundException(ARVIHealthLinkException):
    """Raised when patient is not found"""

    def __init__(self, patient_identifier: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Patient {patient_identifier} not found",
            error_code="PATIENT_NOT_FOUND",
            details=details
        )


class ProviderNotFoundException(ARVIHealthLinkException):
    """Raised when provider is not found"""

    def __init__(self, provider_identifier: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Provider {provider_identifier} not found",
            error_code="PROVIDER_NOT_FOUND",
            details=details
        )


class MessageNotFoundException(ARVIHealthLinkException):
    """Raised when message is not found"""

    def __init__(self, message_id: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Message {message_id} not found",
            error_code="MESSAGE_NOT_FOUND",
            details=details
        )


class HealthLinkFileException(ARVIHealthLinkException):
    """Raised when HealthLink file operation fails"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"HealthLink file operation failed: {message}",
            error_code="HEALTHLINK_FILE_ERROR",
            details=details
        )


class AuthenticationException(ARVIHealthLinkException):
    """Raised when authentication fails"""

    def __init__(self, message: str = "Authentication failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            details=details
        )


class AuthorizationException(ARVIHealthLinkException):
    """Raised when authorization fails"""

    def __init__(self, message: str = "Access denied", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            details=details
        )


class ValidationException(ARVIHealthLinkException):
    """Raised when validation fails"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Validation failed: {message}",
            error_code="VALIDATION_ERROR",
            details=details
        )


# ==================================================================
# EXCEPTION HANDLERS FOR FASTAPI
# ==================================================================

async def arvi_exception_handler(request: Request, exc: ARVIHealthLinkException):
    """Handle custom ARVI exceptions"""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": exc.error_code,
            "message": exc.message,
            "details": exc.details
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "details": exc.errors()
        }
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP_ERROR",
            "message": exc.detail,
            "details": {}
        }
    )


async def generic_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions"""
    # Log the exception
    import traceback
    error_trace = traceback.format_exc()

    # In production, don't expose internal errors
    from app.config import settings
    if settings.DEBUG:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "INTERNAL_SERVER_ERROR",
                "message": str(exc),
                "details": {"trace": error_trace}
            }
        )
    else:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "INTERNAL_SERVER_ERROR",
                "message": "An internal error occurred",
                "details": {}
            }
        )


def register_exception_handlers(app):
    """
    Register all exception handlers with FastAPI app

    Usage:
        from fastapi import FastAPI
        from app.utils.exceptions import register_exception_handlers

        app = FastAPI()
        register_exception_handlers(app)
    """
    app.add_exception_handler(ARVIHealthLinkException, arvi_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
