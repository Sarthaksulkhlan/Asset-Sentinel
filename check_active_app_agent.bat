@echo off
setlocal
cd /d "%~dp0"

echo Asset Sentinel Active Application Agent status
echo --------------------------------------------
if exist "logs\active_application_user_agent.pid" (
  set /p AGENT_PID=<"logs\active_application_user_agent.pid"
  echo PID: %AGENT_PID%
  powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "try { $p = Get-Process -Id %AGENT_PID% -ErrorAction Stop; 'Process: RUNNING'; 'SessionId: ' + $p.SessionId; 'Started: ' + $p.StartTime } catch { 'Process: NOT RUNNING' }"
) else (
  echo PID file: missing
)

if exist "logs\active_application_user_agent_status.json" (
  echo.
  type "logs\active_application_user_agent_status.json"
) else (
  echo Status file: missing
)
