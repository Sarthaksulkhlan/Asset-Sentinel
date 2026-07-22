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
| **What it sees** | Device identity, hardware, users, login and unlock events, foreground applications, idle time, and heartbeat health. |
| **What it answers** | Which endpoints are alive, who is signed in, what is active, how time is distributed, and whether hardware state has changed. |
| **Why it is different** | Event-driven telemetry and explicit heartbeats replace periodic scans and manually maintained asset registers. |
| **Who it is for** | IT operations, endpoint security, support teams, and organization administrators responsible for Windows fleets. |
| **Trust boundary** | Agents and the dashboard communicate through one authenticated backend API; neither connects directly to the database or to each other. |
| **Production shape** | Windows agent + Flask/Gunicorn backend + Supabase PostgreSQL + React/Vite frontend, deployed through Render. |

> [Open the live demo](https://assetsentinel.onrender.com/demo) to explore Asset Sentinel with demonstration data.

## The Problem

Traditional asset registers and periodic inventory scans provide an outdated picture of a Windows fleet. They cannot reliably answer who is currently signed in, which application is active, whether a device is still online, or whether its hardware has changed since the last audit.

Asset Sentinel continuously captures session, application, hardware, and liveness events from managed endpoints. The dashboard reflects the fleet's current state instead of its last scheduled scan.

<div align="center">

<img src="docs/screenshots/asset-sentinel-visibility.png" alt="Stale endpoint snapshots compared with live Asset Sentinel signals" width="100%"/>

<sub><em>Periodic inventory leaves hardware changes, missed heartbeats, and session activity hidden. Asset Sentinel turns those gaps into live, attributable signals.</em></sub>

</div>

## Why Asset Sentinel

| Traditional fleet visibility | Asset Sentinel |
|---|---|
| Inventory updated when someone runs a scan | Telemetry updated continuously from the endpoint |
| Online state inferred from an old record | Explicit heartbeat establishes current liveness |
| Hardware stored as a static specification | Hardware identity can be compared over time |
| Application usage reconstructed from assumptions | Foreground, active, idle, and locked time come from measured events |
| Monitoring, alerts, and support live in separate tools | The same telemetry supports dashboards, alerts, reports, and tickets |
| Fleet totals hide the evidence behind them | Operators can move from fleet overview to device-level activity |

## Key Features

| Category | Capability |
|---|---|
| Real-Time Telemetry | Continuous heartbeat stream from registered endpoints |
| Session Intelligence | Login, logout, lock, and unlock activity per device and user |
| Application Monitoring | Active-window detection and per-application usage duration |
| Productivity Analytics | Active, idle, locked, and productive time derived from telemetry |
| Hardware Inventory | Hardware cataloging and change detection |
| Device Monitoring | Online/offline state and detailed endpoint information |
| Alerts and Reports | Fleet and device-level conditions presented for review |
| Support Tickets | Ticketing connected to organization and device context |
| Super Admin | Platform-level company and fleet administration |

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

## Dashboard Modules

- Real-Time Fleet Telemetry
- Device Monitoring
- Productivity Analytics
- Login Activity
- Active Application Timeline
- Application Usage
- Hardware and security alerts
- Reports
- Support Tickets
- Super Admin Dashboard

## Windows Monitoring Agent

The agent runs on monitored Windows endpoints and reports:

| Data | Description |
|---|---|
| Login Activity | Genuine Windows login and unlock events |
| Logout Activity | Logout, lock, and disconnect transitions |
| Active Applications | Current foreground application |
| Application Usage | Time spent in monitored applications |
| Productivity | Active, idle, and locked time |
| Hardware Inventory | Device specifications and identifiers |
| Heartbeat | Periodic device liveness signal |
| Device Information | Host, user, network, and operating-system metadata |

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
