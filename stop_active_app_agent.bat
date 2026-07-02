@echo off
setlocal
cd /d "%~dp0"

if not exist logs mkdir logs
echo stop>"logs\active_application_user_agent.stop"

powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='SilentlyContinue'; $root=(Get-Location).Path; $pidFiles=@('logs\active_application_user_agent.pid','logs\active_application_launcher.pid'); foreach($pidFile in $pidFiles){ $path=Join-Path $root $pidFile; if(Test-Path -LiteralPath $path){ $pidValue=[int]((Get-Content -LiteralPath $path -Raw).Trim()); Stop-Process -Id $pidValue -Force } }; Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like ('*' + $root + '*launch_active_app_agent.ps1*') -or $_.CommandLine -like ('*' + $root + '*active_application_user_agent.py*') } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
exit /b 0
