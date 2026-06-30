@echo off
setlocal
cd /d "%~dp0"
if exist "logs\active_application_user_agent.stop" del "logs\active_application_user_agent.stop"

set TASK_NAME=AssetSentinelActiveApplicationAgent
schtasks.exe /Run /TN "%TASK_NAME%"
if not errorlevel 1 exit /b 0

set "PYTHON_EXE="
for /f "delims=" %%P in ('where python.exe 2^>nul') do if not defined PYTHON_EXE set "PYTHON_EXE=%%P"
if not defined PYTHON_EXE set "PYTHON_EXE=python"
set "AGENT_SCRIPT=%CD%\active_application_user_agent.py"
start "Asset Sentinel Active Application Agent" /min "%PYTHON_EXE%" "%AGENT_SCRIPT%"
if not errorlevel 1 exit /b 0

set "STARTUP_SCRIPT=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\AssetSentinelActiveApplicationAgent.vbs"
if exist "%STARTUP_SCRIPT%" wscript.exe "%STARTUP_SCRIPT%"
