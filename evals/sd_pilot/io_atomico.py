"""Escritura atomica de artefactos de estado y evidencia."""
from __future__ import annotations

import os
from pathlib import Path


def escribir_texto_atomico(path: Path, texto: str) -> None:
    """Escribe `texto` en `path` via fichero temporal + os.replace.

    Un corte a mitad de escritura deja el destino anterior intacto (nunca
    un JSON truncado). El temporal se elimina siempre, tambien si falla.
    """
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(texto)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()
