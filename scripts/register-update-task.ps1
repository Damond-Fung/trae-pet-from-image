param(
    [Parameter(Mandatory=$true)][string]$Bundle,
    [string]$PythonExe,
    [switch]$Remove
)
$ErrorActionPreference = 'Stop'
$bundlePath = (Resolve-Path -LiteralPath $Bundle).Path
$manifest = Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $bundlePath 'manifest.json') | ConvertFrom-Json
$sha = [System.Security.Cryptography.SHA256]::Create()
try { $hash = $sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($manifest.media.ToLowerInvariant())) }
finally { $sha.Dispose() }
$suffix = ([BitConverter]::ToString($hash)).Replace('-','').Substring(0,12)
$taskName = "TRAE-Custom-Pet-$suffix"
if ($Remove) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output "Removed update check: $taskName"
    exit
}
if (-not $PythonExe) { throw 'Pass the actual Python executable path with -PythonExe.' }
$pythonPath = (Resolve-Path -LiteralPath $PythonExe).Path
$controller = Join-Path $PSScriptRoot 'petctl.py'
if (-not (Test-Path -LiteralPath $controller)) { throw 'petctl.py missing' }
$pythonw = Join-Path (Split-Path -Parent $pythonPath) 'pythonw.exe'
if (-not (Test-Path -LiteralPath $pythonw)) { throw 'pythonw.exe required; no console fallback allowed.' }
$launcherSource = Join-Path $PSScriptRoot 'silent-update.pyw'
if (-not (Test-Path -LiteralPath $launcherSource)) { throw 'silent-update.pyw missing' }
& $pythonPath $controller status --bundle $bundlePath | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Bundle validation failed; task unchanged.' }
# Copy all runtime dependencies outside the project before registering the task.
$runtime = Join-Path $env:LOCALAPPDATA "TraePetLibrary/update-runtime/$suffix"
$release = Join-Path $runtime ([Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force -Path $release | Out-Null
Copy-Item -LiteralPath $bundlePath -Destination (Join-Path $release 'bundle') -Recurse
Copy-Item -LiteralPath $controller -Destination (Join-Path $release 'petctl.py')
Copy-Item -LiteralPath $launcherSource -Destination (Join-Path $release 'silent-update.pyw')
& $pythonPath (Join-Path $release 'petctl.py') status --bundle (Join-Path $release 'bundle') | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Stable copy validation failed; task unchanged.' }
$existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existing) {
    [IO.File]::WriteAllText((Join-Path $release 'previous-task.xml'), (Export-ScheduledTask -TaskName $taskName))
    Stop-ScheduledTask -TaskName $taskName
}
# Direct GUI-subsystem Python: no PowerShell/cmd or child console processes.
$action = New-ScheduledTaskAction -Execute $pythonw -Argument ('"' + (Join-Path $release 'silent-update.pyw') + '"') -WorkingDirectory $release
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 2)
$identity = [Security.Principal.WindowsIdentity]::GetCurrent().Name
$principal = New-ScheduledTaskPrincipal -UserId $identity -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 1) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$null = Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description 'Check known TRAE pet compatibility and reapply backed-up custom skin; unknown versions remain untouched.' -Force
Write-Output "Registered: $taskName"
Write-Output "Runtime and logs: $release"
Write-Output 'A reapply changes files only. An already loaded pet window may still require off/on.'
