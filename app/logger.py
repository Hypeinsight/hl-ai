"""Logging configuration with database support"""
import structlog
import logging
import sys
import traceback
from datetime import datetime
from typing import Optional, Dict, Any
from contextvars import ContextVar
from uuid import UUID

from app.config import settings

# ==================================================================
# CONTEXT VARIABLES (for request tracking)
# ==================================================================

_request_id: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
_tenant_id: ContextVar[Optional[str]] = ContextVar('tenant_id', default=None)
_user_id: ContextVar[Optional[str]] = ContextVar('user_id', default=None)


def set_request_context(request_id: str, tenant_id: str = None, user_id: str = None):
    """
    Set context for logging

    Args:
        request_id: Unique request identifier
        tenant_id: Tenant UUID (optional)
        user_id: User UUID (optional)
    """
    _request_id.set(request_id)
    if tenant_id:
        _tenant_id.set(tenant_id)
    if user_id:
        _user_id.set(user_id)


def get_request_context() -> Dict[str, Optional[str]]:
    """
    Get current request context

    Returns:
        Dictionary with request_id, tenant_id, user_id
    """
    return {
        'request_id': _request_id.get(),
        'tenant_id': _tenant_id.get(),
        'user_id': _user_id.get()
    }


def clear_request_context():
    """Clear request context"""
    _request_id.set(None)
    _tenant_id.set(None)
    _user_id.set(None)


# ==================================================================
# DATABASE LOGGER
# ==================================================================

class DatabaseLogger:
    """Logger that writes to both console and database"""

    def __init__(self):
        # Setup structlog for console output
        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.processors.add_log_level,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.dev.ConsoleRenderer()
            ],
            wrapper_class=structlog.make_filtering_bound_logger(
                logging.getLevelName(settings.LOG_LEVEL)
            ),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=False
        )
        self.console = structlog.get_logger()

    def _log_to_db(
        self,
        level: str,
        message: str,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        message_control_id: Optional[str] = None,
        exception: Optional[Exception] = None,
        extra_data: Optional[Dict[str, Any]] = None,
        logger_name: Optional[str] = None
    ):
        """
        Write log entry to database

        Args:
            level: Log level (INFO, WARNING, ERROR, CRITICAL)
            message: Log message
            tenant_id: Tenant UUID
            user_id: User UUID
            message_control_id: HL7 message control ID
            exception: Exception object if error
            extra_data: Additional context data
            logger_name: Logger name/module
        """
        if not settings.LOG_TO_DATABASE:
            return

        try:
            from app.database import get_registry_session
            from app.models.registry import ApplicationLog

            context = get_request_context()

            # Extract exception details if present
            exception_type = None
            exception_message = None
            stack_trace = None

            if exception:
                exception_type = type(exception).__name__
                exception_message = str(exception)
                stack_trace = traceback.format_exc()

            # Create log entry
            log_entry = ApplicationLog(
                level=level,
                logger_name=logger_name or 'app',
                message=message,
                tenant_id=UUID(tenant_id) if tenant_id else (UUID(context['tenant_id']) if context['tenant_id'] else None),
                user_id=UUID(user_id) if user_id else (UUID(context['user_id']) if context['user_id'] else None),
                message_control_id=message_control_id,
                exception_type=exception_type,
                exception_message=exception_message,
                stack_trace=stack_trace,
                extra_data=extra_data,
                request_id=context['request_id'],
                created_at=datetime.utcnow()
            )

            # Write to database
            with get_registry_session() as session:
                session.add(log_entry)
                session.commit()

        except Exception as e:
            # If database logging fails, at least log to console
            self.console.error(
                "Failed to log to database",
                error=str(e),
                original_message=message
            )

    def info(
        self,
        message: str,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        message_control_id: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """Log info message"""
        self.console.info(message, **kwargs)
        self._log_to_db(
            level='INFO',
            message=message,
            tenant_id=tenant_id,
            user_id=user_id,
            message_control_id=message_control_id,
            extra_data=extra_data or kwargs
        )

    def warning(
        self,
        message: str,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        message_control_id: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """Log warning message"""
        self.console.warning(message, **kwargs)
        self._log_to_db(
            level='WARNING',
            message=message,
            tenant_id=tenant_id,
            user_id=user_id,
            message_control_id=message_control_id,
            extra_data=extra_data or kwargs
        )

    def error(
        self,
        message: str,
        exception: Optional[Exception] = None,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        message_control_id: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """Log error message"""
        self.console.error(message, exception=exception, **kwargs)
        self._log_to_db(
            level='ERROR',
            message=message,
            tenant_id=tenant_id,
            user_id=user_id,
            message_control_id=message_control_id,
            exception=exception,
            extra_data=extra_data or kwargs
        )

    def critical(
        self,
        message: str,
        exception: Optional[Exception] = None,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        message_control_id: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """Log critical message"""
        self.console.critical(message, exception=exception, **kwargs)
        self._log_to_db(
            level='CRITICAL',
            message=message,
            tenant_id=tenant_id,
            user_id=user_id,
            message_control_id=message_control_id,
            exception=exception,
            extra_data=extra_data or kwargs
        )


# ==================================================================
# GLOBAL LOGGER INSTANCE
# ==================================================================

logger = DatabaseLogger()


# ==================================================================
# CONVENIENCE FUNCTIONS
# ==================================================================

def log_info(message: str, **kwargs):
    """Convenience function for info logging"""
    logger.info(message, **kwargs)


def log_warning(message: str, **kwargs):
    """Convenience function for warning logging"""
    logger.warning(message, **kwargs)


def log_error(message: str, exception: Optional[Exception] = None, **kwargs):
    """Convenience function for error logging"""
    logger.error(message, exception=exception, **kwargs)


def log_critical(message: str, exception: Optional[Exception] = None, **kwargs):
    """Convenience function for critical logging"""
    logger.critical(message, exception=exception, **kwargs)


# ==================================================================
# LOGGING DECORATORS
# ==================================================================

def log_function_call(func):
    """
    Decorator to log function calls

    Usage:
        @log_function_call
        def my_function(arg1, arg2):
            ...
    """
    def wrapper(*args, **kwargs):
        func_name = f"{func.__module__}.{func.__name__}"
        log_info(f"Calling {func_name}", extra_data={'args': str(args), 'kwargs': str(kwargs)})
        try:
            result = func(*args, **kwargs)
            log_info(f"Completed {func_name}")
            return result
        except Exception as e:
            log_error(f"Error in {func_name}", exception=e)
            raise

    return wrapper


def log_async_function_call(func):
    """
    Decorator to log async function calls

    Usage:
        @log_async_function_call
        async def my_async_function(arg1, arg2):
            ...
    """
    async def wrapper(*args, **kwargs):
        func_name = f"{func.__module__}.{func.__name__}"
        log_info(f"Calling {func_name}", extra_data={'args': str(args), 'kwargs': str(kwargs)})
        try:
            result = await func(*args, **kwargs)
            log_info(f"Completed {func_name}")
            return result
        except Exception as e:
            log_error(f"Error in {func_name}", exception=e)
            raise

    return wrapper
