@echo off
setlocal

set "TASK_NAME=AssetSentinelActiveApplicationAgent"
set "RUN_KEY=HKCU\Software\Microsoft\Windows\CurrentVersion\Run"
set "RUN_VALUE=AssetSentinelActiveApplicationAgent"
set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "STARTUP_SCRIPT=%STARTUP_DIR%\AssetSentinelActiveApplicationAgent.vbs"
set "STARTUP_SHORTCUT=%STARTUP_DIR%\AssetSentinelActiveApplicationAgent.lnk"
set "WATCHDOG_SCRIPT=%~dp0logs\AssetSentinelActiveApplicationAgentWatchdog.vbs"

echo Stopping Asset Sentinel Active Application user-session agent if it is running...
call "%~dp0stop_active_app_agent.bat" >nul 2>&1

echo Removing Asset Sentinel Active Application user-session startup...
schtasks.exe /End /TN "%TASK_NAME%" >nul 2>&1
schtasks.exe /Delete /TN "%TASK_NAME%" /F >nul 2>&1
reg.exe delete "%RUN_KEY%" /v "%RUN_VALUE%" /f >nul 2>&1
if exist "%STARTUP_SCRIPT%" del /f /q "%STARTUP_SCRIPT%"
if exist "%STARTUP_SHORTCUT%" del /f /q "%STARTUP_SHORTCUT%"
if exist "%WATCHDOG_SCRIPT%" del /f /q "%WATCHDOG_SCRIPT%"
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$startup=Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Startup'; Remove-Item -LiteralPath (Join-Path $startup 'AssetSentinelActiveApplicationAgent.vbs') -Force -ErrorAction SilentlyContinue; Remove-Item -LiteralPath (Join-Path $startup 'AssetSentinelActiveApplicationAgent.lnk') -Force -ErrorAction SilentlyContinue"

echo Asset Sentinel Active Application user-session agent removed.
exit /b 0
