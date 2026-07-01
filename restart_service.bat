@echo off
setlocal
cd /d "%~dp0"
if not exist "logs" mkdir "logs"

echo Restarting Asset Sentinel Monitoring Service...
python asset_sentinel_service.py --wait 30 stop
python asset_sentinel_service.py --wait 30 start
sc.exe query AssetSentinelMonitoringService | find "RUNNING" >nul
if errorlevel 1 goto :error

echo Asset Sentinel Monitoring Service restarted.
exit /b 0

:error
echo Failed to restart Asset Sentinel Monitoring Service. Run this script as Administrator.
exit /b 1
