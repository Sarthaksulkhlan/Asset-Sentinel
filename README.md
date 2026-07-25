<div align="center">

<img src="docs/screenshots/asset-sentinel-hero.png" alt="Asset Sentinel endpoint truth layer" width="100%"/>

# Asset Sentinel

### Continuous visibility from the endpoint to the fleet

Asset Sentinel turns Windows session, application, hardware, and heartbeat events into a live operational picture—so teams can act on what is true now, not what an inventory sheet remembered.

<br/>

<a href="https://assetsentinel.onrender.com/demo"><img src="https://img.shields.io/badge/%E2%96%B6_LIVE_DEMO-0078D6?style=for-the-badge" alt="Open live demo"/></a>
<a href="https://github.com/Sarthaksulkhlan/Asset-Sentinel"><img src="https://img.shields.io/badge/VIEW_ON-GITHUB-181717?style=for-the-badge&logo=github" alt="View Asset Sentinel on GitHub"/></a>
<a href="LICENSE"><img src="https://img.shields.io/badge/LICENSE-MIT-2ea44f?style=for-the-badge" alt="Open MIT license"/></a>

**Website:** [https://assetsentinel.onrender.com](https://assetsentinel.onrender.com)

<br/><br/>

<a href="https://www.microsoft.com/windows"><img src="https://img.shields.io/badge/Windows-Agent-0078D4?style=flat-square&logo=windows11&logoColor=white" alt="Windows agent"/></a>
<a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-Backend-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python backend"/></a>
<a href="https://flask.palletsprojects.com/"><img src="https://img.shields.io/badge/Flask-API-000000?style=flat-square&logo=flask&logoColor=white" alt="Flask API"/></a>
<a href="https://react.dev/"><img src="https://img.shields.io/badge/React-Frontend-61DAFB?style=flat-square&logo=react&logoColor=000000" alt="React frontend"/></a>
<a href="https://www.typescriptlang.org/"><img src="https://img.shields.io/badge/TypeScript-3178C6?style=flat-square&logo=typescript&logoColor=white" alt="TypeScript"/></a>
<a href="https://supabase.com/"><img src="https://img.shields.io/badge/Supabase-PostgreSQL-3FCF8E?style=flat-square&logo=supabase&logoColor=white" alt="Supabase PostgreSQL"/></a>
<a href="https://render.com/"><img src="https://img.shields.io/badge/Deployed_on-Render-46E3B7?style=flat-square&logo=render&logoColor=white" alt="Deployed on Render"/></a>

</div>

> **Production status:** Windows Agent → Flask API → Supabase PostgreSQL → React dashboard is deployed end to end. The optional AI Audit currently exists only in the Express runtime and is not exposed by the static Render frontend deployment.

## Explore

[Why Asset Sentinel](#why-asset-sentinel) · [Features](#key-features) · [Architecture](#system-architecture) · [Quick Start](#quick-start) · [Configuration](#configuration-reference) · [Security](#security) · [Roadmap](#roadmap)

## At a Glance

| | Description |
|---|---|
| **What** | A Windows endpoint monitoring and asset-intelligence platform built around continuous agent telemetry rather than periodic fleet scans. |
| **Why it is different** | Verified Windows events and frequent collectors report endpoint state close to when it changes instead of waiting for the next inventory cycle. |
| **Who it is for** | IT operations, endpoint security, support teams, and organization administrators responsible for Windows fleets. |
| **Current coverage** | Heartbeat, hardware inventory, login/logout and lock/unlock state, active applications, usage aggregation, idle time, and productivity analytics. |
| **Trust spine** | Agent → authenticated backend → PostgreSQL → dashboard. The backend validates and persists telemetry; agents and the dashboard never write directly to the database. |
| **The moat** | A unified evidence pipeline whose per-device history becomes more valuable as session, application, hardware, and liveness records accumulate. |
| **Built with** | Python Windows Agent, Flask/Gunicorn API, Supabase PostgreSQL, and a React/TypeScript/Vite dashboard deployed on Render. |

> [Open the live demo](https://assetsentinel.onrender.com/demo) to explore Asset Sentinel with demonstration data.

## The Problem

Enterprise IT teams are expected to answer a deceptively simple question at any moment: **what is the current state of every endpoint in the fleet?** In many organizations, they cannot answer without consulting several tools and manually correlating their results.

Periodic inventories begin aging as soon as they are produced. RAM is upgraded, storage is replaced, a laptop disappears from the network, or a user locks and resumes a session—but those facts may remain buried until another scan or investigation. Responders lose time establishing whether a machine is online, who used it, which application was active, and what changed before an issue surfaced.

Hardware records, Windows session events, application activity, monitoring, and support workflows commonly live in disconnected systems. That creates an operating model based on stale snapshots and reactive reconstruction. Asset Sentinel replaces that gap with one continuously updated evidence pipeline and a fleet view grounded in endpoint records.

<div align="center">

<img src="docs/screenshots/asset-sentinel-visibility.png" alt="Stale endpoint snapshots compared with live Asset Sentinel signals" width="100%"/>

<sub><em>Periodic inventory leaves hardware changes, missed heartbeats, and session activity hidden. Asset Sentinel turns those gaps into live, attributable signals.</em></sub>

</div>

## Why Asset Sentinel

| Traditional fleet visibility | Asset Sentinel |
|---|---|
| Periodic scans on a fixed schedule | Continuous agent reporting and verified Windows events |
| Inventory snapshots age between scans | Endpoint records are refreshed throughout operation |
| Availability inferred from an old scan | Explicit heartbeat determines online/offline state |
| Hardware changes discovered during a later audit | Hardware identity is recorded and compared over time |
| Session and usage data scattered across local logs | Login, lock/unlock, idle, and application activity are centralized per device |
| Multiple tools require manual correlation | One backend pipeline supports monitoring, alerts, reports, and support workflows |
| Fleet totals hide their underlying evidence | Operators can drill from fleet state into device-level history |

This is an architectural distinction, not a cosmetic one: a scan describes what was observed at scan time, while continuous telemetry builds a trace of what happened between observations.

## Key Features

| Category | Capability |
|---|---|
| Endpoint Monitoring | Agents report device state continuously through authenticated backend telemetry. |
| Heartbeat | Configurable liveness signals allow the backend to distinguish online, offline, and unresponsive devices. |
| Device Inventory | Structured endpoint identity and status records remain connected to ongoing telemetry. |
| Hardware Integrity | WMI-backed hardware details and identifiers provide a baseline for detecting configuration changes. |
| Login and Logout Activity | Genuine Windows authentication and session-end records provide a per-device access history. |
| Lock and Unlock Detection | Verified workstation transitions separate active use from locked sessions without creating heartbeat-based logins. |
| Active Application Timeline | Foreground application changes form a chronological activity record for each endpoint. |
| Application Usage | Application records are aggregated into open, active, and idle duration views. |
| Productivity Analytics | Active, idle, and locked time is summarized into higher-level usage insights. |
| Idle Tracking | User inactivity is measured separately from application-open time and device uptime. |
| Fleet Overview | Device telemetry is aggregated into a current organization-wide operational view. |
| Device Monitoring | Administrators can drill into hardware, connectivity, sessions, and activity history for one endpoint. |
| Alerts and Reports | Telemetry conditions are surfaced for review and consolidated reporting. |
| Support Tickets | Endpoint-related issues can be tracked alongside the operational context that informs them. |
| Super Admin | Platform-level controls manage companies, administrators, devices, and support state. |

## From Endpoint Evidence to Fleet Intelligence

<div align="center">

<img src="docs/screenshots/asset-sentinel-pipeline.png" alt="Asset Sentinel endpoint evidence and fleet intelligence pipeline" width="100%"/>

<sub><em>Session, application, hardware, and heartbeat evidence is authenticated and normalized before it becomes fleet health, timelines, usage insight, and actionable integrity alerts.</em></sub>

</div>

## System Architecture

```mermaid
flowchart TB
    subgraph Fleet[Windows Fleet]
        A1[Agent - Device 1]
        A2[Agent - Device 2]
        A3[Agent - Device N]
    end

    subgraph Backend[Flask Backend - Render Web Service]
        AUTH[JWT and Agent Authentication]
        API[REST API]
        VAL[Validation]
        PROC[Telemetry Processing]
    end

    subgraph Store[Supabase PostgreSQL]
        DB[(Devices, Sessions, Applications,<br/>Hardware, Heartbeats, Alerts)]
    end

    subgraph Dashboard[React Dashboard - Render Static Site]
        ADMIN[Company Dashboard]
        SUPER[Super Admin]
    end

    A1 -->|HTTPS, JSON, Agent Token| AUTH
    A2 -->|HTTPS, JSON, Agent Token| AUTH
    A3 -->|HTTPS, JSON, Agent Token| AUTH
    AUTH --> API
    API --> VAL --> PROC --> DB
    ADMIN -->|HTTPS and JWT| AUTH
    SUPER -->|HTTPS and JWT| AUTH
    API -->|Tenant-scoped JSON| ADMIN
    API -->|Platform JSON| SUPER
```

The agent never connects directly to the database, and the dashboard never connects directly to monitored devices. Telemetry passes through the backend API for authentication, validation, processing, and persistence.

### Architecture principles

- **Separate trust channels:** Windows agents use a dedicated bearer token; dashboard users use JWT access and refresh tokens.
- **Tenant-aware access:** company users are scoped to their organization, while platform-wide operations require the `SUPER_ADMIN` role.
- **Evidence before analytics:** raw session, application, heartbeat, and hardware observations are normalized before they become timelines, alerts, and usage insights.
- **Database as source of truth:** PostgreSQL holds operational state and history; the agent and dashboard never write to it directly.
- **Deployment-aware design:** Render hosts the React application as a static site and the Flask API as a separate Gunicorn service.

## How It Works

1. The Windows agent runs continuously on each managed endpoint.
2. It detects session state, foreground applications, hardware information, and device health.
3. Timestamped telemetry is sent securely to the backend API.
4. The backend validates and stores records in Supabase PostgreSQL.
5. The React dashboard retrieves current and aggregated fleet information from the API.

```mermaid
flowchart LR
    Start([Agent starts]) --> Observe[Observe session, application, and hardware state]
    Observe --> Stamp[Timestamp and serialize]
    Stamp --> Push[Send to backend API]
    Push --> Store[(Supabase PostgreSQL)]
    Push --> Beat[Continue heartbeat]
    Beat --> Observe
```

## Technology Stack

| Layer | Technology | Responsibility |
|---|---|---|
| Windows Agent | Python, pywin32, WMI, psutil | Hardware, session, heartbeat, foreground application, and usage collection |
| Backend API | Python, Flask, Flask-CORS | Authentication, validation, tenant isolation, telemetry ingestion, and analytics |
| Data Access | SQLAlchemy 2, psycopg2 | PostgreSQL models, constraints, transactions, and queries |
| Authentication | PyJWT, bcrypt | Access/refresh tokens, password hashing, role checks, and password-reset OTPs |
| Database | Supabase PostgreSQL | Operational state and historical evidence |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS | Dashboard, administration, support, and responsive user experience |
| Deployment | Render Static Site, Render Web Service, Gunicorn | Production hosting and process management |
| Transport | HTTPS and JSON | Agent-to-API and browser-to-API communication |

## Repository Structure

```text
asset-sentinel/
├── agent/
│   ├── collectors/       Session, heartbeat, hardware, and application collectors
│   ├── detectors/        Hardware change detectors
│   ├── scripts/          Agent and service management scripts
│   └── windows/          Windows Service implementation
├── backend/
│   ├── api/              Flask API routes
│   ├── core/             Configuration, database, storage, and health
│   ├── models/           SQLAlchemy models
│   └── services/         Backend services
├── database/
│   ├── migrations/       Database migrations
│   └── schemas/          PostgreSQL schema
├── frontend/             React and Vite dashboard
├── docs/                 Architecture, setup, and installation documentation
├── tools/                Migration and verification utilities
├── app.py                Backend launcher and Gunicorn application export
└── requirements.txt      Python dependencies
```

## Windows Monitoring Agent

The Python agent runs on monitored Windows endpoints as either the installed Windows Service or an interactive console process. It combines verified native session notifications with scheduled heartbeat, hardware, and foreground-application collectors. Telemetry is authenticated and sent only to the backend API; the agent does not connect to PostgreSQL directly.

The service path handles genuine Windows session changes through the Service Control Manager. Interactive runs register a native Windows session hook for real unlock notifications, keeping login creation separate from heartbeat, foreground-application changes, timers, and dashboard refreshes.

## Quick Start

Choose the path that matches what you are trying to do:

- **Install a monitored Windows device:** use the deployed Asset Sentinel website and backend. This is the normal endpoint setup.
- **Run the complete project locally:** start PostgreSQL, the Flask backend, and the React frontend for development.

## Install the Windows Agent

Use these steps on every Windows computer that should report to the deployed Asset Sentinel dashboard.

### Requirements

- Windows 10 or Windows 11
- Python 3.10 or newer
- Administrator access to install a Windows Service
- An Asset Sentinel account
- The agent token supplied by the Asset Sentinel deployment administrator

### 1. Download the project

Either select **Code -> Download ZIP** on GitHub and extract it, or clone the repository:

```powershell
git clone https://github.com/Sarthaksulkhlan/Asset-Sentinel.git
cd Asset-Sentinel
```

Run all remaining commands from the repository root.

### 2. Install the Python dependencies

```powershell
python -m pip install -r requirements.txt
```

### 3. Configure the Windows Agent

Create a local `.env` file from the example:

```powershell
Copy-Item .env.example .env
```

For a monitored Windows device, these are the only required settings:

```dotenv
ASSET_SENTINEL_API_URL=https://asset-sentinel-backend.onrender.com
ASSET_SENTINEL_AGENT_TOKEN=replace_with_the_token_from_your_deployment_administrator
```

The Windows Agent does not connect directly to PostgreSQL. It does not need `ASSET_SENTINEL_DATABASE_URL`, JWT, SMTP, or super-admin settings. Keep `.env` private and never commit it.

### 4. Get a pairing code

1. Open [Asset Sentinel](https://assetsentinel.onrender.com) and sign in.
2. Open **Settings -> Device Pairing**.
3. Use the active pairing code, or select **Generate New Pairing Code**.
4. Keep the four-digit code ready. It is valid for 20 hours and can be used only once.

New accounts receive a pairing code during signup. Existing users, administrators, and super administrators can generate a fresh code from Settings whenever they reinstall the Agent or pair another device.

### 5. Install and pair the device

Open PowerShell or VS Code **as Administrator**, return to the repository root, and run:

```powershell
.\install_service.bat
```

The installer pauses and asks:

```text
Enter your 4-digit Pairing Code:
```

After the backend accepts the code, the installer:

1. Pairs the Windows device with the signed-in Asset Sentinel account.
2. Replaces an older `AssetSentinelMonitoringService` registration when present.
3. Installs the service with delayed automatic startup and recovery actions.
4. Starts the Windows Monitoring Service.
5. Installs the independent Active Application user-session agent.

An invalid, expired, or previously used code stops installation. Pairing codes are requested only by `install_service.bat`; Windows startup and the service-control scripts never request one.

### 6. Verify the installation

Confirm that the Windows Service is running:

```powershell
sc.exe query AssetSentinelMonitoringService
```

The result should contain:

```text
STATE : 4  RUNNING
```

Confirm that the Active Application Agent is running in the signed-in Windows session:

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\agent\scripts\check_active_app_agent.ps1
```

Wait a few minutes, then open the dashboard and confirm that the device heartbeat, hardware inventory, login activity, application timeline, and productivity data are updating.

### Reinstall or update the Agent

Generate a fresh pairing code and run the installer again:

```powershell
.\install_service.bat
```

The installer safely stops and removes the existing service registration before installing the current version. You do not need to run `uninstall_service.bat` first.

### Service controls

Run service-management scripts from an Administrator shell:

| Action | Command | Pairing code required |
|---|---|---|
| Start the Windows Service | `.\start_service.bat` | No |
| Stop the Windows Service | `.\stop_service.bat` | No |
| Restart the Windows Service | `.\restart_service.bat` | No |
| Uninstall the Windows Service | `.\uninstall_service.bat` | No |
| Start the Active Application Agent | `.\start_active_app_agent.bat` | No |
| Stop the Active Application Agent | `.\stop_active_app_agent.bat` | No |

The Windows Service starts automatically after a reboot without asking for a pairing code. The Active Application Agent is a separate user-session process configured to start when the monitored Windows user signs in.

## Local Development

Use this path only when developing or self-hosting the backend and frontend.

### Requirements

- Python 3.10 or newer
- Node.js 20 or newer and npm
- A reachable PostgreSQL database

### 1. Configure the environment

```powershell
Copy-Item .env.example .env
Copy-Item frontend/.env.example frontend/.env
```

Set the backend database URL, JWT secret, agent token, administrator credentials, and CORS origins in `.env`. Set `VITE_API_BASE_URL` in `frontend/.env` to the backend URL. SMTP settings are required only for email delivery.

### 2. Install dependencies

```powershell
python -m pip install -r requirements.txt
cd frontend
npm install
cd ..
```

### 3. Prepare PostgreSQL

For a clean database, the backend creates the current SQLAlchemy tables during startup. When upgrading an existing database, apply the required SQL migrations from `database/migrations/`. See [docs/SETUP.md](docs/SETUP.md) for the project setup notes.

### 4. Start the applications

Backend, from the repository root:

```powershell
python app.py
```

Frontend, from a second terminal:

```powershell
cd frontend
npm run dev
```

Optional interactive Windows agent, from a third terminal:

```powershell
python agent/collectors/monitoring_agent.py --console
```

## Configuration Reference

| Variable | Used by | Purpose |
|---|---|---|
| `ASSET_SENTINEL_API_URL` | Windows Agent | Base URL of the Flask backend |
| `ASSET_SENTINEL_AGENT_TOKEN` | Backend and Windows Agent | Authenticates endpoint telemetry; both sides must use the same value |
| `ASSET_SENTINEL_DATABASE_URL` | Backend only | PostgreSQL connection string |
| `ASSET_SENTINEL_JWT_SECRET` | Backend only | Signs and validates dashboard user tokens |
| `VITE_API_BASE_URL` | Frontend only | Backend URL used for browser API requests |
| `ASSET_SENTINEL_CORS_ORIGINS` | Backend only | Comma-separated allowed frontend origins |
| `SUPER_ADMIN_USERNAME`, `SUPER_ADMIN_EMAIL`, `SUPER_ADMIN_PASSWORD` | Backend only | Bootstrap platform administrator |
| `SMTP_*`, `ALERT_EMAIL` | Backend only | OTP, alert, and support email delivery |

Additional retry, timeout, spool, and collector settings are documented in [.env.example](.env.example).

> **Security:** never commit `.env`, database credentials, JWT secrets, SMTP passwords, or the production agent token. Replace all example credentials before deployment.

## Security

- Agent-to-backend and frontend-to-backend traffic uses HTTPS in production.
- Secrets are supplied through environment variables.
- Agent telemetry uses a dedicated bearer token with configurable request timeout and retry behavior.
- User passwords are hashed with bcrypt.
- Dashboard sessions use signed access tokens and database-backed, revocable refresh tokens.
- Password-reset OTPs are hashed, expire, count failed attempts, and are single-use.
- Company data is tenant-scoped; platform operations require the `SUPER_ADMIN` role.
- Administrative functions are restricted by role and company status.

For production deployments, rotate all sample credentials, restrict diagnostic endpoints, configure exact CORS origins, and define retention rules for session and application history. See [SECURITY.md](SECURITY.md) for the disclosure policy.

## Current Limitations

| Feature | Status | Notes |
|---|---|---|
| Agent telemetry pipeline | Operational | Hardware, heartbeat, sessions, applications, usage, alerts, and changes |
| Company and super-admin dashboards | Operational | Tenant-aware monitoring, support, and platform administration |
| Email and password-reset delivery | Configuration-dependent | Requires valid SMTP settings |
| AI Audit | Experimental | Implemented in `frontend/server.ts`; unavailable through the current static Render frontend |
| Formal OpenAPI specification | Planned | Routes are currently documented in source and project documentation |
| Automated exports and retention controls | Planned | Not yet exposed as complete workflows |

## Roadmap

- [ ] Move AI Audit behind a production API or deploy the Express runtime explicitly
- [ ] Expand automated report exports
- [ ] Add more granular role-based permissions
- [ ] Publish formal OpenAPI documentation
- [ ] Add configurable historical data-retention policies
- [ ] Add automated contract tests for tenant isolation, token lifecycle, and telemetry deduplication

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Installation](docs/INSTALLATION.md)
- [Setup](docs/SETUP.md)
- [Screenshot guidance](docs/screenshots/README.md)
- [Security policy](SECURITY.md)
- [MIT license](LICENSE)

## Contributing

Keep agent payloads, backend models, database migrations, and frontend types aligned. Before submitting a change:

1. Run `npm run lint` from `frontend/`.
2. Run the relevant checks under `tools/verification/`.
3. Document new environment variables, routes, migrations, and operational behavior.
4. Never commit `.env`, credentials, access tokens, database URLs, or sensitive endpoint telemetry.
