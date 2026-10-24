"""Tests del escaner de secretos (sin tocar la red ni el repo real)."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts import scan_secrets


def _clave(prefix: str, cuerpo: str = "A" * 24) -> str:
    return prefix + cuerpo


def test_detecta_claves_conocidas():
    texto = ("linea normal\n"
             f"key = {_clave('nvapi-')}\n"
             f"key2 = {_clave('sk-')}\n")
    hits = scan_secrets.escanear("ejemplo.py", texto)
    assert {h["familia"] for h in hits} == {"nvidia", "deepseek"}
    assert hits[0]["archivo"] == "ejemplo.py"
    assert hits[0]["linea"] == 2
    assert "AAAA" not in hits[0]["pista"]


def test_no_marca_placeholders_ni_ejemplos_cortos():
    texto = ("nvapi-... (ejemplo en AGENTS.md)\n"
             "sk-corta\n"
             "AQ.Ab8RN6Lpmj\n")
    assert scan_secrets.escanear("AGENTS.md", texto) == []


def test_excluye_el_propio_escaner():
    assert scan_secrets.escanear("scripts/scan_secrets.py",
                                 _clave("nvapi-")) == []


def _repo_con(tmp_path: Path, nombre: str, texto: str) -> Path:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / nombre).write_text(texto, encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", nombre], check=True)
    return tmp_path


def test_main_limpio_devuelve_0(tmp_path, capsys):
    root = _repo_con(tmp_path, "ok.txt", "sin claves\n")
    assert scan_secrets.main(["--root", str(root)]) == 0
    assert "0 coincidencias" in capsys.readouterr().out


def test_main_con_clave_devuelve_1_y_redacta(tmp_path, capsys):
    root = _repo_con(tmp_path, "malo.txt", _clave("nvapi-") + "\n")
    assert scan_secrets.main(["--root", str(root)]) == 1
    salida = capsys.readouterr().out
    assert "SECRETO?" in salida and "AAAA" not in salida


def test_main_sin_git_devuelve_3(tmp_path, capsys):
    with pytest.raises(subprocess.CalledProcessError):
        subprocess.run(["git", "-C", str(tmp_path), "rev-parse"],
                       check=True, capture_output=True)
    assert scan_secrets.main(["--root", str(tmp_path)]) == 3
    assert "ERROR" in capsys.readouterr().err
