@echo off
setlocal
cd /d "%~dp0..\.."

set "TASK_NAME=AssetSentinelActiveApplicationAgent"
set "RUN_KEY=HKCU\Software\Microsoft\Windows\CurrentVersion\Run"
set "RUN_VALUE=AssetSentinelActiveApplicationAgent"
set "LAUNCHER_SCRIPT=%CD%\launch_active_app_agent.ps1"
set "AGENT_SCRIPT=%CD%\agent\collectors\active_application_user_agent.py"
set "WATCHDOG_SCRIPT=%CD%\logs\AssetSentinelActiveApplicationAgentWatchdog.vbs"
set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "STARTUP_SCRIPT=%STARTUP_DIR%\AssetSentinelActiveApplicationAgent.vbs"
set "STARTUP_SHORTCUT=%STARTUP_DIR%\AssetSentinelActiveApplicationAgent.lnk"
if not defined VERIFY_SECONDS set "VERIFY_SECONDS=600"

echo Installing Asset Sentinel Active Application user-session agent...
if not exist "logs" mkdir "logs"
if exist "logs\active_application_user_agent.stop" del "logs\active_application_user_agent.stop"

call :resolve_python_exe
if errorlevel 1 goto :python_error

call :remove_stale_startup
if errorlevel 1 goto :error

call :validate_launcher
if errorlevel 1 goto :validation_error

set "RUN_CMD=powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File ""%LAUNCHER_SCRIPT%"""
reg.exe add "%RUN_KEY%" /v "%RUN_VALUE%" /t REG_SZ /d "%RUN_CMD%" /f >nul
if errorlevel 1 goto :error

echo Starting Active Application launcher...
start "" powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%LAUNCHER_SCRIPT%"
if errorlevel 1 goto :error

call :verify_agent
if errorlevel 1 goto :verify_error

echo Asset Sentinel Active Application user-session agent installed.
echo Startup mechanism: HKCU Run value "%RUN_VALUE%".
exit /b 0

:remove_stale_startup
echo Removing stale Active Application startup mechanisms...
schtasks.exe /End /TN "%TASK_NAME%" >nul 2>&1
schtasks.exe /Delete /TN "%TASK_NAME%" /F >nul 2>&1
reg.exe delete "%RUN_KEY%" /v "%RUN_VALUE%" /f >nul 2>&1
if exist "%STARTUP_SCRIPT%" del /f /q "%STARTUP_SCRIPT%"
if exist "%STARTUP_SHORTCUT%" del /f /q "%STARTUP_SHORTCUT%"
if exist "%WATCHDOG_SCRIPT%" del /f /q "%WATCHDOG_SCRIPT%"
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$startup=Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Startup'; Remove-Item -LiteralPath (Join-Path $startup 'AssetSentinelActiveApplicationAgent.vbs') -Force -ErrorAction SilentlyContinue; Remove-Item -LiteralPath (Join-Path $startup 'AssetSentinelActiveApplicationAgent.lnk') -Force -ErrorAction SilentlyContinue"
exit /b 0

:validate_launcher
if not exist "%LAUNCHER_SCRIPT%" (
  echo ERROR: Active Application launcher not found: "%LAUNCHER_SCRIPT%"
  exit /b 1
)
if not exist "%AGENT_SCRIPT%" (
  echo ERROR: Active Application agent not found: "%AGENT_SCRIPT%"
  exit /b 1
)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%LAUNCHER_SCRIPT%" -ValidateOnly
exit /b %errorlevel%

:verify_agent
echo Verifying Active Application agent remains alive for %VERIFY_SECONDS% seconds...
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $deadline=(Get-Date).AddSeconds([int]$env:VERIFY_SECONDS); $pidFile=Join-Path (Get-Location) 'logs\active_application_user_agent.pid'; $seen=$false; while((Get-Date) -lt $deadline){ if(Test-Path -LiteralPath $pidFile){ try { $agentPid=[int]((Get-Content -LiteralPath $pidFile -Raw).Trim()) } catch { Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue; Start-Sleep -Seconds 2; continue }; $p=Get-Process -Id $agentPid -ErrorAction SilentlyContinue; if($p){ $seen=$true; Start-Sleep -Seconds 5; continue }; Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue }; Start-Sleep -Seconds 2 }; if(-not $seen){ throw 'Active Application agent did not create a live PID during verification.' }; 'Active Application agent remained alive through verification.'"
exit /b %errorlevel%

:error
echo ERROR: Failed to install or start Asset Sentinel Active Application user-session agent.
exit /b 1

:validation_error
echo ERROR: Active Application launcher validation failed. Installation aborted.
exit /b 1

:verify_error
echo ERROR: Active Application agent did not remain alive during verification. See logs\agent.log, logs\error.log, and logs\active_application_launcher.log.
exit /b 1

:python_error
echo ERROR: Failed to resolve a real Python interpreter. Install Python and rerun this script.
exit /b 1

:resolve_python_exe
set "PYTHON_EXE="
for /f "delims=" %%P in ('powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%CD%\agent\windows\resolve_python_exe.ps1" 2^>nul') do if not defined PYTHON_EXE set "PYTHON_EXE=%%P"
if not defined PYTHON_EXE exit /b 1
echo Resolved Python interpreter: %PYTHON_EXE%
exit /b 0

