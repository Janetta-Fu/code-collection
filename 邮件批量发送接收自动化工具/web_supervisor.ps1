$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

if (!(Test-Path "web_data")) {
    New-Item -ItemType Directory "web_data" | Out-Null
}

$Log = Join-Path $Root "web_data\web_supervisor.log"
$OutLog = Join-Path $Root "web_data\web_stdout.log"
$ErrLog = Join-Path $Root "web_data\web_stderr.log"

while ($true) {
    try {
        $listener = Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue
        if ($listener) {
            Start-Sleep -Seconds 5
            continue
        }

        "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] starting web_app.py" | Add-Content -Path $Log -Encoding UTF8
        $process = Start-Process -FilePath "python" `
            -ArgumentList "web_app.py" `
            -WorkingDirectory $Root `
            -RedirectStandardOutput $OutLog `
            -RedirectStandardError $ErrLog `
            -WindowStyle Hidden `
            -PassThru
        Start-Sleep -Seconds 5
    } catch {
        "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] supervisor error: $($_.Exception.Message)" | Add-Content -Path $Log -Encoding UTF8
        Start-Sleep -Seconds 5
    }
}
