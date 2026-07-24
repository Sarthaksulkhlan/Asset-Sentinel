@echo off
setlocal
cd /d "%~dp0..\.."

echo Installing Asset Sentinel production startup...
if not exist ".env" (
  echo ERROR: .env file is missing. Configure .env before installing Asset Sentinel.
  exit /b 1
)
if not exist "logs" mkdir "logs"

call :validate_agent_env
if errorlevel 1 exit /b 1

call :resolve_python_exe
if errorlevel 1 goto :python_error

call :is_admin
if errorlevel 1 goto :admin_required

call :pair_device
if errorlevel 1 exit /b 1

echo Administrator rights detected. Installing Windows Service...
sc.exe query AssetSentinelMonitoringService >nul 2>&1
if not errorlevel 1 (
  echo Existing Asset Sentinel service found. Stopping and removing old registration...
  "%PYTHON_EXE%" agent\windows\asset_sentinel_service.py --wait 30 stop >nul 2>&1
  "%PYTHON_EXE%" agent\windows\asset_sentinel_service.py remove
  if errorlevel 1 goto :service_failed
  call :wait_service_removed
  if errorlevel 1 goto :service_failed
)

echo Installing latest Asset Sentinel Windows Agent service registration...
"%PYTHON_EXE%" agent\windows\asset_sentinel_service.py --startup delayed install
if errorlevel 1 goto :service_failed

sc.exe config AssetSentinelMonitoringService start= delayed-auto
sc.exe description AssetSentinelMonitoringService "Runs the Asset Sentinel Windows telemetry agent and sends endpoint telemetry to the Render backend."
sc.exe failure AssetSentinelMonitoringService reset= 86400 actions= restart/60000/restart/120000/restart/300000
sc.exe failureflag AssetSentinelMonitoringService 1

echo Starting Asset Sentinel Monitoring Service...
"%PYTHON_EXE%" agent\windows\asset_sentinel_service.py --wait 30 start
sc.exe query AssetSentinelMonitoringService | find "RUNNING" >nul
if errorlevel 1 goto :service_failed

call :install_active_agent
if errorlevel 1 goto :active_agent_warning

echo Asset Sentinel Windows Service, recovery policy, and user-session agent are installed.
exit /b 0

:active_agent_warning
echo WARNING: Backend service is running, but Active Application user-session install failed.
echo Run install_active_app_agent.bat from the monitored Windows user account.
exit /b 0

:service_failed
echo ERROR: Windows Service installation/start failed.
echo Review logs\service.log and rerun this script as Administrator.
exit /b 1

:admin_required
echo ERROR: Administrator rights are required to install the Windows Service.
echo Right-click install_service.bat and choose "Run as administrator".
exit /b 1

:install_active_agent
if exist "install_active_app_agent.bat" (
  call install_active_app_agent.bat
  exit /b %errorlevel%
)
exit /b 1

:python_error
echo Failed to resolve a real Python interpreter. Install Python and rerun this script.
exit /b 1

:validate_agent_env
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $envPath=Join-Path (Get-Location) '.env'; $values=@{}; Get-Content -LiteralPath $envPath -Encoding UTF8 | ForEach-Object { $line=$_.Trim(); if($line -and -not $line.StartsWith('#') -and $line.Contains('=')) { $parts=$line.Split('=',2); $values[$parts[0].Trim()]=$parts[1].Trim().Trim([char]34).Trim([char]39) } }; $api=($values['ASSET_SENTINEL_API_URL'] + '').TrimEnd('/'); $token=($values['ASSET_SENTINEL_AGENT_TOKEN'] + '').Trim(); if($api -ne 'https://asset-sentinel-backend.onrender.com') { throw 'ASSET_SENTINEL_API_URL must be https://asset-sentinel-backend.onrender.com' }; if([string]::IsNullOrWhiteSpace($token) -or $token -eq 'asset-sentinel-development-agent-token') { throw 'ASSET_SENTINEL_AGENT_TOKEN must be configured with the Render agent token' }; Write-Host 'Agent environment validated for Render backend.'"
if errorlevel 1 (
  echo ERROR: .env is not ready for the Render Windows Agent service.
  exit /b 1
)
exit /b 0

:pair_device
"%PYTHON_EXE%" agent\scripts\pair_device.py --status >nul 2>&1
if not errorlevel 1 (
  echo Device is already paired. Continuing installation.
  exit /b 0
)
echo ==================================
echo.
echo Asset Sentinel Device Pairing
echo.
set /p "PAIRING_CODE=Enter your 4-digit Pairing Code: "
echo.
echo ==================================
"%PYTHON_EXE%" agent\scripts\pair_device.py --otp "%PAIRING_CODE%"
set "PAIRING_CODE="
if errorlevel 1 (
  echo.
  echo Invalid or Expired Pairing Code.
  echo.
  echo Installation cancelled.
  exit /b 1
)
exit /b 0

:wait_service_removed
for /l %%I in (1,1,30) do (
  sc.exe query AssetSentinelMonitoringService >nul 2>&1
  if errorlevel 1 exit /b 0
  timeout /t 1 /nobreak >nul
)
echo ERROR: Existing service was not removed within 30 seconds.
exit /b 1

:resolve_python_exe
set "PYTHON_EXE="
for /f "delims=" %%P in ('powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%CD%\agent\windows\resolve_python_exe.ps1" 2^>nul') do if not defined PYTHON_EXE set "PYTHON_EXE=%%P"
if not defined PYTHON_EXE exit /b 1
echo Resolved Python interpreter: %PYTHON_EXE%
exit /b 0

:is_admin
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "exit ([int]-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator))" >nul 2>&1
exit /b %errorlevel%

