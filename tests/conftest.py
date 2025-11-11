"""Pytest configuration and fixtures"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from uuid import uuid4
import os

from app.database import get_registry_session, get_tenant_session
from app.models.registry import Base as RegistryBase, Tenant, TenantProvider
from app.models.tenant import Base as TenantBase, User, Patient, Message
from app.config import settings


# ==================================================================
# DATABASE FIXTURES
# ==================================================================

@pytest.fixture(scope="session")
def test_registry_engine():
    """Create test registry database engine"""
    # Use separate test database
    test_db_url = settings.REGISTRY_DB_URL.replace(
        'arvi_healthlink_registry',
        'arvi_healthlink_registry_test'
    )
    engine = create_engine(test_db_url)

    # Create all tables
    RegistryBase.metadata.create_all(bind=engine)

    yield engine

    # Cleanup
    RegistryBase.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def registry_session(test_registry_engine):
    """Create registry database session for testing"""
    Session = sessionmaker(bind=test_registry_engine)
    session = Session()

    yield session

    session.rollback()
    session.close()


@pytest.fixture(scope="session")
def test_tenant_engine():
    """Create test tenant database engine"""
    # Use separate test database
    test_db_url = f"postgresql://{settings.TENANT_DB_USER}:{settings.TENANT_DB_PASSWORD}@{settings.TENANT_DB_HOST}:{settings.TENANT_DB_PORT}/arvi_tenant_test"
    engine = create_engine(test_db_url)

    # Create all tables
    TenantBase.metadata.create_all(bind=engine)

    yield engine

    # Cleanup
    TenantBase.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def tenant_session(test_tenant_engine):
    """Create tenant database session for testing"""
    Session = sessionmaker(bind=test_tenant_engine)
    session = Session()

    yield session

    session.rollback()
    session.close()


# ==================================================================
# TEST DATA FIXTURES
# ==================================================================

@pytest.fixture
def test_tenant(registry_session):
    """Create a test tenant"""
    tenant = Tenant(
        tenant_key='test_clinic',
        organization_name='Test Clinic',
        database_name='arvi_tenant_test',
        database_host='localhost',
        database_port=5432,
        healthlink_enabled=True,
        status='ACTIVE'
    )
    registry_session.add(tenant)
    registry_session.commit()
    registry_session.refresh(tenant)

    yield tenant

    # Cleanup
    registry_session.delete(tenant)
    registry_session.commit()


@pytest.fixture
def test_provider(registry_session, test_tenant):
    """Create a test provider"""
    provider = TenantProvider(
        tenant_id=test_tenant.id,
        provider_number='1234567A',
        healthlink_edi='TESTEDI1',
        family_name='Test',
        given_name='Doctor',
        specialty='General Practice',
        is_active=True
    )
    registry_session.add(provider)
    registry_session.commit()
    registry_session.refresh(provider)

    yield provider

    # Cleanup
    registry_session.delete(provider)
    registry_session.commit()


@pytest.fixture
def test_user(tenant_session):
    """Create a test user"""
    user = User(
        email='test.doctor@example.com',
        first_name='Test',
        last_name='Doctor',
        provider_number='1234567A',
        specialty='General Practice',
        is_active=True
    )
    tenant_session.add(user)
    tenant_session.commit()
    tenant_session.refresh(user)

    yield user

    # Cleanup
    tenant_session.delete(user)
    tenant_session.commit()


@pytest.fixture
def test_patient(tenant_session):
    """Create a test patient"""
    from datetime import date

    patient = Patient(
        arvi_patient_id='TEST-PAT-001',
        family_name='Mouse',
        given_name='Mickey',
        date_of_birth=date(1981, 1, 30),
        gender='M',
        medicare_number='2428778132',
        medicare_reference='1',
        address_line1='1 Testing St',
        city='Woonona',
        state='NSW',
        postcode='2517',
        mobile_phone='0488888888'
    )
    tenant_session.add(patient)
    tenant_session.commit()
    tenant_session.refresh(patient)

    yield patient

    # Cleanup
    tenant_session.delete(patient)
    tenant_session.commit()


@pytest.fixture
def test_message(tenant_session, test_patient, test_user):
    """Create a test message"""
    message = Message(
        message_control_id='TEST-MSG-001',
        hl7_message_type='REF^I12',
        direction='OUTBOUND',
        sender_edi='ARVIHLT1',
        recipient_edi='TESTEDI1',
        patient_id=test_patient.id,
        patient_family_name=test_patient.family_name,
        patient_given_name=test_patient.given_name,
        patient_medicare_number=test_patient.medicare_number,
        patient_match_status='MATCHED',
        created_by_user_id=test_user.id,
        document_type='referral',
        status='NEW'
    )
    tenant_session.add(message)
    tenant_session.commit()
    tenant_session.refresh(message)

    yield message

    # Cleanup
    tenant_session.delete(message)
    tenant_session.commit()


# ==================================================================
# API FIXTURES
# ==================================================================

@pytest.fixture
def api_client():
    """Create FastAPI test client"""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    yield client


# ==================================================================
# HL7 MESSAGE FIXTURES
# ==================================================================

@pytest.fixture
def sample_hl7_referral():
    """Sample HL7 referral message"""
    return """MSH|^~\\&|ARVIHealth|ARVIHLT1|HealthLink|GPTEST01|20251111143000||REF^I12|550e8400-e29b-41d4-a716-446655440000|P|2.3.1
PID|1|TEST-PAT-001|||Mouse^Mickey||19810130|M|||1 Testing St^^Woonona^NSW^2517^AU||0488888888|||||||2428778132^1
PRD|PP|Doctor^Test^^Dr|||||||1234567A^^^AUSHIC|ARVIHLT1
PRD|RT|Specialist^Test^^Dr|||||||7654321B^^^AUSHIC|GPTEST01
ORC|RE|TEST-ORD-001|||||||20251111143000
OBR|1|TEST-ORD-001||REF^Referral||20251111143000||||||||Test Doctor|||20251111143000|||F
OBX|1|ED|PDF^Referral||^application/pdf^Base64^JVBERi0xLjQKJeLjz9MK||||||F|||20251111143000"""


@pytest.fixture
def sample_hl7_ack():
    """Sample HL7 acknowledgment message"""
    return """MSH|^~\\&|HealthLink|GPTEST01|ARVIHealth|ARVIHLT1|20251111150100||ACK|ACK-550e8400|P|2.3.1
MSA|AA|550e8400-e29b-41d4-a716-446655440000"""


# ==================================================================
# UTILITY FIXTURES
# ==================================================================

@pytest.fixture
def temp_file(tmp_path):
    """Create temporary file for testing"""
    file_path = tmp_path / "test_file.txt"
    file_path.write_text("Test content")

    yield file_path

    # Cleanup happens automatically with tmp_path


@pytest.fixture
def mock_healthlink_dir(tmp_path):
    """Create mock HealthLink directory structure"""
    base_dir = tmp_path / "healthlink"
    base_dir.mkdir()

    # Create directories
    (base_dir / "HL7_in" / "RSDAU").mkdir(parents=True)
    (base_dir / "HL7_in" / "LAB2").mkdir(parents=True)
    (base_dir / "HL7_out" / "RSDAU").mkdir(parents=True)

    yield base_dir


# ==================================================================
# CLEANUP HOOKS
# ==================================================================

@pytest.fixture(autouse=True)
def reset_logging_context():
    """Reset logging context before each test"""
    from app.logger import clear_request_context
    clear_request_context()
    yield
    clear_request_context()
