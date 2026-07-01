@echo off
setlocal
cd /d "%~dp0"
if not exist "logs" mkdir "logs"
python asset_sentinel_service.py --wait 30 start
