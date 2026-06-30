@echo off
setlocal

set TASK_NAME=AssetSentinelActiveApplicationAgent
set RUN_KEY=HKCU\Software\Microsoft\Windows\CurrentVersion\Run
set "STARTUP_SCRIPT=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\AssetSentinelActiveApplicationAgent.vbs"

echo Stopping Asset Sentinel Active Application user-session agent if it is running...
call "%~dp0stop_active_app_agent.bat" >nul 2>&1

echo Removing Asset Sentinel Active Application user-session agent...
schtasks.exe /Delete /TN "%TASK_NAME%" /F >nul 2>&1
reg.exe delete "%RUN_KEY%" /v AssetSentinelActiveApplicationAgent /f >nul 2>&1
if exist "%STARTUP_SCRIPT%" del "%STARTUP_SCRIPT%"

echo Asset Sentinel Active Application user-session agent removed.
exit /b 0
