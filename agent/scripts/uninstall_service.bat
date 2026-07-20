@echo off
setlocal
cd /d "%~dp0..\.."
call :resolve_python_exe
if errorlevel 1 exit /b 1

sc.exe query AssetSentinelMonitoringService >nul 2>&1
if errorlevel 1 (
  echo Asset Sentinel Monitoring Service is not installed.
  exit /b 0
)

echo Stopping Asset Sentinel Monitoring Service if it is running...
"%PYTHON_EXE%" agent\windows\asset_sentinel_service.py --wait 30 stop >nul 2>&1

echo Removing Asset Sentinel Monitoring Service...
"%PYTHON_EXE%" agent\windows\asset_sentinel_service.py remove
if errorlevel 1 goto :error
call :wait_service_removed
if errorlevel 1 goto :error

echo Asset Sentinel Monitoring Service removed.
exit /b 0

:error
echo Failed to uninstall Asset Sentinel Monitoring Service. Run this script as Administrator.
exit /b 1

:wait_service_removed
for /l %%I in (1,1,30) do (
  sc.exe query AssetSentinelMonitoringService >nul 2>&1
  if errorlevel 1 exit /b 0
  timeout /t 1 /nobreak >nul
)
echo ERROR: Service was not removed within 30 seconds.
exit /b 1

:resolve_python_exe
set "PYTHON_EXE="
for /f "delims=" %%P in ('powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%CD%\agent\windows\resolve_python_exe.ps1" 2^>nul') do if not defined PYTHON_EXE set "PYTHON_EXE=%%P"
if not defined PYTHON_EXE exit /b 1
echo Resolved Python interpreter: %PYTHON_EXE%
exit /b 0

