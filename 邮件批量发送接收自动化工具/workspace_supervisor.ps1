param(
    [string]$InstanceName = "user1",
    [int]$Port = 5001
)

$ErrorActionPreference = "Continue"
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

$env:MAIL_INSTANCE_NAME = $SafeName
$env:MAIL_WORKSPACE_DIR = $WorkspaceRoot
$env:MAIL_WEB_DATA_DIR = $WebData
$env:MAIL_APP_DATA_DIR = $AppData
$env:MAIL_DOWNLOAD_DIR = $Downloads
$env:MAIL_CHROME_USER_DATA_DIR = $ChromeProfile
$env:MAIL_CONFIG_PATH = $ConfigPath
$env:MAIL_WEB_PORT = "$Port"

$Log = Join-Path $Logs "supervisor.log"
$OutLog = Join-Path $Logs "web_stdout.log"
$ErrLog = Join-Path $Logs "web_stderr.log"
$ExePath = Join-Path $Root "MailWeb\MailWeb.exe"
$PythonPath = Join-Path $Root "runtime\python\python.exe"

if (Test-Path $ExePath) {
    $Runner = $ExePath
    $RunnerArgs = @()
} elseif (Test-Path $PythonPath) {
    $Runner = $PythonPath
    $RunnerArgs = @("web_app.py")
} else {
    $Runner = "python"
    $RunnerArgs = @("web_app.py")
}

while ($true) {
    try {
        $listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
        if ($listener) {
            Start-Sleep -Seconds 5
            continue
        }

        "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] starting $SafeName on port $Port" | Add-Content -Path $Log -Encoding UTF8
        Start-Process -FilePath $Runner `
            -ArgumentList $RunnerArgs `
            -WorkingDirectory $Root `
            -RedirectStandardOutput $OutLog `
            -RedirectStandardError $ErrLog `
            -WindowStyle Hidden `
            -PassThru | Out-Null
        Start-Sleep -Seconds 5
    } catch {
        "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] supervisor error: $($_.Exception.Message)" | Add-Content -Path $Log -Encoding UTF8
        Start-Sleep -Seconds 5
    }
}
