-- Prevent replayed Windows Event Log records from creating duplicate sessions.
-- Run against Supabase/PostgreSQL after deploying the backend/agent changes.

BEGIN;

ALTER TABLE sessions ADD COLUMN IF NOT EXISTS windows_event_record_id VARCHAR(255);

WITH duplicate_session_events AS (
    SELECT
        id,
        ROW_NUMBER() OVER (
            PARTITION BY hostname, windows_event_record_id
            ORDER BY recorded_at ASC, id ASC
        ) AS duplicate_rank
    FROM sessions
    WHERE windows_event_record_id IS NOT NULL
)
DELETE FROM sessions
WHERE id IN (
    SELECT id
    FROM duplicate_session_events
    WHERE duplicate_rank > 1
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_sessions_hostname_windows_event_record_id
    ON sessions (hostname, windows_event_record_id)
    WHERE windows_event_record_id IS NOT NULL;

COMMIT;
