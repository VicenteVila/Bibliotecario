#!/usr/bin/env python3
"""Escaneo de secretos en el arbol de trabajo (CI y gate local).

Busca patrones de claves conocidas en los ficheros trackeados por git y
falla con exit 1 si encuentra alguno. Nunca imprime el secreto completo:
solo fichero, linea y una pista redactada.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

PATRONES = {
    "nvidia": re.compile(r"nvapi" + r"-[A-Za-z0-9]{20,}"),
    "deepseek": re.compile(r"sk" + r"-[A-Za-z0-9]{20,}"),
    "google_aq": re.compile(r"AQ" + r"\.[A-Za-z0-9_-]{20,}"),
    "google_aiza": re.compile(r"AIza" + r"[0-9A-Za-z_-]{30,}"),
    "github": re.compile(r"gh[pousr]" + r"_[A-Za-z0-9]{20,}"),
    "slack": re.compile(r"xox" + r"[baprs]-[A-Za-z0-9-]{10,}"),
}
EXCLUIDOS = {"scripts/scan_secrets.py", "tests/test_scan_secrets.py"}


def _redactar(match: re.Match) -> str:
    texto = match.group(0)
    return f"{texto[:6]}...({len(texto)} chars)"


def escanear(nombre: str, texto: str) -> list[dict]:
    if nombre.replace("\\", "/") in EXCLUIDOS:
        return []
    hits = []
    for linea_no, linea in enumerate(texto.splitlines(), start=1):
        for familia, patron in PATRONES.items():
            for m in patron.finditer(linea):
                hits.append({"archivo": nombre, "linea": linea_no,
                             "familia": familia, "pista": _redactar(m)})
    return hits


def _trackeados(root: Path) -> list[str]:
    out = subprocess.run(["git", "-C", str(root), "ls-files", "-z"],
                         capture_output=True, check=True).stdout
    return [p for p in out.decode("utf-8", "replace").split("\0") if p]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Escanea secretos en git ls-files")
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = ap.parse_args(argv)
    root = args.root
    try:
        nombres = _trackeados(root)
    except (OSError, subprocess.CalledProcessError) as e:
        print(f"ERROR: no se pudo listar git ls-files: {e}", file=sys.stderr)
        return 3
    hits: list[dict] = []
    for nombre in nombres:
        p = root / nombre
        if not p.is_file():
            continue
        try:
            texto = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        hits.extend(escanear(nombre, texto))
    if not hits:
        print(f"secretos: 0 coincidencias en {len(nombres)} ficheros trackeados")
        return 0
    for h in hits:
        print(f"SECRETO? {h['archivo']}:{h['linea']} [{h['familia']}] {h['pista']}")
    print(f"secretos: {len(hits)} coincidencias — NO commitear hasta limpiarlas")
    return 1


if __name__ == "__main__":
    sys.exit(main())
