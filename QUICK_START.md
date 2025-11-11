# Quick Start Guide - ARVI HealthLink Integration

## Phase 1 Status: ✅ COMPLETE

All foundation components are built and committed to git.

---

## 🚀 Quick Setup (5 Minutes)

### 1. Install Dependencies

```bash
# Activate virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install packages
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Generate JWT secret
openssl rand -hex 32

# Edit .env and update:
# - REGISTRY_DB_URL with your PostgreSQL connection
# - TENANT_DB_PASSWORD
# - JWT_SECRET_KEY (paste the generated secret)
```

### 3. Setup Databases

```bash
# Create PostgreSQL databases
psql -U postgres -c "CREATE DATABASE arvi_healthlink_registry;"
psql -U postgres -c "CREATE USER arvi WITH PASSWORD 'your_password';"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE arvi_healthlink_registry TO arvi;"

# Initialize schema
psql -U arvi -d arvi_healthlink_registry -f migrations/init_registry_schema.sql
```

### 4. Test Setup

```python
# Test database connection
python -c "from app.database import test_registry_connection; print('Connection:', test_registry_connection())"

# Test logging
python -c "from app.logger import log_info; log_info('Test log message')"
```

---

## 📁 What You Have Now

### ✅ Complete Infrastructure

1. **Multi-Tenant Database Architecture**
   - Registry database for central coordination
   - Tenant database template for each clinic
   - Connection pooling and caching

2. **Logging System**
   - Console logging (structlog)
   - Database logging (PostgreSQL)
   - Request context tracking
   - Exception tracking

3. **Audit Trail**
   - Registry audit logs
   - Tenant audit logs
   - Event categorization
   - Compliance reporting

4. **Error Tracking**
   - Automatic error grouping
   - Occurrence counting
   - Resolution tracking
   - Statistics and reporting

5. **14 Database Tables**
   - 9 in registry database
   - 5 in tenant database template
   - Full relationships and indexes

---

## 📊 Key Files

| File | Purpose | Status |
|------|---------|--------|
| `app/config.py` | Configuration management | ✅ |
| `app/database.py` | Multi-tenant connections | ✅ |
| `app/logger.py` | Logging system | ✅ |
| `app/models/registry.py` | Registry DB models | ✅ |
| `app/models/tenant.py` | Tenant DB models | ✅ |
| `app/repositories/audit_repo.py` | Audit logging | ✅ |
| `app/repositories/error_repo.py` | Error tracking | ✅ |
| `app/utils/exceptions.py` | Exception handlers | ✅ |
| `migrations/init_registry_schema.sql` | Registry schema | ✅ |
| `migrations/init_tenant_schema.sql` | Tenant schema | ✅ |

---

## 🎯 Next Phase: Core Services

Ready to build in Phase 2:

### 1. HL7 Parser (`app/services/hl7_parser.py`)
- Parse HL7 v2.3.1 messages
- Extract patient/provider info
- Decode Base64 PDFs

### 2. HL7 Generator (`app/services/hl7_generator.py`)
- Generate REF^I12 (referral) messages
- Generate ACK messages
- Encode PDFs in Base64

### 3. Tenant Routing (`app/services/tenant_routing.py`)
- Route by provider number (HIGH confidence)
- Route by patient Medicare (MEDIUM confidence)
- Route by sender history (LOW confidence)
- Store unassigned messages

### 4. Patient Matching (`app/services/patient_matching.py`)
- Match by Medicare number
- Match by IHI
- Fuzzy match by DOB + name

---

## 💡 Usage Examples

### Create a Tenant

```python
from app.database import get_registry_session, create_tenant_tables
from app.models.registry import Tenant
from uuid import uuid4

tenant_id = uuid4()

with get_registry_session() as session:
    tenant = Tenant(
        id=tenant_id,
        tenant_key='melbourne_clinic',
        organization_name='Melbourne Medical Clinic',
        database_name='arvi_tenant_melbourne_clinic',
        status='ACTIVE'
    )
    session.add(tenant)
    session.commit()

# Create tenant database tables
create_tenant_tables(tenant_id)
```

### Register a Provider

```python
from app.database import get_registry_session
from app.models.registry import TenantProvider
from app.repositories.audit_repo import audit_provider_registered

with get_registry_session() as session:
    provider = TenantProvider(
        tenant_id=tenant_id,
        provider_number='1234567A',
        family_name='Jones',
        given_name='Sarah',
        specialty='General Practice',
        is_active=True
    )
    session.add(provider)
    session.commit()

# Audit the registration
audit_provider_registered(
    tenant_id=tenant_id,
    provider_number='1234567A',
    provider_name='Sarah Jones'
)
```

### Log with Context

```python
from app.logger import set_request_context, log_info, log_error
from uuid import uuid4

# Set context
request_id = str(uuid4())
set_request_context(request_id, tenant_id=str(tenant_id))

# Log with context
log_info("Processing message", message_control_id="MSG-001")

# Log error with exception
try:
    # Some operation
    pass
except Exception as e:
    log_error("Operation failed", exception=e, extra_data={'details': '...'})
```

### Track Errors

```python
from app.repositories.error_repo import ErrorTrackingRepository

# Track an error
ErrorTrackingRepository.track_error(
    error_type='HL7ParseException',
    error_message='Invalid segment structure',
    component='hl7_parser',
    function_name='parse_message',
    context_data={'filename': 'message.hl7'}
)

# Get unresolved errors
errors = ErrorTrackingRepository.get_unresolved_errors(
    min_occurrences=5
)

# Get statistics
stats = ErrorTrackingRepository.get_error_stats()
print(f"Total errors: {stats['total_unique_errors']}")
print(f"Unresolved: {stats['unresolved_errors']}")
```

---

## 📚 Documentation

- **README.md** - Full project documentation
- **PHASE1_COMPLETE.md** - Phase 1 completion summary
- **This file** - Quick start guide

---

## ✅ Phase 1 Checklist

- [x] Project structure created
- [x] Dependencies installed (requirements.txt)
- [x] Configuration system (Pydantic Settings)
- [x] Database models (Registry + Tenant)
- [x] Multi-tenant connection manager
- [x] Logging system (console + database)
- [x] Audit logging repository
- [x] Error tracking repository
- [x] Custom exceptions
- [x] Migration scripts
- [x] Test infrastructure
- [x] Documentation
- [x] Git commit
- [x] Git push

**Phase 1: 100% Complete** ✅

---

## 🎉 Success!

You now have a solid foundation for the ARVI HealthLink Integration.

**Next:** Start Phase 2 to build the HL7 parsing and routing services.

```bash
# Ready for Phase 2!
# Next files to create:
# - app/services/hl7_parser.py
# - app/services/hl7_generator.py
# - app/services/tenant_routing.py
# - app/services/patient_matching.py
```
