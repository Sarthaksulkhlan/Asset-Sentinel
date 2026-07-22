# Asset Sentinel

Centralized IT asset monitoring for Windows PCs, with a Flask backend, React frontend, Windows service support, and a user-session active-application agent.

## Repository Layout

```text
backend/
  api/          Flask API helpers for auth, assets, activity, and alerts
  core/         configuration, database, logging, storage, and runtime health
  models/       SQLAlchemy models
  services/     notifications and telemetry bootstrap services
  main.py       backend application entry point

agent/
  collectors/   hardware, login, heartbeat, active application, and agent loops
  detectors/    RAM and motherboard change detectors
  windows/      Windows service implementation and Python resolver
  scripts/      service and active-application startup scripts

database/
  schemas/      PostgreSQL schema
  migrations/   SQL migrations
  data/         historical JSON backup/report files

frontend/       existing React/Vite frontend
docs/           architecture, setup, and installation notes
tools/          migration and verification utilities
```

Root-level `.bat`, `app.py`, `resolve_python_exe.ps1`, and `launch_active_app_agent.ps1` files are compatibility wrappers so existing commands continue to work.

## Screenshots

### Landing Page

![Asset Sentinel landing page](docs/screenshots/landing-page.png)

*Screenshot not yet available; add `docs/screenshots/landing-page.png` later.*

### Login Page

![Asset Sentinel login page](docs/screenshots/login-page.png)

*Screenshot not yet available; add `docs/screenshots/login-page.png` later.*

### Signup Page

![Asset Sentinel signup page](docs/screenshots/signup-page.png)

*Screenshot not yet available; add `docs/screenshots/signup-page.png` later.*

### Dashboard Overview

![Asset Sentinel dashboard overview](docs/screenshots/dashboard-overview.png)

*Screenshot not yet available; add `docs/screenshots/dashboard-overview.png` later.*

### Fleet Telemetry

![Asset Sentinel fleet telemetry](docs/screenshots/fleet-telemetry.png)

*Screenshot not yet available; add `docs/screenshots/fleet-telemetry.png` later.*

### Device Monitoring

![Asset Sentinel device monitoring](docs/screenshots/device-monitoring.png)

*Screenshot not yet available; add `docs/screenshots/device-monitoring.png` later.*

### Login Activity

![Asset Sentinel login activity](docs/screenshots/login-activity.png)

*Screenshot not yet available; add `docs/screenshots/login-activity.png` later.*

### Active Application Timeline

![Asset Sentinel active application timeline](docs/screenshots/active-application-timeline.png)

*Screenshot not yet available; add `docs/screenshots/active-application-timeline.png` later.*

### Application Usage

![Asset Sentinel application usage](docs/screenshots/application-usage.png)

*Screenshot not yet available; add `docs/screenshots/application-usage.png` later.*

### Productivity Insights

![Asset Sentinel productivity insights](docs/screenshots/productivity-insights.png)

*Screenshot not yet available; add `docs/screenshots/productivity-insights.png` later.*

### Support Tickets

![Asset Sentinel support tickets](docs/screenshots/support-tickets.png)

*Screenshot not yet available; add `docs/screenshots/support-tickets.png` later.*

### Super Admin Dashboard

![Asset Sentinel super admin dashboard](docs/screenshots/super-admin-dashboard.png)

*Screenshot not yet available; add `docs/screenshots/super-admin-dashboard.png` later.*

## Features Preserved

- Device status and heartbeat tracking
- Hardware collection
- Login activity tracking and last successful login
- Active application timeline
- Windows service auto-start
- Manual backend and frontend startup
- Non-admin PC compatibility
- Active application user-session agent

## Environment

Copy `.env.example` to `.env` and configure at least:

```powershell
ASSET_SENTINEL_DATABASE_URL=postgresql://username:password@host/database
```

Optional settings include JWT, SMTP, SQL echo, heartbeat timeout, and display timezone values. Do not commit production secrets.

Install backend dependencies:

```powershell
pip install -r requirements.txt
```

## Database

The production schema and migrations live under `database/`:

```powershell
psql -d asset_sentinel -f database/schemas/schema.sql
psql -d asset_sentinel -f database/migrations/enterprise_migration.sql
psql -d asset_sentinel -f database/migrations/auth_login_activity_migration.sql
psql -d asset_sentinel -f database/migrations/enterprise_registration_migration.sql
```

Historical JSON backups and migration reports are kept in `database/data/`.

## Manual Development

Backend:

```powershell
python backend/main.py
```

The legacy command still works:

```powershell
python app.py
```

Frontend:

```powershell
cd frontend
npm run dev
```

Manual active-application agent:

```bat
start_active_app_agent.bat
```

Direct agent console run:

```powershell
python agent/collectors/monitoring_agent.py --console
```

## Windows Service

Install from an elevated Command Prompt or PowerShell:

```bat
install_service.bat
```

The wrapper delegates to `agent/scripts/install_service.bat`, which registers `agent/windows/asset_sentinel_service.py` as `AssetSentinelMonitoringService`, configures delayed auto-start, applies restart-on-failure recovery, starts the backend service, and attempts to install the user-session active-application helper.

Service controls:

```bat
start_service.bat
stop_service.bat
restart_service.bat
uninstall_service.bat
```

Active-application user-session controls:

```bat
install_active_app_agent.bat
start_active_app_agent.bat
stop_active_app_agent.bat
check_active_app_agent.bat
uninstall_active_app_agent.bat
```

Runtime logs remain in root `logs/`:

```text
logs/service.log
logs/agent.log
logs/app.log
logs/error.log
logs/active_application_launcher.log
logs/telemetry_spool.jsonl
```

## Utilities

Migration and verification scripts are under `tools/verification/`:

```powershell
python tools/verification/migrate_json_to_postgres.py
python tools/verification/validate_postgres_migration.py
```

PyInstaller service packaging assets live in `agent/windows/`:

```powershell
pyinstaller agent/windows/nexis_agent.spec
```

## API Compatibility

The existing frontend API surface is preserved:

- `GET /api/assets`
- `GET /api/alerts`
- `GET /api/active-applications`
- `GET /api/sessions`
- `GET /api/sessions/count`
- `GET /current-user`
- `GET /current-session`
- `GET /device-status`
- `GET /api/debug/startup-health`
- `GET /api/debug/device-health/<hostname-or-device-id>`
