"""Caché con TTL para el catálogo.

IMPLEMENTACIÓN DE PARTIDA: es funcional pero aún no cubre todo el contrato de
la capa de caché (expiración en el borde, orden LRU, invalidación por
prefijo, estadísticas completas...). Completa este módulo sin tocar el resto
del paquete.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any


class CacheTTL:
    def __init__(
        self,
        capacidad: int = 16,
        reloj: Callable[[], float] | None = None,
    ) -> None:
        self._reloj: Callable[[], float] = (
            reloj if reloj is not None else time.monotonic
        )
        self._capacidad = capacidad
        self._datos: dict[str, tuple[Any, float]] = {}
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
        if self._reloj() > expira_en:
            del self._datos[clave]
            self._expiraciones += 1
            self._fallos += 1
            return False, None
        self._aciertos += 1
        return True, valor

    def poner(self, clave: str, valor: Any, ttl: float) -> None:
        self._datos[clave] = (valor, self._reloj() + ttl)
        if len(self._datos) > self._capacidad:
            primera_clave = next(iter(self._datos))
            del self._datos[primera_clave]
            self._evicciones += 1

    def invalidar_prefijo(self, prefijo: str) -> int:
        if prefijo in self._datos:
            del self._datos[prefijo]
            return 1
        return 0

    def estadisticas(self) -> dict[str, int]:
        return {
            "aciertos": self._aciertos,
            "fallos": self._fallos,
            "tamano": len(self._datos),
            "capacidad": self._capacidad,
        }

    def limpiar(self) -> None:
        self._datos.clear()
