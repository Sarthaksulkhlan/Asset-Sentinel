@echo off
setlocal
cd /d "%~dp0..\.."

echo Asset Sentinel Active Application Agent status
echo --------------------------------------------
reg.exe query "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v AssetSentinelActiveApplicationAgent
echo.
schtasks.exe /Query /TN AssetSentinelActiveApplicationAgent >nul 2>&1
if not errorlevel 1 (
  echo WARNING: stale Scheduled Task exists: AssetSentinelActiveApplicationAgent
)
if exist "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\AssetSentinelActiveApplicationAgent.vbs" (
  echo WARNING: stale Startup VBS exists.
)
if exist "logs\active_application_launcher.pid" (
  set /p LAUNCHER_PID=<"logs\active_application_launcher.pid"
  echo Launcher PID: %LAUNCHER_PID%
  powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "try { $p = Get-Process -Id %LAUNCHER_PID% -ErrorAction Stop; 'Launcher: RUNNING'; 'SessionId: ' + $p.SessionId; 'Started: ' + $p.StartTime } catch { 'Launcher: NOT RUNNING' }"
)
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

