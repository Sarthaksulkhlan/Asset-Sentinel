@echo off
setlocal
cd /d "%~dp0"
call :resolve_python_exe
if errorlevel 1 exit /b 1
"%PYTHON_EXE%" asset_sentinel_service.py --wait 30 stop
exit /b %errorlevel%

:resolve_python_exe
set "PYTHON_EXE="
for /f "delims=" %%P in ('powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0resolve_python_exe.ps1" 2^>nul') do if not defined PYTHON_EXE set "PYTHON_EXE=%%P"
if not defined PYTHON_EXE exit /b 1
echo Resolved Python interpreter: %PYTHON_EXE%
exit /b 0
