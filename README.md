# Asset-Sentinel

Centralized IT Asset Monitoring Tool for Windows PCs.

## PostgreSQL Setup

This repository is being migrated from local JSON file storage to PostgreSQL while preserving the current Flask API contracts and React dashboard behavior.

The backend integration uses SQLAlchemy ORM for Flask APIs and Python monitoring scripts. The React frontend and Express proxy API contracts remain unchanged.

## Database Schema

The production schema is defined in:

```powershell
schema.sql
```

It creates these tables:

- `assets`
- `sessions`
- `alerts`
- `active_applications`
- `hardware_changes`
- `users`

The schema keeps the current append-only behavior of JSON files. In particular, `assets` stores hardware snapshots, not only one mutable row per machine, because existing RAM and motherboard detectors compare historical snapshots.

## Create Database

Create or select a Neon PostgreSQL database for Asset Sentinel.

If `python app.py` fails during database startup, confirm `ASSET_SENTINEL_DATABASE_URL` is set to the Neon connection string and includes the required SSL options.

Example using `psql` as a PostgreSQL admin:

```sql
CREATE DATABASE asset_sentinel;
CREATE USER asset_sentinel_app WITH PASSWORD 'change_this_password';
GRANT CONNECT ON DATABASE asset_sentinel TO asset_sentinel_app;
```

Connect to the database and apply the schema:

```powershell
psql -d asset_sentinel -f schema.sql
psql -d asset_sentinel -f enterprise_migration.sql
psql -d asset_sentinel -f auth_login_activity_migration.sql
psql -d asset_sentinel -f enterprise_registration_migration.sql
```

Grant table and sequence permissions if you use a separate application user:

```sql
GRANT USAGE ON SCHEMA public TO asset_sentinel_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO asset_sentinel_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO asset_sentinel_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO asset_sentinel_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT USAGE, SELECT ON SEQUENCES TO asset_sentinel_app;
```

## Planned Environment Variables

The Flask integration uses this environment variable:

```powershell
ASSET_SENTINEL_DATABASE_URL=postgresql://username:password@host/database
```

Optional SQL logging:

```powershell
ASSET_SENTINEL_SQL_ECHO=true
```

Default local Super Admin bootstrap credentials:

```powershell
username: centralcommand
password: your_admin_password
```

Email notifications use SMTP settings from environment variables only:

```powershell
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=alerts@example.com
SMTP_PASSWORD=your_app_password
ALERT_EMAIL=security_team@example.com
```

Do not commit real production passwords or service credentials.

## Python Dependencies

Install backend dependencies with:

```powershell
pip install -r requirements.txt
```

The PostgreSQL integration uses SQLAlchemy ORM and `psycopg2-binary`.

## Current JSON Files

The current JSON files remain as optional historical backup/import files:

- `assets.json`
- `alerts.json`
- `sessions.json`
- `active_applications.json`

They will be imported during the later migration phase. Flask and the Python monitoring scripts now use PostgreSQL for runtime storage.

## Data Migration

Import existing JSON backup files into PostgreSQL with:

```powershell
python migrate_json_to_postgres.py
```

The migration is idempotent. Running it multiple times skips records that are already present. A report is written to:

```powershell
migration_report.json
```

## Validation

Run the PostgreSQL migration validation suite with:

```powershell
python validate_postgres_migration.py
```

The validation checks database connectivity, rollback-safe CRUD, Flask API response shapes, hardware/session/activity hooks, and remaining runtime JSON dependencies. A report is written to:

```powershell
validation_report.json
```

## Compatibility Target

The database design is intended to preserve these existing response shapes:

- `GET /api/assets`
- `GET /api/alerts`
- `GET /api/sessions`
- `GET /api/active-applications`
- `GET /current-user`
- `GET /current-session`
- `GET /device-status`
- `GET /sessions/count`

The frontend should continue to work without modification once the Flask storage layer is moved to PostgreSQL.

## Windows Monitoring Service

Asset Sentinel separates runtime responsibilities:

```text
Windows Endpoint
  AssetSentinelMonitoringService
    -> monitoring_agent.py
    -> Windows/WMI/Event Log/foreground window telemetry
    -> ASSET_SENTINEL_DATABASE_URL
    -> Neon PostgreSQL

API Server
  app.py
    -> Flask authenticated API
    -> Neon PostgreSQL

React Dashboard
  frontend/
    -> API Server
    -> live fleet, login, heartbeat, hardware and active app views
```

The React frontend and dashboard are not Windows Services. Only the endpoint monitoring agent is installed as a Windows Service.

### Install

Run Command Prompt or PowerShell as Administrator:

```bat
install_service.bat
```

The installer registers `AssetSentinelMonitoringService`, sets Automatic Delayed Start, configures restart-on-failure recovery, and starts the service.

### Start and Stop

```bat
start_service.bat
stop_service.bat
```

### Uninstall

Run as Administrator:

```bat
uninstall_service.bat
```

### Debug the Agent Without Installing

```powershell
python monitoring_agent.py --console
```

### Logs

Runtime logs are written to:

```text
logs/service.log
logs/agent.log
logs/error.log
logs/telemetry_spool.jsonl
```

`telemetry_spool.jsonl` stores telemetry that could not be uploaded during temporary Neon or network failures. The service retries this spool until uploads succeed.

### Verify the Service

Run as Administrator:

```powershell
Get-Service AssetSentinelMonitoringService
sc.exe qc AssetSentinelMonitoringService
sc.exe qfailure AssetSentinelMonitoringService
```

Confirm Neon receives records:

```sql
select hostname, last_seen from assets order by last_seen desc limit 5;
select hostname, application, timestamp from active_application_history order by timestamp desc limit 5;
select username, hostname, event_type, recorded_at from sessions order by recorded_at desc limit 5;
```

### Production Notes

`app.py` no longer starts endpoint monitoring by default. For legacy local development only, set:

```powershell
$env:ASSET_SENTINEL_EMBEDDED_MONITOR="1"
```

Production deployments should run the Flask API and `AssetSentinelMonitoringService` separately.
