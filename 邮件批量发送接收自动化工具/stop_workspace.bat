@echo off
setlocal
cd /d %~dp0

set "INSTANCE=%~1"
if "%INSTANCE%"=="" (
  set /p INSTANCE=Workspace name to stop:
)

set "PORT=%~2"
if "%PORT%"=="" (
  set /p PORT=Port to stop:
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop_workspace.ps1" -InstanceName "%INSTANCE%" -Port %PORT%
pause
