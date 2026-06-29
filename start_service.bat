@echo off
setlocal
cd /d "%~dp0"
python asset_sentinel_service.py --wait 30 start
