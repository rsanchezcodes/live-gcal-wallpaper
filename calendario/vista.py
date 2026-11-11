"""Prepara lo que dibuja la página: la semana, «Ahora», «Después», «Más adelante» y los detalles."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from . import sincronizacion

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
DIAS_CORTOS = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]
MAX_PROXIMOS = 6


def hhmm(d):
    return d.strftime("%H:%M")


def fecha_corta(d):
    return f"{DIAS_CORTOS[d.weekday()]} {d.day} {MESES[d.month - 1][:3]}"


def fecha_larga(d):
    return f"{DIAS[d.weekday()]} {d.day} de {MESES[d.month - 1]}"


def medianoche(d):
    return datetime.combine(d, datetime.min.time())


def describir_cuando(e):
    """«Miércoles 11 de noviembre, de 10:45 a 12:15», «Del jueves 12 al viernes 13 de noviembre»..."""
    ini, fin = e["ini"], e["fin"]
    if e["todo_dia"]:
        ultimo = fin - timedelta(days=1)
        texto = (f"{fecha_larga(ini)}, todo el día" if ultimo.date() <= ini.date()
                 else f"del {fecha_larga(ini)} al {fecha_larga(ultimo)}")
    elif fin.date() == ini.date() or fin == medianoche(ini.date() + timedelta(days=1)):
        texto = f"{fecha_larga(ini)}, de {hhmm(ini)} a {hhmm(fin)}"
    else:
        texto = f"del {fecha_larga(ini)} a las {hhmm(ini)} al {fecha_larga(fin)} a las {hhmm(fin)}"
    return texto[0].upper() + texto[1:]


def detalle(e):
    return {"titulo": e["titulo"], "cuando": describir_cuando(e), "lugar": e["lugar"],
            "calendario": e["calendario"], "descripcion": e["descripcion"], "color": e["color"],
            "enlaces": [x["texto"] for x in e["enlaces"]], "abrir": bool(e["url"])}


def _dia(dia, eventos, ahora, rango):
    """Eventos de un día. Amplía `rango` (minutos visibles) si hay algo antes o después."""
    d0, d1 = medianoche(dia), medianoche(dia + timedelta(days=1))
    todo, horas = [], []
    for e in eventos:
        if e["todo_dia"]:
            if e["ini"] < d1 and e["fin"] > d0:
                todo.append({"id": e["id"], "titulo": e["titulo"], "color": e["color"]})
            continue
        if not (e["ini"] < d1 and (e["fin"] > d0 or (e["fin"] == e["ini"] and e["ini"] >= d0))):
            continue
        ini, fin = max(e["ini"], d0), min(e["fin"], d1)  # recorta lo que cruza la medianoche
        mi = int((ini - d0).total_seconds() // 60)
        mf = max(int((fin - d0).total_seconds() // 60), mi + 30)
        if ini == e["ini"] and fin == e["fin"]:
            rango[0] = min(rango[0], mi // 60 * 60)
            rango[1] = max(rango[1], min(1440, (mf + 59) // 60 * 60))
        horas.append({"id": e["id"], "titulo": e["titulo"], "lugar": e["lugar"], "color": e["color"],
                      "ini": mi, "fin": mf, "texto_hora": f"{hhmm(e['ini'])}–{hhmm(e['fin'])}",
                      "pasado": e["fin"] <= ahora})
    horas.sort(key=lambda x: (x["ini"], -x["fin"], x["titulo"]))
    todo.sort(key=lambda x: x["titulo"])
    return todo, horas


def construir(cfg, ahora=None, estado=None):
    estado = estado or sincronizacion.ESTADO
    ahora = ahora or datetime.now(ZoneInfo(cfg["zona_horaria"])).replace(tzinfo=None)
    eventos, aviso, version = estado.foto()
    hoy = ahora.date()
    lunes = hoy - timedelta(days=hoy.weekday())
    rango = [cfg["hora_inicio"] * 60, cfg["hora_fin"] * 60]
    visibles = set()

    dias = []
    for i in range(7):
        dia = lunes + timedelta(days=i)
        todo, horas = _dia(dia, eventos, ahora, rango)
        visibles.update(x["id"] for x in todo + horas)
        dias.append({"corto": DIAS_CORTOS[i], "numero": dia.day, "hoy": dia == hoy,
                     "todo_dia": todo, "eventos": horas})

    def resumen(e):
        visibles.add(e["id"])
        return {"id": e["id"], "titulo": e["titulo"], "lugar": e["lugar"], "color": e["color"],
                "hora": f"{hhmm(e['ini'])}–{hhmm(e['fin'])}", "cuando": fecha_corta(e["ini"]),
                "es_hoy": e["ini"].date() == hoy}

    con_hora = sorted((e for e in eventos if not e["todo_dia"]), key=lambda e: e["ini"])
    en_curso = [resumen(e) for e in con_hora if e["ini"] <= ahora < e["fin"]][:2]
    siguiente = next((resumen(e) for e in con_hora if e["ini"] > ahora), None)

    # «Más adelante»: lo que no se repite (exámenes, entregas, citas); las clases semanales lo taparían.
    fin_semana = medianoche(lunes + timedelta(days=7))
    futuros = sorted((e for e in eventos if e["ini"] >= fin_semana and e["proximos"] and not e["recurrente"]),
                     key=lambda e: e["ini"])[:MAX_PROXIMOS]
    proximos = [{"id": e["id"], "titulo": e["titulo"], "cuando": fecha_corta(e["ini"])} for e in futuros]
    visibles.update(p["id"] for p in proximos)

    return {
        "version": version,
        "hoy": {"dia": DIAS[hoy.weekday()], "numero": hoy.day, "mes": MESES[hoy.month - 1]},
        "ahora_min": ahora.hour * 60 + ahora.minute,
        "rango": rango, "dias": dias,
        "en_curso": en_curso, "siguiente": siguiente, "proximos": proximos,
        "aviso": aviso, "reconectar": sincronizacion.puede_reconectar(),
        "detalles": {e["id"]: detalle(e) for e in eventos if e["id"] in visibles},
    }
