$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$PackageDir = Join-Path $Root "一键包_免环境"
$BuildDir = Join-Path $Root "build"
$DistDir = Join-Path $Root "dist"

Write-Host "Installing build tools..."
python -m pip install --upgrade pip | Out-Host
python -m pip install --upgrade pyinstaller Flask | Out-Host

Write-Host "Building executable..."
pyinstaller `
    --noconfirm `
    --clean `
    --onedir `
    --name MailWeb `
    --add-data "templates;templates" `
    --add-data "static;static" `
    --add-data "config.ini.example;." `
    web_app.py | Out-Host

if (Test-Path $PackageDir) {
    Remove-Item -Path $PackageDir -Recurse -Force
}
New-Item -ItemType Directory -Path $PackageDir | Out-Null

Copy-Item -Path (Join-Path $DistDir "MailWeb") -Destination (Join-Path $PackageDir "MailWeb") -Recurse

$items = @(
    "一键启动网页版.bat",
    "一键停止网页版.bat",
    "workspace_launcher.ps1",
    "workspace_supervisor.ps1",
    "workspace_browser_watch.ps1",
    "stop_workspace.ps1",
    "run_workspace.bat",
    "stop_workspace.bat",
    "config.ini",
    "config.ini.example",
    "使用指南.md"
)

foreach ($item in $items) {
    $source = Join-Path $Root $item
    if (Test-Path $source) {
        Copy-Item -Path $source -Destination (Join-Path $PackageDir $item) -Recurse
    }
}

Write-Host ""
Write-Host "Done. Send this folder to users:"
Write-Host $PackageDir
