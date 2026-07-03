@echo off
setlocal
cd /d "%~dp0..\.."
call :resolve_python_exe
if errorlevel 1 exit /b 1

echo Stopping Asset Sentinel Monitoring Service if it is running...
"%PYTHON_EXE%" agent\windows\asset_sentinel_service.py --wait 30 stop

echo Removing Asset Sentinel Monitoring Service...
"%PYTHON_EXE%" agent\windows\asset_sentinel_service.py remove
if errorlevel 1 goto :error

echo Asset Sentinel Monitoring Service removed.
exit /b 0

:error
echo Failed to uninstall Asset Sentinel Monitoring Service. Run this script as Administrator.
exit /b 1

:resolve_python_exe
set "PYTHON_EXE="
for /f "delims=" %%P in ('powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%CD%\agent\windows\resolve_python_exe.ps1" 2^>nul') do if not defined PYTHON_EXE set "PYTHON_EXE=%%P"
if not defined PYTHON_EXE exit /b 1
echo Resolved Python interpreter: %PYTHON_EXE%
exit /b 0

