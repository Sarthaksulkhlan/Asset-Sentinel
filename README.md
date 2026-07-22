<div align="center">

<img src="docs/screenshots/asset-sentinel-hero.png" alt="Asset Sentinel endpoint truth layer" width="100%"/>

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

> **Production status:** Windows Agent → Flask API → Supabase PostgreSQL → React dashboard is deployed end to end. AI Audit remains intentionally unavailable until its backend endpoint is implemented.

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
        API[REST API]
        VAL[Validation]
        PROC[Telemetry Processing]
    end

    subgraph Store[Supabase PostgreSQL]
        DB[(Devices, Sessions, Applications,<br/>Hardware, Heartbeats, Alerts)]
    end

    subgraph Dashboard[React Dashboard - Render Static Site]
        UI[React and Vite]
    end

    A1 -->|HTTPS and JSON| API
    A2 -->|HTTPS and JSON| API
    A3 -->|HTTPS and JSON| API
    API --> VAL --> PROC --> DB
    UI -->|HTTPS| API
    API -->|JSON| UI
```

The agent never connects directly to the database, and the dashboard never connects directly to monitored devices. Telemetry passes through the backend API for authentication, validation, processing, and persistence.

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

| Layer | Technology |
|---|---|
| Windows Agent | Python and Windows Service APIs |
| Backend API | Python and Flask |
| Database | Supabase PostgreSQL |
| Frontend | React, TypeScript, and Vite |
| Frontend Hosting | Render Static Site |
| Backend Hosting | Render Web Service and Gunicorn |
| Transport | HTTPS and JSON |

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

## Environment Setup

Copy `.env.example` to `.env` for local development and configure the required values. Production secrets must be set through Render environment variables and must never be committed.

Install backend dependencies:

```powershell
pip install -r requirements.txt
```

## Run Locally

Backend:

```powershell
python app.py
```

Frontend:

```powershell
cd frontend
npm install
npm run dev
```

Manual Windows agent:

```powershell
python agent/collectors/monitoring_agent.py --console
```

## Windows Service

Run the installation command from an elevated Windows Command Prompt or PowerShell:

```bat
install_service.bat
```

Service controls:

```bat
start_service.bat
stop_service.bat
restart_service.bat
uninstall_service.bat
```

## Render Deployment

Backend Web Service:

```text
Root Directory: leave blank
Build Command: pip install -r requirements.txt
Start Command: python -m backend.render_start && gunicorn --bind 0.0.0.0:$PORT --workers 1 app:app
```

Frontend Static Site:

```text
Root Directory: frontend
Build Command: npm ci && npm run build
Publish Directory: dist
```

React routes require this Render rewrite rule:

```text
Source: /*
Destination: /index.html
Action: Rewrite
```

## Security

- Agent-to-backend and frontend-to-backend traffic uses HTTPS in production.
- Secrets are supplied through environment variables.
- Agent telemetry requests are authenticated.
- Dashboard access is protected by authentication and role checks.
- Administrative functions are restricted to appropriate roles.

## Current Limitations

| Feature | Status |
|---|---|
| AI Audit | Coming soon; its backend endpoint is not currently implemented |
| Monitoring modules | Operational |

## Roadmap

- [ ] Implement the AI Audit backend endpoint
- [ ] Expand automated report exports
- [ ] Add more granular role-based permissions
- [ ] Publish formal OpenAPI documentation
- [ ] Add configurable historical data-retention policies

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Installation](docs/INSTALLATION.md)
- [Setup](docs/SETUP.md)
- [Screenshot guidance](docs/screenshots/README.md)
