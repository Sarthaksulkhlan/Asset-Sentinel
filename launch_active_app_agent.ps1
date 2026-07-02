param(
    [switch]$ValidateOnly
)

$ErrorActionPreference = "Stop"

$RepoDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$LogsDir = Join-Path $RepoDir "logs"
$AgentScript = Join-Path $RepoDir "active_application_user_agent.py"
$ResolverScript = Join-Path $RepoDir "resolve_python_exe.ps1"
$StopFile = Join-Path $LogsDir "active_application_user_agent.stop"
$AgentPidFile = Join-Path $LogsDir "active_application_user_agent.pid"
$LauncherPidFile = Join-Path $LogsDir "active_application_launcher.pid"
$LauncherLog = Join-Path $LogsDir "active_application_launcher.log"
$StdoutLog = Join-Path $LogsDir "active_application_stdout.log"
$StderrLog = Join-Path $LogsDir "active_application_stderr.log"

function Write-LauncherLog {
    param([string]$Message)

    if (-not (Test-Path -LiteralPath $LogsDir)) {
        New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null
    }

    $timestamp = (Get-Date).ToString("o")
    Add-Content -LiteralPath $LauncherLog -Encoding UTF8 -Value "$timestamp $Message"
}

function Resolve-PythonExe {
    if (-not (Test-Path -LiteralPath $ResolverScript -PathType Leaf)) {
        throw "Python resolver not found: $ResolverScript"
    }

    $python = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $ResolverScript |
        Select-Object -First 1
    if ([string]::IsNullOrWhiteSpace($python)) {
        throw "Could not resolve a real Python interpreter."
    }
    if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
        throw "Resolved Python interpreter does not exist: $python"
    }
    return $python
}

function Test-ProcessAlive {
    param([int]$ProcessId)

    if ($ProcessId -le 0) {
        return $false
    }

    try {
        Get-Process -Id $ProcessId -ErrorAction Stop | Out-Null
        return $true
    } catch {
        return $false
    }
}

function Get-ExistingAgentPid {
    if (-not (Test-Path -LiteralPath $AgentPidFile -PathType Leaf)) {
        return $null
    }

    try {
        $pidText = (Get-Content -LiteralPath $AgentPidFile -Raw).Trim()
        if (-not $pidText) {
            return $null
        }
        $agentPid = [int]$pidText
        if (Test-ProcessAlive $agentPid) {
            return $agentPid
        }
    } catch {
        Write-LauncherLog "Ignoring stale or unreadable agent PID file: $($_.Exception.Message)"
    }

    Remove-Item -LiteralPath $AgentPidFile -Force -ErrorAction SilentlyContinue
    return $null
}

if (-not (Test-Path -LiteralPath $AgentScript -PathType Leaf)) {
    throw "Active Application agent script not found: $AgentScript"
}

if (-not (Test-Path -LiteralPath $LogsDir)) {
    New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null
}

$pythonExe = Resolve-PythonExe

if ($ValidateOnly) {
    & $pythonExe -m py_compile $AgentScript
    if ($LASTEXITCODE -ne 0) {
        throw "Python validation failed for $AgentScript"
    }
    Write-Output "Active Application launcher validation succeeded. Python: $pythonExe"
    exit 0
}

if (Test-Path -LiteralPath $LauncherPidFile -PathType Leaf) {
    try {
        $existingLauncherPid = [int]((Get-Content -LiteralPath $LauncherPidFile -Raw).Trim())
        if ($existingLauncherPid -ne $PID -and (Test-ProcessAlive $existingLauncherPid)) {
            Write-LauncherLog "Launcher already running. existing_pid=$existingLauncherPid current_pid=$PID"
            exit 0
        }
    } catch {
        Write-LauncherLog "Ignoring stale or unreadable launcher PID file: $($_.Exception.Message)"
    }
}

Set-Content -LiteralPath $LauncherPidFile -Encoding UTF8 -Value $PID
Remove-Item -LiteralPath $StopFile -Force -ErrorAction SilentlyContinue
Write-LauncherLog "Launcher startup. pid=$PID repo=$RepoDir"

try {
    while (-not (Test-Path -LiteralPath $StopFile -PathType Leaf)) {
        $existingAgentPid = Get-ExistingAgentPid
        if ($existingAgentPid) {
            Write-LauncherLog "Agent already running. pid=$existingAgentPid"
            Start-Sleep -Seconds 10
            continue
        }

        $pythonExe = Resolve-PythonExe
        Write-LauncherLog "Starting agent. python=$pythonExe script=$AgentScript"
        $process = Start-Process `
            -FilePath $pythonExe `
            -ArgumentList @($AgentScript) `
            -WorkingDirectory $RepoDir `
            -WindowStyle Hidden `
            -RedirectStandardOutput $StdoutLog `
            -RedirectStandardError $StderrLog `
            -PassThru

        Write-LauncherLog "Agent process started. pid=$($process.Id)"
        $process.WaitForExit()
        Write-LauncherLog "Agent process exited. pid=$($process.Id) exit_code=$($process.ExitCode)"

        if (Test-Path -LiteralPath $StopFile -PathType Leaf) {
            Write-LauncherLog "Stop file detected; launcher shutdown requested."
            break
        }

        Write-LauncherLog "Restarting agent after unexpected exit in 5 seconds."
        Start-Sleep -Seconds 5
    }
} catch {
    Write-LauncherLog "Launcher exception: $($_.Exception.Message)"
    throw
} finally {
    Write-LauncherLog "Launcher shutdown. pid=$PID"
    Remove-Item -LiteralPath $LauncherPidFile -Force -ErrorAction SilentlyContinue
}
