# Installation

## Admin PC

Run from the repository root in an elevated shell:

```bat
install_service.bat
```

This installs `AssetSentinelMonitoringService`, starts the backend service, configures automatic delayed start, and installs the active-application user-session helper when possible.

## Non-Admin PC

Run the backend manually:

```powershell
python backend/main.py
```

Start the frontend manually:

```powershell
cd frontend
npm run dev
```

Start the active-application user-session agent:

```bat
start_active_app_agent.bat
```

