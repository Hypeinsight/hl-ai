# ARVI HealthLink Integration

**Version:** 1.0.0
**Status:** Phase 1 - Foundation Complete ✅

A Python-based integration layer that connects ARVI's multi-tenant healthcare platform with HealthLink Australia's EDI network.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Database Setup](#database-setup)
- [Running the Application](#running-the-application)
- [Project Structure](#project-structure)
- [Development Status](#development-status)
- [Next Steps](#next-steps)

---

## Overview

The ARVI HealthLink Integration Service enables:

- **Multi-tenant architecture** with separate PostgreSQL databases per clinic
- **Intelligent message routing** to automatically direct incoming HealthLink messages to the correct tenant
- **HL7 v2.3.1 support** for generating and parsing referral and medical correspondence messages
- **Comprehensive logging** with all logs, errors, and audit trails stored in PostgreSQL
- **Background workers** using Celery for processing messages asynchronously

---

## Architecture

### High-Level Components

```
┌─────────────────────────────────────────┐
│         ARVI Application                │
│      (Multiple Tenants/Clinics)         │
└─────────────┬───────────────────────────┘
              │ REST API (JWT Auth)
              ▼
┌─────────────────────────────────────────┐
│   HealthLink Integration Service        │
│   - FastAPI (API Layer)                 │
│   - Service Layer (Routing, HL7)        │
│   - Celery Workers (Processing)         │
└─────────┬───────────────────┬───────────┘
          │                   │
          ▼                   ▼
┌──────────────────┐   ┌──────────────────┐
│ Registry DB      │   │ HealthLink HMS   │
│ (Central)        │   │ File System      │
└──────────────────┘   └──────────────────┘
          │
          ▼
┌─────────────────────────────────────────┐
│    Tenant Databases (One per clinic)    │
│    - arvi_tenant_clinic1                │
│    - arvi_tenant_clinic2                │
└─────────────────────────────────────────┘
```

### Message Routing

1. **Provider Number** (PRIMARY) - Routes by Medicare provider number
2. **Patient Medicare** (SECONDARY) - Routes by patient Medicare number
3. **Sender History** (TERTIARY) - Routes based on previous messages
4. **Manual Queue** (FALLBACK) - Admin manually assigns unrouted messages

---

## Features

### ✅ Phase 1 - Foundation (COMPLETED)

- ✅ Project structure and configuration
- ✅ SQLAlchemy models for registry and tenant databases
- ✅ Database connection manager (multi-tenant support)
- ✅ Comprehensive logging system (console + database)
- ✅ Audit logging repository
- ✅ Error tracking and grouping
- ✅ Custom exception handlers
- ✅ Database migration scripts (Alembic)

### 🚧 Phase 2 - Core Services (TODO)

- ⬜ HL7 message parser
- ⬜ HL7 message generator
- ⬜ Tenant routing service
- ⬜ Patient matching service
- ⬜ Provider registration

### 🚧 Phase 3 - API Layer (TODO)

- ⬜ JWT authentication
- ⬜ Message endpoints (send, list, get)
- ⬜ Provider endpoints (search, register)
- ⬜ Admin endpoints (tenant management)

### 🚧 Phase 4 - Workers (TODO)

- ⬜ Celery configuration
- ⬜ Outbound message processor
- ⬜ Inbound message poller
- ⬜ Acknowledgment processor

### 🚧 Phase 5 - Testing & Deployment (TODO)

- ⬜ Unit tests
- ⬜ Integration tests
- ⬜ Docker deployment
- ⬜ Documentation

---

## Prerequisites

- **Python 3.11+**
- **PostgreSQL 15+**
- **Redis 7+** (for Celery task queue)
- **Git**

---

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd hl-ai
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Configuration

### 1. Create Environment File

```bash
cp .env.example .env
```

### 2. Edit `.env` File

Update the following values:

```bash
# Database Configuration
REGISTRY_DB_URL=postgresql://arvi:your_password@localhost:5432/arvi_healthlink_registry
TENANT_DB_USER=arvi
TENANT_DB_PASSWORD=your_password

# JWT Configuration
JWT_SECRET_KEY=your-secret-key-here-generate-with-openssl-rand-hex-32

# HealthLink Configuration
HEALTHLINK_BASE_DIR=/opt/healthlink
```

### 3. Generate JWT Secret

```bash
openssl rand -hex 32
```

Copy the output and paste it into `JWT_SECRET_KEY` in `.env`.

---

## Database Setup

### Option 1: Using SQL Scripts (Recommended for Development)

#### Create Registry Database

```bash
# Connect to PostgreSQL
psql -U postgres

# Create database and user
CREATE DATABASE arvi_healthlink_registry;
CREATE USER arvi WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE arvi_healthlink_registry TO arvi;

# Exit psql
\q

# Run registry schema
psql -U arvi -d arvi_healthlink_registry -f migrations/init_registry_schema.sql
```

#### Create Tenant Database (Example)

```bash
# Connect to PostgreSQL
psql -U postgres

# Create tenant database
CREATE DATABASE arvi_tenant_clinic1;
GRANT ALL PRIVILEGES ON DATABASE arvi_tenant_clinic1 TO arvi;

# Exit psql
\q

# Run tenant schema
psql -U arvi -d arvi_tenant_clinic1 -f migrations/init_tenant_schema.sql
```

### Option 2: Using Alembic (For Production)

```bash
# Initialize Alembic (already configured)
alembic revision --autogenerate -m "Initial schema"

# Run migrations
alembic upgrade head
```

### Option 3: Using Python

```python
from app.database import create_registry_tables, create_tenant_tables
from uuid import UUID

# Create registry tables
create_registry_tables()

# Create tenant tables
tenant_id = UUID('your-tenant-id-here')
create_tenant_tables(tenant_id)
```

---

## Running the Application

### 1. Start Redis (Required for Celery)

```bash
# Using Docker
docker run -d -p 6379:6379 redis:7

# Or using system service
sudo systemctl start redis
```

### 2. Start FastAPI Application

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

API documentation at `http://localhost:8000/docs`

### 3. Start Celery Worker (When Phase 4 is complete)

```bash
celery -A app.workers.celery_app worker --loglevel=info
```

### 4. Start Celery Beat Scheduler (When Phase 4 is complete)

```bash
celery -A app.workers.celery_app beat --loglevel=info
```

---

## Project Structure

```
hl-ai/
├── app/
│   ├── __init__.py
│   ├── config.py                    # Configuration management
│   ├── database.py                  # Multi-tenant database connections
│   ├── logger.py                    # Logging system (console + database)
│   │
│   ├── api/                         # API Endpoints (Phase 3)
│   │   ├── __init__.py
│   │   ├── auth.py                  # JWT authentication
│   │   ├── messages.py              # Message endpoints
│   │   ├── providers.py             # Provider endpoints
│   │   └── admin.py                 # Admin endpoints
│   │
│   ├── services/                    # Business Logic (Phase 2)
│   │   ├── __init__.py
│   │   ├── tenant_routing.py        # Route messages to tenants
│   │   ├── hl7_generator.py         # Generate HL7 messages
│   │   ├── hl7_parser.py            # Parse HL7 messages
│   │   ├── patient_matching.py      # Match patients
│   │   └── message_service.py       # Message CRUD operations
│   │
│   ├── repositories/                # Database Access ✅
│   │   ├── __init__.py
│   │   ├── audit_repo.py            # Audit logging
│   │   └── error_repo.py            # Error tracking
│   │
│   ├── workers/                     # Celery Workers (Phase 4)
│   │   ├── __init__.py
│   │   ├── celery_app.py            # Celery configuration
│   │   ├── outbound_processor.py    # Process outbound messages
│   │   ├── inbound_poller.py        # Poll for inbound messages
│   │   └── ack_processor.py         # Process acknowledgments
│   │
│   ├── models/                      # Data Models ✅
│   │   ├── __init__.py
│   │   ├── registry.py              # Registry database models
│   │   ├── tenant.py                # Tenant database models
│   │   └── schemas.py               # Pydantic schemas for API
│   │
│   └── utils/                       # Utilities ✅
│       ├── __init__.py
│       ├── exceptions.py            # Custom exceptions & handlers
│       ├── hl7_helpers.py           # HL7 utility functions
│       └── file_helpers.py          # File operations
│
├── tests/                           # Tests (Phase 5)
│   ├── __init__.py
│   ├── conftest.py                  # Pytest fixtures
│   ├── test_api/
│   ├── test_services/
│   └── test_workers/
│
├── migrations/                      # Database Migrations ✅
│   ├── registry/                    # Alembic for registry
│   │   ├── env.py
│   │   └── script.py.mako
│   ├── init_registry_schema.sql     # Manual registry setup
│   └── init_tenant_schema.sql       # Manual tenant setup
│
├── scripts/                         # Management Scripts (Phase 5)
│   ├── create_tenant.py
│   ├── register_provider.py
│   └── seed_data.py
│
├── requirements.txt                 # Python dependencies ✅
├── .env.example                     # Environment variables template ✅
├── alembic.ini                      # Alembic configuration ✅
└── README.md                        # This file ✅
```

---

## Development Status

### ✅ Completed (Phase 1)

- [x] Project structure
- [x] Configuration system (Pydantic Settings)
- [x] Database models (Registry + Tenant)
- [x] Multi-tenant database connection manager
- [x] Comprehensive logging (console + database)
- [x] Audit logging repository
- [x] Error tracking repository
- [x] Custom exception handlers
- [x] Database migration scripts

### 🚧 Next Steps (Phase 2)

1. **HL7 Parser** (`app/services/hl7_parser.py`)
   - Parse MSH, PID, PRD, OBX segments
   - Extract patient and provider information
   - Decode Base64 PDF content

2. **HL7 Generator** (`app/services/hl7_generator.py`)
   - Generate REF^I12 (referral) messages
   - Generate ACK (acknowledgment) messages
   - Encode PDF content

3. **Tenant Routing Service** (`app/services/tenant_routing.py`)
   - Route by provider number (PRIMARY)
   - Route by patient Medicare (SECONDARY)
   - Route by sender history (TERTIARY)
   - Store unassigned messages

4. **Provider Registration**
   - Script to register providers in registry database
   - Link provider numbers to tenants

---

## Testing

### Run Tests (When Phase 5 is complete)

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_services/test_tenant_routing.py
```

---

## Logging

All logs are written to both console and database.

### View Logs in Database

```sql
-- Recent application logs
SELECT level, message, created_at
FROM application_logs
ORDER BY created_at DESC
LIMIT 100;

-- Errors only
SELECT level, message, exception_type, created_at
FROM application_logs
WHERE level = 'ERROR'
ORDER BY created_at DESC;

-- Audit logs
SELECT event_type, description, created_at
FROM audit_logs
ORDER BY created_at DESC
LIMIT 100;

-- Error tracking
SELECT error_type, error_message, occurrences, resolved
FROM error_tracking
WHERE resolved = FALSE
ORDER BY occurrences DESC;
```

---

## API Documentation

Once the application is running, visit:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

Copyright © 2025 ARVI Health

---

## Support

For issues and questions, please contact the development team.

---

## Acknowledgments

- HealthLink Australia for EDI infrastructure
- FastAPI for the excellent web framework
- SQLAlchemy for robust ORM capabilities
- Celery for distributed task processing
