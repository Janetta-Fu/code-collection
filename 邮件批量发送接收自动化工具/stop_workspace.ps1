param(
    [string]$InstanceName = "user1",
    [int]$Port = 5001
)

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$SafeName = ($InstanceName -replace '[^0-9A-Za-z._-]+', '_').Trim('._-')
if ([string]::IsNullOrWhiteSpace($SafeName)) {
    $SafeName = "user1"
}
$WorkspaceRoot = Join-Path $Root "workspaces\$SafeName"
$ChromeProfile = Join-Path $WorkspaceRoot "chrome_profile"

$targets = Get-CimInstance Win32_Process | Where-Object {
    $_.ProcessId -ne $PID -and (
        ($_.CommandLine -like "*workspace_supervisor.ps1*" -and $_.CommandLine -like "*$SafeName*") -or
        ($_.Name -match "chrome" -and $_.CommandLine -like "*$ChromeProfile*")
    )
}
foreach ($proc in $targets) {
    Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
}

$listeners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
foreach ($pid in $listeners) {
    Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
}

Write-Host "Stopped workspace $SafeName on port $Port"
