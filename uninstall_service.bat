@echo off
setlocal
cd /d "%~dp0"

echo Stopping Asset Sentinel Monitoring Service if it is running...
python asset_sentinel_service.py --wait 30 stop

echo Removing Asset Sentinel Monitoring Service...
python asset_sentinel_service.py remove
if errorlevel 1 goto :error

echo Asset Sentinel Monitoring Service removed.
exit /b 0

:error
echo Failed to uninstall Asset Sentinel Monitoring Service. Run this script as Administrator.
exit /b 1
