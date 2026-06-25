BEGIN;

ALTER TABLE assets ADD COLUMN IF NOT EXISTS device_uid VARCHAR(255);
ALTER TABLE assets ADD COLUMN IF NOT EXISTS cpu_usage_percent NUMERIC(5, 2);
ALTER TABLE assets ADD COLUMN IF NOT EXISTS ram_usage_percent NUMERIC(5, 2);
ALTER TABLE assets ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'Offline';
ALTER TABLE assets ADD COLUMN IF NOT EXISTS last_seen TIMESTAMPTZ;

UPDATE assets
SET device_uid = lower(coalesce(uuid::text, nullif(bios_serial, ''), nullif(baseboard_serial, ''), nullif(composite_id, ''), hostname));

UPDATE assets
SET last_seen = coalesce(last_seen, collected_at),
    status = CASE
        WHEN coalesce(last_seen, collected_at) > now() - interval '30 seconds' THEN 'Online'
        WHEN coalesce(last_seen, collected_at) > now() - interval '2 minutes' THEN 'Idle'
        ELSE 'Offline'
    END;

WITH ranked AS (
    SELECT
        id,
        row_number() OVER (
            PARTITION BY device_uid
            ORDER BY
                CASE collection_method
                    WHEN 'uuid' THEN 5
                    WHEN 'bios_serial' THEN 4
                    WHEN 'baseboard_serial' THEN 3
                    WHEN 'composite' THEN 2
                    ELSE 1
                END DESC,
                collected_at DESC,
                id DESC
        ) AS rn
    FROM assets
)
DELETE FROM assets
USING ranked
WHERE assets.id = ranked.id
  AND ranked.rn > 1;

WITH ranked AS (
    SELECT
        id,
        row_number() OVER (
            PARTITION BY hostname
            ORDER BY
                CASE collection_method
                    WHEN 'uuid' THEN 5
                    WHEN 'bios_serial' THEN 4
                    WHEN 'baseboard_serial' THEN 3
                    WHEN 'composite' THEN 2
                    ELSE 1
                END DESC,
                collected_at DESC,
                id DESC
        ) AS rn
    FROM assets
)
DELETE FROM assets
USING ranked
WHERE assets.id = ranked.id
  AND ranked.rn > 1;

ALTER TABLE assets ALTER COLUMN device_uid SET NOT NULL;

ALTER TABLE assets
    ADD CONSTRAINT chk_assets_status
    CHECK (status IN ('Online', 'Idle', 'Offline', 'Overload'));

ALTER TABLE assets
    ADD CONSTRAINT uq_assets_device_uid UNIQUE (device_uid);

CREATE INDEX IF NOT EXISTS idx_assets_device_uid ON assets (device_uid);
CREATE INDEX IF NOT EXISTS idx_assets_last_seen ON assets (last_seen DESC);

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

CREATE INDEX IF NOT EXISTS idx_active_application_history_hostname_timestamp
    ON active_application_history (hostname, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_active_application_history_username_timestamp
    ON active_application_history (username, timestamp DESC);

COMMIT;
