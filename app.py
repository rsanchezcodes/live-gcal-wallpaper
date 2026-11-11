"""Calendario en el fondo: Google Calendar en directo en el fondo de pantalla de Windows.

    python app.py              arranca la app (lo hace solo al iniciar Windows)
    python app.py --demo       la prueba con datos inventados, sin cuenta de Google
    python app.py --conectar   abre el navegador para dar o renovar el permiso de Google
"""
import argparse
import logging
import os
import sys
import threading
import time
import webbrowser
from datetime import datetime
from logging.handlers import RotatingFileHandler

from calendario import config

log = logging.getLogger("calendario")


def conectar():
    """Pide el permiso de Google y enseña qué calendarios se van a mostrar."""
    from calendario import google_calendar
    config.cargar()
    try:
        servicio = google_calendar.servicio(autorizar=True)
        calendarios = servicio.calendarList().list().execute().get("items", [])
    except google_calendar.SinAutorizacion as e:
        print(e)
        return 1
    except Exception as e:
        print(f"No se pudo conectar con Google ({type(e).__name__}: {e}).")
        return 1
    print("\nConectado. Se mostrarán los calendarios que tienes marcados en Google Calendar:")
    for c in calendarios:
        if c.get("selected"):
            print("  -", c.get("summaryOverride") or c.get("summary"))
    return 0


def ejecutar(demo=False, una_vez=False):
    from calendario import demo as datos_demo, servidor, sincronizacion, windows

    config.DATOS.mkdir(exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[RotatingFileHandler(config.REGISTRO, maxBytes=500_000, backupCount=1, encoding="utf-8")])
    cfg = config.cargar()
    try:
        http = servidor.crear(cfg)
    except OSError:
        log.info("Ya hay una instancia en marcha o el puerto %s está ocupado.", cfg["puerto"])
        print(f"El puerto {cfg['puerto']} está ocupado: ¿la app ya está en marcha?")
        return 1
    (config.DATOS / "app.pid").write_text(str(os.getpid()))  # para que los .bat puedan cerrarla
    threading.Thread(target=http.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{cfg['puerto']}/"

    if demo:
        sincronizacion.ESTADO.publicar(datos_demo.eventos(datetime.now()), "Modo demo: datos inventados.")
        print(f"Demo en {url} (Ctrl+C para salir)")
        webbrowser.open(url)
        while True:
            time.sleep(3600)

    sincronizacion.cargar_cache()
    windows.capturar_fondo_original()
    if cfg["modo"] == "web":
        windows.quitar_imagen_propia()
    threading.Thread(target=sincronizacion.bucle, args=(cfg,), daemon=True).start()
    while True:
        if cfg["modo"] == "imagen":
            try:
                windows.pintar_imagen(cfg)
            except Exception:
                log.exception("Fallo al generar la imagen de fondo")
            if una_vez:
                return 0
        time.sleep(max(1, int(cfg["minutos_actualizacion"])) * 60)


def principal():
    p = argparse.ArgumentParser(description="Google Calendar en el fondo de pantalla.")
    p.add_argument("--demo", action="store_true", help="probar con datos inventados")
    p.add_argument("--conectar", action="store_true", help="dar o renovar el permiso de Google")
    p.add_argument("--credenciales", action="store_true", help="crear credentials.json con el ID y el secreto")
    p.add_argument("--arranque", choices=["activar", "quitar"], help="arranque automático con Windows")
    p.add_argument("--restaurar-fondo", action="store_true", help="volver a poner tu fondo original")
    p.add_argument("--una-vez", action="store_true", help=argparse.SUPPRESS)
    args = p.parse_args()

    if args.credenciales:
        from calendario import credenciales
        return credenciales.preguntar()
    if args.conectar:
        return conectar()
    if args.arranque or args.restaurar_fondo:
        from calendario import windows
        if args.arranque:
            windows.arranque_automatico(args.arranque == "activar")
        if args.restaurar_fondo and windows.restaurar_fondo():
            print("Fondo original restaurado.")
        return 0
    return ejecutar(demo=args.demo, una_vez=args.una_vez)


if __name__ == "__main__":
    sys.exit(principal())
