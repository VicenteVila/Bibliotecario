"""Relojes inyectables: protocolo y reloj manual determinista."""
from __future__ import annotations

from typing import Protocol


class Clock(Protocol):
    """Callable sin argumentos que devuelve el tiempo actual en segundos."""

    def __call__(self) -> float: ...


class ManualClock:
    """Reloj manual: el tiempo solo avanza con `advance`."""

    def __init__(self, start: float = 0.0) -> None:
        if not isinstance(start, (int, float)) or isinstance(start, bool):
            raise TypeError("start must be a number")
        self._now = float(start)

    def __call__(self) -> float:
        return self._now

    def now(self) -> float:
        return self._now

    def advance(self, seconds: float) -> None:
        if not isinstance(seconds, (int, float)) or isinstance(seconds, bool):
            raise TypeError("seconds must be a number")
        self._now += float(seconds)
