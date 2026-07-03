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

CREATE INDEX IF NOT EXISTS idx_application_usage_segments_device_date
    ON application_usage_segments (device_id, date);

CREATE INDEX IF NOT EXISTS idx_application_usage_segments_hostname_start
    ON application_usage_segments (hostname, start_time DESC);

CREATE INDEX IF NOT EXISTS idx_application_usage_segments_application
    ON application_usage_segments (application_name);

