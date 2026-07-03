@echo off
call "%~dp0agent\scripts\install_service.bat" %*
exit /b %errorlevel%

