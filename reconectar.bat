@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Live Calendar Wallpaper - reconectar con Google
rem Lo mismo que el botón «Volver a conectar» del fondo de pantalla.
.venv\Scripts\python app.py --conectar
pause
