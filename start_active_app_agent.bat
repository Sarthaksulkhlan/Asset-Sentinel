@echo off
call "%~dp0agent\scripts\start_active_app_agent.bat" %*
exit /b %errorlevel%

