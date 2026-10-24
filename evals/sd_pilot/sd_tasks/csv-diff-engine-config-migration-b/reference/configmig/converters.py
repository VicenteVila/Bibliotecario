"""Escritores de formatos de configuración."""
from __future__ import annotations

import json

from .model import Config


def _scalar_to_ini(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _scalar_to_toml(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _group(config: Config) -> tuple[list[tuple[str, str]], list[tuple[str, list[tuple[str, str]]]]]:
    bare: list[tuple[str, str]] = []
    sections: dict[str, list[tuple[str, str]]] = {}
    for key in sorted(config.values):
        if "." in key:
            sec, _, rest = key.partition(".")
            sections.setdefault(sec, []).append(
                (rest, _scalar_to_ini(config.values[key]))
            )
        else:
            bare.append((key, _scalar_to_ini(config.values[key])))
    return bare, sorted(sections.items())


def _group_toml(config: Config) -> tuple[list[tuple[str, str]], list[tuple[str, list[tuple[str, str]]]]]:
    bare: list[tuple[str, str]] = []
    sections: dict[str, list[tuple[str, str]]] = {}
    for key in sorted(config.values):
        if "." in key:
            sec, _, rest = key.partition(".")
            sections.setdefault(sec, []).append(
                (rest, _scalar_to_toml(config.values[key]))
            )
        else:
            bare.append((key, _scalar_to_toml(config.values[key])))
    return bare, sorted(sections.items())


def write_ini(config: Config) -> str:
    """Serializa el config como INI (claves ordenadas, secciones ordenadas)."""
    bare, sections = _group(config)
    lines: list[str] = [f"{k} = {v}" for k, v in bare]
    for sec, pairs in sections:
        if lines:
            lines.append("")
        lines.append(f"[{sec}]")
        lines.extend(f"{k} = {v}" for k, v in pairs)
    return "\n".join(lines) + "\n"


def write_toml(config: Config) -> str:
    """Serializa el config como TOML (cadenas entrecomilladas, secciones ordenadas)."""
    bare, sections = _group_toml(config)
    lines: list[str] = [f"{k} = {v}" for k, v in bare]
    for sec, pairs in sections:
        if lines:
            lines.append("")
        lines.append(f"[{sec}]")
        lines.extend(f"{k} = {v}" for k, v in pairs)
    return "\n".join(lines) + "\n"


def write_json(config: Config) -> str:
    """Serializa el config como JSON plano (claves con punto, ordenadas)."""
    return (
        json.dumps(config.values, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    )
