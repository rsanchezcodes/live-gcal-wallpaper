"""Crea credentials.json a partir del ID y el secreto de cliente que muestra Google Cloud.

Solo usa la biblioteca estándar: instalar.bat lo ejecuta antes de instalar las dependencias.
"""
import json
import re

from . import config

PLANTILLA = {
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "redirect_uris": ["http://localhost"],
}


def id_valido(texto):
    return re.fullmatch(r"[\w.-]+\.apps\.googleusercontent\.com", texto) is not None


def secreto_valido(texto, id_cliente=""):
    return bool(texto) and " " not in texto and texto != id_cliente


def escribir(id_cliente, secreto, destino=None):
    destino = destino or config.CREDENCIALES
    contenido = {"installed": {"client_id": id_cliente, "client_secret": secreto, **PLANTILLA}}
    destino.write_text(json.dumps(contenido, indent=2), encoding="utf-8")


def preguntar():
    print("\nCopia los dos códigos de Google Cloud > Google Auth Platform > Clientes > tu cliente.")
    print("Para pegar en esta ventana: clic derecho o Ctrl+V.\n")
    while not id_valido(id_cliente := input("ID de cliente (acaba en .apps.googleusercontent.com): ").strip()):
        print("  No parece un ID de cliente. Debe acabar en .apps.googleusercontent.com\n")
    while not secreto_valido(secreto := input("Secreto de cliente (suele empezar por GOCSPX-): ").strip(), id_cliente):
        print("  Ese secreto no parece válido. Cópialo entero, sin espacios.\n")
    escribir(id_cliente, secreto)
    print("\ncredentials.json creado.\n")
