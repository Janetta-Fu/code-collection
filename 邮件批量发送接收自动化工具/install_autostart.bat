@echo off
cd /d %~dp0
powershell -NoProfile -ExecutionPolicy Bypass -Command "$startup=[Environment]::GetFolderPath('Startup'); $shortcutPath=Join-Path $startup 'Mail System Web.lnk'; $shell=New-Object -ComObject WScript.Shell; $shortcut=$shell.CreateShortcut($shortcutPath); $shortcut.TargetPath='powershell.exe'; $shortcut.Arguments='-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File \"%~dp0web_supervisor.ps1\"'; $shortcut.WorkingDirectory='%~dp0'; $shortcut.WindowStyle=7; $shortcut.Description='Keep Mail System web service available'; $shortcut.Save()"
echo Mail System has been added to your Windows startup folder.
echo It will keep http://127.0.0.1:5000 available after you sign in.
pause
