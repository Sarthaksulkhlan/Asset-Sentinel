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
    login_source VARCHAR(50),
    windows_event_id VARCHAR(20),
    windows_event_record_id VARCHAR(255),
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

CREATE TABLE IF NOT EXISTS application_usage_segments (
    id BIGSERIAL PRIMARY KEY,
    device_id VARCHAR(255) NOT NULL,
    hostname VARCHAR(255) NOT NULL,
    username VARCHAR(255),
    application_name VARCHAR(512) NOT NULL,
    window_title TEXT,
    process_path TEXT,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    active_duration INTEGER NOT NULL DEFAULT 0,
    idle_duration INTEGER NOT NULL DEFAULT 0,
    date TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_application_usage_segments_identity
        UNIQUE (device_id, application_name, start_time, end_time)
);

CREATE TABLE IF NOT EXISTS application_usage_daily (
    id BIGSERIAL PRIMARY KEY,
    date TIMESTAMPTZ NOT NULL,
    hostname VARCHAR(255) NOT NULL,
    username VARCHAR(255),
    application_name VARCHAR(512) NOT NULL,
    window_title TEXT,
    first_seen TIMESTAMPTZ NOT NULL,
    last_seen TIMESTAMPTZ NOT NULL,
    total_foreground_seconds INTEGER NOT NULL DEFAULT 0,
    active_seconds INTEGER NOT NULL DEFAULT 0,
    idle_seconds INTEGER NOT NULL DEFAULT 0,
    locked_seconds INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_application_usage_daily_app
        UNIQUE (date, hostname, username, application_name, window_title)
);

CREATE TABLE IF NOT EXISTS activity_sessions (
    id BIGSERIAL PRIMARY KEY,
    hostname VARCHAR(255) NOT NULL,
    username VARCHAR(255),
    app_name VARCHAR(512) NOT NULL,
    window_title TEXT,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    total_seconds INTEGER NOT NULL DEFAULT 0,
    active_seconds INTEGER NOT NULL DEFAULT 0,
    idle_seconds INTEGER NOT NULL DEFAULT 0,
    locked_seconds INTEGER NOT NULL DEFAULT 0,
    created_date TIMESTAMPTZ NOT NULL,
    last_state VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_activity_sessions_last_state
        CHECK (last_state IN ('ACTIVE', 'IDLE', 'LOCKED'))
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
    role VARCHAR(50) NOT NULL DEFAULT 'Admin',
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
        CHECK (role IN ('Super Admin', 'Admin', 'IT Admin', 'Viewer'))
);

CREATE TABLE IF NOT EXISTS refresh_tokens (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(128) NOT NULL,
    jwt_id VARCHAR(255) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_refresh_tokens_token_hash UNIQUE (token_hash),
    CONSTRAINT uq_refresh_tokens_jwt_id UNIQUE (jwt_id)
);

CREATE TABLE IF NOT EXISTS password_reset_otps (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    otp_hash VARCHAR(128) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    verified BOOLEAN NOT NULL DEFAULT false,
    used BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    verified_at TIMESTAMPTZ,
    used_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS admin_users (
    id BIGSERIAL PRIMARY KEY,
    company_name VARCHAR(255) NOT NULL,
    company_website VARCHAR(512),
    industry VARCHAR(120) NOT NULL,
    company_size VARCHAR(80) NOT NULL,
    country VARCHAR(120) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    work_email VARCHAR(320) NOT NULL,
    mobile_number VARCHAR(40) NOT NULL,
    job_title VARCHAR(160) NOT NULL,
    department VARCHAR(160) NOT NULL,
    username VARCHAR(255) NOT NULL,
    password_hash TEXT NOT NULL,
    terms_accepted BOOLEAN NOT NULL DEFAULT false,
    privacy_accepted BOOLEAN NOT NULL DEFAULT false,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_admin_users_work_email UNIQUE (work_email),
    CONSTRAINT uq_admin_users_username UNIQUE (username)
);

CREATE TABLE IF NOT EXISTS early_access_requests (
    id BIGSERIAL PRIMARY KEY,
    full_name VARCHAR(255),
    email VARCHAR(320) NOT NULL,
    company VARCHAR(255),
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_early_access_requests_email UNIQUE (email)
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
CREATE INDEX IF NOT EXISTS idx_sessions_windows_event_record_id
    ON sessions (windows_event_record_id);

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

CREATE INDEX IF NOT EXISTS idx_application_usage_segments_device_date
    ON application_usage_segments (device_id, date);
CREATE INDEX IF NOT EXISTS idx_application_usage_segments_hostname_start
    ON application_usage_segments (hostname, start_time DESC);
CREATE INDEX IF NOT EXISTS idx_application_usage_segments_application
    ON application_usage_segments (application_name);
CREATE INDEX IF NOT EXISTS idx_application_usage_daily_host_date
    ON application_usage_daily (hostname, date);
CREATE INDEX IF NOT EXISTS idx_application_usage_daily_app
    ON application_usage_daily (application_name);
CREATE INDEX IF NOT EXISTS idx_activity_sessions_host_created_date
    ON activity_sessions (hostname, created_date);
CREATE INDEX IF NOT EXISTS idx_activity_sessions_host_end
    ON activity_sessions (hostname, end_time DESC);
CREATE INDEX IF NOT EXISTS idx_activity_sessions_app
    ON activity_sessions (app_name);

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

CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_id
    ON refresh_tokens (user_id);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_expires_at
    ON refresh_tokens (expires_at);

CREATE INDEX IF NOT EXISTS idx_password_reset_otps_user_created
    ON password_reset_otps (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_password_reset_otps_expires_at
    ON password_reset_otps (expires_at);

CREATE INDEX IF NOT EXISTS idx_admin_users_company_name
    ON admin_users (company_name);
CREATE INDEX IF NOT EXISTS idx_admin_users_created_at
    ON admin_users (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_early_access_requests_company
    ON early_access_requests (company);
CREATE INDEX IF NOT EXISTS idx_early_access_requests_created_at
    ON early_access_requests (created_at DESC);

COMMIT;
