-- Keeps heartbeat status stable when older agents or skewed endpoint clocks
-- attempt to write an older assets.last_seen value after a fresh heartbeat.

CREATE OR REPLACE FUNCTION prevent_assets_last_seen_rewind()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.last_seen IS NOT NULL
       AND NEW.last_seen IS NOT NULL
       AND NEW.last_seen < OLD.last_seen THEN
        NEW.last_seen := OLD.last_seen;
    END IF;

    IF NEW.last_seen IS NOT NULL
       AND NEW.last_seen > now() + interval '10 seconds' THEN
        NEW.last_seen := now();
    END IF;

    IF NEW.last_seen IS NOT NULL
       AND NEW.last_seen >= now() - interval '45 seconds' THEN
        NEW.status := 'Online';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_assets_prevent_last_seen_rewind ON assets;

CREATE TRIGGER trg_assets_prevent_last_seen_rewind
BEFORE UPDATE OF last_seen, status ON assets
FOR EACH ROW
EXECUTE FUNCTION prevent_assets_last_seen_rewind();
