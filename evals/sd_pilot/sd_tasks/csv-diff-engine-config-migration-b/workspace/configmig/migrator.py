"""Detección de formato y migración entre formatos."""
from __future__ import annotations

from pathlib import Path

from .converters import write_ini, write_json
from .errors import UnknownFormatError
from .model import Config
from .readers import read_ini, read_json
from .validator import validate

SUFFIXES: dict[str, str] = {
    ".ini": "ini",
    ".cfg": "ini",
    ".json": "json",
}

READERS = {
    "ini": read_ini,
    "json": read_json,
}

WRITERS = {
    "ini": write_ini,
    "json": write_json,
}


def detect_format(path: str | Path) -> str:
    suffix = Path(path).suffix.lower()
    if suffix not in SUFFIXES:
        raise UnknownFormatError(str(path))
    return SUFFIXES[suffix]


def load(path: str | Path) -> Config:
    """Lee un config desde disco (utf-8) y devuelve el modelo canónico."""
    text = Path(path).read_text(encoding="utf-8")
    fmt = detect_format(path)
    return READERS[fmt](text)


def migrate(src_path: str | Path, dst_format: str = "json") -> str:
    """Carga, valida y serializa el config al formato destino."""
    if dst_format not in WRITERS:
        raise UnknownFormatError(dst_format)
    config = load(src_path)
    validate(config)
    return WRITERS[dst_format](config)
