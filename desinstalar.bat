@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Live Calendar Wallpaper - desinstalar

set PID=
if exist datos\app.pid set /p PID=<datos\app.pid
if defined PID taskkill /F /FI "PID eq %PID%" /FI "IMAGENAME eq python*" >nul 2>&1

.venv\Scripts\python app.py --arranque quitar --restaurar-fondo
if exist datos\token.json del datos\token.json

echo.
echo Hecho: la app está cerrada, ya no arranca con Windows, tu fondo original está restaurado
echo y el permiso de Google se ha borrado de este equipo. Ya puedes borrar la carpeta.
echo Para retirar también el permiso en tu cuenta: https://myaccount.google.com/permissions
pause
