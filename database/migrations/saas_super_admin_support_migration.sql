CREATE TABLE IF NOT EXISTS companies (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    website VARCHAR(512),
    industry VARCHAR(120),
    company_size VARCHAR(80),
    country VARCHAR(120),
    plan VARCHAR(80) NOT NULL DEFAULT 'Trial',
    status VARCHAR(30) NOT NULL DEFAULT 'Active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_companies_name UNIQUE (name),
    CONSTRAINT chk_companies_status CHECK (status IN ('Active', 'Suspended'))
);

CREATE INDEX IF NOT EXISTS idx_companies_status ON companies (status);
CREATE INDEX IF NOT EXISTS idx_companies_created_at ON companies (created_at DESC);
ALTER TABLE companies ALTER COLUMN plan SET DEFAULT 'Trial';
ALTER TABLE companies ALTER COLUMN status SET DEFAULT 'Active';

ALTER TABLE users ADD COLUMN IF NOT EXISTS company_id BIGINT REFERENCES companies(id) ON DELETE SET NULL;
ALTER TABLE admin_users ADD COLUMN IF NOT EXISTS company_id BIGINT REFERENCES companies(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_users_company_id ON users (company_id);
CREATE INDEX IF NOT EXISTS idx_admin_users_company_id ON admin_users (company_id);

ALTER TABLE assets ADD COLUMN IF NOT EXISTS company_id BIGINT REFERENCES companies(id) ON DELETE SET NULL;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS company_id BIGINT REFERENCES companies(id) ON DELETE SET NULL;
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS company_id BIGINT REFERENCES companies(id) ON DELETE SET NULL;
ALTER TABLE active_applications ADD COLUMN IF NOT EXISTS company_id BIGINT REFERENCES companies(id) ON DELETE SET NULL;
ALTER TABLE active_application_history ADD COLUMN IF NOT EXISTS company_id BIGINT REFERENCES companies(id) ON DELETE SET NULL;
ALTER TABLE application_usage_segments ADD COLUMN IF NOT EXISTS company_id BIGINT REFERENCES companies(id) ON DELETE SET NULL;
ALTER TABLE application_usage_daily ADD COLUMN IF NOT EXISTS company_id BIGINT REFERENCES companies(id) ON DELETE SET NULL;
ALTER TABLE activity_sessions ADD COLUMN IF NOT EXISTS company_id BIGINT REFERENCES companies(id) ON DELETE SET NULL;
ALTER TABLE hardware_changes ADD COLUMN IF NOT EXISTS company_id BIGINT REFERENCES companies(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_assets_company_id ON assets (company_id);
CREATE INDEX IF NOT EXISTS idx_sessions_company_id ON sessions (company_id);
CREATE INDEX IF NOT EXISTS idx_alerts_company_id ON alerts (company_id);
CREATE INDEX IF NOT EXISTS idx_active_applications_company_id ON active_applications (company_id);
CREATE INDEX IF NOT EXISTS idx_active_application_history_company_id ON active_application_history (company_id);
CREATE INDEX IF NOT EXISTS idx_application_usage_segments_company_id ON application_usage_segments (company_id);
CREATE INDEX IF NOT EXISTS idx_application_usage_daily_company_id ON application_usage_daily (company_id);
CREATE INDEX IF NOT EXISTS idx_activity_sessions_company_id ON activity_sessions (company_id);
CREATE INDEX IF NOT EXISTS idx_hardware_changes_company_id ON hardware_changes (company_id);

ALTER TABLE users DROP CONSTRAINT IF EXISTS chk_users_role;
ALTER TABLE users ALTER COLUMN role SET DEFAULT 'COMPANY_ADMIN';
UPDATE users
SET role = CASE lower(role)
    WHEN 'super_admin' THEN 'SUPER_ADMIN'
    WHEN 'super admin' THEN 'SUPER_ADMIN'
    WHEN 'company_admin' THEN 'COMPANY_ADMIN'
    WHEN 'company admin' THEN 'COMPANY_ADMIN'
    WHEN 'admin' THEN 'COMPANY_ADMIN'
    WHEN 'analyst' THEN 'IT Admin'
    WHEN 'it admin' THEN 'IT Admin'
    WHEN 'viewer' THEN 'Viewer'
    ELSE role
END;
ALTER TABLE users
ADD CONSTRAINT chk_users_role
CHECK (role IN ('SUPER_ADMIN', 'COMPANY_ADMIN', 'Super Admin', 'Admin', 'IT Admin', 'Viewer'));

INSERT INTO companies (name, website, industry, company_size, country, plan, status)
SELECT DISTINCT au.company_name, au.company_website, au.industry, au.company_size, au.country, 'Trial', 'Active'
FROM admin_users au
WHERE au.company_id IS NULL
ON CONFLICT (name) DO NOTHING;

UPDATE admin_users au
SET company_id = c.id
FROM companies c
WHERE au.company_id IS NULL AND c.name = au.company_name;

UPDATE users u
SET company_id = au.company_id
FROM admin_users au
WHERE u.company_id IS NULL
  AND (lower(u.email) = lower(au.work_email) OR lower(u.username) = lower(au.username));

WITH only_company AS (SELECT id FROM companies WHERE (SELECT count(*) FROM companies) = 1 LIMIT 1)
UPDATE assets SET company_id = (SELECT id FROM only_company) WHERE company_id IS NULL AND EXISTS (SELECT 1 FROM only_company);
WITH only_company AS (SELECT id FROM companies WHERE (SELECT count(*) FROM companies) = 1 LIMIT 1)
UPDATE sessions SET company_id = (SELECT id FROM only_company) WHERE company_id IS NULL AND EXISTS (SELECT 1 FROM only_company);
WITH only_company AS (SELECT id FROM companies WHERE (SELECT count(*) FROM companies) = 1 LIMIT 1)
UPDATE alerts SET company_id = (SELECT id FROM only_company) WHERE company_id IS NULL AND EXISTS (SELECT 1 FROM only_company);
WITH only_company AS (SELECT id FROM companies WHERE (SELECT count(*) FROM companies) = 1 LIMIT 1)
UPDATE active_applications SET company_id = (SELECT id FROM only_company) WHERE company_id IS NULL AND EXISTS (SELECT 1 FROM only_company);
WITH only_company AS (SELECT id FROM companies WHERE (SELECT count(*) FROM companies) = 1 LIMIT 1)
UPDATE active_application_history SET company_id = (SELECT id FROM only_company) WHERE company_id IS NULL AND EXISTS (SELECT 1 FROM only_company);
WITH only_company AS (SELECT id FROM companies WHERE (SELECT count(*) FROM companies) = 1 LIMIT 1)
UPDATE application_usage_segments SET company_id = (SELECT id FROM only_company) WHERE company_id IS NULL AND EXISTS (SELECT 1 FROM only_company);
WITH only_company AS (SELECT id FROM companies WHERE (SELECT count(*) FROM companies) = 1 LIMIT 1)
UPDATE application_usage_daily SET company_id = (SELECT id FROM only_company) WHERE company_id IS NULL AND EXISTS (SELECT 1 FROM only_company);
WITH only_company AS (SELECT id FROM companies WHERE (SELECT count(*) FROM companies) = 1 LIMIT 1)
UPDATE activity_sessions SET company_id = (SELECT id FROM only_company) WHERE company_id IS NULL AND EXISTS (SELECT 1 FROM only_company);
WITH only_company AS (SELECT id FROM companies WHERE (SELECT count(*) FROM companies) = 1 LIMIT 1)
UPDATE hardware_changes SET company_id = (SELECT id FROM only_company) WHERE company_id IS NULL AND EXISTS (SELECT 1 FROM only_company);

CREATE TABLE IF NOT EXISTS support_tickets (
    id BIGSERIAL PRIMARY KEY,
    ticket_number VARCHAR(40) NOT NULL,
    company_id BIGINT REFERENCES companies(id) ON DELETE SET NULL,
    created_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    category VARCHAR(120) NOT NULL,
    priority VARCHAR(20) NOT NULL DEFAULT 'MEDIUM',
    description TEXT NOT NULL,
    related_device VARCHAR(255),
    status VARCHAR(30) NOT NULL DEFAULT 'OPEN',
    admin_response TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at TIMESTAMPTZ,
    CONSTRAINT uq_support_tickets_ticket_number UNIQUE (ticket_number),
    CONSTRAINT chk_support_tickets_category CHECK (category IN ('Agent Issue', 'Device Offline', 'Login Tracking Issue', 'Application Monitoring Issue', 'Performance Issue', 'Account Issue', 'Other')),
    CONSTRAINT chk_support_tickets_priority CHECK (priority IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    CONSTRAINT chk_support_tickets_status CHECK (status IN ('OPEN', 'IN_PROGRESS', 'RESOLVED', 'CLOSED'))
);

CREATE INDEX IF NOT EXISTS idx_support_tickets_company_id ON support_tickets (company_id);
CREATE INDEX IF NOT EXISTS idx_support_tickets_status ON support_tickets (status);
CREATE INDEX IF NOT EXISTS idx_support_tickets_created_at ON support_tickets (created_at DESC);
CREATE SEQUENCE IF NOT EXISTS support_ticket_number_seq START 1;
