"""SQLAlchemy models for tenant databases"""
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, ForeignKey, Text, Index, UUID, Date, CHAR
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
from uuid import uuid4

Base = declarative_base()


class Message(Base):
    """Messages (inbound and outbound)"""

    __tablename__ = "messages"

    id = Column(UUID, primary_key=True, default=uuid4)
    message_control_id = Column(String(255), unique=True, nullable=False)
    hl7_message_type = Column(String(50), nullable=False)
    direction = Column(String(10), nullable=False, index=True)

    # Sender information
    sender_edi = Column(String(20))
    sender_name = Column(String(255))
    sender_provider_number = Column(String(50))

    # Recipient information
    recipient_edi = Column(String(20))
    recipient_name = Column(String(255))
    recipient_provider_number = Column(String(50))

    # Patient information
    patient_id = Column(UUID, ForeignKey("patients.id"), index=True)
    patient_family_name = Column(String(100))
    patient_given_name = Column(String(100))
    patient_dob = Column(Date)
    patient_medicare_number = Column(String(20))
    patient_match_status = Column(String(20))

    # Assignment
    assigned_user_id = Column(UUID, ForeignKey("users.id"))

    # Document information
    document_type = Column(String(50))
    document_title = Column(String(255))
    content_type = Column(String(20))
    content_file_path = Column(String(500))

    # Status tracking
    status = Column(String(50), nullable=False, index=True)
    error_details = Column(Text)

    # File paths
    original_filename = Column(String(255))
    hl7_file_path = Column(String(500))

    # Timestamps
    created_at = Column(DateTime, default=func.now(), index=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    sent_to_hms_at = Column(DateTime)
    delivered_at = Column(DateTime)
    viewed_at = Column(DateTime)

    # Audit
    created_by_user_id = Column(UUID, ForeignKey("users.id"))

    # Relationships
    patient = relationship("Patient", back_populates="messages")
    acknowledgments = relationship("MessageAcknowledgment", back_populates="message", cascade="all, delete-orphan")
    assigned_user = relationship("User", foreign_keys=[assigned_user_id], back_populates="assigned_messages")
    created_by_user = relationship("User", foreign_keys=[created_by_user_id], back_populates="created_messages")

    def __repr__(self):
        return f"<Message(id={self.id}, control_id={self.message_control_id}, direction={self.direction})>"


class MessageAcknowledgment(Base):
    """Message acknowledgments from HealthLink"""

    __tablename__ = "message_acknowledgments"

    id = Column(UUID, primary_key=True, default=uuid4)
    original_message_id = Column(UUID, ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, index=True)
    ack_message_control_id = Column(String(255))
    ack_code = Column(String(10), nullable=False)
    ack_text = Column(Text)
    error_code = Column(String(50))
    error_description = Column(Text)
    received_at = Column(DateTime, default=func.now())

    # Relationships
    message = relationship("Message", back_populates="acknowledgments")

    def __repr__(self):
        return f"<MessageAcknowledgment(message_id={self.original_message_id}, ack_code={self.ack_code})>"


class Patient(Base):
    """Patients in tenant database"""

    __tablename__ = "patients"

    id = Column(UUID, primary_key=True, default=uuid4)
    arvi_patient_id = Column(String(50), unique=True, nullable=False)
    family_name = Column(String(100), nullable=False)
    given_name = Column(String(100), nullable=False)
    date_of_birth = Column(Date, nullable=False)
    gender = Column(CHAR(1))
    medicare_number = Column(String(20))
    medicare_reference = Column(CHAR(1))
    ihi_number = Column(String(16))
    address_line1 = Column(String(255))
    city = Column(String(100))
    state = Column(String(50))
    postcode = Column(String(10))
    mobile_phone = Column(String(20))
    created_at = Column(DateTime, default=func.now())

    # Relationships
    messages = relationship("Message", back_populates="patient")

    __table_args__ = (
        Index(
            'idx_patient_medicare',
            'medicare_number',
            'medicare_reference',
            unique=True,
            postgresql_where=Column('medicare_number').isnot(None)
        ),
    )

    def __repr__(self):
        return f"<Patient(id={self.id}, name={self.family_name}, {self.given_name})>"


class User(Base):
    """Users (doctors/practitioners) in tenant database"""

    __tablename__ = "users"

    id = Column(UUID, primary_key=True, default=uuid4)
    email = Column(String(255), unique=True, nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    provider_number = Column(String(50), index=True)
    specialty = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())

    # Relationships
    assigned_messages = relationship("Message", foreign_keys=[Message.assigned_user_id], back_populates="assigned_user")
    created_messages = relationship("Message", foreign_keys=[Message.created_by_user_id], back_populates="created_by_user")
    audit_logs = relationship("TenantAuditLog", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, provider_number={self.provider_number})>"


class TenantAuditLog(Base):
    """Audit logs within tenant database"""

    __tablename__ = "tenant_audit_logs"

    id = Column(UUID, primary_key=True, default=uuid4)
    event_type = Column(String(100), nullable=False, index=True)
    event_category = Column(String(50), nullable=False)
    user_id = Column(UUID, ForeignKey("users.id"))
    patient_id = Column(UUID, ForeignKey("patients.id"))
    message_id = Column(UUID, ForeignKey("messages.id"))
    description = Column(Text, nullable=False)
    metadata = Column(JSONB)
    created_at = Column(DateTime, default=func.now(), index=True)

    # Relationships
    user = relationship("User", back_populates="audit_logs")

    def __repr__(self):
        return f"<TenantAuditLog(event_type={self.event_type}, user_id={self.user_id})>"
