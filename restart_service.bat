@echo off
call "%~dp0agent\scripts\restart_service.bat" %*
exit /b %errorlevel%

