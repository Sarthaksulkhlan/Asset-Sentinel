@echo off
setlocal
cd /d "%~dp0"

set TASK_NAME=AssetSentinelActiveApplicationAgent
set RUN_KEY=HKCU\Software\Microsoft\Windows\CurrentVersion\Run
set "PYTHON_EXE="
for /f "delims=" %%P in ('where python.exe 2^>nul') do if not defined PYTHON_EXE set "PYTHON_EXE=%%P"
if not defined PYTHON_EXE set "PYTHON_EXE=python"
set "AGENT_SCRIPT=%CD%\active_application_user_agent.py"
set "TASK_CMD=\"%PYTHON_EXE%\" \"%AGENT_SCRIPT%\""

echo Installing Asset Sentinel Active Application user-session agent...
schtasks.exe /Create /TN "%TASK_NAME%" /SC ONLOGON /TR "%TASK_CMD%" /RL LIMITED /IT /F
if errorlevel 1 (
  echo Interactive Scheduled Task install failed. Retrying as current-user ONLOGON task...
  schtasks.exe /Create /TN "%TASK_NAME%" /SC ONLOGON /TR "%TASK_CMD%" /RL LIMITED /F
)
if errorlevel 1 goto :per_user_fallback

echo Starting Asset Sentinel Active Application user-session agent...
schtasks.exe /Run /TN "%TASK_NAME%"
if errorlevel 1 goto :per_user_fallback

echo Asset Sentinel Active Application user-session agent installed and started.
exit /b 0

:per_user_fallback
echo Scheduled Task install failed. Installing current-user auto-start fallback...
reg.exe add "%RUN_KEY%" /v AssetSentinelActiveApplicationAgent /t REG_SZ /d "%TASK_CMD%" /f
if errorlevel 1 goto :startup_fallback
echo Current-user Run key installed. The agent will start in the real desktop at next logon.
goto :startup_fallback

:startup_fallback
set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "STARTUP_SCRIPT=%STARTUP_DIR%\AssetSentinelActiveApplicationAgent.vbs"
if not exist "%STARTUP_DIR%" mkdir "%STARTUP_DIR%"
(
  echo Set shell = CreateObject^("WScript.Shell"^)
  echo shell.CurrentDirectory = "%CD%"
  echo shell.Run """%PYTHON_EXE%"" ""%AGENT_SCRIPT%""", 0, False
) > "%STARTUP_SCRIPT%"
if errorlevel 1 goto :error

echo Asset Sentinel Active Application user-session agent installed via Startup launcher.
echo Sign out and sign back in to start it inside the real interactive desktop.
exit /b 0

:error
echo Failed to install or start Asset Sentinel Active Application user-session agent.
exit /b 1
