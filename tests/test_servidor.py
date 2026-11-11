import json
import threading
import urllib.error
import urllib.request
from datetime import datetime

import pytest

from calendario import credenciales, servidor, sincronizacion

PUERTO = 8799


@pytest.fixture
def app(monkeypatch):
    cfg = {"puerto": PUERTO, "imagen_fondo": "", "zona_horaria": "Europe/Madrid", "hora_inicio": 8, "hora_fin": 22}
    sincronizacion.ESTADO.publicar([{
        "id": "e1", "titulo": "Parcial", "lugar": "", "descripcion": "", "calendario": "C", "color": "#039be5",
        "enlaces": [{"texto": "Campus", "url": "https://campus.example.com/"}],
        "url": "https://www.google.com/calendar/event?eid=e1", "proximos": True, "recurrente": False,
        "todo_dia": False, "ini": datetime(2026, 11, 11, 10), "fin": datetime(2026, 11, 11, 12)}], "")
    abiertos = []
    monkeypatch.setattr(servidor.webbrowser, "open", abiertos.append)
    http = servidor.crear(cfg)
    threading.Thread(target=http.serve_forever, daemon=True).start()
    yield abiertos
    http.shutdown()
    http.server_close()


def peticion(ruta, metodo="GET", cabeceras=None, cuerpo=None):
    r = urllib.request.Request(f"http://127.0.0.1:{PUERTO}{ruta}", method=metodo,
                               headers=cabeceras or {}, data=cuerpo)
    try:
        with urllib.request.urlopen(r, timeout=3) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code


def abrir(cuerpo, cabeceras=None):
    cabeceras = {"X-Calendario": "1"} if cabeceras is None else cabeceras
    return peticion("/api/abrir", "POST", cabeceras, json.dumps(cuerpo).encode())


def test_sirve_la_pagina_y_la_vista(app):
    for ruta in ("/", "/estilo.css", "/calendario.js", "/api/vista"):
        assert peticion(ruta) == 200
    assert peticion("/../config.json") == 404


def test_rechaza_otros_hosts(app):
    assert peticion("/api/vista", cabeceras={"Host": "malicioso.example.com"}) == 403


def test_abrir_solo_enlaces_de_eventos_cargados(app):
    assert abrir({"id": "e1", "n": -1}, cabeceras={}) == 403      # sin la cabecera propia
    assert abrir({"id": "otro", "n": -1}) == 404
    assert abrir({"id": "e1", "n": 7}) == 404
    assert abrir({"id": "e1", "n": True}) == 404
    assert abrir({"id": "e1", "n": 0}) == 204
    assert app == ["https://campus.example.com/"]


def test_reconectar_solo_si_hace_falta(app):
    assert peticion("/api/reconectar", "POST", {"X-Calendario": "1"}) == 409


def test_credenciales(carpeta_temporal):
    assert credenciales.id_valido("123-abc.apps.googleusercontent.com")
    assert not credenciales.id_valido("hola")
    assert not credenciales.secreto_valido("GOCSPX abc")
    credenciales.escribir("123-abc.apps.googleusercontent.com", "GOCSPX-x")
    datos = json.loads((carpeta_temporal / "credentials.json").read_text())
    assert datos["installed"]["client_id"].startswith("123-abc")
