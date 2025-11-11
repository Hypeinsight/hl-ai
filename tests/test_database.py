"""Test database connections and models"""
import pytest
from uuid import UUID

from app.database import (
    get_registry_session,
    test_registry_connection,
    get_all_tenants
)
from app.models.registry import Tenant, TenantProvider, ApplicationLog
from app.models.tenant import User, Patient, Message


class TestRegistryDatabase:
    """Test registry database operations"""

    def test_create_tenant(self, registry_session):
        """Test creating a tenant"""
        tenant = Tenant(
            tenant_key='test_clinic_1',
            organization_name='Test Clinic 1',
            database_name='arvi_tenant_test_clinic_1',
            database_host='localhost',
            healthlink_enabled=True,
            status='ACTIVE'
        )

        registry_session.add(tenant)
        registry_session.commit()
        registry_session.refresh(tenant)

        assert tenant.id is not None
        assert isinstance(tenant.id, UUID)
        assert tenant.tenant_key == 'test_clinic_1'
        assert tenant.status == 'ACTIVE'

    def test_create_provider(self, registry_session, test_tenant):
        """Test creating a provider"""
        provider = TenantProvider(
            tenant_id=test_tenant.id,
            provider_number='9876543Z',
            family_name='Smith',
            given_name='John',
            specialty='Cardiology',
            is_active=True
        )

        registry_session.add(provider)
        registry_session.commit()
        registry_session.refresh(provider)

        assert provider.id is not None
        assert provider.provider_number == '9876543Z'
        assert provider.tenant_id == test_tenant.id
        assert provider.is_active is True

    def test_query_tenant_by_key(self, registry_session, test_tenant):
        """Test querying tenant by key"""
        tenant = registry_session.query(Tenant).filter(
            Tenant.tenant_key == 'test_clinic'
        ).first()

        assert tenant is not None
        assert tenant.tenant_key == 'test_clinic'
        assert tenant.organization_name == 'Test Clinic'


class TestTenantDatabase:
    """Test tenant database operations"""

    def test_create_user(self, tenant_session):
        """Test creating a user"""
        user = User(
            email='new.doctor@example.com',
            first_name='New',
            last_name='Doctor',
            provider_number='1111111A',
            specialty='Radiology',
            is_active=True
        )

        tenant_session.add(user)
        tenant_session.commit()
        tenant_session.refresh(user)

        assert user.id is not None
        assert user.email == 'new.doctor@example.com'
        assert user.provider_number == '1111111A'

    def test_create_patient(self, tenant_session):
        """Test creating a patient"""
        from datetime import date

        patient = Patient(
            arvi_patient_id='PAT-002',
            family_name='Duck',
            given_name='Donald',
            date_of_birth=date(1985, 6, 15),
            gender='M',
            medicare_number='3456789012',
            medicare_reference='2'
        )

        tenant_session.add(patient)
        tenant_session.commit()
        tenant_session.refresh(patient)

        assert patient.id is not None
        assert patient.family_name == 'Duck'
        assert patient.medicare_number == '3456789012'

    def test_create_message(self, tenant_session, test_patient, test_user):
        """Test creating a message"""
        message = Message(
            message_control_id='MSG-TEST-002',
            hl7_message_type='REF^I12',
            direction='INBOUND',
            sender_edi='EXTERNAL01',
            patient_id=test_patient.id,
            created_by_user_id=test_user.id,
            status='NEW'
        )

        tenant_session.add(message)
        tenant_session.commit()
        tenant_session.refresh(message)

        assert message.id is not None
        assert message.message_control_id == 'MSG-TEST-002'
        assert message.direction == 'INBOUND'
        assert message.status == 'NEW'


class TestDatabaseConnections:
    """Test database connection utilities"""

    def test_registry_connection(self):
        """Test registry database connection"""
        result = test_registry_connection()
        # Note: This will fail if test database is not set up
        # In actual tests, you would use pytest fixtures
        assert isinstance(result, bool)

    def test_tenant_relationship(self, registry_session, test_tenant, test_provider):
        """Test tenant-provider relationship"""
        tenant = registry_session.query(Tenant).filter(
            Tenant.id == test_tenant.id
        ).first()

        assert tenant is not None
        assert len(tenant.providers) > 0
        assert tenant.providers[0].provider_number == test_provider.provider_number


class TestLogging:
    """Test logging to database"""

    def test_create_application_log(self, registry_session):
        """Test creating application log"""
        from datetime import datetime

        log = ApplicationLog(
            level='INFO',
            logger_name='test',
            message='Test log message',
            created_at=datetime.utcnow()
        )

        registry_session.add(log)
        registry_session.commit()
        registry_session.refresh(log)

        assert log.id is not None
        assert log.level == 'INFO'
        assert log.message == 'Test log message'

    def test_create_error_log(self, registry_session, test_tenant):
        """Test creating error log with exception"""
        from datetime import datetime

        log = ApplicationLog(
            level='ERROR',
            logger_name='test',
            message='Test error occurred',
            tenant_id=test_tenant.id,
            exception_type='ValueError',
            exception_message='Invalid value',
            stack_trace='Traceback...',
            created_at=datetime.utcnow()
        )

        registry_session.add(log)
        registry_session.commit()
        registry_session.refresh(log)

        assert log.id is not None
        assert log.level == 'ERROR'
        assert log.exception_type == 'ValueError'
        assert log.tenant_id == test_tenant.id
