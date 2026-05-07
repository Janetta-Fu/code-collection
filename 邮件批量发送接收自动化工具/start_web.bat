@echo off
cd /d %~dp0
python -m pip install -r requirements-web.txt
if not exist web_data mkdir web_data
echo Web service supervisor started. Close this window to stop the system.
echo Open http://127.0.0.1:5000
:restart
echo [%date% %time%] starting web_app.py>>web_data\web_server.log
python web_app.py >>web_data\web_server.log 2>&1
echo [%date% %time%] web_app.py stopped, restarting in 3 seconds>>web_data\web_server.log
timeout /t 3 /nobreak >nul
goto restart
