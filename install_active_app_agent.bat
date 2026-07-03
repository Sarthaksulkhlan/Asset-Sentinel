@echo off
call "%~dp0agent\scripts\install_active_app_agent.bat" %*
exit /b %errorlevel%

