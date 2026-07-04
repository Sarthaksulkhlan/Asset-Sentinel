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

function Get-PidFromFile {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        return $null
    }

    try {
        $text = (Get-Content -LiteralPath $Path -Raw).Trim()
        if ($text) {
            return [int]$text
        }
    } catch {
        return $null
    }

    return $null
}

function Get-ProcessInfo {
    param([Nullable[int]]$ProcessId)

    if (-not $ProcessId) {
        return $null
    }

    try {
        return Get-CimInstance Win32_Process -Filter "ProcessId=$ProcessId"
    } catch {
        return $null
    }
}

Write-Host "Asset Sentinel Active Application Agent status"
Write-Host "--------------------------------------------"

$runCommand = $null
try {
    $runCommand = (Get-ItemProperty -Path $RunKey -Name $RunValue -ErrorAction Stop).$RunValue
} catch {
    $runCommand = $null
}

Write-Check "HKCU Run startup registration exists" (-not [string]::IsNullOrWhiteSpace($runCommand)) $RunValue
Write-Check "HKCU Run command uses the expected launcher script" ($runCommand -eq $ExpectedRunCommand) "Actual: $runCommand"

schtasks.exe /Query /TN $RunValue *> $null
Write-Check "No stale scheduled task startup remains" ($LASTEXITCODE -ne 0) "Task name: $RunValue"

Write-Check "No stale Startup folder VBS remains" (-not (Test-Path -LiteralPath $StartupScript)) $StartupScript
Write-Check "No stale Startup folder shortcut remains" (-not (Test-Path -LiteralPath $StartupShortcut)) $StartupShortcut

$resolvedPython = $null
try {
    $resolvedPython = (& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $ResolverScript | Select-Object -First 1)
} catch {
    $resolvedPython = $null
}

Write-Check "Python resolver returns a real executable" ((-not [string]::IsNullOrWhiteSpace($resolvedPython)) -and (Test-Path -LiteralPath $resolvedPython -PathType Leaf)) $resolvedPython

$launcherPid = Get-PidFromFile $LauncherPidFile
$launcherProcess = Get-ProcessInfo $launcherPid
Write-Check "Launcher PID file exists" ($null -ne $launcherPid) $LauncherPidFile
Write-Check "Launcher process is running" ($null -ne $launcherProcess) "PID: $launcherPid"
if ($launcherProcess) {
    Write-Check "Launcher process runs in an interactive session" ([int]$launcherProcess.SessionId -gt 0) "SessionId: $($launcherProcess.SessionId)"
    Write-Check "Launcher command uses the expected script path" (Test-ContainsPath $launcherProcess.CommandLine $LauncherScript) $launcherProcess.CommandLine
}
