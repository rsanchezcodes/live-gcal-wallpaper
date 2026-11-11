"""Rutas de la aplicación y lectura de config.json."""
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DATOS = RAIZ / "datos"              # permiso de Google, copia de eventos, fondo original
WEB = RAIZ / "web"                  # la página que se muestra como fondo
RUTA_CONFIG = RAIZ / "config.json"
CREDENCIALES = RAIZ / "credentials.json"
REGISTRO = RAIZ / "app.log"

VERSION = 2
POR_DEFECTO = {
    "version": VERSION,
    "zona_horaria": "Europe/Madrid",
    "modo": "web",               # "web": página en vivo; "imagen": imagen fija de Windows, sin clics
    "segundos_comprobacion": 15,
    "minutos_actualizacion": 5,  # solo en modo imagen
    "hora_inicio": 8,
    "hora_fin": 22,
    "puerto": 8765,
    "resolucion": "auto",
    "imagen_fondo": "",
}
# Claves que se conservan al actualizar desde la primera versión (enlace iCal + imagen fija).
CONSERVAR = ("zona_horaria", "hora_inicio", "hora_fin", "puerto", "resolucion", "imagen_fondo")


def cargar():
    datos = json.loads(RUTA_CONFIG.read_text(encoding="utf-8")) if RUTA_CONFIG.exists() else {}
    if datos.get("version") != VERSION:
        datos = {**POR_DEFECTO, **{k: v for k, v in datos.items() if k in CONSERVAR}}
        guardar(datos)
    return {**POR_DEFECTO, **datos}


def guardar(cfg):
    RUTA_CONFIG.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
