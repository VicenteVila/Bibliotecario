"""Coalescencia de lotes con ventana temporal (esqueleto inicial)."""
from __future__ import annotations

from collections import deque
from collections.abc import Callable


class BatchCoalescer:
    """Agrupa items en lotes; la ventana la decide el reloj inyectado."""

    def __init__(
        self,
        window: float,
        clock: Callable[[], float],
        max_size: int | None = None,
    ) -> None:
        self._window = float(window)
        self._clock = clock
        self._max_size = max_size
        self._open_items: list[str] = []
        self._open_ts: float | None = None
        self._ready: deque[list[str]] = deque()

    def add(self, item: str, ts: float | None = None) -> None:
        raise NotImplementedError("implementa add")

    def poll(self) -> list[list[str]]:
        raise NotImplementedError("implementa poll")

    def flush(self) -> list[list[str]]:
        raise NotImplementedError("implementa flush")

    @property
    def pending(self) -> int:
        raise NotImplementedError("implementa pending")
