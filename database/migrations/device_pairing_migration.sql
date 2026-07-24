BEGIN;

ALTER TABLE assets
    ADD COLUMN IF NOT EXISTS owner_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_assets_owner_user_id ON assets (owner_user_id);

CREATE TABLE IF NOT EXISTS device_pairing_codes (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    code VARCHAR(4) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    used BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    used_at TIMESTAMPTZ,
    paired_device_uid VARCHAR(255),
    CONSTRAINT chk_device_pairing_codes_numeric CHECK (code ~ '^[0-9]{4}$')
);

CREATE INDEX IF NOT EXISTS idx_device_pairing_codes_code ON device_pairing_codes (code);
CREATE INDEX IF NOT EXISTS idx_device_pairing_codes_user_created ON device_pairing_codes (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_device_pairing_codes_expires_at ON device_pairing_codes (expires_at);

COMMIT;
