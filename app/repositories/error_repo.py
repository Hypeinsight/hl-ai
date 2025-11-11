"""Error tracking repository"""
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime, timedelta
import traceback
import hashlib

from app.database import get_registry_session
from app.models.registry import ErrorTracking


class ErrorTrackingRepository:
    """Repository for tracking and grouping errors"""

    @staticmethod
    def _generate_error_code(error_type: str, component: str, function_name: str) -> str:
        """
        Generate unique error code based on error characteristics

        Args:
            error_type: Type of error
            component: Component where error occurred
            function_name: Function name

        Returns:
            Unique error code (hash)
        """
        key = f"{error_type}:{component}:{function_name}"
        return hashlib.md5(key.encode()).hexdigest()[:12].upper()

    @staticmethod
    def track_error(
        error_type: str,
        error_message: str,
        component: str,
        function_name: str,
        exception: Optional[Exception] = None,
        tenant_id: Optional[UUID] = None,
        message_control_id: Optional[str] = None,
        context_data: Optional[Dict[str, Any]] = None
    ) -> ErrorTracking:
        """
        Track an error occurrence

        If a similar error exists (same code), increment occurrence count.
        Otherwise, create new error tracking entry.

        Args:
            error_type: Type of error (e.g., 'ValueError', 'DatabaseError')
            error_message: Error message
            component: Component name (e.g., 'hl7_parser', 'tenant_routing')
            function_name: Function where error occurred
            exception: Exception object (optional)
            tenant_id: Tenant UUID (optional)
            message_control_id: HL7 message control ID (optional)
            context_data: Additional context

        Returns:
            ErrorTracking instance

        Example:
            ErrorTrackingRepository.track_error(
                error_type='HL7ParseException',
                error_message='Invalid segment structure',
                component='hl7_parser',
                function_name='parse_message',
                exception=e,
                context_data={'filename': 'message.hl7'}
            )
        """
        # Generate error code
        error_code = ErrorTrackingRepository._generate_error_code(
            error_type, component, function_name
        )

        # Get stack trace if exception provided
        stack_trace = None
        if exception:
            stack_trace = traceback.format_exc()

        with get_registry_session() as session:
            # Check if similar error exists
            existing_error = session.query(ErrorTracking).filter(
                ErrorTracking.error_code == error_code,
                ErrorTracking.resolved == False
            ).first()

            if existing_error:
                # Update existing error
                existing_error.occurrences += 1
                existing_error.last_seen_at = datetime.utcnow()
                existing_error.error_message = error_message  # Update with latest message
                if stack_trace:
                    existing_error.stack_trace = stack_trace
                if context_data:
                    existing_error.context_data = context_data

                session.commit()
                session.refresh(existing_error)
                return existing_error
            else:
                # Create new error tracking entry
                new_error = ErrorTracking(
                    error_code=error_code,
                    error_type=error_type,
                    error_message=error_message,
                    tenant_id=tenant_id,
                    message_control_id=message_control_id,
                    component=component,
                    function_name=function_name,
                    stack_trace=stack_trace,
                    context_data=context_data,
                    occurrences=1,
                    first_seen_at=datetime.utcnow(),
                    last_seen_at=datetime.utcnow(),
                    resolved=False
                )

                session.add(new_error)
                session.commit()
                session.refresh(new_error)
                return new_error

    @staticmethod
    def resolve_error(error_id: UUID) -> bool:
        """
        Mark error as resolved

        Args:
            error_id: Error tracking UUID

        Returns:
            True if successful, False if error not found
        """
        with get_registry_session() as session:
            error = session.query(ErrorTracking).filter(
                ErrorTracking.id == error_id
            ).first()

            if not error:
                return False

            error.resolved = True
            session.commit()
            return True

    @staticmethod
    def resolve_errors_by_code(error_code: str) -> int:
        """
        Resolve all errors with given code

        Args:
            error_code: Error code

        Returns:
            Number of errors resolved
        """
        with get_registry_session() as session:
            count = session.query(ErrorTracking).filter(
                ErrorTracking.error_code == error_code,
                ErrorTracking.resolved == False
            ).update({'resolved': True})

            session.commit()
            return count

    @staticmethod
    def get_unresolved_errors(
        component: Optional[str] = None,
        error_type: Optional[str] = None,
        tenant_id: Optional[UUID] = None,
        min_occurrences: int = 1,
        limit: int = 100
    ) -> List[ErrorTracking]:
        """
        Get unresolved errors

        Args:
            component: Filter by component
            error_type: Filter by error type
            tenant_id: Filter by tenant
            min_occurrences: Minimum number of occurrences
            limit: Maximum number of results

        Returns:
            List of ErrorTracking instances ordered by occurrences
        """
        with get_registry_session() as session:
            query = session.query(ErrorTracking).filter(
                ErrorTracking.resolved == False
            )

            if component:
                query = query.filter(ErrorTracking.component == component)
            if error_type:
                query = query.filter(ErrorTracking.error_type == error_type)
            if tenant_id:
                query = query.filter(ErrorTracking.tenant_id == tenant_id)
            if min_occurrences > 1:
                query = query.filter(ErrorTracking.occurrences >= min_occurrences)

            query = query.order_by(ErrorTracking.occurrences.desc())
            query = query.limit(limit)

            return query.all()

    @staticmethod
    def get_recent_errors(hours: int = 24, limit: int = 100) -> List[ErrorTracking]:
        """
        Get errors from last N hours

        Args:
            hours: Number of hours to look back
            limit: Maximum number of results

        Returns:
            List of ErrorTracking instances
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        with get_registry_session() as session:
            query = session.query(ErrorTracking).filter(
                ErrorTracking.last_seen_at >= cutoff_time
            )

            query = query.order_by(ErrorTracking.last_seen_at.desc())
            query = query.limit(limit)

            return query.all()

    @staticmethod
    def get_error_by_code(error_code: str) -> Optional[ErrorTracking]:
        """
        Get error by code

        Args:
            error_code: Error code

        Returns:
            ErrorTracking instance or None
        """
        with get_registry_session() as session:
            return session.query(ErrorTracking).filter(
                ErrorTracking.error_code == error_code
            ).first()

    @staticmethod
    def get_error_stats(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get error statistics

        Args:
            start_date: Start date (optional)
            end_date: End date (optional)

        Returns:
            Dictionary with error statistics
        """
        with get_registry_session() as session:
            query = session.query(ErrorTracking)

            if start_date:
                query = query.filter(ErrorTracking.first_seen_at >= start_date)
            if end_date:
                query = query.filter(ErrorTracking.first_seen_at <= end_date)

            all_errors = query.all()

            total_errors = len(all_errors)
            unresolved_errors = len([e for e in all_errors if not e.resolved])
            resolved_errors = total_errors - unresolved_errors
            total_occurrences = sum(e.occurrences for e in all_errors)

            # Group by component
            by_component = {}
            for error in all_errors:
                component = error.component or 'unknown'
                if component not in by_component:
                    by_component[component] = {'count': 0, 'occurrences': 0}
                by_component[component]['count'] += 1
                by_component[component]['occurrences'] += error.occurrences

            # Group by type
            by_type = {}
            for error in all_errors:
                error_type = error.error_type or 'unknown'
                if error_type not in by_type:
                    by_type[error_type] = {'count': 0, 'occurrences': 0}
                by_type[error_type]['count'] += 1
                by_type[error_type]['occurrences'] += error.occurrences

            return {
                'total_unique_errors': total_errors,
                'unresolved_errors': unresolved_errors,
                'resolved_errors': resolved_errors,
                'total_occurrences': total_occurrences,
                'by_component': by_component,
                'by_type': by_type
            }


# ==================================================================
# CONVENIENCE FUNCTIONS
# ==================================================================

def track_hl7_parse_error(
    error_message: str,
    exception: Optional[Exception] = None,
    filename: Optional[str] = None
):
    """Track HL7 parsing error"""
    return ErrorTrackingRepository.track_error(
        error_type='HL7ParseException',
        error_message=error_message,
        component='hl7_parser',
        function_name='parse_message',
        exception=exception,
        context_data={'filename': filename} if filename else None
    )


def track_routing_error(
    error_message: str,
    message_control_id: str,
    exception: Optional[Exception] = None,
    context_data: Optional[Dict[str, Any]] = None
):
    """Track message routing error"""
    return ErrorTrackingRepository.track_error(
        error_type='MessageRoutingException',
        error_message=error_message,
        component='tenant_routing',
        function_name='route_message',
        exception=exception,
        message_control_id=message_control_id,
        context_data=context_data
    )


def track_database_error(
    error_message: str,
    tenant_id: Optional[UUID] = None,
    exception: Optional[Exception] = None
):
    """Track database error"""
    return ErrorTrackingRepository.track_error(
        error_type='DatabaseError',
        error_message=error_message,
        component='database',
        function_name='get_tenant_session',
        exception=exception,
        tenant_id=tenant_id
    )
