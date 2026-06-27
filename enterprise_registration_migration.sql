BEGIN;

ALTER TABLE users DROP CONSTRAINT IF EXISTS chk_users_role;
ALTER TABLE users ALTER COLUMN role SET DEFAULT 'Admin';
UPDATE users
SET role = CASE lower(role)
    WHEN 'super admin' THEN 'Super Admin'
    WHEN 'super_admin' THEN 'Super Admin'
    WHEN 'admin' THEN 'Admin'
    WHEN 'it admin' THEN 'IT Admin'
    WHEN 'analyst' THEN 'IT Admin'
    WHEN 'viewer' THEN 'Viewer'
    ELSE 'Viewer'
END;
ALTER TABLE users
    ADD CONSTRAINT chk_users_role
    CHECK (role IN ('Super Admin', 'Admin', 'IT Admin', 'Viewer'));

CREATE TABLE IF NOT EXISTS admin_users (
    id BIGSERIAL PRIMARY KEY,
    company_name VARCHAR(255) NOT NULL,
    company_website VARCHAR(512),
    industry VARCHAR(120) NOT NULL,
    company_size VARCHAR(80) NOT NULL,
    country VARCHAR(120) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    work_email VARCHAR(320) NOT NULL,
    mobile_number VARCHAR(40) NOT NULL,
    job_title VARCHAR(160) NOT NULL,
    department VARCHAR(160) NOT NULL,
    username VARCHAR(255) NOT NULL,
    password_hash TEXT NOT NULL,
    terms_accepted BOOLEAN NOT NULL DEFAULT false,
    privacy_accepted BOOLEAN NOT NULL DEFAULT false,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_admin_users_work_email UNIQUE (work_email),
    CONSTRAINT uq_admin_users_username UNIQUE (username)
);

CREATE INDEX IF NOT EXISTS idx_admin_users_company_name
    ON admin_users (company_name);
CREATE INDEX IF NOT EXISTS idx_admin_users_created_at
    ON admin_users (created_at DESC);

CREATE TABLE IF NOT EXISTS early_access_requests (
    id BIGSERIAL PRIMARY KEY,
    full_name VARCHAR(255),
    email VARCHAR(320) NOT NULL,
    company VARCHAR(255),
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_early_access_requests_email UNIQUE (email)
);

CREATE INDEX IF NOT EXISTS idx_early_access_requests_company
    ON early_access_requests (company);
CREATE INDEX IF NOT EXISTS idx_early_access_requests_created_at
    ON early_access_requests (created_at DESC);

COMMIT;
