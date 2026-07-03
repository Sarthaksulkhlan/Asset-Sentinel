@echo off
call "%~dp0agent\scripts\check_active_app_agent.bat" %*
exit /b %errorlevel%

