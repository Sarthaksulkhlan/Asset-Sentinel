@echo off
setlocal
cd /d "%~dp0"

set "LAUNCHER_SCRIPT=%CD%\launch_active_app_agent.ps1"
if exist "logs\active_application_user_agent.stop" del "logs\active_application_user_agent.stop"

if not exist "%LAUNCHER_SCRIPT%" (
  echo ERROR: Active Application launcher not found: "%LAUNCHER_SCRIPT%"
  exit /b 1
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%LAUNCHER_SCRIPT%" -ValidateOnly
if errorlevel 1 exit /b 1

start "" powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%LAUNCHER_SCRIPT%"
exit /b %errorlevel%
