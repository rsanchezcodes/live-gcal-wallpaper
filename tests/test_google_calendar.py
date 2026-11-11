from datetime import datetime
from zoneinfo import ZoneInfo

import httplib2
from googleapiclient.errors import HttpError

from calendario import google_calendar as gc

TZ = ZoneInfo("Europe/Madrid")
CAL = {"id": "yo@example.com", "nombre": "Mi calendario", "color": "#9fe1e7", "propio": True}


def evento(**extra):
    base = {"id": "a1", "status": "confirmed", "summary": "Clase",
            "start": {"dateTime": "2026-11-09T09:00:00+01:00"}, "end": {"dateTime": "2026-11-09T10:30:00+01:00"}}
    return {**base, **extra}


def test_descripcion_html_a_texto_sin_codigo():
    texto, enlaces = gc.limpiar_descripcion(
        'Temas 4 a 6<br><b>Lleva calculadora</b><script>alert(1)</script>'
        '<a href="https://campus.example.com/ec">Campus</a> <a href="javascript:alert(1)">malo</a>')
    assert "<" not in texto and "alert" not in texto
    assert texto.startswith("Temas 4 a 6\nLleva calculadora")
    assert enlaces == [{"texto": "Campus", "url": "https://campus.example.com/ec"}]


def test_descripcion_texto_plano_y_urls_sueltas():
    texto, enlaces = gc.limpiar_descripcion("Si x < y, mira https://ejemplo.es/a.")
    assert texto == "Si x < y, mira https://ejemplo.es/a."
    assert enlaces == [{"texto": "ejemplo.es", "url": "https://ejemplo.es/a"}]


def test_convertir_hora_local_y_color_de_google():
    e = gc.convertir(evento(colorId="3", start={"dateTime": "2026-11-09T08:00:00Z"}), CAL, TZ)
    assert e["ini"] == datetime(2026, 11, 9, 9, 0) and e["color"] == "#8e24aa"


def test_convertir_descarta_cancelados_y_rechazados():
    assert gc.convertir(evento(status="cancelled"), CAL, TZ) is None
    rechazado = evento(attendees=[{"self": True, "responseStatus": "declined"}])
    assert gc.convertir(rechazado, CAL, TZ) is None


def test_convertir_todo_el_dia():
    e = gc.convertir(evento(start={"date": "2026-11-13"}, end={"date": "2026-11-14"}), CAL, TZ)
    assert e["todo_dia"] and e["ini"] == datetime(2026, 11, 13)


class Peticion:
    def __init__(self, respuesta):
        self.respuesta = respuesta

    def execute(self):
        if isinstance(self.respuesta, Exception):
            raise self.respuesta
        return self.respuesta


class GoogleFalso:
    """Imita lo justo de la API: lista de calendarios, syncToken y eventos paginados."""

    def __init__(self):
        self.cambio = False
        self.caducar_token = False
        self.descargas = 0

    def calendarList(self):
        return self

    def events(self):
        return self

    def list(self, calendarId=None, syncToken=None, timeMin=None, pageToken=None, **kw):
        if calendarId is None:
            return Peticion({"items": [{"id": CAL["id"], "summary": "yo", "selected": True,
                                        "accessRole": "owner", "primary": True}]})
        if syncToken:
            if self.caducar_token:
                self.caducar_token = False
                return Peticion(HttpError(httplib2.Response({"status": 410}), b"gone"))
            hubo = self.cambio
            self.cambio = False
            return Peticion({"nextSyncToken": "t2", "items": [{"id": "a1"}] if hubo else []})
        if timeMin is None:  # sincronización inicial, en dos páginas
            return Peticion({"nextSyncToken": "t1"} if pageToken else {"nextPageToken": "p2"})
        self.descargas += 1
        return Peticion({"items": [evento()]})


def test_sincronizador_solo_descarga_cuando_hay_cambios():
    google = GoogleFalso()
    s = gc.Sincronizador(google, TZ)
    primeros = s.paso()
    assert [e["titulo"] for e in primeros] == ["Clase"] and primeros[0]["calendario"] == "Mi calendario"
    assert s.paso() is None
    google.cambio = True
    assert s.paso() is not None
    assert google.descargas == 2


def test_sincronizador_rehace_el_token_si_google_lo_invalida():
    google = GoogleFalso()
    s = gc.Sincronizador(google, TZ)
    s.paso()
    google.caducar_token = True
    assert s.paso() is not None
