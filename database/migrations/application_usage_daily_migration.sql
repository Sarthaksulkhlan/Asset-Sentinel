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

CREATE INDEX IF NOT EXISTS idx_application_usage_daily_host_date
    ON application_usage_daily (hostname, date);

CREATE INDEX IF NOT EXISTS idx_application_usage_daily_app
    ON application_usage_daily (application_name);

