@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Live Calendar Wallpaper - instalación

set PY=
py -3 -c "import sys" >nul 2>&1 && set PY=py -3
if not defined PY python -c "import sys" >nul 2>&1 && set PY=python
if not defined PY (
  echo No encuentro Python. Instala Python 3.10 o superior desde python.org y vuelve a ejecutar esto.
  pause & exit /b 1
)

if not exist credentials.json (
  %PY% app.py --credenciales || (pause & exit /b 1)
)

echo Instalando las dependencias. Puede tardar un par de minutos sin mostrar nada...
%PY% -m venv .venv || (pause & exit /b 1)
.venv\Scripts\python -m pip install -q --upgrade -r requirements.txt || (pause & exit /b 1)

call :cerrar_app
.venv\Scripts\python app.py --conectar || (pause & exit /b 1)
.venv\Scripts\python app.py --arranque activar
start "" "%~dp0.venv\Scripts\pythonw.exe" "%~dp0app.py"

echo.
echo Listo. La app ya está en marcha y arrancará sola con Windows.
echo Último paso: pon fondo_pantalla\calendario.html como fondo en Wallpaper Engine o Lively (mira LEEME.md).
pause
exit /b 0

:cerrar_app
rem Cierra la versión que esté en marcha (la app guarda su número de proceso en datos\app.pid).
set PID=
if exist datos\app.pid set /p PID=<datos\app.pid
if defined PID taskkill /F /FI "PID eq %PID%" /FI "IMAGENAME eq python*" >nul 2>&1
exit /b 0
