"""Semana inventada para probar la app sin cuenta de Google: python app.py --demo"""
from datetime import datetime, timedelta

from .google_calendar import COLORES_EVENTO

# (día desde el lunes, inicio, fin, título, color de Google, lugar, descripción, se repite)
PLAN = [
    (0, "09:00", "10:30", "Cálculo II", "9", "Aula 1.2", "Tema 4: integrales múltiples.\nTraer la relación 3 hecha.", True),
    (0, "10:45", "12:15", "Programación Orientada a Objetos", "10", "Laboratorio 3", "Práctica de herencia y polimorfismo en Java.", True),
    (0, "16:00", "17:30", "Gimnasio", "2", "", "Pierna y core.", True),
    (1, "08:30", "10:00", "Álgebra Lineal", "3", "Aula 0.4", "Diagonalización. Hay test corto al final de la clase.", True),
    (1, "10:15", "11:45", "Física", "6", "Aula 2.1", "Campo eléctrico y ley de Gauss.", True),
    (1, "18:00", "20:00", "Estudio · Cálculo", "9", "Biblioteca", "Ejercicios 4.1 a 4.12.", True),
    (2, "09:00", "10:30", "Cálculo II", "9", "Aula 1.2", "Tema 4: cambio de variable.", True),
    (2, "11:00", "12:30", "Programación Orientada a Objetos", "10", "Laboratorio 3", "Interfaces y clases abstractas.", True),
    (2, "12:00", "13:00", "Tutoría de Física", "6", "Despacho 2.14", "Llevar las dudas del boletín 5.", False),
    (2, "17:00", "18:30", "Club de lectura", "4", "Biblioteca central", "Comentamos los capítulos 5 a 8.", True),
    (3, "08:30", "10:00", "Álgebra Lineal", "3", "Aula 0.4", "Formas de Jordan.", True),
    (3, "10:15", "11:45", "Física", "6", "Aula 2.1", "Potencial eléctrico.", True),
    (3, "19:30", "21:00", "Cena con amigos", "5", "Centro", "Reserva a las 19:30.", False),
    (4, "09:00", "11:00", "Estudio · Álgebra", "3", "Casa", "Repaso para el parcial.", True),
    (4, "11:30", "12:30", "Entrega práctica 2", "11", "Campus virtual", "Subir el .zip con el código y la memoria en PDF.", False),
    (5, "10:00", "12:00", "Partido de pádel", "2", "Polideportivo", "Pista 4.", True),
    (6, "11:00", "12:30", "Revisión semanal", "8", "", "Repasar la semana y planificar la siguiente.", True),
    (9, "10:00", "12:00", "Parcial de Álgebra Lineal", "11", "Aula magna", "Temas 1 a 4. Se permite calculadora no programable.", False),
    (15, "09:00", "11:00", "Parcial de Cálculo II", "11", "Aula magna", "Temas 3 y 4.", False),
    (19, "23:59", "23:59", "Entrega del proyecto de POO", "10", "Campus virtual", "Repositorio y vídeo de demostración.", False),
]


def eventos(ahora):
    lunes = ahora.date() - timedelta(days=ahora.weekday())
    lista = []
    for i, (d, ini, fin, titulo, color, lugar, descripcion, repite) in enumerate(PLAN):
        dia = lunes + timedelta(days=d)
        lista.append({
            "id": f"demo{i}", "titulo": titulo, "lugar": lugar, "descripcion": descripcion,
            "enlaces": [{"texto": "Campus virtual", "url": "https://example.com/"}] if "Entrega" in titulo else [],
            "url": "", "calendario": "Calendario de ejemplo", "color": COLORES_EVENTO[color],
            "proximos": True, "recurrente": repite, "todo_dia": False,
            "ini": datetime.combine(dia, datetime.strptime(ini, "%H:%M").time()),
            "fin": datetime.combine(dia, datetime.strptime(fin, "%H:%M").time()),
        })
    festivo = lunes + timedelta(days=4)
    lista.append({
        "id": "demo-festivo", "titulo": "Fiesta local", "lugar": "", "descripcion": "No hay clase.",
        "enlaces": [], "url": "", "calendario": "Festivos", "color": "#16a765", "proximos": False,
        "recurrente": False, "todo_dia": True,
        "ini": datetime.combine(festivo, datetime.min.time()),
        "fin": datetime.combine(festivo + timedelta(days=1), datetime.min.time()),
    })
    return lista
