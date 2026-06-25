-- Asset Sentinel PostgreSQL Schema
-- Phase 3: database setup only. Application code is not modified by this file.

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS assets (
    id BIGSERIAL PRIMARY KEY,
    device_uid VARCHAR(255) NOT NULL,
    hostname VARCHAR(255) NOT NULL,
    ip_address INET,
    mac_address VARCHAR(32),
    bios_serial VARCHAR(255),
    baseboard_serial VARCHAR(255),
    uuid UUID,
    composite_id VARCHAR(128),
    cpu_name TEXT,
    ram_total_gb NUMERIC(10, 2),
    baseboard_manufacturer VARCHAR(255),
    baseboard_product VARCHAR(255),
    windows_version VARCHAR(255),
    current_website TEXT,
    active_window_title TEXT,
    active_process_path TEXT,
    active_process_name VARCHAR(512),
    cpu_usage_percent NUMERIC(5, 2),
    ram_usage_percent NUMERIC(5, 2),
    status VARCHAR(20) NOT NULL DEFAULT 'Offline',
    last_seen TIMESTAMPTZ,
    collection_method VARCHAR(50) NOT NULL DEFAULT 'none',
    collection_errors JSONB NOT NULL DEFAULT '[]'::jsonb,
    collected_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_assets_collection_method
        CHECK (collection_method IN ('bios_serial', 'baseboard_serial', 'uuid', 'composite', 'none')),
    CONSTRAINT chk_assets_status
        CHECK (status IN ('Online', 'Idle', 'Offline', 'Overload')),
    CONSTRAINT uq_assets_device_uid UNIQUE (device_uid),
    CONSTRAINT uq_assets_hostname_collected_at UNIQUE (hostname, collected_at)
);

CREATE TABLE IF NOT EXISTS sessions (
    id BIGSERIAL PRIMARY KEY,
    event_type VARCHAR(20) NOT NULL,
    username VARCHAR(255),
    hostname VARCHAR(255) NOT NULL,
    ip_address INET,
    session_id VARCHAR(255),
    login_timestamp TIMESTAMPTZ,
    logout_timestamp TIMESTAMPTZ,
    session_duration VARCHAR(50),
    active BOOLEAN NOT NULL DEFAULT false,
    device_status VARCHAR(20),
    last_seen TIMESTAMPTZ,
    recorded_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_sessions_event_type
        CHECK (event_type IN ('LOGIN', 'LOGOUT')),
    CONSTRAINT chk_sessions_device_status
        CHECK (device_status IS NULL OR device_status IN ('Online', 'Offline')),
    CONSTRAINT uq_sessions_event_identity
        UNIQUE (event_type, hostname, username, session_id, recorded_at)
);

CREATE TABLE IF NOT EXISTS alerts (
    id BIGSERIAL PRIMARY KEY,
    alert_type VARCHAR(100) NOT NULL,
    hostname VARCHAR(255) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    acknowledged BOOLEAN NOT NULL DEFAULT false,
    acknowledged_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_alerts_severity
        CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    CONSTRAINT uq_alerts_event_identity
        UNIQUE (alert_type, hostname, severity, timestamp)
);

CREATE TABLE IF NOT EXISTS active_applications (
    id BIGSERIAL PRIMARY KEY,
    hostname VARCHAR(255) NOT NULL,
    username VARCHAR(255),
    application_name VARCHAR(512),
    executable_name VARCHAR(512),
    window_title TEXT,
    timestamp TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_active_applications_signature
        UNIQUE (hostname, username, executable_name, window_title, timestamp)
);

CREATE TABLE IF NOT EXISTS active_application_history (
    id BIGSERIAL PRIMARY KEY,
    hostname VARCHAR(255) NOT NULL,
    username VARCHAR(255),
    application VARCHAR(512),
    window_title TEXT,
    process_path TEXT,
    timestamp TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS hardware_changes (
    id BIGSERIAL PRIMARY KEY,
    hostname VARCHAR(255) NOT NULL,
    change_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    previous_asset_id BIGINT REFERENCES assets(id) ON DELETE SET NULL,
    current_asset_id BIGINT REFERENCES assets(id) ON DELETE SET NULL,
    previous_value JSONB NOT NULL DEFAULT '{}'::jsonb,
    current_value JSONB NOT NULL DEFAULT '{}'::jsonb,
    difference JSONB NOT NULL DEFAULT '{}'::jsonb,
    detected_at TIMESTAMPTZ NOT NULL,
    alert_id BIGINT REFERENCES alerts(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_hardware_changes_type
        CHECK (change_type IN ('RAM_CHANGE', 'MOTHERBOARD_CHANGE')),
    CONSTRAINT chk_hardware_changes_severity
        CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    CONSTRAINT uq_hardware_changes_snapshot_pair
        UNIQUE (hostname, change_type, previous_asset_id, current_asset_id)
);

CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    email VARCHAR(320) NOT NULL,
    username VARCHAR(255) NOT NULL,
    password_hash TEXT,
    display_name VARCHAR(255),
    role VARCHAR(50) NOT NULL DEFAULT 'admin',
    is_active BOOLEAN NOT NULL DEFAULT true,
    external_provider VARCHAR(100),
    external_subject VARCHAR(255),
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_users_email UNIQUE (email),
    CONSTRAINT uq_users_username UNIQUE (username),
    CONSTRAINT uq_users_external_identity UNIQUE (external_provider, external_subject),
    CONSTRAINT chk_users_role
        CHECK (role IN ('super_admin', 'admin', 'analyst', 'viewer'))
);

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_users_set_updated_at ON users;
CREATE TRIGGER trg_users_set_updated_at
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE INDEX IF NOT EXISTS idx_assets_hostname_collected_at
    ON assets (hostname, collected_at DESC);
CREATE INDEX IF NOT EXISTS idx_assets_device_uid
    ON assets (device_uid);
CREATE INDEX IF NOT EXISTS idx_assets_last_seen
    ON assets (last_seen DESC);
CREATE INDEX IF NOT EXISTS idx_assets_bios_serial
    ON assets (bios_serial);
CREATE INDEX IF NOT EXISTS idx_assets_baseboard_serial
    ON assets (baseboard_serial);
CREATE INDEX IF NOT EXISTS idx_assets_uuid
    ON assets (uuid);
CREATE INDEX IF NOT EXISTS idx_assets_composite_id
    ON assets (composite_id);
CREATE INDEX IF NOT EXISTS idx_assets_collected_at
    ON assets (collected_at DESC);

CREATE INDEX IF NOT EXISTS idx_sessions_hostname_recorded_at
    ON sessions (hostname, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_username_recorded_at
    ON sessions (username, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_active
    ON sessions (active);
CREATE INDEX IF NOT EXISTS idx_sessions_event_type
    ON sessions (event_type);
CREATE INDEX IF NOT EXISTS idx_sessions_login_timestamp
    ON sessions (login_timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_alerts_hostname_timestamp
    ON alerts (hostname, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_severity_timestamp
    ON alerts (severity, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_alert_type
    ON alerts (alert_type);
CREATE INDEX IF NOT EXISTS idx_alerts_details_gin
    ON alerts USING GIN (details);
CREATE INDEX IF NOT EXISTS idx_alerts_unacknowledged
    ON alerts (acknowledged)
    WHERE acknowledged = false;

CREATE INDEX IF NOT EXISTS idx_active_applications_hostname_timestamp
    ON active_applications (hostname, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_active_applications_username_timestamp
    ON active_applications (username, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_active_applications_timestamp
    ON active_applications (timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_active_application_history_hostname_timestamp
    ON active_application_history (hostname, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_active_application_history_username_timestamp
    ON active_application_history (username, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_hardware_changes_hostname_detected_at
    ON hardware_changes (hostname, detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_hardware_changes_type_detected_at
    ON hardware_changes (change_type, detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_hardware_changes_alert_id
    ON hardware_changes (alert_id);

CREATE INDEX IF NOT EXISTS idx_users_role
    ON users (role);
CREATE INDEX IF NOT EXISTS idx_users_is_active
    ON users (is_active);
CREATE INDEX IF NOT EXISTS idx_users_external_identity
    ON users (external_provider, external_subject);

COMMIT;
