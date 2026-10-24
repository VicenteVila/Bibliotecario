"""Caché con TTL para el catálogo. Implementación de referencia del contrato."""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable
from typing import Any


class CacheTTL:
    def __init__(self, capacidad: int, reloj: Callable[[], float]) -> None:
        if capacidad < 1:
            raise ValueError("capacidad debe ser >= 1")
        self._capacidad = capacidad
        self._reloj = reloj
        self._datos: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._aciertos = 0
        self._fallos = 0
        self._expiraciones = 0
        self._evicciones = 0

    def obtener(self, clave: str) -> tuple[bool, Any]:
        entrada = self._datos.get(clave)
        if entrada is None:
            self._fallos += 1
            return False, None
        valor, expira_en = entrada
        if self._reloj() >= expira_en:
            del self._datos[clave]
            self._expiraciones += 1
            self._fallos += 1
            return False, None
        self._datos.move_to_end(clave)
        self._aciertos += 1
        return True, valor

    def poner(self, clave: str, valor: Any, ttl: float) -> None:
        if ttl <= 0:
            raise ValueError("ttl debe ser > 0")
        self._datos[clave] = (valor, self._reloj() + ttl)
        self._datos.move_to_end(clave)
        while len(self._datos) > self._capacidad:
            self._datos.popitem(last=False)
            self._evicciones += 1

    def invalidar_prefijo(self, prefijo: str) -> int:
        claves = [c for c in self._datos if c.startswith(prefijo)]
        for clave in claves:
            del self._datos[clave]
        return len(claves)

    def estadisticas(self) -> dict[str, int]:
        return {
            "aciertos": self._aciertos,
            "fallos": self._fallos,
            "expiraciones": self._expiraciones,
            "evicciones": self._evicciones,
            "tamano": len(self._datos),
            "capacidad": self._capacidad,
        }

    def limpiar(self) -> None:
        self._datos.clear()
        self._aciertos = 0
        self._fallos = 0
        self._expiraciones = 0
        self._evicciones = 0
