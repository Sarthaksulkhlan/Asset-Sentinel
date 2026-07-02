$ErrorActionPreference = "SilentlyContinue"

function Test-RealPython {
    param([string]$Path)

    if ([string]::IsNullOrWhiteSpace($Path)) {
        return $null
    }

    $resolved = [Environment]::ExpandEnvironmentVariables($Path.Trim('"'))
    if ($resolved -like "*\Microsoft\WindowsApps\python.exe") {
        return $null
    }
    if (-not (Test-Path -LiteralPath $resolved -PathType Leaf)) {
        return $null
    }

    try {
        $probe = & $resolved -c "import os, sys; print(os.path.realpath(sys.executable))" 2>$null
        $probe = ($probe | Select-Object -First 1).Trim()
        if ($probe -and
            $probe -notlike "*\Microsoft\WindowsApps\python.exe" -and
            (Test-Path -LiteralPath $probe -PathType Leaf)) {
            return $probe
        }
    } catch {
        return $null
    }

    return $null
}

function Invoke-PythonLauncher {
    param(
        [string]$Command,
        [string[]]$Arguments
    )

    try {
        $probeScript = "import os, sys; print(os.path.realpath(sys.executable))"
        $output = & $Command @Arguments -c $probeScript 2>$null
        $candidate = ($output | Select-Object -First 1).Trim()
        return Test-RealPython $candidate
    } catch {
        return $null
    }
}

$python = Invoke-PythonLauncher "python" @()
if ($python) {
    Write-Output $python
    exit 0
}

$python = Invoke-PythonLauncher "py" @("-3")
if ($python) {
    Write-Output $python
    exit 0
}

$python = Invoke-PythonLauncher "py" @()
if ($python) {
    Write-Output $python
    exit 0
}

$registryRoots = @(
    "HKCU:\Software\Python\PythonCore",
    "HKLM:\Software\Python\PythonCore",
    "HKLM:\Software\WOW6432Node\Python\PythonCore"
)

foreach ($root in $registryRoots) {
    if (-not (Test-Path $root)) {
        continue
    }

    foreach ($versionKey in Get-ChildItem $root) {
        $installPathKey = Join-Path $versionKey.PSPath "InstallPath"
        if (-not (Test-Path $installPathKey)) {
            continue
        }

        $installPath = Get-ItemProperty $installPathKey
        foreach ($candidate in @($installPath.ExecutablePath, (Join-Path $installPath."(default)" "python.exe"))) {
            $python = Test-RealPython $candidate
            if ($python) {
                Write-Output $python
                exit 0
            }
        }
    }
}

$installPatterns = @(
    (Join-Path $env:LOCALAPPDATA "Python\pythoncore-*\python.exe"),
    (Join-Path $env:LOCALAPPDATA "Programs\Python\Python*\python.exe"),
    (Join-Path $env:ProgramFiles "Python*\python.exe")
)

if (${env:ProgramFiles(x86)}) {
    $installPatterns += (Join-Path ${env:ProgramFiles(x86)} "Python*\python.exe")
}

foreach ($pattern in $installPatterns) {
    foreach ($candidate in Get-ChildItem -Path $pattern -File | Sort-Object LastWriteTime -Descending) {
        $python = Test-RealPython $candidate.FullName
        if ($python) {
            Write-Output $python
            exit 0
        }
    }
}

exit 1
