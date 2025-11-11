-- ==================================================================
-- ARVI HealthLink Integration - Registry Database Schema
-- ==================================================================
-- This script creates all tables for the registry database
-- Database: arvi_healthlink_registry
-- ==================================================================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ==================================================================
-- 1. TENANTS TABLE
-- ==================================================================
CREATE TABLE IF NOT EXISTS tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_key VARCHAR(100) UNIQUE NOT NULL,
    organization_name VARCHAR(255) NOT NULL,
    database_name VARCHAR(100) NOT NULL,
    database_host VARCHAR(255) DEFAULT 'localhost',
    database_port INTEGER DEFAULT 5432,
    healthlink_enabled BOOLEAN DEFAULT TRUE,
    status VARCHAR(20) DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tenants_key ON tenants(tenant_key);
CREATE INDEX IF NOT EXISTS idx_tenants_status ON tenants(status);

COMMENT ON TABLE tenants IS 'Organizations using ARVI (each clinic/practice)';
COMMENT ON COLUMN tenants.tenant_key IS 'Unique identifier for tenant (used in URLs, database names)';
COMMENT ON COLUMN tenants.database_name IS 'Name of tenant-specific PostgreSQL database';

-- ==================================================================
-- 2. TENANT PROVIDERS TABLE (CRITICAL FOR ROUTING!)
-- ==================================================================
CREATE TABLE IF NOT EXISTS tenant_providers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    provider_number VARCHAR(50) NOT NULL UNIQUE,
    healthlink_edi VARCHAR(20),
    family_name VARCHAR(100),
    given_name VARCHAR(100),
    specialty VARCHAR(100),
    tenant_user_id UUID,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_message_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tenant_providers_number ON tenant_providers(provider_number);
CREATE INDEX IF NOT EXISTS idx_tenant_providers_tenant ON tenant_providers(tenant_id);

COMMENT ON TABLE tenant_providers IS 'Provider → Tenant mapping (PRIMARY routing key)';
COMMENT ON COLUMN tenant_providers.provider_number IS 'Medicare provider number - PRIMARY routing key';
COMMENT ON COLUMN tenant_providers.tenant_user_id IS 'Reference to user ID in tenant database';

-- ==================================================================
-- 3. TENANT PATIENTS TABLE (Patient cache for routing)
-- ==================================================================
CREATE TABLE IF NOT EXISTS tenant_patients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    medicare_number VARCHAR(20) NOT NULL,
    medicare_reference CHAR(1),
    ihi_number VARCHAR(16),
    family_name VARCHAR(100),
    given_name VARCHAR(100),
    date_of_birth DATE,
    tenant_patient_id UUID,
    last_seen_at TIMESTAMP DEFAULT NOW(),
    message_count INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_patient_cache_medicare ON tenant_patients(medicare_number, medicare_reference);
CREATE INDEX IF NOT EXISTS idx_patient_cache_tenant ON tenant_patients(tenant_id);

COMMENT ON TABLE tenant_patients IS 'Patient cache for routing when provider not found';
COMMENT ON COLUMN tenant_patients.tenant_patient_id IS 'Reference to patient ID in tenant database';

-- ==================================================================
-- 4. MESSAGE ROUTING TABLE (Audit trail)
-- ==================================================================
CREATE TABLE IF NOT EXISTS message_routing (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_control_id VARCHAR(255) NOT NULL,
    hl7_message_type VARCHAR(10),
    direction VARCHAR(10),
    tenant_id UUID REFERENCES tenants(id),
    routing_method VARCHAR(50) NOT NULL,
    confidence VARCHAR(20),
    sender_edi VARCHAR(20),
    recipient_provider_number VARCHAR(50),
    patient_medicare_number VARCHAR(20),
    patient_family_name VARCHAR(100),
    routing_data JSONB,
    decided_by_user_id UUID,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_routing_message_id ON message_routing(message_control_id);
CREATE INDEX IF NOT EXISTS idx_routing_tenant ON message_routing(tenant_id);
CREATE INDEX IF NOT EXISTS idx_routing_method ON message_routing(routing_method);

COMMENT ON TABLE message_routing IS 'Message routing audit trail';
COMMENT ON COLUMN message_routing.routing_method IS 'PROVIDER, PATIENT, HISTORY, or MANUAL';
COMMENT ON COLUMN message_routing.confidence IS 'HIGH, MEDIUM, LOW, or NONE';

-- ==================================================================
-- 5. GLOBAL PROVIDERS TABLE
-- ==================================================================
CREATE TABLE IF NOT EXISTS global_providers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    edi_address VARCHAR(20) UNIQUE NOT NULL,
    provider_number VARCHAR(50),
    family_name VARCHAR(100),
    given_name VARCHAR(100),
    specialty VARCHAR(100),
    organization_name VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(50),
    verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_global_providers_edi ON global_providers(edi_address);

COMMENT ON TABLE global_providers IS 'Global provider directory (all known HealthLink providers)';

-- ==================================================================
-- 6. UNASSIGNED MESSAGES TABLE
-- ==================================================================
CREATE TABLE IF NOT EXISTS unassigned_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_control_id VARCHAR(255) UNIQUE NOT NULL,
    hl7_message_type VARCHAR(10),
    sender_edi VARCHAR(20),
    recipient_provider_number VARCHAR(50),
    patient_medicare_number VARCHAR(20),
    patient_family_name VARCHAR(100),
    patient_given_name VARCHAR(100),
    document_type VARCHAR(50),
    original_filename VARCHAR(255),
    file_path VARCHAR(500),
    status VARCHAR(20) DEFAULT 'PENDING',
    assigned_tenant_id UUID REFERENCES tenants(id),
    assigned_by_user_id UUID,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_unassigned_status ON unassigned_messages(status);

COMMENT ON TABLE unassigned_messages IS 'Messages that could not be routed automatically';

-- ==================================================================
-- 7. APPLICATION LOGS TABLE
-- ==================================================================
CREATE TABLE IF NOT EXISTS application_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    level VARCHAR(20) NOT NULL,
    logger_name VARCHAR(100),
    message TEXT NOT NULL,
    tenant_id UUID REFERENCES tenants(id),
    user_id UUID,
    message_control_id VARCHAR(255),
    exception_type VARCHAR(100),
    exception_message TEXT,
    stack_trace TEXT,
    extra_data JSONB,
    request_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_logs_level ON application_logs(level);
CREATE INDEX IF NOT EXISTS idx_logs_tenant ON application_logs(tenant_id);
CREATE INDEX IF NOT EXISTS idx_logs_created ON application_logs(created_at DESC);

COMMENT ON TABLE application_logs IS 'All application logs stored in database';

-- ==================================================================
-- 8. AUDIT LOGS TABLE
-- ==================================================================
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(100) NOT NULL,
    event_category VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    tenant_id UUID REFERENCES tenants(id),
    user_id UUID,
    message_control_id VARCHAR(255),
    description TEXT NOT NULL,
    old_value JSONB,
    new_value JSONB,
    metadata JSONB,
    request_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_logs(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_tenant ON audit_logs(tenant_id);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs(created_at DESC);

COMMENT ON TABLE audit_logs IS 'Audit logs for compliance';

-- ==================================================================
-- 9. ERROR TRACKING TABLE
-- ==================================================================
CREATE TABLE IF NOT EXISTS error_tracking (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    error_code VARCHAR(50) NOT NULL,
    error_type VARCHAR(100) NOT NULL,
    error_message TEXT NOT NULL,
    tenant_id UUID REFERENCES tenants(id),
    message_control_id VARCHAR(255),
    component VARCHAR(100),
    function_name VARCHAR(100),
    stack_trace TEXT,
    context_data JSONB,
    occurrences INTEGER DEFAULT 1,
    first_seen_at TIMESTAMP DEFAULT NOW(),
    last_seen_at TIMESTAMP DEFAULT NOW(),
    resolved BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_errors_type ON error_tracking(error_type);
CREATE INDEX IF NOT EXISTS idx_errors_resolved ON error_tracking(resolved);

COMMENT ON TABLE error_tracking IS 'Error tracking and grouping';

-- ==================================================================
-- COMPLETE
-- ==================================================================
