@echo off
call "%~dp0agent\scripts\stop_service.bat" %*
exit /b %errorlevel%

