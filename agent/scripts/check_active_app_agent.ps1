$ErrorActionPreference = "Continue"

$RepoDir = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$RunKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
$RunValue = "AssetSentinelActiveApplicationAgent"
$LauncherScript = Join-Path $RepoDir "launch_active_app_agent.ps1"
$AgentScript = Join-Path $RepoDir "agent\collectors\active_application_user_agent.py"
$ResolverScript = Join-Path $RepoDir "agent\windows\resolve_python_exe.ps1"
$LogsDir = Join-Path $RepoDir "logs"
$LauncherPidFile = Join-Path $LogsDir "active_application_launcher.pid"
$AgentPidFile = Join-Path $LogsDir "active_application_user_agent.pid"
$StatusFile = Join-Path $LogsDir "active_application_user_agent_status.json"
$StartupDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup"
$StartupScript = Join-Path $StartupDir "AssetSentinelActiveApplicationAgent.vbs"
$StartupShortcut = Join-Path $StartupDir "AssetSentinelActiveApplicationAgent.lnk"
$ExpectedRunCommand = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "' + $LauncherScript + '"'
$Failures = 0

function Write-Check {
    param(
        [string]$Name,
        [bool]$Passed,
        [string]$Detail = ""
    )

    if ($Passed) {
        Write-Host "[OK]   $Name"
    } else {
        Write-Host "[FAIL] $Name"
        $script:Failures += 1
    }

    if (-not [string]::IsNullOrWhiteSpace($Detail)) {
        Write-Host "       $Detail"
    }
}

function Normalize-Path {
    param([string]$Path)

    if ([string]::IsNullOrWhiteSpace($Path)) {
        return ""
    }

    try {
        return [System.IO.Path]::GetFullPath([Environment]::ExpandEnvironmentVariables($Path.Trim('"'))).TrimEnd('\')
    } catch {
        return $Path.Trim('"').TrimEnd('\')
    }
}

function Test-ContainsPath {
    param(
        [string]$CommandLine,
        [string]$Path
    )

    if ([string]::IsNullOrWhiteSpace($CommandLine) -or [string]::IsNullOrWhiteSpace($Path)) {
        return $false
    }

    return $CommandLine.IndexOf($Path, [System.StringComparison]::OrdinalIgnoreCase) -ge 0
}
