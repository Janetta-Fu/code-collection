 t@echo off
setlocal
cd /d "%~dp0"

title OKKI Web Portable

set "PYTHON_EXE="
for /f "delims=" %%P in ('where python 2^>nul') do (
    if not defined PYTHON_EXE set "PYTHON_EXE=%%P"
)

if not defined PYTHON_EXE (
    echo Python 3 was not found. Please install Python 3 first:
    echo https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

echo Checking dependencies...
"%PYTHON_EXE%" -c "import fastapi, uvicorn, multipart, selenium, requests, pandas, openpyxl" >nul 2>nul
if errorlevel 1 (
    echo Installing dependencies. Please wait...
    "%PYTHON_EXE%" -m pip install -r simple_web\requirements_web.txt
    if errorlevel 1 (
        echo.
        echo Dependency installation failed.
        echo Please check the network, then run this command manually:
        echo "%PYTHON_EXE%" -m pip install -r simple_web\requirements_web.txt
        echo.
        pause
        exit /b 1
    )
)

echo.
echo Starting OKKI Web...
echo Local URL: http://127.0.0.1:8000
echo Close this window to stop the service.
echo.
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ports = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue; foreach ($item in $ports) { if ($item.OwningProcess -ne $PID) { Stop-Process -Id $item.OwningProcess -Force -ErrorAction SilentlyContinue } }"
powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 2; Start-Process 'http://127.0.0.1:8000'"
"%PYTHON_EXE%" -m uvicorn simple_web.web_app:app --host 0.0.0.0 --port 8000

echo.
pause