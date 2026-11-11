"""Estado compartido entre la sincronización con Google y el servidor local."""
import json
import logging
import threading
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from . import config, google_calendar

log = logging.getLogger("calendario")


class Estado:
    """Eventos actuales y aviso visible. Cada cambio sube `version` y despierta a quien espere."""

    def __init__(self):
        self.cond = threading.Condition()
        self.eventos, self.aviso, self.version, self.actualizado = [], "", 0, None
        self.necesita_permiso = False

    def publicar(self, eventos=None, aviso=None):
        with self.cond:
            cambio = False
            if eventos is not None:
                self.actualizado = datetime.now()
                if eventos != self.eventos:
                    self.eventos, cambio = eventos, True
            if aviso is not None and aviso != self.aviso:
                self.aviso, cambio = aviso, True
            if cambio:
                self.version += 1
                self.cond.notify_all()

    def foto(self):
        with self.cond:
            return list(self.eventos), self.aviso, self.version

    def url_de(self, id_evento, n):
        """URL que se puede abrir de un evento cargado: -1 es el evento en Google, 0..n sus enlaces."""
        with self.cond:
            ev = next((e for e in self.eventos if e["id"] == id_evento), None)
        if ev is None:
            return None
        if n == -1:
            url = ev["url"]
        elif isinstance(n, int) and not isinstance(n, bool) and 0 <= n < len(ev["enlaces"]):
            url = ev["enlaces"][n]["url"]
        else:
            return None
        return url if google_calendar.url_segura(url) else None


ESTADO = Estado()


# --- Copia local para arrancar sin conexión ----------------------------------------------------

def ruta_cache():
    return config.DATOS / "eventos.json"


def guardar_cache(eventos):
    config.DATOS.mkdir(exist_ok=True)
    serie = [{**e, "ini": e["ini"].isoformat(), "fin": e["fin"].isoformat()} for e in eventos]
    tmp = ruta_cache().with_suffix(".tmp")
    tmp.write_text(json.dumps(serie, ensure_ascii=False), encoding="utf-8")
    tmp.replace(ruta_cache())


def cargar_cache():
    try:
        serie = json.loads(ruta_cache().read_text(encoding="utf-8"))
        eventos = [{**e, "ini": datetime.fromisoformat(e["ini"]), "fin": datetime.fromisoformat(e["fin"])}
                   for e in serie]
        hora = datetime.fromtimestamp(ruta_cache().stat().st_mtime).strftime("%d/%m %H:%M")
        ESTADO.publicar(eventos, f"Conectando con Google Calendar. Mostrando datos del {hora}.")
    except (OSError, ValueError, KeyError):
        pass


# --- Bucle de sincronización -------------------------------------------------------------------

def bucle(cfg, crear=None):
    """Pregunta a Google cada pocos segundos y publica los cambios. Nunca termina."""
    tz = ZoneInfo(cfg["zona_horaria"])
    crear = crear or (lambda: google_calendar.Sincronizador(google_calendar.servicio(), tz))
    sinc = None
    while True:
        try:
            if sinc is None:
                sinc = crear()
            eventos = sinc.paso()
            if eventos is not None:
                guardar_cache(eventos)
            ESTADO.necesita_permiso = False
            ESTADO.publicar(eventos, "")
        except google_calendar.SinAutorizacion as e:
            sinc = None
            ESTADO.necesita_permiso = True
            ESTADO.publicar(aviso=str(e))
        except Exception as e:  # red caída, Google no responde...: se reintenta en el siguiente ciclo
            log.warning("Sin conexión con Google: %s", type(e).__name__)
            hora = ESTADO.actualizado.strftime("%H:%M") if ESTADO.actualizado else None
            ESTADO.publicar(aviso="Sin conexión con Google Calendar" + (f". Datos de las {hora}." if hora else "."))
        time.sleep(max(5, int(cfg["segundos_comprobacion"])))


# --- Renovar el permiso desde el fondo de pantalla ---------------------------------------------

_RENOVANDO = threading.Lock()


def puede_reconectar():
    return ESTADO.necesita_permiso and config.CREDENCIALES.exists()


def reconectar():
    """Abre el navegador para renovar el permiso. Si ya hay una ventana abierta, no abre otra."""
    if not _RENOVANDO.acquire(blocking=False):
        return

    def tarea():
        try:
            google_calendar.credenciales(autorizar=True)
            log.info("Permiso de Google renovado")
        except Exception:
            log.exception("No se pudo renovar el permiso")
        finally:
            _RENOVANDO.release()

    threading.Thread(target=tarea, daemon=True).start()
