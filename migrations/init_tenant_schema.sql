-- ==================================================================
-- ARVI HealthLink Integration - Tenant Database Schema Template
-- ==================================================================
-- This script creates all tables for a tenant database
-- Database: arvi_tenant_{tenant_key}
-- ==================================================================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ==================================================================
-- 1. MESSAGES TABLE
-- ==================================================================
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_control_id VARCHAR(255) UNIQUE NOT NULL,
    hl7_message_type VARCHAR(50) NOT NULL,
    direction VARCHAR(10) NOT NULL,

    -- Sender information
    sender_edi VARCHAR(20),
    sender_name VARCHAR(255),
    sender_provider_number VARCHAR(50),

    -- Recipient information
    recipient_edi VARCHAR(20),
    recipient_name VARCHAR(255),
    recipient_provider_number VARCHAR(50),

    -- Patient information
    patient_id UUID,
    patient_family_name VARCHAR(100),
    patient_given_name VARCHAR(100),
    patient_dob DATE,
    patient_medicare_number VARCHAR(20),
    patient_match_status VARCHAR(20),

    -- Assignment
    assigned_user_id UUID,

    -- Document information
    document_type VARCHAR(50),
    document_title VARCHAR(255),
    content_type VARCHAR(20),
    content_file_path VARCHAR(500),

    -- Status tracking
    status VARCHAR(50) NOT NULL,
    error_details TEXT,

    -- File paths
    original_filename VARCHAR(255),
    hl7_file_path VARCHAR(500),

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    sent_to_hms_at TIMESTAMP,
    delivered_at TIMESTAMP,
    viewed_at TIMESTAMP,

    -- Audit
    created_by_user_id UUID
);

CREATE INDEX IF NOT EXISTS idx_msg_direction ON messages(direction);
CREATE INDEX IF NOT EXISTS idx_msg_status ON messages(status);
CREATE INDEX IF NOT EXISTS idx_msg_patient ON messages(patient_id);
CREATE INDEX IF NOT EXISTS idx_msg_created ON messages(created_at DESC);

COMMENT ON TABLE messages IS 'Messages (inbound and outbound)';
COMMENT ON COLUMN messages.direction IS 'INBOUND or OUTBOUND';
COMMENT ON COLUMN messages.status IS 'NEW, GENERATING, SENT_TO_HMS, DELIVERED, VIEWED, FAILED';

-- ==================================================================
-- 2. MESSAGE ACKNOWLEDGMENTS TABLE
-- ==================================================================
CREATE TABLE IF NOT EXISTS message_acknowledgments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    original_message_id UUID NOT NULL,
    ack_message_control_id VARCHAR(255),
    ack_code VARCHAR(10) NOT NULL,
    ack_text TEXT,
    error_code VARCHAR(50),
    error_description TEXT,
    received_at TIMESTAMP DEFAULT NOW(),

    FOREIGN KEY (original_message_id) REFERENCES messages(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_ack_message ON message_acknowledgments(original_message_id);

COMMENT ON TABLE message_acknowledgments IS 'Message acknowledgments from HealthLink';
COMMENT ON COLUMN message_acknowledgments.ack_code IS 'AA (success), AE (error), AR (reject)';

-- ==================================================================
-- 3. PATIENTS TABLE
-- ==================================================================
CREATE TABLE IF NOT EXISTS patients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    arvi_patient_id VARCHAR(50) UNIQUE NOT NULL,
    family_name VARCHAR(100) NOT NULL,
    given_name VARCHAR(100) NOT NULL,
    date_of_birth DATE NOT NULL,
    gender CHAR(1),
    medicare_number VARCHAR(20),
    medicare_reference CHAR(1),
    ihi_number VARCHAR(16),
    address_line1 VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(50),
    postcode VARCHAR(10),
    mobile_phone VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_patient_medicare ON patients(medicare_number, medicare_reference)
    WHERE medicare_number IS NOT NULL;

COMMENT ON TABLE patients IS 'Patients in tenant database';

-- ==================================================================
-- 4. USERS TABLE (Doctors/Practitioners)
-- ==================================================================
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    provider_number VARCHAR(50),
    specialty VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_provider ON users(provider_number);

COMMENT ON TABLE users IS 'Users (doctors/practitioners) in tenant database';
COMMENT ON COLUMN users.provider_number IS 'Medicare provider number';

-- ==================================================================
-- 5. TENANT AUDIT LOGS TABLE
-- ==================================================================
CREATE TABLE IF NOT EXISTS tenant_audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(100) NOT NULL,
    event_category VARCHAR(50) NOT NULL,
    user_id UUID,
    patient_id UUID,
    message_id UUID,
    description TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),

    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (patient_id) REFERENCES patients(id),
    FOREIGN KEY (message_id) REFERENCES messages(id)
);

CREATE INDEX IF NOT EXISTS idx_tenant_audit_type ON tenant_audit_logs(event_type);
CREATE INDEX IF NOT EXISTS idx_tenant_audit_created ON tenant_audit_logs(created_at DESC);

COMMENT ON TABLE tenant_audit_logs IS 'Audit logs within tenant database';

-- ==================================================================
-- ADD FOREIGN KEY CONSTRAINTS TO MESSAGES TABLE
-- (Done after users table is created)
-- ==================================================================
ALTER TABLE messages
    ADD CONSTRAINT fk_messages_patient
    FOREIGN KEY (patient_id) REFERENCES patients(id);

ALTER TABLE messages
    ADD CONSTRAINT fk_messages_assigned_user
    FOREIGN KEY (assigned_user_id) REFERENCES users(id);

ALTER TABLE messages
    ADD CONSTRAINT fk_messages_created_by_user
    FOREIGN KEY (created_by_user_id) REFERENCES users(id);

-- ==================================================================
-- COMPLETE
-- ==================================================================
