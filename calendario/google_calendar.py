"""Conexión con la API de Google Calendar: autorización OAuth, sincronización y conversión de eventos."""
import hashlib
import logging
import re
import time
from datetime import datetime, timedelta
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urlsplit

from . import config

log = logging.getLogger("calendario")

# Solo lectura: la app no puede crear, cambiar ni borrar nada de tu calendario.
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

# Colores de evento tal y como los muestra Google Calendar (Lavanda, Salvia, Uva...).
COLORES_EVENTO = {
    "1": "#7986cb", "2": "#33b679", "3": "#8e24aa", "4": "#e67c73", "5": "#f6bf26", "6": "#f4511e",
    "7": "#039be5", "8": "#616161", "9": "#3f51b5", "10": "#0b8043", "11": "#d50000",
}
CAMPOS_EVENTO = ("nextPageToken,items(id,status,summary,location,description,start,end,colorId,"
                 "htmlLink,hangoutLink,recurringEventId,attendees(self,responseStatus))")


class SinAutorizacion(Exception):
    """Falta el permiso de Google o ha caducado: hay que volver a conectar."""


# --- Autorización ------------------------------------------------------------------------

def credenciales(autorizar=False):
    """Devuelve el permiso guardado; con autorizar=True abre el navegador si falta o ha caducado."""
    from google.auth.exceptions import RefreshError
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    token = config.DATOS / "token.json"
    creds = Credentials.from_authorized_user_file(str(token), SCOPES) if token.exists() else None
    if creds and not creds.valid and creds.refresh_token:
        try:
            creds.refresh(Request())
            token.write_text(creds.to_json(), encoding="utf-8")
        except RefreshError:
            creds = None
    if creds and creds.valid:
        return creds
    if not autorizar:
        raise SinAutorizacion("El permiso de Google ha caducado o falta. Pulsa «Volver a conectar».")
    secreto = config.CREDENCIALES
    if not secreto.exists():
        raise SinAutorizacion("Falta credentials.json en la carpeta de la app (mira LEEME.md).")
    from google_auth_oauthlib.flow import InstalledAppFlow
    flujo = InstalledAppFlow.from_client_secrets_file(str(secreto), SCOPES)
    creds = flujo.run_local_server(
        port=0, prompt="consent",
        authorization_prompt_message="Se abrirá el navegador para que des permiso. Si no se abre, entra aquí:\n{url}\n",
        success_message="Listo. Ya puedes cerrar esta pestaña: el calendario se actualizará solo.",
        timeout_seconds=300)
    config.DATOS.mkdir(exist_ok=True)
    token.write_text(creds.to_json(), encoding="utf-8")
    return creds


def servicio(autorizar=False):
    import google_auth_httplib2
    import httplib2
    from googleapiclient.discovery import build
    creds = credenciales(autorizar)
    http = google_auth_httplib2.AuthorizedHttp(creds, http=httplib2.Http(timeout=20))
    return build("calendar", "v3", http=http, cache_discovery=False)


# --- Conversión de eventos -----------------------------------------------------------------

class _TextoHTML(HTMLParser):
    """Pasa la descripción (que Google guarda como HTML) a texto plano y recoge sus enlaces."""
    SALTOS = {"br", "p", "div", "li", "ul", "ol", "tr", "h1", "h2", "h3", "h4"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.partes, self.enlaces, self._href, self._texto_a = [], [], None, []

    def handle_starttag(self, tag, attrs):
        if tag in self.SALTOS:
            self.partes.append("\n")
        if tag == "li":
            self.partes.append("• ")
        if tag == "a":
            self._href, self._texto_a = dict(attrs).get("href"), []

    def handle_endtag(self, tag):
        if tag in {"p", "div", "li"}:
            self.partes.append("\n")
        if tag == "a" and self._href:
            self.enlaces.append(("".join(self._texto_a).strip(), self._href))
            self._href = None

    def handle_data(self, data):
        if self.lasttag in ("script", "style") and self.cdata_elem:
            return
        self.partes.append(data)
        if self._href:
            self._texto_a.append(data)


URL_EN_TEXTO = re.compile(r"https?://[^\s<>\"')\]]+")
PARECE_HTML = re.compile(r"<(br|p|div|a|b|i|u|ul|ol|li|span|strong|em)\b", re.I)


def url_segura(url):
    try:
        p = urlsplit(url.strip())
    except ValueError:
        return False
    return p.scheme in ("http", "https") and bool(p.hostname)


def limpiar_descripcion(bruto):
    bruto = bruto or ""
    if PARECE_HTML.search(bruto):
        lector = _TextoHTML()
        lector.feed(bruto)
        lector.close()
        texto, enlaces = "".join(lector.partes), lector.enlaces
    else:
        texto, enlaces = unescape(bruto), []
    enlaces += [("", u.rstrip(".,;:")) for u in URL_EN_TEXTO.findall(texto)]
    texto = re.sub(r"[ \t]+\n", "\n", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto).strip()
    if len(texto) > 3000:
        texto = texto[:3000].rstrip() + "…"
    vistos, limpios = set(), []
    for nombre, url in enlaces:
        url = url.strip()
        if url_segura(url) and url not in vistos:
            vistos.add(url)
            limpios.append({"texto": nombre if nombre and nombre != url else urlsplit(url).hostname, "url": url})
    return texto, limpios[:5]


def _fecha(valor, tz):
    """Devuelve (datetime de pared sin zona, es_todo_el_dia)."""
    if "date" in valor:
        return datetime.fromisoformat(valor["date"]), True
    d = datetime.fromisoformat(valor["dateTime"].replace("Z", "+00:00"))
    return d.astimezone(tz).replace(tzinfo=None), False


def convertir(ev, cal, tz):
    if ev.get("status") == "cancelled":
        return None
    if any(a.get("self") and a.get("responseStatus") == "declined" for a in ev.get("attendees", [])):
        return None
    ini, todo_dia = _fecha(ev["start"], tz)
    fin = _fecha(ev["end"], tz)[0] if ev.get("end") else ini + timedelta(minutes=30)
    descripcion, enlaces = limpiar_descripcion(ev.get("description", ""))
    if ev.get("hangoutLink") and url_segura(ev["hangoutLink"]):
        enlaces.insert(0, {"texto": "Videollamada", "url": ev["hangoutLink"]})
    abrir = ev.get("htmlLink", "")
    return {
        "id": hashlib.sha1(f"{cal['id']}|{ev['id']}".encode()).hexdigest()[:12],
        "titulo": (ev.get("summary") or "").strip() or "(sin título)",
        "lugar": (ev.get("location") or "").strip(),
        "descripcion": descripcion,
        "enlaces": enlaces,
        "url": abrir if url_segura(abrir) else "",
        "calendario": cal["nombre"],
        "color": COLORES_EVENTO.get(ev.get("colorId"), cal["color"]),
        "proximos": cal["propio"],
        "recurrente": bool(ev.get("recurringEventId")),
        "ini": ini, "fin": fin, "todo_dia": todo_dia,
    }


# --- Sincronización ------------------------------------------------------------------------

class Sincronizador:
    """Pregunta a Google si ha cambiado algo (petición mínima con syncToken) y solo entonces
    descarga los eventos de la semana actual y los próximos días."""

    def __init__(self, servicio, tz, dias=60):
        self.s, self.tz, self.dias = servicio, tz, dias
        self.tokens, self.calendarios = {}, []
        self.t_lista = self.t_ventana = 0.0
        self.dia = None

    def _todas(self, metodo, **kw):
        items, pagina = [], None
        while True:
            r = metodo(**kw, **({"pageToken": pagina} if pagina else {})).execute()
            items += r.get("items", [])
            pagina = r.get("nextPageToken")
            if not pagina:
                return items, r

    def _calendarios(self):
        items, _ = self._todas(self.s.calendarList().list, fields=(
            "nextPageToken,items(id,summary,summaryOverride,backgroundColor,selected,hidden,accessRole,primary)"))
        return [{"id": c["id"], "nombre": "Mi calendario" if c.get("primary") else (c.get("summaryOverride") or c.get("summary") or c["id"]),
                 "color": c.get("backgroundColor") or "#9fc6e7",
                 "propio": c.get("accessRole") in ("owner", "writer")}
                for c in items if c.get("selected") and not c.get("hidden")]

    def _hay_cambios(self, cal):
        from googleapiclient.errors import HttpError
        cid, token = cal["id"], self.tokens.get(cal["id"])
        try:
            if token is None:
                _, r = self._todas(self.s.events().list, calendarId=cid, maxResults=2500,
                                   fields="nextPageToken,nextSyncToken")
                self.tokens[cid] = r.get("nextSyncToken")
                return True
            items, r = self._todas(self.s.events().list, calendarId=cid, syncToken=token, maxResults=250,
                                   fields="nextPageToken,nextSyncToken,items(id)")
            self.tokens[cid] = r.get("nextSyncToken") or token
            return bool(items)
        except HttpError as e:
            if e.resp.status == 410:  # Google invalidó el token: se rehace desde cero
                self.tokens.pop(cid, None)
                return True
            if e.resp.status in (401, 403) and b"insufficient" in (e.content or b"").lower():
                raise SinAutorizacion("Falta el permiso de lectura del calendario: pulsa «Volver a conectar».")
            log.warning("No se pudo comprobar cambios en %s (HTTP %s)", cal["nombre"], e.resp.status)
            return False

    def _ventana(self, hoy):
        lunes = hoy - timedelta(days=hoy.weekday())
        desde = datetime.combine(lunes, datetime.min.time(), tzinfo=self.tz)
        hasta = desde + timedelta(days=self.dias)
        eventos = []
        for cal in self.calendarios:
            items, _ = self._todas(self.s.events().list, calendarId=cal["id"], timeMin=desde.isoformat(),
                                   timeMax=hasta.isoformat(), singleEvents=True, orderBy="startTime",
                                   maxResults=2500, fields=CAMPOS_EVENTO)
            eventos += [e for e in (convertir(ev, cal, self.tz) for ev in items) if e]
        return eventos

    def paso(self):
        """Devuelve la lista de eventos si algo cambió, o None si todo sigue igual."""
        from google.auth.exceptions import RefreshError
        try:
            ahora, hoy, cambios = time.time(), datetime.now(self.tz).date(), False
            if not self.calendarios or ahora - self.t_lista > 300:
                nuevos = self._calendarios()
                if nuevos != self.calendarios:
                    self.calendarios, cambios = nuevos, True
                self.t_lista = ahora
            for cal in self.calendarios:
                cambios = self._hay_cambios(cal) or cambios
            if cambios or hoy != self.dia or ahora - self.t_ventana > 900:
                eventos = self._ventana(hoy)
                self.dia, self.t_ventana = hoy, ahora
                return eventos
            return None
        except RefreshError:
            raise SinAutorizacion("El permiso de Google ha caducado. Pulsa «Volver a conectar».")
