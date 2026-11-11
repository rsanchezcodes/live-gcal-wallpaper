"""Servidor local (solo 127.0.0.1) que entrega la página y avisa de los cambios al instante."""
import json
import mimetypes
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import config, sincronizacion, vista

ARCHIVOS_WEB = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/estilo.css": ("estilo.css", "text/css; charset=utf-8"),
    "/calendario.js": ("calendario.js", "text/javascript; charset=utf-8"),
}


def ruta_fondo(cfg):
    """Imagen detrás del calendario: la elegida en config.json o tu fondo de Windows original."""
    if cfg.get("imagen_fondo"):
        p = Path(cfg["imagen_fondo"])
        return p if p.is_file() else None
    return next(iter(sorted(config.DATOS.glob("fondo_original.*"))), None)


def crear(cfg, construir_vista=None):
    construir_vista = construir_vista or (lambda: vista.construir(cfg))
    estado = sincronizacion.ESTADO
    puerto = cfg["puerto"]
    hosts_locales = {f"127.0.0.1:{puerto}", f"localhost:{puerto}"}

    class Manejador(BaseHTTPRequestHandler):
        def enviar(self, codigo, cuerpo=b"", tipo="text/plain"):
            self.send_response(codigo)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(cuerpo)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(cuerpo)

        def es_local(self):
            # Rechaza peticiones con otro Host: evita que una web lea datos mediante DNS rebinding.
            return self.headers.get("Host") in hosts_locales

        def do_GET(self):
            if not self.es_local():
                return self.enviar(403)
            ruta = urllib.parse.urlsplit(self.path).path
            if ruta in ARCHIVOS_WEB:
                nombre, tipo = ARCHIVOS_WEB[ruta]
                return self.enviar(200, (config.WEB / nombre).read_bytes(), tipo)
            if ruta == "/api/ping":
                return self.enviar(204)
            if ruta == "/api/vista":
                cuerpo = json.dumps(construir_vista(), ensure_ascii=False).encode()
                return self.enviar(200, cuerpo, "application/json; charset=utf-8")
            if ruta == "/api/cambios":
                return self.avisar_cambios()
            if ruta == "/fondo":
                p = ruta_fondo(cfg)
                if p:
                    return self.enviar(200, p.read_bytes(), mimetypes.guess_type(p.name)[0] or "image/jpeg")
            self.enviar(404)

        def avisar_cambios(self):
            """Server-Sent Events: la página se entera en cuanto llega algo nuevo de Google."""
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            vista_enviada = estado.version
            try:
                while True:
                    with estado.cond:
                        estado.cond.wait_for(lambda: estado.version != vista_enviada, timeout=15)
                        actual = estado.version
                    if actual != vista_enviada:
                        vista_enviada = actual
                        self.wfile.write(f"data: {actual}\n\n".encode())
                    else:
                        self.wfile.write(b": latido\n\n")
                    self.wfile.flush()
            except OSError:
                pass  # la página se ha cerrado

        def do_POST(self):
            # La cabecera propia obliga al navegador a pedir permiso CORS, que este servidor nunca da:
            # ninguna web puede pedirle que abra enlaces o ventanas de permiso.
            if not self.es_local() or self.headers.get("X-Calendario") != "1":
                return self.enviar(403)
            ruta = urllib.parse.urlsplit(self.path).path
            if ruta == "/api/reconectar":
                if not sincronizacion.puede_reconectar():
                    return self.enviar(409)
                sincronizacion.reconectar()
                return self.enviar(204)
            if ruta == "/api/abrir":
                return self.abrir_enlace()
            self.enviar(404)

        def abrir_enlace(self):
            largo = int(self.headers.get("Content-Length") or 0)
            if largo > 2000:
                return self.enviar(413)
            try:
                datos = json.loads(self.rfile.read(largo) or b"{}")
                url = estado.url_de(str(datos.get("id")), datos.get("n"))
            except (ValueError, AttributeError):
                url = None
            if not url:
                return self.enviar(404)
            webbrowser.open(url)
            self.enviar(204)

        def log_message(self, *args):
            pass

    servidor = ThreadingHTTPServer(("127.0.0.1", puerto), Manejador)
    servidor.daemon_threads = True
    return servidor
