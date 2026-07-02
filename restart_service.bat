@echo off
setlocal
cd /d "%~dp0"
if not exist "logs" mkdir "logs"
call :resolve_python_exe
if errorlevel 1 exit /b 1

echo Restarting Asset Sentinel Monitoring Service...
"%PYTHON_EXE%" asset_sentinel_service.py --wait 30 stop
"%PYTHON_EXE%" asset_sentinel_service.py --wait 30 start
sc.exe query AssetSentinelMonitoringService | find "RUNNING" >nul
if errorlevel 1 goto :error

echo Asset Sentinel Monitoring Service restarted.
exit /b 0

:error
echo Failed to restart Asset Sentinel Monitoring Service. Run this script as Administrator.
exit /b 1

:resolve_python_exe
set "PYTHON_EXE="
for /f "delims=" %%P in ('powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0resolve_python_exe.ps1" 2^>nul') do if not defined PYTHON_EXE set "PYTHON_EXE=%%P"
if not defined PYTHON_EXE exit /b 1
echo Resolved Python interpreter: %PYTHON_EXE%
exit /b 0
