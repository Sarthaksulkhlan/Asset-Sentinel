BEGIN;

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

CREATE INDEX IF NOT EXISTS idx_password_reset_otps_user_created
    ON password_reset_otps (user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_password_reset_otps_expires_at
    ON password_reset_otps (expires_at);

COMMIT;
