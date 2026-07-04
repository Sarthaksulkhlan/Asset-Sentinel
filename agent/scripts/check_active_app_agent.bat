@echo off
setlocal
cd /d "%~dp0..\.."

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0check_active_app_agent.ps1"
exit /b %errorlevel%

