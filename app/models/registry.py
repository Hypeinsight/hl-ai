"""SQLAlchemy models for registry database"""
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, ForeignKey, Text, Index, UUID, Date, CHAR
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
from uuid import uuid4
from datetime import datetime

Base = declarative_base()


class Tenant(Base):
    """Organizations using ARVI (each clinic/practice)"""

    __tablename__ = "tenants"

    id = Column(UUID, primary_key=True, default=uuid4)
    tenant_key = Column(String(100), unique=True, nullable=False, index=True)
    organization_name = Column(String(255), nullable=False)
    database_name = Column(String(100), nullable=False)
    database_host = Column(String(255), default="localhost")
    database_port = Column(Integer, default=5432)
    healthlink_enabled = Column(Boolean, default=True)
    status = Column(String(20), default="ACTIVE", index=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    providers = relationship("TenantProvider", back_populates="tenant", cascade="all, delete-orphan")
    patients = relationship("TenantPatient", back_populates="tenant", cascade="all, delete-orphan")
    routing_logs = relationship("MessageRouting", back_populates="tenant")
    audit_logs = relationship("AuditLog", back_populates="tenant")
    application_logs = relationship("ApplicationLog", back_populates="tenant")
    error_tracking = relationship("ErrorTracking", back_populates="tenant")

    def __repr__(self):
        return f"<Tenant(id={self.id}, key={self.tenant_key}, name={self.organization_name})>"


class TenantProvider(Base):
    """Provider → Tenant mapping (CRITICAL FOR ROUTING!)"""

    __tablename__ = "tenant_providers"

    id = Column(UUID, primary_key=True, default=uuid4)
    tenant_id = Column(UUID, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    provider_number = Column(String(50), unique=True, nullable=False, index=True)
    healthlink_edi = Column(String(20))
    family_name = Column(String(100))
    given_name = Column(String(100))
    specialty = Column(String(100))
    tenant_user_id = Column(UUID)  # Reference to user in tenant database
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_message_at = Column(DateTime)

    # Relationships
    tenant = relationship("Tenant", back_populates="providers")

    def __repr__(self):
        return f"<TenantProvider(provider_number={self.provider_number}, tenant_id={self.tenant_id})>"


class TenantPatient(Base):
    """Patient cache for routing when provider not found"""

    __tablename__ = "tenant_patients"

    id = Column(UUID, primary_key=True, default=uuid4)
    tenant_id = Column(UUID, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    medicare_number = Column(String(20), nullable=False)
    medicare_reference = Column(CHAR(1))
    ihi_number = Column(String(16))
    family_name = Column(String(100))
    given_name = Column(String(100))
    date_of_birth = Column(Date)
    tenant_patient_id = Column(UUID)  # Reference to patient in tenant database
    last_seen_at = Column(DateTime, default=func.now())
    message_count = Column(Integer, default=1)
    created_at = Column(DateTime, default=func.now())

    # Relationships
    tenant = relationship("Tenant", back_populates="patients")

    __table_args__ = (
        Index('idx_patient_cache_medicare', 'medicare_number', 'medicare_reference'),
    )

    def __repr__(self):
        return f"<TenantPatient(medicare={self.medicare_number}, tenant_id={self.tenant_id})>"


class MessageRouting(Base):
    """Message routing audit trail"""

    __tablename__ = "message_routing"

    id = Column(UUID, primary_key=True, default=uuid4)
    message_control_id = Column(String(255), nullable=False, index=True)
    hl7_message_type = Column(String(10))
    direction = Column(String(10))
    tenant_id = Column(UUID, ForeignKey("tenants.id"))
    routing_method = Column(String(50), nullable=False, index=True)
    confidence = Column(String(20))
    sender_edi = Column(String(20))
    recipient_provider_number = Column(String(50))
    patient_medicare_number = Column(String(20))
    patient_family_name = Column(String(100))
    routing_data = Column(JSONB)
    decided_by_user_id = Column(UUID)
    created_at = Column(DateTime, default=func.now())

    # Relationships
    tenant = relationship("Tenant", back_populates="routing_logs")

    def __repr__(self):
        return f"<MessageRouting(message_id={self.message_control_id}, method={self.routing_method})>"


class GlobalProvider(Base):
    """Global provider directory (all known HealthLink providers)"""

    __tablename__ = "global_providers"

    id = Column(UUID, primary_key=True, default=uuid4)
    edi_address = Column(String(20), unique=True, nullable=False, index=True)
    provider_number = Column(String(50))
    family_name = Column(String(100))
    given_name = Column(String(100))
    specialty = Column(String(100))
    organization_name = Column(String(255))
    city = Column(String(100))
    state = Column(String(50))
    verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())

    def __repr__(self):
        return f"<GlobalProvider(edi={self.edi_address}, name={self.family_name})>"


class UnassignedMessage(Base):
    """Messages that couldn't be routed automatically"""

    __tablename__ = "unassigned_messages"

    id = Column(UUID, primary_key=True, default=uuid4)
    message_control_id = Column(String(255), unique=True, nullable=False)
    hl7_message_type = Column(String(10))
    sender_edi = Column(String(20))
    recipient_provider_number = Column(String(50))
    patient_medicare_number = Column(String(20))
    patient_family_name = Column(String(100))
    patient_given_name = Column(String(100))
    document_type = Column(String(50))
    original_filename = Column(String(255))
    file_path = Column(String(500))
    status = Column(String(20), default="PENDING", index=True)
    assigned_tenant_id = Column(UUID, ForeignKey("tenants.id"))
    assigned_by_user_id = Column(UUID)
    created_at = Column(DateTime, default=func.now())

    def __repr__(self):
        return f"<UnassignedMessage(message_id={self.message_control_id}, status={self.status})>"


class ApplicationLog(Base):
    """Application logs (all logs in database)"""

    __tablename__ = "application_logs"

    id = Column(UUID, primary_key=True, default=uuid4)
    level = Column(String(20), nullable=False, index=True)
    logger_name = Column(String(100))
    message = Column(Text, nullable=False)
    tenant_id = Column(UUID, ForeignKey("tenants.id"), index=True)
    user_id = Column(UUID)
    message_control_id = Column(String(255))
    exception_type = Column(String(100))
    exception_message = Column(Text)
    stack_trace = Column(Text)
    extra_data = Column(JSONB)
    request_id = Column(String(100))
    created_at = Column(DateTime, default=func.now(), index=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="application_logs")

    def __repr__(self):
        return f"<ApplicationLog(level={self.level}, message={self.message[:50]})>"


class AuditLog(Base):
    """Audit logs (compliance trail)"""

    __tablename__ = "audit_logs"

    id = Column(UUID, primary_key=True, default=uuid4)
    event_type = Column(String(100), nullable=False, index=True)
    event_category = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False)
    tenant_id = Column(UUID, ForeignKey("tenants.id"), index=True)
    user_id = Column(UUID)
    message_control_id = Column(String(255))
    description = Column(Text, nullable=False)
    old_value = Column(JSONB)
    new_value = Column(JSONB)
    metadata = Column(JSONB)
    request_id = Column(String(100))
    created_at = Column(DateTime, default=func.now(), index=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="audit_logs")

    def __repr__(self):
        return f"<AuditLog(event_type={self.event_type}, tenant_id={self.tenant_id})>"


class ErrorTracking(Base):
    """Error tracking (group similar errors)"""

    __tablename__ = "error_tracking"

    id = Column(UUID, primary_key=True, default=uuid4)
    error_code = Column(String(50), nullable=False)
    error_type = Column(String(100), nullable=False, index=True)
    error_message = Column(Text, nullable=False)
    tenant_id = Column(UUID, ForeignKey("tenants.id"))
    message_control_id = Column(String(255))
    component = Column(String(100))
    function_name = Column(String(100))
    stack_trace = Column(Text)
    context_data = Column(JSONB)
    occurrences = Column(Integer, default=1)
    first_seen_at = Column(DateTime, default=func.now())
    last_seen_at = Column(DateTime, default=func.now())
    resolved = Column(Boolean, default=False, index=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="error_tracking")

    def __repr__(self):
        return f"<ErrorTracking(error_type={self.error_type}, occurrences={self.occurrences})>"
