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

CREATE INDEX IF NOT EXISTS idx_activity_sessions_host_created_date
    ON activity_sessions (hostname, created_date);

CREATE INDEX IF NOT EXISTS idx_activity_sessions_host_end
    ON activity_sessions (hostname, end_time DESC);

CREATE INDEX IF NOT EXISTS idx_activity_sessions_app
    ON activity_sessions (app_name);

