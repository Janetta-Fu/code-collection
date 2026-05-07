@echo off
setlocal
cd /d %~dp0

set "INSTANCE=%~1"
if "%INSTANCE%"=="" (
  set /p INSTANCE=Workspace name ^(for example user1^):
)
if "%INSTANCE%"=="" set "INSTANCE=user1"

set "PORT=%~2"
if "%PORT%"=="" (
  set /p PORT=Port ^(for example 5001^):
)
if "%PORT%"=="" set "PORT=5001"

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0workspace_launcher.ps1" -InstanceName "%INSTANCE%" -Port %PORT%
pause
