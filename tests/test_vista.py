from datetime import datetime

from calendario import demo, sincronizacion, vista

CFG = {"zona_horaria": "Europe/Madrid", "hora_inicio": 8, "hora_fin": 22}
AHORA = datetime(2026, 11, 11, 11, 15)  # miércoles


def ev(id_, ini, fin, **extra):
    return {"id": id_, "titulo": id_, "lugar": "", "descripcion": "", "enlaces": [], "url": "",
            "calendario": "C", "color": "#039be5", "proximos": True, "recurrente": False,
            "todo_dia": False, "ini": ini, "fin": fin, **extra}


def construir(eventos):
    sincronizacion.ESTADO.publicar(eventos, "")
    return vista.construir(CFG, AHORA)


def test_ahora_despues_y_mas_adelante():
    v = construir([
        ev("clase", datetime(2026, 11, 11, 11, 0), datetime(2026, 11, 11, 12, 0)),
        ev("tutoria", datetime(2026, 11, 11, 13, 0), datetime(2026, 11, 11, 14, 0)),
        ev("parcial", datetime(2026, 12, 1, 10, 0), datetime(2026, 12, 1, 12, 0)),
        ev("semanal", datetime(2026, 11, 23, 9, 0), datetime(2026, 11, 23, 10, 0), recurrente=True),
    ])
    assert [e["titulo"] for e in v["en_curso"]] == ["clase"]
    assert v["siguiente"]["titulo"] == "tutoria"
    assert [p["titulo"] for p in v["proximos"]] == ["parcial"]  # lo que se repite no aparece
    assert set(v["detalles"]) == {"clase", "tutoria", "parcial"}


def test_evento_que_cruza_medianoche_y_amplia_horas():
    v = construir([ev("noche", datetime(2026, 11, 13, 23, 30), datetime(2026, 11, 14, 1, 30)),
                   ev("pronto", datetime(2026, 11, 10, 6, 45), datetime(2026, 11, 10, 7, 30))])
    viernes, sabado = v["dias"][4]["eventos"], v["dias"][5]["eventos"]
    assert (viernes[0]["ini"], viernes[0]["fin"]) == (1410, 1440)
    assert (sabado[0]["ini"], sabado[0]["fin"]) == (0, 90)
    assert v["rango"] == [360, 22 * 60]  # empieza a las 6 por el evento de las 6:45


def test_textos_de_fecha():
    e = ev("x", datetime(2026, 11, 13), datetime(2026, 11, 15), todo_dia=True)
    assert vista.describir_cuando(e) == "Del viernes 13 de noviembre al sábado 14 de noviembre"
    e = ev("y", datetime(2026, 11, 11, 10, 45), datetime(2026, 11, 11, 12, 15))
    assert vista.describir_cuando(e) == "Miércoles 11 de noviembre, de 10:45 a 12:15"


def test_la_demo_se_pinta_entera():
    v = construir(demo.eventos(AHORA))
    assert sum(len(d["eventos"]) for d in v["dias"]) == 17
    assert v["dias"][4]["todo_dia"][0]["titulo"] == "Fiesta local"
    assert len(v["proximos"]) == 3
