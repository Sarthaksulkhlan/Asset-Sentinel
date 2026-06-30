@echo off
setlocal
cd /d "%~dp0"
set TASK_NAME=AssetSentinelActiveApplicationAgent
schtasks.exe /End /TN "%TASK_NAME%"
if not exist logs mkdir logs
echo stop>"logs\active_application_user_agent.stop"
