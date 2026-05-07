@echo off
cd /d %~dp0
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*web_supervisor.ps1*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":5000" ^| findstr "LISTENING"') do (
  taskkill /PID %%p /F >nul 2>nul
)
start "Mail System Supervisor" /min powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0web_supervisor.ps1"
timeout /t 3 /nobreak >nul
start http://127.0.0.1:5000/send
