param(
    [string]$InstanceName = "default",
    [int]$Port = 5001,
    [string]$ChromeProfile = ""
)

$ErrorActionPreference = "Continue"

if ([string]::IsNullOrWhiteSpace($ChromeProfile)) {
    exit 0
}

$escapedProfile = [WildcardPattern]::Escape($ChromeProfile)

Start-Sleep -Seconds 3

while ($true) {
    $chromeProcesses = Get-CimInstance Win32_Process | Where-Object {
        $_.Name -match 'chrome' -and $_.CommandLine -like "*$escapedProfile*"
    }
    if (-not $chromeProcesses) {
        break
    }
    Start-Sleep -Seconds 2
}

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
& (Join-Path $Root "stop_workspace.ps1") -InstanceName $InstanceName -Port $Port
