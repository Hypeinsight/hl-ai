"""Audit logging repository"""
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime

from app.database import get_registry_session, get_tenant_session
from app.models.registry import AuditLog
from app.models.tenant import TenantAuditLog
from app.logger import get_request_context


class AuditRepository:
    """Repository for audit logging (compliance trail)"""

    @staticmethod
    def log_registry_event(
        event_type: str,
        event_category: str,
        severity: str,
        description: str,
        tenant_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        message_control_id: Optional[str] = None,
        old_value: Optional[Dict[str, Any]] = None,
        new_value: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        """
        Log audit event to registry database

        Args:
            event_type: Type of event (e.g., 'MESSAGE_SENT', 'USER_LOGIN', 'TENANT_CREATED')
            event_category: Category (e.g., 'AUTHENTICATION', 'MESSAGE', 'CONFIGURATION')
            severity: Severity level ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')
            description: Human-readable description
            tenant_id: Tenant UUID (optional)
            user_id: User UUID (optional)
            message_control_id: HL7 message control ID (optional)
            old_value: Previous value (for updates)
            new_value: New value (for updates)
            metadata: Additional metadata

        Returns:
            Created AuditLog instance

        Example:
            AuditRepository.log_registry_event(
                event_type='PROVIDER_REGISTERED',
                event_category='CONFIGURATION',
                severity='MEDIUM',
                description='Provider 1234567A registered for tenant XYZ',
                tenant_id=tenant_id,
                metadata={'provider_number': '1234567A'}
            )
        """
        context = get_request_context()

        audit_entry = AuditLog(
            event_type=event_type,
            event_category=event_category,
            severity=severity,
            tenant_id=tenant_id,
            user_id=user_id,
            message_control_id=message_control_id,
            description=description,
            old_value=old_value,
            new_value=new_value,
            metadata=metadata,
            request_id=context['request_id'],
            created_at=datetime.utcnow()
        )

        with get_registry_session() as session:
            session.add(audit_entry)
            session.commit()
            session.refresh(audit_entry)

        return audit_entry

    @staticmethod
    def log_tenant_event(
        tenant_id: UUID,
        event_type: str,
        event_category: str,
        description: str,
        user_id: Optional[UUID] = None,
        patient_id: Optional[UUID] = None,
        message_id: Optional[UUID] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> TenantAuditLog:
        """
        Log audit event to tenant database

        Args:
            tenant_id: Tenant UUID
            event_type: Type of event
            event_category: Category
            description: Description
            user_id: User UUID (optional)
            patient_id: Patient UUID (optional)
            message_id: Message UUID (optional)
            metadata: Additional metadata

        Returns:
            Created TenantAuditLog instance

        Example:
            AuditRepository.log_tenant_event(
                tenant_id=tenant_id,
                event_type='MESSAGE_VIEWED',
                event_category='MESSAGE',
                description='User viewed inbound message',
                user_id=user_id,
                message_id=message_id
            )
        """
        audit_entry = TenantAuditLog(
            event_type=event_type,
            event_category=event_category,
            user_id=user_id,
            patient_id=patient_id,
            message_id=message_id,
            description=description,
            metadata=metadata,
            created_at=datetime.utcnow()
        )

        with get_tenant_session(tenant_id) as session:
            session.add(audit_entry)
            session.commit()
            session.refresh(audit_entry)

        return audit_entry

    @staticmethod
    def get_registry_audit_logs(
        tenant_id: Optional[UUID] = None,
        event_type: Optional[str] = None,
        event_category: Optional[str] = None,
        severity: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[AuditLog]:
        """
        Query audit logs from registry database

        Args:
            tenant_id: Filter by tenant
            event_type: Filter by event type
            event_category: Filter by category
            severity: Filter by severity
            start_date: Filter by start date
            end_date: Filter by end date
            limit: Maximum number of results

        Returns:
            List of AuditLog instances
        """
        with get_registry_session() as session:
            query = session.query(AuditLog)

            if tenant_id:
                query = query.filter(AuditLog.tenant_id == tenant_id)
            if event_type:
                query = query.filter(AuditLog.event_type == event_type)
            if event_category:
                query = query.filter(AuditLog.event_category == event_category)
            if severity:
                query = query.filter(AuditLog.severity == severity)
            if start_date:
                query = query.filter(AuditLog.created_at >= start_date)
            if end_date:
                query = query.filter(AuditLog.created_at <= end_date)

            query = query.order_by(AuditLog.created_at.desc())
            query = query.limit(limit)

            return query.all()

    @staticmethod
    def get_tenant_audit_logs(
        tenant_id: UUID,
        event_type: Optional[str] = None,
        event_category: Optional[str] = None,
        user_id: Optional[UUID] = None,
        patient_id: Optional[UUID] = None,
        message_id: Optional[UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[TenantAuditLog]:
        """
        Query audit logs from tenant database

        Args:
            tenant_id: Tenant UUID
            event_type: Filter by event type
            event_category: Filter by category
            user_id: Filter by user
            patient_id: Filter by patient
            message_id: Filter by message
            start_date: Filter by start date
            end_date: Filter by end date
            limit: Maximum number of results

        Returns:
            List of TenantAuditLog instances
        """
        with get_tenant_session(tenant_id) as session:
            query = session.query(TenantAuditLog)

            if event_type:
                query = query.filter(TenantAuditLog.event_type == event_type)
            if event_category:
                query = query.filter(TenantAuditLog.event_category == event_category)
            if user_id:
                query = query.filter(TenantAuditLog.user_id == user_id)
            if patient_id:
                query = query.filter(TenantAuditLog.patient_id == patient_id)
            if message_id:
                query = query.filter(TenantAuditLog.message_id == message_id)
            if start_date:
                query = query.filter(TenantAuditLog.created_at >= start_date)
            if end_date:
                query = query.filter(TenantAuditLog.created_at <= end_date)

            query = query.order_by(TenantAuditLog.created_at.desc())
            query = query.limit(limit)

            return query.all()


# ==================================================================
# CONVENIENCE FUNCTIONS
# ==================================================================

def audit_message_sent(
    tenant_id: UUID,
    user_id: UUID,
    message_id: UUID,
    message_control_id: str,
    recipient_edi: str
):
    """Audit: Message sent"""
    AuditRepository.log_registry_event(
        event_type='MESSAGE_SENT',
        event_category='MESSAGE',
        severity='MEDIUM',
        description=f'Outbound message sent to {recipient_edi}',
        tenant_id=tenant_id,
        user_id=user_id,
        message_control_id=message_control_id,
        metadata={'recipient_edi': recipient_edi}
    )

    AuditRepository.log_tenant_event(
        tenant_id=tenant_id,
        event_type='MESSAGE_SENT',
        event_category='MESSAGE',
        description=f'Outbound message sent to {recipient_edi}',
        user_id=user_id,
        message_id=message_id,
        metadata={'recipient_edi': recipient_edi}
    )


def audit_message_received(
    tenant_id: UUID,
    message_id: UUID,
    message_control_id: str,
    sender_edi: str
):
    """Audit: Message received"""
    AuditRepository.log_registry_event(
        event_type='MESSAGE_RECEIVED',
        event_category='MESSAGE',
        severity='MEDIUM',
        description=f'Inbound message received from {sender_edi}',
        tenant_id=tenant_id,
        message_control_id=message_control_id,
        metadata={'sender_edi': sender_edi}
    )

    AuditRepository.log_tenant_event(
        tenant_id=tenant_id,
        event_type='MESSAGE_RECEIVED',
        event_category='MESSAGE',
        description=f'Inbound message received from {sender_edi}',
        message_id=message_id,
        metadata={'sender_edi': sender_edi}
    )


def audit_provider_registered(
    tenant_id: UUID,
    provider_number: str,
    provider_name: str,
    user_id: Optional[UUID] = None
):
    """Audit: Provider registered"""
    AuditRepository.log_registry_event(
        event_type='PROVIDER_REGISTERED',
        event_category='CONFIGURATION',
        severity='MEDIUM',
        description=f'Provider {provider_number} ({provider_name}) registered',
        tenant_id=tenant_id,
        user_id=user_id,
        metadata={'provider_number': provider_number, 'provider_name': provider_name}
    )


def audit_tenant_created(
    tenant_id: UUID,
    tenant_key: str,
    organization_name: str,
    user_id: Optional[UUID] = None
):
    """Audit: Tenant created"""
    AuditRepository.log_registry_event(
        event_type='TENANT_CREATED',
        event_category='CONFIGURATION',
        severity='HIGH',
        description=f'Tenant {tenant_key} ({organization_name}) created',
        tenant_id=tenant_id,
        user_id=user_id,
        metadata={'tenant_key': tenant_key, 'organization_name': organization_name}
    )


def audit_authentication_success(user_id: UUID, tenant_id: Optional[UUID] = None):
    """Audit: Successful authentication"""
    AuditRepository.log_registry_event(
        event_type='AUTHENTICATION_SUCCESS',
        event_category='AUTHENTICATION',
        severity='LOW',
        description='User authenticated successfully',
        tenant_id=tenant_id,
        user_id=user_id
    )


def audit_authentication_failure(email: str, reason: str):
    """Audit: Failed authentication"""
    AuditRepository.log_registry_event(
        event_type='AUTHENTICATION_FAILURE',
        event_category='AUTHENTICATION',
        severity='MEDIUM',
        description=f'Authentication failed for {email}: {reason}',
        metadata={'email': email, 'reason': reason}
    )
