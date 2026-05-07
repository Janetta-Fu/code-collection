param(
    [string]$InstanceName = "user1",
    [int]$Port = 5001
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$SafeName = ($InstanceName -replace '[^0-9A-Za-z._-]+', '_').Trim('._-')
if ([string]::IsNullOrWhiteSpace($SafeName)) {
    $SafeName = "user1"
}

$WorkspaceRoot = Join-Path $Root "workspaces\$SafeName"
$WebData = Join-Path $WorkspaceRoot "web_data"
$AppData = Join-Path $WorkspaceRoot "app_data"
$Downloads = Join-Path $WorkspaceRoot "downloads"
$ChromeProfile = Join-Path $WorkspaceRoot "chrome_profile"
$Logs = Join-Path $WorkspaceRoot "logs"
$ConfigPath = Join-Path $WorkspaceRoot "config.ini"

foreach ($dir in @($WorkspaceRoot, $WebData, $AppData, $Downloads, $ChromeProfile, $Logs)) {
    if (!(Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir | Out-Null
    }
}

if (!(Test-Path $ConfigPath)) {
    if (Test-Path (Join-Path $Root "config.ini")) {
        Copy-Item -Path (Join-Path $Root "config.ini") -Destination $ConfigPath
    } elseif (Test-Path (Join-Path $Root "config.ini.example")) {
        Copy-Item -Path (Join-Path $Root "config.ini.example") -Destination $ConfigPath
    }
}

$listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if (-not $listener) {
    $Supervisor = Join-Path $Root "workspace_supervisor.ps1"
    Start-Process -FilePath "powershell" -ArgumentList @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", $Supervisor,
        "-InstanceName", $SafeName,
        "-Port", "$Port"
    ) -WindowStyle Hidden
}

$deadline = (Get-Date).AddSeconds(25)
while ((Get-Date) -lt $deadline) {
    $listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if ($listener) { break }
    Start-Sleep -Milliseconds 500
}

$defaultProfile = Join-Path $ChromeProfile "Default"
if (!(Test-Path $defaultProfile)) {
    New-Item -ItemType Directory -Path $defaultProfile | Out-Null
}

$prefsPath = Join-Path $defaultProfile "Preferences"
$prefs = @{
    download = @{
        default_directory = $Downloads
        prompt_for_download = $false
        directory_upgrade = $true
    }
}
$prefs | ConvertTo-Json -Depth 10 | Set-Content -Path $prefsPath -Encoding UTF8

$url = "http://127.0.0.1:$Port/inbox"
$chromeCandidates = @(@(
    "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
    "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
    "$env:LocalAppData\Google\Chrome\Application\chrome.exe"
) | Where-Object { $_ -and (Test-Path $_) })

if ($chromeCandidates.Count -gt 0) {
    Start-Process -FilePath $chromeCandidates[0] -ArgumentList @(
        "--user-data-dir=$ChromeProfile",
        "--profile-directory=Default",
        "--no-first-run",
        "--disable-default-apps",
        "--app=$url"
    )
    Start-Process -FilePath "powershell" -ArgumentList @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", (Join-Path $Root "workspace_browser_watch.ps1"),
        "-InstanceName", $SafeName,
        "-Port", "$Port",
        "-ChromeProfile", $ChromeProfile
    ) -WindowStyle Hidden
} else {
    Start-Process $url
}

Write-Host ""
Write-Host "Workspace started"
Write-Host "Name:      $SafeName"
Write-Host "URL:       $url"
Write-Host "Data:      $WorkspaceRoot"
Write-Host "Downloads: $Downloads"
Write-Host "Chrome:    $ChromeProfile"
