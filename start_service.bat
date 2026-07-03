@echo off
call "%~dp0agent\scripts\start_service.bat" %*
exit /b %errorlevel%

