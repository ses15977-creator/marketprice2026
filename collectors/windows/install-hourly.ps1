# Run once in PowerShell, under the Windows account that will run the collector.
# Stores no credentials. Uses the current account's Python and existing user environment.
$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$pythonCommand = Get-Command python.exe -ErrorAction Stop
$pythonExe = $pythonCommand.Source
$script = Join-Path $repoRoot "collectors\run_local.py"
if (-not (Test-Path $script)) { throw "Missing collector script: $script" }
$action = New-ScheduledTaskAction -Execute $pythonExe -Argument ('"' + $script + '"') -WorkingDirectory $repoRoot
$trigger = New-ScheduledTaskTrigger -Once -At ((Get-Date).AddMinutes(5)) -RepetitionInterval (New-TimeSpan -Hours 1)
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 7) -MultipleInstances IgnoreNew -StartWhenAvailable
$principal = New-ScheduledTaskPrincipal -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName "MarketPrice-Gmarket-Hourly" -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null
Write-Host "Created: MarketPrice-Gmarket-Hourly (hourly while this user is signed in)."
Write-Host "Logs: $(Join-Path $repoRoot 'local-logs')"
Write-Host "Run dry check: python collectors/run_local.py --check-only"
