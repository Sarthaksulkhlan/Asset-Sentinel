@echo off
call "%~dp0agent\scripts\uninstall_service.bat" %*
exit /b %errorlevel%

