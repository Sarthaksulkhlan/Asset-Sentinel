@echo off
call "%~dp0agent\scripts\stop_active_app_agent.bat" %*
exit /b %errorlevel%

