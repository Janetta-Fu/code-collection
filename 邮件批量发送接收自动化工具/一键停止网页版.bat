@echo off
setlocal
cd /d %~dp0

set "INSTANCE=default"
set "PORT=5001"

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop_workspace.ps1" -InstanceName "%INSTANCE%" -Port %PORT%
