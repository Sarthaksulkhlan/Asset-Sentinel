@echo off
call "%~dp0agent\scripts\uninstall_active_app_agent.bat" %*
exit /b %errorlevel%

