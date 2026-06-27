-- Run this against the existing Asset Sentinel database:
--   psql -U postgres -d asset_sentinel -f auth_login_activity_migration.sql

BEGIN;

ALTER TABLE sessions ADD COLUMN IF NOT EXISTS login_source VARCHAR(50);
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS windows_event_id VARCHAR(20);
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS windows_event_record_id VARCHAR(255);

CREATE INDEX IF NOT EXISTS idx_sessions_windows_event_record_id
    ON sessions (windows_event_record_id);

ALTER TABLE users DROP CONSTRAINT IF EXISTS chk_users_role;
ALTER TABLE users ALTER COLUMN role SET DEFAULT 'Admin';
UPDATE users
SET role = CASE lower(role)
    WHEN 'super admin' THEN 'Super Admin'
    WHEN 'super_admin' THEN 'Super Admin'
    WHEN 'admin' THEN 'Admin'
    WHEN 'analyst' THEN 'IT Admin'
    WHEN 'it admin' THEN 'IT Admin'
    WHEN 'viewer' THEN 'Viewer'
    ELSE 'Viewer'
END;
ALTER TABLE users
    ADD CONSTRAINT chk_users_role
    CHECK (role IN ('Super Admin', 'Admin', 'IT Admin', 'Viewer'));

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

CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_id
    ON refresh_tokens (user_id);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_expires_at
    ON refresh_tokens (expires_at);

COMMIT;
