import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from calendario import config, sincronizacion  # noqa: E402


@pytest.fixture(autouse=True)
def carpeta_temporal(tmp_path, monkeypatch):
    """Cada prueba trabaja en su propia carpeta y con un estado limpio."""
    monkeypatch.setattr(config, "DATOS", tmp_path / "datos")
    monkeypatch.setattr(config, "CREDENCIALES", tmp_path / "credentials.json")
    monkeypatch.setattr(config, "RUTA_CONFIG", tmp_path / "config.json")
    monkeypatch.setattr(sincronizacion, "ESTADO", sincronizacion.Estado())
    return tmp_path
