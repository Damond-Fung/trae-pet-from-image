param([switch]$CheckOnly)
$ErrorActionPreference = 'Stop'
$tasks = @(Get-ScheduledTask | Where-Object { $_.TaskName -match '^TRAE-Custom-Pet-[0-9A-Fa-f]{12}$' })
$backup = Join-Path $env:LOCALAPPDATA ('TraePetLibrary/task-repairs/' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [Guid]::NewGuid().ToString('N').Substring(0,8))
if (-not $CheckOnly) { New-Item -ItemType Directory -Force -Path $backup | Out-Null }
$report = @()
foreach ($task in $tasks) {
    $name = $task.TaskName
    $row = [ordered]@{ taskName=$name; taskPath=$task.TaskPath; previousState=[string]$task.State; actions=@($task.Actions | Select-Object Execute,Arguments); changed=$false }
    if (-not $CheckOnly) {
        $xml = Export-ScheduledTask -TaskName $name -TaskPath $task.TaskPath
        [IO.File]::WriteAllText((Join-Path $backup ($name + '.xml')), $xml)
        Disable-ScheduledTask -TaskName $name -TaskPath $task.TaskPath | Out-Null
        Stop-ScheduledTask -TaskName $name -TaskPath $task.TaskPath
        $row.changed = $true
        $row['currentState'] = [string](Get-ScheduledTask -TaskName $name -TaskPath $task.TaskPath).State
    }
    $report += [pscustomobject]$row
}
if (-not $CheckOnly) { $report | ConvertTo-Json -Depth 6 | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $backup 'report.json') }
$report | ConvertTo-Json -Depth 6
Write-Output "Matched tasks: $($tasks.Count)"
if (-not $CheckOnly) { Write-Output "Backup: $backup" }
Write-Output 'Current pet and TRAE processes are untouched. Old update checks are paused; re-register with the fixed skill to resume.'
