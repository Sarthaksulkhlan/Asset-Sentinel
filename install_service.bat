@echo off
setlocal
cd /d "%~dp0"

echo Installing Asset Sentinel Monitoring Service...
if not exist ".env" (
  echo ERROR: .env file is missing. Configure .env before installing the service.
  exit /b 1
)
if not exist "logs" mkdir "logs"
sc.exe query AssetSentinelMonitoringService >nul 2>&1
if errorlevel 1 (
  python asset_sentinel_service.py --startup delayed install
) else (
  echo Existing Asset Sentinel service found. Updating service registration...
  python asset_sentinel_service.py --startup delayed update
)
sc.exe query AssetSentinelMonitoringService >nul 2>&1
if errorlevel 1 goto :error

sc.exe config AssetSentinelMonitoringService start= delayed-auto
sc.exe description AssetSentinelMonitoringService "Runs the Asset Sentinel/NEXIS backend API and supervised endpoint telemetry workers."
sc.exe failure AssetSentinelMonitoringService reset= 86400 actions= restart/60000/restart/120000/restart/300000
sc.exe failureflag AssetSentinelMonitoringService 1

echo Starting Asset Sentinel Monitoring Service...
python asset_sentinel_service.py --wait 30 start
sc.exe query AssetSentinelMonitoringService | find "RUNNING" >nul
if errorlevel 1 goto :error

if exist "install_active_app_agent.bat" (
  echo Installing Active Application user-session helper...
  call install_active_app_agent.bat
  if errorlevel 1 echo WARNING: Active Application helper install failed. Backend service is still installed; run install_active_app_agent.bat from the monitored Windows user session.
)

echo Asset Sentinel Monitoring Service installed and started.
exit /b 0

:error
echo Failed to install or start Asset Sentinel Monitoring Service. Run this script as Administrator.
exit /b 1
