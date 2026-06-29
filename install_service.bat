@echo off
setlocal
cd /d "%~dp0"

echo Installing Asset Sentinel Monitoring Service...
python asset_sentinel_service.py --startup delayed install
sc.exe query AssetSentinelMonitoringService >nul 2>&1
if errorlevel 1 goto :error

sc.exe config AssetSentinelMonitoringService start= delayed-auto
sc.exe description AssetSentinelMonitoringService "Collects Asset Sentinel endpoint telemetry and uploads it to Neon PostgreSQL."
sc.exe failure AssetSentinelMonitoringService reset= 86400 actions= restart/60000/restart/120000/restart/300000
sc.exe failureflag AssetSentinelMonitoringService 1

echo Starting Asset Sentinel Monitoring Service...
python asset_sentinel_service.py --wait 30 start
sc.exe query AssetSentinelMonitoringService | find "RUNNING" >nul
if errorlevel 1 goto :error

echo Asset Sentinel Monitoring Service installed and started.
exit /b 0

:error
echo Failed to install or start Asset Sentinel Monitoring Service. Run this script as Administrator.
exit /b 1
