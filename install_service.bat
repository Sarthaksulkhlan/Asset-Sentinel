@echo off
setlocal
cd /d "%~dp0"

echo Installing Asset Sentinel production startup...
if not exist ".env" (
  echo ERROR: .env file is missing. Configure .env before installing Asset Sentinel.
  exit /b 1
)
if not exist "logs" mkdir "logs"

call :resolve_python_exe
if errorlevel 1 goto :python_error

call :is_admin
if errorlevel 1 goto :user_mode_install

echo Administrator rights detected. Installing Windows Service...
sc.exe query AssetSentinelMonitoringService >nul 2>&1
if errorlevel 1 (
  "%PYTHON_EXE%" asset_sentinel_service.py --startup delayed install
) else (
  echo Existing Asset Sentinel service found. Updating service registration...
  "%PYTHON_EXE%" asset_sentinel_service.py --startup delayed update
)
if errorlevel 1 goto :service_failed

sc.exe config AssetSentinelMonitoringService start= delayed-auto
sc.exe description AssetSentinelMonitoringService "Runs the Asset Sentinel/NEXIS backend API and supervised endpoint telemetry workers."
sc.exe failure AssetSentinelMonitoringService reset= 86400 actions= restart/60000/restart/120000/restart/300000
sc.exe failureflag AssetSentinelMonitoringService 1

echo Starting Asset Sentinel Monitoring Service...
"%PYTHON_EXE%" asset_sentinel_service.py --wait 30 start
sc.exe query AssetSentinelMonitoringService | find "RUNNING" >nul
if errorlevel 1 goto :service_failed

call :install_active_agent
if errorlevel 1 goto :active_agent_warning

echo Asset Sentinel Windows Service, recovery policy, and user-session agent are installed.
exit /b 0

:active_agent_warning
echo WARNING: Backend service is running, but Active Application user-session install failed.
echo Run install_active_app_agent.bat from the monitored Windows user account.
exit /b 0

:service_failed
echo WARNING: Windows Service installation/start failed. Falling back to user-mode startup.
goto :user_mode_install

:user_mode_install
echo Installing user-mode Active Application agent fallback...
call :install_active_agent
if errorlevel 1 (
  echo ERROR: User-mode Active Application agent installation failed.
  exit /b 1
)
echo User-mode fallback installed.
echo Start the backend manually with:
echo   "%PYTHON_EXE%" app.py
echo All monitoring workers will run inside that interactive backend process.
exit /b 0

:install_active_agent
if exist "install_active_app_agent.bat" (
  call install_active_app_agent.bat
  exit /b %errorlevel%
)
exit /b 1

:python_error
echo Failed to resolve a real Python interpreter. Install Python and rerun this script.
exit /b 1

:resolve_python_exe
set "PYTHON_EXE="
for /f "delims=" %%P in ('powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0resolve_python_exe.ps1" 2^>nul') do if not defined PYTHON_EXE set "PYTHON_EXE=%%P"
if not defined PYTHON_EXE exit /b 1
echo Resolved Python interpreter: %PYTHON_EXE%
exit /b 0

:is_admin
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "exit ([int]-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator))" >nul 2>&1
exit /b %errorlevel%
