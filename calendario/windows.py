"""Integración con Windows: fondo de pantalla, arranque automático y modo imagen."""
import ctypes
import shutil
import sys
from pathlib import Path

from . import config

ES_WINDOWS = sys.platform == "win32"
CLAVE_ARRANQUE = r"Software\Microsoft\Windows\CurrentVersion\Run"
NOMBRE_ARRANQUE = "CalendarioFondo"
SPI_SETDESKWALLPAPER, SPI_GETDESKWALLPAPER = 0x14, 0x73


def marca_fondo():
    return config.DATOS / "fondo_capturado"


def fondo_original():
    return next(iter(sorted(config.DATOS.glob("fondo_original.*"))), None)


def fondo_actual():
    buf = ctypes.create_unicode_buffer(1024)
    ctypes.windll.user32.SystemParametersInfoW(SPI_GETDESKWALLPAPER, 1024, buf, 0)
    return Path(buf.value) if buf.value else None


def poner_fondo(ruta):
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop", 0, winreg.KEY_SET_VALUE) as k:
        winreg.SetValueEx(k, "WallpaperStyle", 0, winreg.REG_SZ, "10")  # rellenar la pantalla
        winreg.SetValueEx(k, "TileWallpaper", 0, winreg.REG_SZ, "0")
    if not ctypes.windll.user32.SystemParametersInfoW(SPI_SETDESKWALLPAPER, 0, str(ruta), 3):
        raise ctypes.WinError()


def es_imagen_propia(p):
    """True si el fondo de Windows es una imagen generada por el modo imagen de esta app."""
    return p is not None and p.name.startswith("escritorio_") and p.parent.resolve() == config.DATOS.resolve()


def capturar_fondo_original():
    """Guarda una vez tu fondo actual, para mostrarlo detrás del calendario y poder restaurarlo."""
    if not ES_WINDOWS or marca_fondo().exists():
        return
    config.DATOS.mkdir(exist_ok=True)
    origen = fondo_actual()
    if es_imagen_propia(origen):
        return
    if not (origen and origen.is_file()):
        origen = Path.home() / "AppData/Roaming/Microsoft/Windows/Themes/TranscodedWallpaper"
    if origen.is_file():
        sufijo = origen.suffix.lower() if origen.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp"} else ".jpg"
        shutil.copyfile(origen, config.DATOS / f"fondo_original{sufijo}")
    marca_fondo().write_text("1")


def restaurar_fondo():
    original = fondo_original()
    if original and ES_WINDOWS:
        poner_fondo(original)
        return True
    return False


def quitar_imagen_propia():
    """Al usar el modo web, vuelve a poner tu fondo si quedó una imagen fija del modo imagen."""
    if ES_WINDOWS and es_imagen_propia(fondo_actual()):
        restaurar_fondo()


def arranque_automatico(activar):
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, CLAVE_ARRANQUE, 0, winreg.KEY_SET_VALUE) as k:
        if activar:
            exe = Path(sys.executable).with_name("pythonw.exe")
            app = config.RAIZ / "app.py"
            winreg.SetValueEx(k, NOMBRE_ARRANQUE, 0, winreg.REG_SZ, f'"{exe}" "{app}"')
        else:
            try:
                winreg.DeleteValue(k, NOMBRE_ARRANQUE)
            except FileNotFoundError:
                pass


# --- Modo imagen: captura de la página como fondo fijo de Windows -------------------------------

def resolucion(cfg):
    if cfg["resolucion"] != "auto":
        return tuple(int(x) for x in cfg["resolucion"].lower().split("x"))
    if not ES_WINDOWS:
        return 1920, 1080
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except OSError:
        ctypes.windll.user32.SetProcessDPIAware()
    return ctypes.windll.user32.GetSystemMetrics(0), ctypes.windll.user32.GetSystemMetrics(1)


def _navegador(playwright):
    for canal in ("msedge", "chrome"):
        try:
            return playwright.chromium.launch(channel=canal)
        except Exception:
            continue
    return playwright.chromium.launch()


_cara = [0]


def pintar_imagen(cfg):
    from playwright.sync_api import sync_playwright
    config.DATOS.mkdir(exist_ok=True)
    _cara[0] ^= 1  # alterna dos archivos: Windows puede no repintar si la ruta no cambia
    destino = config.DATOS / f"escritorio_{_cara[0]}.png"
    ancho, alto = resolucion(cfg)
    with sync_playwright() as p:
        nav = _navegador(p)
        try:
            pagina = nav.new_page(viewport={"width": ancho, "height": alto}, device_scale_factor=1)
            pagina.goto(f"http://127.0.0.1:{cfg['puerto']}/?estatico=1")
            pagina.wait_for_selector("body[data-listo]", timeout=20000, state="attached")
            pagina.screenshot(path=str(destino))
        finally:
            nav.close()
    if ES_WINDOWS:
        poner_fondo(destino)
