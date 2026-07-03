# Architecture

Asset Sentinel is organized as four runtime areas:

- `backend/`: Flask API, auth, database access, SQLAlchemy models, logging, and startup health.
- `agent/`: Windows telemetry collection, hardware/login/activity collectors, change detectors, service code, and launch scripts.
- `frontend/`: React/Vite dashboard, kept in its existing structure.
- `database/`: PostgreSQL schema, migrations, and historical JSON backup/report files.

The backend entry point is `backend/main.py`. Root `app.py` remains as a compatibility wrapper.

The Windows service entry point is `agent/windows/asset_sentinel_service.py`. Root service scripts remain as compatibility wrappers and delegate to `agent/scripts/`.

Logs and `.env` remain rooted at the repository root to preserve existing runtime behavior.

